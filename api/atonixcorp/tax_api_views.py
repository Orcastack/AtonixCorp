"""Public tax API façade for compliance, filings, and registry lookups."""

from __future__ import annotations

from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status as drf_status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .enterprise_views import _get_accessible_entity_or_404, _filter_queryset_by_entity_scope
from .models import Entity, TaxAuditLog, TaxCalculation, TaxFiling, TaxProfile, TaxRegimeRegistry
from .serializers import (
    TaxAuditLogSerializer,
    TaxCalculationSerializer,
    TaxFilingSerializer,
    TaxProfileSerializer,
    TaxRegimeRegistrySerializer,
)
from .tax_compliance import build_compliance_alerts, persist_compliance_calendar
from .tax_engine import build_tax_filing, calculate_liability, log_tax_audit, persist_tax_calculation
from .tax_regimes import build_regime_rules, resolve_regime_code
from .tax_security import build_device_metadata, can_manage_global_tax_rules, can_view_partial_tax_audit
from .tax_throttles import TaxApiBurstThrottle, TaxApiWriteThrottle


class TaxRegimeCollectionAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle]

    def get(self, request):
        queryset = TaxRegimeRegistry.objects.all().order_by('jurisdiction_code', 'regime_name')
        country = request.query_params.get('country')
        if country:
            queryset = queryset.filter(country__iexact=country)
        serializer = TaxRegimeRegistrySerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not can_manage_global_tax_rules(request.user):
            return Response({'detail': 'Permission denied.'}, status=drf_status.HTTP_403_FORBIDDEN)
        serializer = TaxRegimeRegistrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED)


class TaxRegimeCountryAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle]

    def get(self, request, country: str):
        built = build_regime_rules(country)
        registry = TaxRegimeRegistry.objects.filter(country__iexact=country)
        registry_data = TaxRegimeRegistrySerializer(registry, many=True).data
        return Response({
            'country': country,
            'jurisdiction_code': built['jurisdiction_code'],
            'regime_codes': built['regime_codes'],
            'rules': built['tax_rules'],
            'registry': registry_data,
        })


class CompanyTaxProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle, TaxApiWriteThrottle]

    def get(self, request, entity_id: int):
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        profiles = TaxProfile.objects.filter(entity=entity).order_by('country')
        serializer = TaxProfileSerializer(profiles, many=True)
        return Response(serializer.data)

    def post(self, request, entity_id: int):
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        payload = request.data.copy()
        payload['entity'] = entity.id
        payload.setdefault('country', entity.country)
        payload.setdefault('jurisdiction_code', entity.country)
        if not payload.get('registered_regimes'):
            payload['registered_regimes'] = build_regime_rules(payload['country']).get('regime_codes', [])
        if not payload.get('tax_rules'):
            payload['tax_rules'] = build_regime_rules(payload['country']).get('tax_rules', {})
        serializer = TaxProfileSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        serializer.save(entity=entity)
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED)


class TaxCalculateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle, TaxApiWriteThrottle]

    def post(self, request):
        entity = _get_accessible_entity_or_404(request.user, request.data.get('entity') or request.data.get('entity_id'))
        requested_regime_code = request.data.get('regime_code') or request.data.get('tax_regime')
        fallback_regimes = build_regime_rules(entity.country).get('regime_codes', [])
        regime_code = resolve_regime_code(requested_regime_code) if requested_regime_code else (fallback_regimes[0] if fallback_regimes else '')
        if not regime_code:
            regime_code = 'corporate_income_tax'
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        tax_year = request.data.get('tax_year')
        calculation_type = request.data.get('calculation_type')
        jurisdiction = request.data.get('jurisdiction') or entity.country
        payload = {
            'taxable_income': request.data.get('taxable_income'),
            'tax_rate': request.data.get('tax_rate'),
            'deductions': request.data.get('deductions') or {},
            'credits': request.data.get('credits') or {},
            'exemptions': request.data.get('exemptions') or {},
            'carryforwards': request.data.get('carryforwards') or {},
            'output_vat': request.data.get('output_vat'),
            'input_vat': request.data.get('input_vat'),
            'taxable_sales': request.data.get('taxable_sales'),
            'employment_income': request.data.get('employment_income'),
            'asset_value': request.data.get('asset_value'),
            'emissions': request.data.get('emissions'),
            'digital_revenue': request.data.get('digital_revenue'),
            'customs_value': request.data.get('customs_value'),
            'estimated_profit': request.data.get('estimated_profit'),
        }

        calculation = persist_tax_calculation(
            entity=entity,
            regime_code=regime_code,
            period_start=period_start,
            period_end=period_end,
            payload=payload,
            tax_year=int(tax_year) if tax_year else None,
            calculation_type=calculation_type,
            jurisdiction=jurisdiction,
            status='draft',
        )

        log_tax_audit(
            entity=entity,
            user=request.user,
            action_type='calculate',
            new_value_json={'tax_calculation_id': str(calculation.id), 'regime_code': calculation.regime_code},
            reason='Tax calculation executed through the public tax API.',
            ip_address=request.META.get('REMOTE_ADDR'),
            device_metadata=build_device_metadata(request),
        )

        return Response(TaxCalculationSerializer(calculation).data, status=drf_status.HTTP_201_CREATED)


class TaxFilingCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle, TaxApiWriteThrottle]

    def post(self, request):
        entity = _get_accessible_entity_or_404(request.user, request.data.get('entity') or request.data.get('entity_id'))
        calculation = get_object_or_404(TaxCalculation, id=request.data.get('calculation_id'), entity=entity)
        filing = build_tax_filing(
            entity=entity,
            calculation=calculation,
            form_type=request.data.get('form_type') or None,
            reference_number=request.data.get('reference_number') or '',
            submission_status=request.data.get('submission_status') or 'draft',
        )
        log_tax_audit(
            entity=entity,
            user=request.user,
            action_type='file',
            new_value_json={'tax_filing_id': str(filing.id), 'submission_status': filing.submission_status},
            reason='Tax filing created through the public tax API.',
            ip_address=request.META.get('REMOTE_ADDR'),
            device_metadata=build_device_metadata(request),
        )
        return Response(TaxFilingSerializer(filing).data, status=drf_status.HTTP_201_CREATED)


class TaxFilingSubmitAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle, TaxApiWriteThrottle]

    def post(self, request):
        filing = get_object_or_404(TaxFiling, id=request.data.get('filing_id'))
        entity = filing.entity
        _get_accessible_entity_or_404(request.user, entity.id)
        filing.submission_status = request.data.get('submission_status') or 'submitted'
        if filing.submission_status == 'submitted' and filing.submitted_at is None:
            filing.submitted_at = request.data.get('submitted_at') or timezone.now()
        if request.data.get('reference_number'):
            filing.reference_number = request.data.get('reference_number')
        filing.save(update_fields=['submission_status', 'submitted_at', 'reference_number', 'updated_at'])
        log_tax_audit(
            entity=entity,
            user=request.user,
            action_type='submit',
            new_value_json={'tax_filing_id': str(filing.id), 'submission_status': filing.submission_status},
            reason='Tax filing submitted through the public tax API.',
            ip_address=request.META.get('REMOTE_ADDR'),
            device_metadata=build_device_metadata(request),
        )
        return Response(TaxFilingSerializer(filing).data)


class TaxComplianceCalendarAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle]

    def get(self, request):
        entity = _get_accessible_entity_or_404(request.user, request.query_params.get('entity') or request.query_params.get('entity_id'))
        horizon_months = int(request.query_params.get('horizon_months') or 12)
        calendar = persist_compliance_calendar(entity, horizon_months=horizon_months)
        return Response({'entity_id': entity.id, 'calendar': calendar})


class TaxComplianceAlertsAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle]

    def get(self, request):
        entity = _get_accessible_entity_or_404(request.user, request.query_params.get('entity') or request.query_params.get('entity_id'))
        window_days = int(request.query_params.get('window_days') or 30)
        alerts = build_compliance_alerts(entity, window_days=window_days)
        return Response({'entity_id': entity.id, 'alerts': alerts})


class TaxAuditAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [TaxApiBurstThrottle]

    def get(self, request):
        entity = _get_accessible_entity_or_404(request.user, request.query_params.get('entity') or request.query_params.get('entity_id'))
        if not can_view_partial_tax_audit(request.user, entity.organization):
            return Response({'detail': 'Permission denied.'}, status=drf_status.HTTP_403_FORBIDDEN)
        queryset = _filter_queryset_by_entity_scope(TaxAuditLog.objects.all(), request.user).filter(entity=entity).order_by('-timestamp')
        serializer = TaxAuditLogSerializer(queryset, many=True)
        return Response(serializer.data)
