from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from io import BytesIO

from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date

from finances.models import Entity
from finances.enterprise_views import _accessible_entities_queryset

from .models import (
    EquityDeliveryLog,
    EquityExerciseRequest,
    EquityExternalAdapterConfig,
    EquityFundingRound,
    EquityGrant,
    EquityHolding,
    EquityOptionPoolReserve,
    EquityPayrollTaxEvent,
    EquityReport,
    EquityScenarioApprovalPolicy,
    EquityScenarioApproval,
    EquityShareCertificate,
    EquityShareClass,
    EquityShareholder,
    EquityTransaction,
    EquityValuation,
    EquityVestingEvent,
    WorkspaceEquityProfile,
)
from .serializers import (
    EquityDeliveryLogSerializer,
    EquityExerciseRequestSerializer,
    EquityExternalAdapterConfigSerializer,
    EquityFundingRoundSerializer,
    EquityGrantSerializer,
    EquityHoldingSerializer,
    EquityOptionPoolReserveSerializer,
    EquityPayrollTaxEventSerializer,
    EquityReportSerializer,
    EquityScenarioApprovalPolicySerializer,
    EquityScenarioApprovalRequestSerializer,
    EquityScenarioApprovalSerializer,
    EquityScenarioDecisionSerializer,
    EquityScenarioInboxSerializer,
    EquityScenarioRequestSerializer,
    EquityScenarioCommitSerializer,
    EquityScenarioReportSerializer,
    EquityShareCertificateSerializer,
    EquityShareClassSerializer,
    EquityShareholderSerializer,
    EquityTransactionSerializer,
    EquityValuationSerializer,
    EquityVestingEventSerializer,
    WorkspaceEquityProfileSerializer,
)
from .automation import notify_grant_issued, sync_exercise_payment, sync_payroll_tax_event, test_external_adapter
from .documents import ensure_certificate_pdf, ensure_grant_package_pdf
from .documents import build_scenario_report_pdf
from .presets import get_provider_presets
from .scenario_services import (
    approve_scenario_for_board,
    approve_scenario_for_legal,
    commit_approved_scenario,
    create_scenario_approval_request,
    create_scenario_report,
    get_scenario_overview,
    get_scenario_approval_inbox,
    get_or_create_scenario_approval_policy,
    reject_scenario_approval,
    run_scenario_approval_sla_sweep,
    simulate_financing_scenario,
)
from .services import (
    apply_acceleration,
    apply_termination,
    approve_exercise_request,
    calculate_grant_summary,
    complete_exercise_request,
    create_exercise_request,
    rebuild_vesting_schedule,
    reject_exercise_request,
    run_vesting_notification_sweep,
)


class WorkspaceScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    workspace_lookup_kwarg = 'workspace_id'

    def get_workspace(self):
        return get_object_or_404(
            _accessible_entities_queryset(self.request.user),
            pk=self.kwargs[self.workspace_lookup_kwarg],
        )

    def get_queryset(self):
        return self.queryset.filter(workspace_id=self.kwargs[self.workspace_lookup_kwarg])

    def perform_create(self, serializer):
        serializer.save(workspace=self.get_workspace(), **self.get_create_kwargs())

    def get_create_kwargs(self):
        return {}

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['workspace'] = self.get_workspace()
        return context


class WorkspaceScopedActionViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    workspace_lookup_kwarg = 'workspace_id'

    def get_workspace(self):
        return get_object_or_404(
            _accessible_entities_queryset(self.request.user),
            pk=self.kwargs[self.workspace_lookup_kwarg],
        )


class WorkspaceEquityProfileViewSet(WorkspaceScopedViewSet):
    serializer_class = WorkspaceEquityProfileSerializer
    queryset = WorkspaceEquityProfile.objects.select_related('workspace')


class EquityShareholderViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityShareholderSerializer
    queryset = EquityShareholder.objects.select_related('workspace', 'created_by')

    def get_create_kwargs(self):
        return {'created_by': self.request.user}


class EquityShareClassViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityShareClassSerializer
    queryset = EquityShareClass.objects.select_related('workspace')


class EquityHoldingViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityHoldingSerializer
    queryset = EquityHolding.objects.select_related('workspace', 'shareholder', 'share_class')


class EquityOptionPoolReserveViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityOptionPoolReserveSerializer
    queryset = EquityOptionPoolReserve.objects.select_related('workspace', 'share_class', 'funding_round')


class EquityScenarioApprovalPolicyViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityScenarioApprovalPolicySerializer
    queryset = EquityScenarioApprovalPolicy.objects.select_related('workspace').prefetch_related(
        'board_reviewers__role',
        'board_reviewers__department',
        'legal_reviewers__role',
        'legal_reviewers__department',
        'board_escalation_reviewers__role',
        'board_escalation_reviewers__department',
        'legal_escalation_reviewers__role',
        'legal_escalation_reviewers__department',
    )

    def list(self, request, workspace_id=None):
        policy = get_or_create_scenario_approval_policy(self.get_workspace())
        return Response([self.get_serializer(policy).data])


class EquityFundingRoundViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityFundingRoundSerializer
    queryset = EquityFundingRound.objects.select_related('workspace', 'share_class')

    def _derived_round_fields(self, validated_data):
        pre_money = validated_data.get('pre_money_valuation') or 0
        amount = validated_data.get('amount_raised') or 0
        price = validated_data.get('price_per_share') or 0
        new_shares = int(amount / price) if price else 0
        return {
            'post_money_valuation': pre_money + amount,
            'new_shares_issued': new_shares,
        }

    def perform_create(self, serializer):
        serializer.save(workspace=self.get_workspace(), **self._derived_round_fields(serializer.validated_data))

    def perform_update(self, serializer):
        serializer.save(**self._derived_round_fields(serializer.validated_data))

    @action(detail=False, methods=['post'])
    def analyze(self, request, workspace_id=None):
        serializer = EquityScenarioRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(simulate_financing_scenario(self.get_workspace(), serializer.validated_data))


class EquityScenarioViewSet(WorkspaceScopedActionViewSet):
    @action(detail=False, methods=['get'])
    def overview(self, request, workspace_id=None):
        return Response(get_scenario_overview(self.get_workspace()))

    def create(self, request, workspace_id=None):
        serializer = EquityScenarioRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(simulate_financing_scenario(self.get_workspace(), serializer.validated_data), status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def commit(self, request, workspace_id=None):
        serializer = EquityScenarioCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        approval_id = serializer.validated_data.get('approval_id')
        if not approval_id:
            raise ValidationError({'approval_id': 'An approved scenario approval request is required before commit.'})
        approval = get_object_or_404(EquityScenarioApproval, pk=approval_id, workspace=self.get_workspace())
        try:
            result = commit_approved_scenario(approval, request.user)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        return Response(result, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def save_report(self, request, workspace_id=None):
        serializer = EquityScenarioReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = create_scenario_report(
            self.get_workspace(),
            serializer.validated_data['scenario'],
            request.user,
            title=serializer.validated_data['title'],
            reporting_period=serializer.validated_data.get('reporting_period', ''),
        )
        return Response(EquityReportSerializer(report).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def export_pdf(self, request, workspace_id=None):
        serializer = EquityScenarioReportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        analysis = simulate_financing_scenario(self.get_workspace(), serializer.validated_data['scenario'])
        pdf_bytes = build_scenario_report_pdf(
            serializer.validated_data['title'],
            f"{self.get_workspace().name} · {serializer.validated_data.get('reporting_period', '') or 'Scenario Report'}",
            analysis,
        )
        return FileResponse(
            BytesIO(pdf_bytes),
            content_type='application/pdf',
            as_attachment=True,
            filename=f"{serializer.validated_data['title'].lower().replace(' ', '-')}.pdf",
        )

    @action(detail=False, methods=['post'])
    def request_approval(self, request, workspace_id=None):
        serializer = EquityScenarioApprovalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            approval = create_scenario_approval_request(
                self.get_workspace(),
                serializer.validated_data['scenario'],
                request.user,
                title=serializer.validated_data['title'],
                reporting_period=serializer.validated_data.get('reporting_period', ''),
            )
        except ValueError as exc:
            details = exc.args[0] if exc.args else {'detail': 'Scenario approval request could not be created.'}
            raise ValidationError(details) from exc
        return Response(EquityScenarioApprovalSerializer(approval).data, status=status.HTTP_201_CREATED)


class EquityScenarioApprovalViewSet(WorkspaceScopedViewSet):
    http_method_names = ['get', 'head', 'options', 'post']
    serializer_class = EquityScenarioApprovalSerializer
    queryset = EquityScenarioApproval.objects.select_related('workspace', 'requested_by', 'board_approved_by', 'legal_approved_by', 'committed_round').prefetch_related('events__actor')

    @action(detail=False, methods=['get'])
    def inbox(self, request, workspace_id=None):
        inbox = get_scenario_approval_inbox(self.get_workspace(), request.user)
        serializer = EquityScenarioInboxSerializer(
            {
                'pending': inbox['pending'],
                'overdue': inbox['overdue'],
                'summary': inbox['summary'],
            },
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def run_sla_sweep(self, request, workspace_id=None):
        return Response(run_scenario_approval_sla_sweep(workspace=self.get_workspace()))

    @action(detail=True, methods=['post'])
    def board_approve(self, request, workspace_id=None, pk=None):
        approval = self.get_object()
        serializer = EquityScenarioDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = approve_scenario_for_board(approval, request.user, serializer.validated_data.get('comments', ''))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=['post'])
    def legal_approve(self, request, workspace_id=None, pk=None):
        approval = self.get_object()
        serializer = EquityScenarioDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            updated = approve_scenario_for_legal(approval, request.user, serializer.validated_data.get('comments', ''))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, workspace_id=None, pk=None):
        approval = self.get_object()
        serializer = EquityScenarioDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reviewer_type = request.data.get('reviewer_type') or 'board'
        if reviewer_type not in {'board', 'legal'}:
            raise ValidationError({'reviewer_type': 'Reviewer type must be board or legal.'})
        try:
            updated = reject_scenario_approval(approval, reviewer_type, request.user, serializer.validated_data.get('comments', ''))
        except PermissionError as exc:
            raise PermissionDenied(str(exc)) from exc
        return Response(self.get_serializer(updated).data)


class EquityValuationViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityValuationSerializer
    queryset = EquityValuation.objects.select_related('workspace')


class EquityTransactionViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityTransactionSerializer
    queryset = EquityTransaction.objects.select_related('workspace', 'shareholder', 'share_class', 'created_by')

    def get_create_kwargs(self):
        return {'created_by': self.request.user}


class EquityReportViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityReportSerializer
    queryset = EquityReport.objects.select_related('workspace', 'generated_by')

    def get_create_kwargs(self):
        return {'generated_by': self.request.user}

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, workspace_id=None, pk=None):
        report = self.get_object()
        payload = report.payload or {}
        analysis = payload.get('analysis', {})
        pdf_bytes = build_scenario_report_pdf(report.title, f'{report.workspace.name} · {report.reporting_period or "Scenario Report"}', analysis)
        return FileResponse(
            BytesIO(pdf_bytes),
            content_type='application/pdf',
            as_attachment=True,
            filename=f'report-{report.id}.pdf',
        )


class EquityGrantViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityGrantSerializer
    queryset = EquityGrant.objects.select_related('workspace', 'shareholder', 'employee', 'share_class', 'created_by')

    def get_create_kwargs(self):
        return {'created_by': self.request.user}

    def perform_create(self, serializer):
        grant = serializer.save(workspace=self.get_workspace(), created_by=self.request.user)
        rebuild_vesting_schedule(grant)
        notify_grant_issued(grant)

    def perform_update(self, serializer):
        grant = serializer.save()
        rebuild_vesting_schedule(grant)

    @action(detail=True, methods=['get'])
    def summary(self, request, workspace_id=None, pk=None):
        grant = self.get_object()
        return Response(calculate_grant_summary(grant))

    @action(detail=True, methods=['post'])
    def rebuild_schedule(self, request, workspace_id=None, pk=None):
        grant = self.get_object()
        events = rebuild_vesting_schedule(grant)
        return Response(EquityVestingEventSerializer(events, many=True).data)

    @action(detail=True, methods=['post'])
    def terminate(self, request, workspace_id=None, pk=None):
        grant = self.get_object()
        termination_date = parse_date(request.data.get('termination_date') or '')
        if not termination_date:
            return Response({'termination_date': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        grant = apply_termination(grant, termination_date)
        return Response(self.get_serializer(grant).data)

    @action(detail=True, methods=['post'])
    def trigger_single(self, request, workspace_id=None, pk=None):
        grant = self.get_object()
        trigger_date = parse_date(request.data.get('trigger_date') or request.data.get('event_date') or '')
        if not trigger_date:
            return Response({'trigger_date': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        event = apply_acceleration(grant, 'single-trigger', trigger_date)
        return Response(EquityVestingEventSerializer(event).data if event else {'detail': 'No acceleration units available.'})

    @action(detail=True, methods=['post'])
    def trigger_double(self, request, workspace_id=None, pk=None):
        grant = self.get_object()
        trigger_date = parse_date(request.data.get('trigger_date') or request.data.get('event_date') or '')
        if not trigger_date:
            return Response({'trigger_date': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)
        event = apply_acceleration(grant, 'double-trigger', trigger_date)
        return Response(EquityVestingEventSerializer(event).data if event else {'detail': 'No acceleration units available.'})

    @action(detail=True, methods=['get'])
    def download_package(self, request, workspace_id=None, pk=None):
        grant = ensure_grant_package_pdf(self.get_object())
        return FileResponse(
            grant.grant_package_file.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=f'grant-package-{grant.grant_number}.pdf',
        )

    @action(detail=True, methods=['post'])
    def regenerate_package(self, request, workspace_id=None, pk=None):
        grant = ensure_grant_package_pdf(self.get_object(), force=True)
        return Response(self.get_serializer(grant).data)


class EquityVestingEventViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityVestingEventSerializer
    queryset = EquityVestingEvent.objects.select_related('workspace', 'grant')


class EquityExerciseRequestViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityExerciseRequestSerializer
    queryset = EquityExerciseRequest.objects.select_related(
        'workspace', 'grant', 'shareholder', 'tax_calculation', 'journal_entry', 'created_by'
    ).prefetch_related('approvals')

    def perform_create(self, serializer):
        grant = get_object_or_404(EquityGrant, pk=self.request.data.get('grant'), workspace=self.get_workspace())
        try:
            exercise_request = create_exercise_request(
                grant=grant,
                requested_units=int(self.request.data.get('requested_units') or 0),
                payment_method=self.request.data.get('payment_method') or 'bank_transfer',
                created_by=self.request.user,
                notes=self.request.data.get('notes', ''),
            )
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        serializer.instance = exercise_request

    @action(detail=True, methods=['post'])
    def approve(self, request, workspace_id=None, pk=None):
        exercise_request = self.get_object()
        try:
            updated = approve_exercise_request(exercise_request, request.user, request.data.get('comments', ''))
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, workspace_id=None, pk=None):
        exercise_request = self.get_object()
        try:
            updated = reject_exercise_request(exercise_request, request.user, request.data.get('comments', ''))
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, workspace_id=None, pk=None):
        exercise_request = self.get_object()
        exercise_request.payment_status = request.data.get('payment_status') or 'paid'
        exercise_request.save(update_fields=['payment_status', 'updated_at'])
        return Response(self.get_serializer(exercise_request).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, workspace_id=None, pk=None):
        exercise_request = self.get_object()
        try:
            updated = complete_exercise_request(exercise_request, request.user)
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        return Response(self.get_serializer(updated).data)

    @action(detail=True, methods=['post'])
    def sync_payment(self, request, workspace_id=None, pk=None):
        exercise_request = self.get_object()
        result = sync_exercise_payment(exercise_request)
        exercise_request.refresh_from_db()
        return Response({'exercise_request': self.get_serializer(exercise_request).data, 'sync_result': result})


class EquityShareCertificateViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityShareCertificateSerializer
    queryset = EquityShareCertificate.objects.select_related('workspace', 'exercise_request', 'grant', 'issued_to', 'share_class', 'issued_by')

    @action(detail=True, methods=['get'])
    def download_pdf(self, request, workspace_id=None, pk=None):
        certificate = ensure_certificate_pdf(self.get_object())
        return FileResponse(
            certificate.pdf_file.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=f'certificate-{certificate.certificate_number}.pdf',
        )

    @action(detail=True, methods=['post'])
    def regenerate_pdf(self, request, workspace_id=None, pk=None):
        certificate = ensure_certificate_pdf(self.get_object(), force=True)
        return Response(self.get_serializer(certificate).data)


class EquityPayrollTaxEventViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityPayrollTaxEventSerializer
    queryset = EquityPayrollTaxEvent.objects.select_related(
        'workspace', 'grant', 'exercise_request', 'staff', 'source_account', 'destination_account'
    )

    @action(detail=True, methods=['post'])
    def sync(self, request, workspace_id=None, pk=None):
        payroll_tax_event = self.get_object()
        result = sync_payroll_tax_event(payroll_tax_event)
        payroll_tax_event.refresh_from_db()
        return Response({'payroll_tax_event': self.get_serializer(payroll_tax_event).data, 'sync_result': result})


class EquityExternalAdapterConfigViewSet(WorkspaceScopedViewSet):
    serializer_class = EquityExternalAdapterConfigSerializer
    queryset = EquityExternalAdapterConfig.objects.select_related('workspace', 'created_by')

    def get_create_kwargs(self):
        return {'created_by': self.request.user}

    @action(detail=True, methods=['post'])
    def test_connection(self, request, workspace_id=None, pk=None):
        config = self.get_object()
        result = test_external_adapter(config)
        config.refresh_from_db()
        return Response({'adapter': self.get_serializer(config).data, 'result': result})

    @action(detail=False, methods=['get'])
    def presets(self, request, workspace_id=None):
        adapter_type = request.query_params.get('adapter_type')
        return Response(get_provider_presets(adapter_type))


class EquityDeliveryLogViewSet(WorkspaceScopedViewSet):
    http_method_names = ['get', 'head', 'options']
    serializer_class = EquityDeliveryLogSerializer
    queryset = EquityDeliveryLog.objects.select_related(
        'workspace', 'grant', 'vesting_event', 'exercise_request', 'certificate', 'payroll_tax_event', 'recipient_user'
    )

    @action(detail=True, methods=['get'])
    def download_document(self, request, workspace_id=None, pk=None):
        delivery_log = self.get_object()
        if not delivery_log.document_file:
            return Response({'detail': 'No document is attached to this delivery log.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            delivery_log.document_file.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=delivery_log.document_file.name.split('/')[-1],
        )


class EquitySelfServiceViewSet(WorkspaceScopedActionViewSet):
    def _get_employee_profile(self):
        return self.get_workspace().staff.select_related('user', 'manager__user').filter(user=self.request.user).first()

    def _get_grants_queryset(self):
        workspace = self.get_workspace()
        employee = self._get_employee_profile()
        queryset = EquityGrant.objects.select_related('workspace', 'shareholder', 'employee', 'share_class')
        if employee:
            return queryset.filter(workspace=workspace, employee=employee)
        return queryset.filter(workspace=workspace, shareholder__email__iexact=self.request.user.email)

    @action(detail=False, methods=['get'])
    def dashboard(self, request, workspace_id=None):
        workspace = self.get_workspace()
        employee = self._get_employee_profile()
        grants = self._get_grants_queryset()
        grant_ids = grants.values_list('id', flat=True)
        exercise_requests = EquityExerciseRequest.objects.filter(workspace=workspace, grant_id__in=grant_ids).select_related(
            'workspace', 'grant', 'shareholder', 'tax_calculation', 'journal_entry', 'created_by'
        ).prefetch_related('approvals')
        vesting_events = EquityVestingEvent.objects.filter(workspace=workspace, grant_id__in=grant_ids).select_related('grant')
        certificates = EquityShareCertificate.objects.filter(workspace=workspace, grant_id__in=grant_ids).select_related(
            'workspace', 'exercise_request', 'grant', 'issued_to', 'share_class', 'issued_by'
        )
        delivery_logs = EquityDeliveryLog.objects.filter(
            workspace=workspace,
        ).filter(
            Q(recipient_user=request.user) |
            Q(recipient_email__iexact=request.user.email) |
            Q(grant_id__in=grant_ids) |
            Q(exercise_request__grant_id__in=grant_ids) |
            Q(certificate__grant_id__in=grant_ids)
        ).select_related('grant', 'vesting_event', 'exercise_request', 'certificate', 'recipient_user')

        employee_payload = None
        if employee:
            employee_payload = {
                'id': employee.id,
                'employee_id': employee.employee_id,
                'full_name': employee.full_name,
                'email': employee.email,
                'status': employee.status,
                'hire_date': employee.hire_date,
                'manager_name': employee.manager.full_name if employee.manager_id else '',
            }

        return Response({
            'employee': employee_payload,
            'grants': EquityGrantSerializer(grants, many=True).data,
            'vesting_events': EquityVestingEventSerializer(vesting_events, many=True).data,
            'exercise_requests': EquityExerciseRequestSerializer(exercise_requests, many=True).data,
            'certificates': EquityShareCertificateSerializer(certificates, many=True).data,
            'delivery_logs': EquityDeliveryLogSerializer(delivery_logs, many=True).data,
        })

    @action(detail=False, methods=['post'])
    def submit_exercise(self, request, workspace_id=None):
        grant = get_object_or_404(self._get_grants_queryset(), pk=request.data.get('grant'))
        try:
            exercise_request = create_exercise_request(
                grant=grant,
                requested_units=int(request.data.get('requested_units') or 0),
                payment_method=request.data.get('payment_method') or 'bank_transfer',
                created_by=request.user,
                notes=request.data.get('notes', ''),
            )
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)}) from exc
        return Response(EquityExerciseRequestSerializer(exercise_request).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def run_vesting_sweep(self, request, workspace_id=None):
        result = run_vesting_notification_sweep()
        return Response(result)
