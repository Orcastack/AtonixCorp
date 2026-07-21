import hashlib
import yaml
import os
import tempfile
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.contrib.auth.models import User
from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from decimal import Decimal
from .enterprise_reporting import _next_run_at
from .platform_tasks import create_task as create_platform_task_record
from .models import (
    APIKey,
    AuditLog,
    AutomationArtifact,
    BankAccount,
    BankingConsentLog,
    BankingIntegration,
    BankingTransaction,
    AutomationWorkflow,
    Budget,
    CashflowForecast,
    ChartOfAccounts,
    ComplianceDeadline,
    ComplianceDocument,
    GovernanceCommissionEntry,
    Customer,
    Consolidation,
    ConsolidationEntity,
    DeveloperAPI,
    DeveloperAPIEndpoint,
    DeveloperPortalAPILog,
    DeveloperPortalKeyRequest,
    Entity,
    EntityDepartment,
    EntityRole,
    EntityStaff,
    Expense,
    GeneralLedger,
    Income,
    Invoice,
    IntercompanyEliminationEntry,
    IntercompanyTransaction,
    JournalEntry,
    LedgerPeriod,
    Notification,
    NotificationPreference,
    OAuthApplication,
    PlatformAuditEvent,
    PlatformTask,
    Permission,
    BookkeepingAccount,
    BookkeepingCategory,
    PayrollBankPaymentFile,
    PayrollBankOriginatorProfile,
    PayrollComponent,
    PayrollRun,
    PayrollStatutoryReport,
    Payslip,
    RateLimitProfile,
    Role,
    ROLE_COMPLIANCE_OFFICER,
    Organization,
    OrganizationEmailAccount,
    OrganizationEmailCampaign,
    OrganizationEmailDelivery,
    OrganizationEmailSubscription,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    StaffPayrollComponentAssignment,
    StaffPayrollProfile,
    SystemEvent,
    TeamMember,
    TaxCalculation,
    TaxAuditLog,
    TaxExposure,
    TaxProfile,
    TaxRegimeRegistry,
    TaxRiskAlert,
    TaxRuleSetVersion,
    Transaction,
    UserProfile,
    Vendor,
    WebhookDelivery,
    Bill,
    Payment,
    AccountingApprovalRecord,
    AccountingApprovalMatrix,
    AccountingApprovalDelegation,
    EmailVerificationToken,
    IdentityVerification,
)
from .tax_regimes import build_regime_rules, resolve_regime_code
from .tax_engine import calculate_liability
from .tax_compliance import build_compliance_calendar, build_compliance_alerts
from .tax_security import detect_tax_risks
from .serializers import EntitySerializer, TaxProfileSerializer, TaxAuditLogSerializer
from workspaces.models import Workspace, WorkspaceGroup, WorkspaceMember
from workspaces.services import LogService, WorkspaceService


class ExpenseModelTest(TestCase):
    def test_create_expense(self):
        expense = Expense.objects.create(
            description="Test Expense",
            amount=Decimal("50.00"),
            category="Food",
            date=timezone.now().date()
        )
        self.assertEqual(expense.description, "Test Expense")
        self.assertEqual(expense.amount, Decimal("50.00"))


class IncomeModelTest(TestCase):
    def test_create_income(self):
        income = Income.objects.create(
            source="Test Income",
            amount=Decimal("1000.00"),
            date=timezone.now().date()
        )
        self.assertEqual(income.source, "Test Income")
        self.assertEqual(income.amount, Decimal("1000.00"))


class BudgetModelTest(TestCase):
    def test_create_budget(self):
        budget = Budget.objects.create(
            category="Food",
            limit=Decimal("500.00"),
            spent=Decimal("200.00")
        )
        self.assertEqual(budget.remaining, Decimal("300.00"))
        self.assertEqual(budget.percentage_used, 40.0)


class TaxRegimeModelTest(TestCase):
    def test_worldwide_regime_defaults_are_country_aware(self):
        defaults = build_regime_rules('United States')

        self.assertEqual(defaults['jurisdiction_code'], 'US')
        self.assertIn('sales_tax', defaults['regime_codes'])
        self.assertEqual(defaults['active_regimes'][0]['regime_code'], 'corporate_income_tax')

    def test_manual_regime_code_alias_resolves_to_family(self):
        defaults = build_regime_rules('United Kingdom', regime_codes=['UK_VAT', 'CT600'])

        self.assertEqual(defaults['jurisdiction_code'], 'GB')
        self.assertEqual(defaults['regime_codes'], ['vat', 'corporate_income_tax'])
        self.assertIn('vat_return', defaults['required_forms'])
        self.assertIn('corporate_return', defaults['required_forms'])

    def test_registry_record_can_be_created(self):
        regime = TaxRegimeRegistry.objects.create(
            jurisdiction_code='US',
            country='United States',
            regime_code='sales_tax_ca',
            regime_name='California Sales Tax',
            tax_type='sales_tax',
            regime_category='vat',
            filing_frequency='monthly',
            filing_form='sales_tax_return',
            required_forms=['sales_tax_return'],
            calculation_method='point_of_sale',
            penalty_rules={'late_filing': 'jurisdiction_defined'},
            rule_set={'basis': 'sale_transaction'},
        )

        self.assertEqual(regime.jurisdiction_code, 'US')
        self.assertTrue(regime.is_active)


class TaxProfileModelTest(TestCase):
    def test_profile_tracks_jurisdiction_and_regimes(self):
        user = User.objects.create_user(username='tax-user', password='password123')
        organization = Organization.objects.create(name='Tax Org', slug='tax-org', owner=user, primary_country='United Kingdom')
        entity = Entity.objects.create(
            organization=organization,
            name='Global Entity',
            country='United Kingdom',
            local_currency='GBP',
            entity_type='corporation',
        )

        profile = TaxProfile.objects.create(
            entity=entity,
            country='United Kingdom',
            jurisdiction_code='GB',
            effective_from=timezone.now().date(),
            tax_rules={'jurisdiction_code': 'GB'},
            registered_regimes=['corporate_income_tax', 'vat'],
            registration_numbers={'vat': 'GB123456789'},
            filing_preferences={'primary_frequency': 'quarterly'},
        )

        self.assertEqual(profile.resolved_jurisdiction_code, 'GB')
        self.assertEqual(profile.active_regime_codes, ['corporate_income_tax', 'vat'])


class TaxSecurityModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='security-user', password='password123')
        self.organization = Organization.objects.create(name='Security Org', slug='security-org', owner=self.user, primary_country='United States')
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Security Entity',
            country='United States',
            local_currency='USD',
            entity_type='corporation',
            registration_number='US-123456789',
        )

    def test_entity_serializer_masks_registration_number(self):
        data = EntitySerializer(self.entity).data

        self.assertNotEqual(data['registration_number'], 'US-123456789')
        self.assertTrue(data['registration_number'].endswith('6789'))

    def test_tax_profile_serializer_masks_registration_numbers(self):
        profile = TaxProfile.objects.create(
            entity=self.entity,
            country='United States',
            jurisdiction_code='US',
            registered_regimes=['corporate_income_tax'],
            tax_rules={'jurisdiction_code': 'US'},
            registration_numbers={'federal': 'US-123456789'},
        )

        data = TaxProfileSerializer(profile).data

        self.assertNotEqual(data['registration_numbers']['federal'], 'US-123456789')
        self.assertTrue(data['registration_numbers']['federal'].endswith('6789'))

    def test_tax_audit_log_hash_chain_is_populated(self):
        first = TaxAuditLog.objects.create(
            entity=self.entity,
            user=self.user,
            action_type='calculate',
            old_value_json={'tax_base': '1000.00'},
            new_value_json={'tax_base': '1100.00'},
            reason='Initial calculation',
            country='United States',
        )
        second = TaxAuditLog.objects.create(
            entity=self.entity,
            user=self.user,
            action_type='submit',
            old_value_json={'filing': 'draft'},
            new_value_json={'filing': 'submitted'},
            reason='Submission',
            country='United States',
        )

        self.assertTrue(first.event_hash)
        self.assertTrue(second.event_hash)
        self.assertEqual(second.previous_hash, first.event_hash)

    def test_detect_tax_risks_creates_alert_for_large_tax_base_change(self):
        alerts = detect_tax_risks(
            entity=self.entity,
            action_type='calculate',
            old_value={'tax_base': '1000.00'},
            new_value={'tax_base': '2500.00'},
            source_model='TaxCalculation',
            source_id='calc-1',
            persist=True,
        )

        self.assertTrue(alerts)
        self.assertTrue(TaxRiskAlert.objects.filter(entity=self.entity, alert_type='manipulated_tax_base').exists())

    def test_rule_set_version_can_be_created(self):
        registry = TaxRegimeRegistry.objects.create(
            jurisdiction_code='US',
            country='United States',
            regime_code='vat',
            regime_name='Value Added Tax',
            tax_type='vat',
            regime_category='vat',
            filing_frequency='monthly',
            filing_form='vat_return',
            required_forms=['vat_return'],
            calculation_method='invoice_offset',
        )
        version = TaxRuleSetVersion.objects.create(
            registry=registry,
            version_number='2026.1',
            effective_from=timezone.now().date(),
            change_log=[{'field': 'due_day', 'before': 20, 'after': 25}],
            approval_status='approved',
            approved_by=self.user,
            created_by=self.user,
        )

        self.assertEqual(version.version_number, '2026.1')
        self.assertEqual(version.approval_status, 'approved')

    def test_tax_audit_serializer_masks_for_non_privileged_user(self):
        viewer = User.objects.create_user(username='viewer-user', password='password123')
        Role.get_or_create_default_roles()
        viewer_role = Role.objects.get(code='VIEWER')
        TeamMember.objects.create(organization=self.organization, user=viewer, role=viewer_role, is_active=True)

        audit_log = TaxAuditLog.objects.create(
            entity=self.entity,
            user=self.user,
            action_type='calculate',
            old_value_json={'tax_id': 'US-111122223'},
            new_value_json={'tax_id': 'US-999988887'},
            reason='Masking test',
            country='United States',
            device_metadata={'user_agent': 'pytest'},
        )

        serializer = TaxAuditLogSerializer(audit_log, context={'request': SimpleNamespace(user=viewer)})
        data = serializer.data

        self.assertEqual(data['device_metadata'], {})
        self.assertEqual(data['ip_address'], '')
        self.assertNotEqual(data['new_value_json']['tax_id'], 'US-999988887')

    def test_default_roles_include_compliance_officer(self):
        roles = Role.get_or_create_default_roles()

        self.assertIn(ROLE_COMPLIANCE_OFFICER, roles)

    def test_global_tax_registry_write_requires_governance_role(self):
        viewer = User.objects.create_user(username='registry-viewer', password='password123')
        Role.get_or_create_default_roles()
        viewer_role = Role.objects.get(code='VIEWER')
        TeamMember.objects.create(organization=self.organization, user=viewer, role=viewer_role, is_active=True)

        client = APIClient()
        client.force_authenticate(user=viewer)

        response = client.post(
            '/api/tax/regimes',
            {
                'jurisdiction_code': 'US',
                'country': 'United States',
                'regime_code': 'vat',
                'regime_name': 'Value Added Tax',
                'tax_type': 'vat',
                'regime_category': 'vat',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 403)


class TaxCalculationModelTest(TestCase):
    def test_calculation_can_store_regime_metadata(self):
        user = User.objects.create_user(username='calc-user', password='password123')
        organization = Organization.objects.create(name='Calc Org', slug='calc-org', owner=user, primary_country='South Africa')
        entity = Entity.objects.create(
            organization=organization,
            name='Calc Entity',
            country='South Africa',
            local_currency='ZAR',
            entity_type='corporation',
        )

        calculation = TaxCalculation.objects.create(
            entity=entity,
            tax_year=2025,
            calculation_type='corporate',
            jurisdiction='South Africa',
            regime_code='corporate_income_tax',
            regime_name='Corporate Income Tax',
            taxable_income=Decimal('1000.00'),
            tax_rate=Decimal('0.3000'),
            deductions={'allowance': '100.00'},
            credits={'credit': '25.00'},
            calculated_tax=Decimal('245.00'),
            effective_rate=Decimal('0.2450'),
            calculation_json={'line_items': {'taxable_base': '1000.00'}},
            liability_amount=Decimal('245.00'),
            status='final',
            breakdown={'regime_code': 'corporate_income_tax'},
        )

        self.assertEqual(calculation.regime_code, 'corporate_income_tax')
        self.assertEqual(calculation.regime_name, 'Corporate Income Tax')
        self.assertEqual(calculation.status, 'final')
        self.assertEqual(calculation.liability_amount, Decimal('245.00'))


class TaxCalculationApiTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tax-api-user', password='password123')
        self.organization = Organization.objects.create(
            name='Tax API Org',
            slug='tax-api-org',
            owner=self.user,
            primary_country='United States',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Tax API Entity',
            country='United States',
            local_currency='USD',
            entity_type='corporation',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_calculate_uses_worldwide_regime_defaults(self):
        response = self.client.post(
            '/api/tax-calculations/calculate/',
            {
                'entity_id': self.entity.id,
                'tax_year': 2025,
                'calculation_type': 'corporate',
                'taxable_income': '1000.00',
                'tax_rate': '30',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['jurisdiction'], 'United States')
        self.assertEqual(response.data['regime_code'], 'corporate_income_tax')
        self.assertEqual(response.data['breakdown']['jurisdiction_code'], 'US')
        self.assertIn('filing_output', response.data['calculation_json'])
        self.assertEqual(response.data['liability_amount'], '300.00')

    def test_calculate_accepts_manual_regime_alias(self):
        response = self.client.post(
            '/api/tax-calculations/calculate/',
            {
                'entity_id': self.entity.id,
                'tax_year': 2025,
                'calculation_type': 'vat',
                'tax_regime': 'US_FED_CIT',
                'taxable_income': '1500.00',
                'tax_rate': '21',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['regime_code'], 'corporate_income_tax')
        self.assertEqual(response.data['breakdown']['required_forms'], ['corporate_return'])

    def test_generate_filing_creates_submission_payload(self):
        calculation = TaxCalculation.objects.create(
            entity=self.entity,
            tax_year=2025,
            calculation_type='corporate',
            jurisdiction='United States',
            regime_code='corporate_income_tax',
            regime_name='Corporate Income Tax',
            period_start=timezone.now().date().replace(month=1, day=1),
            period_end=timezone.now().date().replace(month=12, day=31),
            taxable_income=Decimal('1000.00'),
            tax_rate=Decimal('0.2100'),
            deductions={'business_expenses': '0'},
            credits={},
            calculated_tax=Decimal('210.00'),
            effective_rate=Decimal('0.2100'),
            calculation_json={'filing_output': {'form_type': 'corporate_return'}},
            liability_amount=Decimal('210.00'),
            status='final',
            breakdown={'taxable_base': '1000.00'},
        )

        response = self.client.post(
            f'/api/tax-calculations/{calculation.id}/generate_filing/',
            {
                'reference_number': 'FILING-2025-001',
                'submission_status': 'ready',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['form_type'], 'corporate_return')
        self.assertEqual(response.data['submission_status'], 'ready')

    def test_public_tax_api_routes_generate_compliance_calendar(self):
        TaxRegimeRegistry.objects.create(
            jurisdiction_code='US',
            country='United States',
            regime_code='vat',
            regime_name='Value Added Tax',
            tax_type='vat',
            regime_category='vat',
            filing_frequency='monthly',
            filing_form='vat_return',
            required_forms=['vat_return'],
            calculation_method='invoice_offset',
            compliance_rules_json={'filing_frequency': 'monthly', 'due_day': 25, 'grace_period_days': 5},
            rules_json={'compliance_rules': {'filing_frequency': 'monthly', 'due_day': 25, 'grace_period_days': 5}},
            forms_json=['vat_return'],
        )
        TaxProfile.objects.create(
            entity=self.entity,
            country='United States',
            jurisdiction_code='US',
            registered_regimes=['vat'],
            tax_rules={'regime_codes': ['vat']},
        )

        response = self.client.get(f'/api/tax/compliance/calendar?entity_id={self.entity.id}&horizon_months=1')

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['calendar']), 1)
        self.assertEqual(response.data['calendar'][0]['regime_code'], 'vat')

    def test_public_tax_api_routes_support_calculation_and_filing_submission(self):
        calc_response = self.client.post(
            '/api/tax/calculate',
            {
                'entity_id': self.entity.id,
                'tax_year': 2025,
                'calculation_type': 'corporate',
                'tax_regime': 'US_FED_CIT',
                'taxable_income': '1000.00',
                'tax_rate': '30',
            },
            format='json',
        )

        self.assertEqual(calc_response.status_code, 201)
        self.assertEqual(calc_response.data['regime_code'], 'corporate_income_tax')

        filing_response = self.client.post(
            '/api/tax/filings/create',
            {
                'entity_id': self.entity.id,
                'calculation_id': calc_response.data['id'],
                'submission_status': 'draft',
            },
            format='json',
        )

        self.assertEqual(filing_response.status_code, 201)
        self.assertEqual(filing_response.data['submission_status'], 'draft')

        submit_response = self.client.post(
            '/api/tax/filings/submit',
            {
                'filing_id': filing_response.data['id'],
                'submission_status': 'submitted',
                'reference_number': 'SUB-001',
            },
            format='json',
        )

        self.assertEqual(submit_response.status_code, 200)
        self.assertEqual(submit_response.data['submission_status'], 'submitted')


class PlatformIntegrationViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_health_endpoint_is_public(self):
        response = self.client.get('/api/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ok')
        self.assertEqual(response.data['checks']['database'], 'ok')

    @override_settings(PLATFORM_EVENT_TOKEN='test-platform-token')
    def test_platform_event_requires_token(self):
        response = self.client.post(
            '/api/platform/events/',
            {'event_type': 'deployment', 'source': 'bitbucket', 'environment': 'dev', 'status': 'succeeded'},
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['error']['code'], 'UNAUTHORIZED')

    @override_settings(PLATFORM_EVENT_TOKEN='test-platform-token')
    def test_platform_event_accepts_valid_payload(self):
        response = self.client.post(
            '/api/platform/events/',
            {
                'event_type': 'deployment',
                'source': 'bitbucket',
                'environment': 'dev',
                'status': 'succeeded',
                'service': 'backend',
            },
            format='json',
            HTTP_AUTHORIZATION='Bearer test-platform-token',
        )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.data['accepted'])


class DeveloperPortalViewTests(TestCase):
    def setUp(self):
        self.client = APIClient(HTTP_HOST='localhost')

    def test_root_landing_page_renders_nasa_style_public_portal(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('AtonixCorp APIs', content)
        self.assertIn('Request API key', content)
        self.assertIn('Search APIs', content)
        self.assertIn('branding/atc-logo-round.svg', content)
        self.assertIn('rel="icon"', content)

    def test_favicon_compatibility_route_redirects_to_atonixcorp_mark(self):
        response = self.client.get('/favicon.ico')

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/static/branding/atc-logo-round.svg')

    def test_api_catalog_list_returns_seeded_results(self):
        response = self.client.get('/developer/apis')

        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data['results']), 1)
        self.assertIn('available_filters', response.data)
        self.assertTrue(any(item['slug'] == 'markets' for item in response.data['available_filters']['categories']))
        self.assertTrue(response.data['results'][0]['rate_limit_profile'])

    def test_api_search_requires_query(self):
        response = self.client.get('/developer/search')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'INVALID_REQUEST')
        self.assertEqual(response.data['error']['details']['field'], 'q')

    def test_api_search_returns_matching_seeded_entry(self):
        response = self.client.get('/developer/search', {'q': 'market'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['query'], 'market')
        self.assertTrue(any(item['slug'] == 'market-data-api' for item in response.data['results']))

    def test_api_detail_returns_seeded_endpoints(self):
        response = self.client.get('/developer/apis/market-data-api')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['slug'], 'market-data-api')
        self.assertTrue(response.data['versions'])
        self.assertTrue(response.data['endpoints'])

    def test_public_api_aliases_return_catalog_detail_and_endpoint_data(self):
        api_response = self.client.get('/apis')
        detail_response = self.client.get('/apis/market-data-api')
        endpoint_list_response = self.client.get('/apis/market-data-api/endpoints')

        self.assertEqual(api_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(endpoint_list_response.status_code, 200)
        self.assertEqual(detail_response.data['slug'], 'market-data-api')
        self.assertTrue(endpoint_list_response.data['endpoints'])

        endpoint_id = endpoint_list_response.data['endpoints'][0]['id']
        endpoint_detail_response = self.client.get(f'/apis/market-data-api/endpoints/{endpoint_id}')
        self.assertEqual(endpoint_detail_response.status_code, 200)
        self.assertEqual(endpoint_detail_response.data['api']['slug'], 'market-data-api')
        self.assertEqual(endpoint_detail_response.data['endpoint']['id'], endpoint_id)

        self.assertGreaterEqual(DeveloperPortalAPILog.objects.filter(path='/apis').count(), 1)
        self.assertGreaterEqual(DeveloperPortalAPILog.objects.filter(path='/apis/market-data-api').count(), 1)
        endpoint_log = DeveloperPortalAPILog.objects.filter(path=f'/apis/market-data-api/endpoints/{endpoint_id}').first()
        self.assertIsNotNone(endpoint_log)
        self.assertEqual(endpoint_log.endpoint_id, endpoint_id)

    def test_docs_aliases_return_catalog_documents(self):
        list_response = self.client.get('/docs/apis')
        detail_response = self.client.get('/docs/apis/market-data-api')

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)
        self.assertTrue(any(item['slug'] == 'market-data-api' for item in list_response.data['results']))
        self.assertEqual(detail_response.data['slug'], 'market-data-api')

    def test_api_detail_returns_standard_not_found_error(self):
        response = self.client.get('/developer/apis/does-not-exist')

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['error']['code'], 'NOT_FOUND')

    def test_docs_and_status_endpoints_are_public(self):
        auth_response = self.client.get('/developer/docs/authentication')
        errors_response = self.client.get('/developer/docs/errors')
        status_response = self.client.get('/developer/status')
        public_status_response = self.client.get('/status')

        self.assertEqual(auth_response.status_code, 200)
        self.assertEqual(auth_response.data['slug'], 'authentication')
        self.assertEqual(errors_response.status_code, 200)
        self.assertEqual(errors_response.data['slug'], 'errors')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.data['service'], 'developer-portal')
        self.assertIn('uptime_seconds', status_response.data)
        self.assertEqual(public_status_response.status_code, 200)
        self.assertEqual(public_status_response.data['version'], status_response.data['version'])
        self.assertTrue(any(component['name'] == 'database' for component in status_response.data['components']))

    def test_key_request_requires_identity_fields(self):
        response = self.client.post('/developer/keys/request', {'email': 'dev@example.com'}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'INVALID_REQUEST')
        self.assertIn('first_name', response.data['error']['details']['missing_fields'])
        self.assertIn('last_name', response.data['error']['details']['missing_fields'])

    def test_key_request_creates_user_profile_org_and_api_key(self):
        response = self.client.post(
            '/developer/keys/request',
            {
                'first_name': 'Ato',
                'last_name': 'Developer',
                'email': 'developer@atonixcorp.test',
                'organization': 'LGX Developer Lab',
                'intended_use': 'Build a portfolio sync integration.',
            },
            format='json',
            REMOTE_ADDR='127.0.0.1',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['developer']['email'], 'developer@atonixcorp.test')
        self.assertIn('.', response.data['api_key']['api_key'])
        self.assertEqual(response.data['api_key']['environment'], 'sandbox')
        self.assertEqual(response.data['api_key']['rate_limit_profile']['name'], 'STANDARD')

        user = User.objects.get(email='developer@atonixcorp.test')
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

        organization = Organization.objects.get(owner=user, name='LGX Developer Lab')
        request_record = DeveloperPortalKeyRequest.objects.get(email='developer@atonixcorp.test')
        application = OAuthApplication.objects.get(pk=request_record.application_id)

        self.assertEqual(request_record.status, 'generated')
        self.assertEqual(request_record.organization, organization)
        self.assertEqual(application.organization, organization)
        self.assertEqual(application.environment, 'sandbox')
        self.assertEqual(application.source_metadata['source'], 'developer_portal')
        self.assertEqual(request_record.source_metadata['ip_address'], '127.0.0.1')
        self.assertEqual(request_record.rate_limit_profile.name, 'STANDARD')

        request_log = DeveloperPortalAPILog.objects.filter(path='/developer/keys/request', key_request=request_record).first()
        self.assertIsNotNone(request_log)
        self.assertEqual(request_log.rate_limit_profile.name, 'STANDARD')

    def test_public_key_register_accepts_name_payload(self):
        response = self.client.post(
            '/keys/register',
            {
                'name': 'Jane Portal',
                'email': 'jane.portal@example.com',
                'organization': 'Portal Labs',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['developer']['first_name'], 'Jane')
        self.assertEqual(response.data['developer']['last_name'], 'Portal')
        self.assertEqual(response.data['api_key']['status'], 'ACTIVE')
        self.assertTrue(DeveloperPortalKeyRequest.objects.filter(email='jane.portal@example.com').exists())

    def test_rate_limit_profiles_are_seeded(self):
        standard = RateLimitProfile.objects.get(name='STANDARD')
        partner = RateLimitProfile.objects.get(name='PARTNER')
        market_api = DeveloperAPI.objects.get(slug='market-data-api')

        self.assertEqual(standard.requests_per_minute, 60)
        self.assertEqual(partner.requests_per_day, 100000)
        self.assertEqual(market_api.rate_limit_profile, standard)

    def test_jwt_token_endpoint_uses_standard_error_envelope(self):
        response = self.client.post(
            '/api/auth/token/',
            {
                'username': 'missing-user',
                'password': 'wrong-password',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['error']['code'], 'UNAUTHORIZED')

    def test_register_requires_email_verification_before_issuing_tokens(self):
        register_response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'secure-id@example.com',
                'password': 'strong-pass-123',
                'username': 'secure-id-user',
                'account_type': 'enterprise',
                'country': 'Nigeria',
            },
            format='json',
        )

        self.assertEqual(register_response.status_code, 201)
        secure_user_id = register_response.data['user']['secure_user_id']
        self.assertEqual(len(secure_user_id), 10)
        self.assertTrue(secure_user_id.isdigit())
        self.assertTrue(register_response.data['verification_required'])
        self.assertNotIn('access', register_response.data)
        self.assertFalse(Organization.objects.filter(owner__email='secure-id@example.com').exists())
        verification_messages = [message for message in mail.outbox if message.subject == 'Confirm your email for AtonixCorp']
        self.assertEqual(len(verification_messages), 1)
        self.assertIn('Thanks for joining AtonixCorp.', verification_messages[-1].body)
        self.assertIn('/verify-email?token=', verification_messages[-1].body)
        self.assertEqual(len(verification_messages[-1].alternatives), 1)
        self.assertEqual(verification_messages[-1].alternatives[0].mimetype, 'text/html')
        self.assertIn('Verify Email', verification_messages[-1].alternatives[0].content)

        token_response = self.client.post(
            '/api/auth/token/',
            {
                'username': secure_user_id,
                'password': 'strong-pass-123',
            },
            format='json',
        )

        self.assertEqual(token_response.status_code, 401)
        self.assertIn('Please verify your email first.', str(token_response.data))
        verification_messages = [message for message in mail.outbox if message.subject == 'Confirm your email for AtonixCorp']
        self.assertEqual(len(verification_messages), 1)

        verification_url = next(line for line in verification_messages[0].body.splitlines() if '/verify-email?token=' in line)
        verification_token = parse_qs(urlparse(verification_url).query)['token'][0]
        verify_response = self.client.get(f'/api/auth/verify-email/?token={verification_token}')

        self.assertEqual(verify_response.status_code, 200)
        self.assertEqual(verify_response.data['next_path'], '/app/verification')
        self.assertIn('access', verify_response.data)
        self.assertTrue(UserProfile.objects.get(user__email='secure-id@example.com').email_verified)
        self.assertIsNotNone(EmailVerificationToken.objects.get(user__email='secure-id@example.com').used_at)

        reused_response = self.client.get(f'/api/auth/verify-email/?token={verification_token}')
        self.assertEqual(reused_response.status_code, 400)

        verified_login_response = self.client.post(
            '/api/auth/token/',
            {'username': secure_user_id, 'password': 'strong-pass-123'},
            format='json',
        )
        self.assertEqual(verified_login_response.status_code, 200)
        self.assertTrue(verified_login_response.data['user']['email_verified'])
        self.assertIn('access', verified_login_response.data)

    @patch('atonixcorp.auth_views.send_verification_email')
    def test_unverified_login_requires_explicit_verification_request(self, send_verification_email):
        user = User.objects.create_user(
            username='unverified-user',
            email='unverified@example.com',
            password='strong-pass-123',
        )
        UserProfile.objects.create(user=user)

        response = self.client.post(
            '/api/auth/token/',
            {'username': 'unverified@example.com', 'password': 'strong-pass-123'},
            format='json',
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['error']['code'], 'UNAUTHORIZED')
        self.assertIn('Request a new verification link', response.data['error']['message'])
        send_verification_email.assert_not_called()

    @patch('atonixcorp.auth_views.send_verification_email', side_effect=RuntimeError('SMTP unavailable'))
    def test_resend_verification_hides_delivery_failures(self, _send_verification_email):
        user = User.objects.create_user(
            username='resend-user',
            email='resend@example.com',
            password='strong-pass-123',
        )
        UserProfile.objects.create(user=user)

        response = self.client.post(
            '/api/auth/resend-verification/',
            {'email': user.email},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['detail'], 'If this account requires verification, a new link has been sent.')

    @patch('atonixcorp.auth_views.send_verification_email')
    def test_resend_verification_accepts_username_or_employee_id(self, send_verification_email):
        user = User.objects.create_user(
            username='resend-employee',
            email='resend-employee@example.com',
            password='strong-pass-123',
        )
        profile = UserProfile.objects.create(user=user, secure_user_id='1234567890')

        for identifier in (user.username, profile.secure_user_id):
            response = self.client.post(
                '/api/auth/resend-verification/',
                {'email': identifier},
                format='json',
            )
            self.assertEqual(response.status_code, 200)

        self.assertEqual(send_verification_email.call_count, 2)

    def test_register_requires_username_distinct_from_email(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'new-owner@example.com',
                'password': 'strong-pass-123',
                'account_type': 'enterprise',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['details']['username'], 'This field is required.')

        matching_username_response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'new-owner@example.com',
                'username': 'new-owner@example.com',
                'password': 'strong-pass-123',
                'account_type': 'enterprise',
            },
            format='json',
        )

        self.assertEqual(matching_username_response.status_code, 400)
        self.assertEqual(
            matching_username_response.data['error']['details']['username'],
            'Username or employee ID must be different from your email address.',
        )

    def test_register_uses_submitted_username_and_rejects_duplicates(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'username-owner@example.com',
                'username': 'username-owner',
                'password': 'strong-pass-123',
                'account_type': 'enterprise',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(User.objects.get(email='username-owner@example.com').username, 'username-owner')

        duplicate_response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'other-owner@example.com',
                'username': 'username-owner',
                'password': 'strong-pass-123',
                'account_type': 'enterprise',
            },
            format='json',
        )

        self.assertEqual(duplicate_response.status_code, 400)
        self.assertEqual(
            duplicate_response.data['error']['details']['username'],
            'This username is already in use.',
        )

    def test_register_routes_existing_unverified_email_to_verification(self):
        existing_user = User.objects.create_user(
            username='existing-user',
            email='existing@example.com',
            password='strong-pass-123',
        )
        UserProfile.objects.create(user=existing_user)

        response = self.client.post(
            '/api/auth/register/',
            {
                'email': 'existing@example.com',
                'username': 'different-user',
                'password': 'strong-pass-123',
                'account_type': 'enterprise',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.data['error']['details']['verification_required'])
        self.assertEqual(
            response.data['error']['details']['email'],
            'An account with this email already exists and needs verification.',
        )

    def test_expired_email_verification_token_is_rejected(self):
        self.client.post(
            '/api/auth/register/',
            {
                'email': 'expired-link@example.com',
                'password': 'strong-pass-123',
                'username': 'expired-link-user',
            },
            format='json',
        )
        verification_message = next(message for message in mail.outbox if message.subject == 'Confirm your email for AtonixCorp')
        verification_url = next(line for line in verification_message.body.splitlines() if '/verify-email?token=' in line)
        verification_token = parse_qs(urlparse(verification_url).query)['token'][0]
        token_record = EmailVerificationToken.objects.get(user__email='expired-link@example.com')
        token_record.expires_at = timezone.now() - timedelta(seconds=1)
        token_record.save(update_fields=['expires_at'])

        response = self.client.get(f'/api/auth/verify-email/?token={verification_token}')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserProfile.objects.get(user__email='expired-link@example.com').email_verified)

    def test_identity_upload_requires_verified_email(self):
        user = User.objects.create_user(username='identity-user', email='identity@example.com', password='strong-pass-123')
        profile = UserProfile.objects.create(user=user)
        self.client.force_authenticate(user)

        blocked_response = self.client.post(
            '/api/auth/identity-verification/',
            {
                'id_document': SimpleUploadedFile('identity.png', b'id-image', content_type='image/png'),
                'selfie': SimpleUploadedFile('selfie.png', b'selfie-image', content_type='image/png'),
            },
            format='multipart',
        )
        self.assertEqual(blocked_response.status_code, 403)
        self.assertEqual(blocked_response.data['error']['message'], 'Please verify your email first.')

        profile.email_verified = True
        profile.save(update_fields=['email_verified'])
        accepted_response = self.client.post(
            '/api/auth/identity-verification/',
            {
                'id_document': SimpleUploadedFile('identity.png', b'id-image', content_type='image/png'),
                'selfie': SimpleUploadedFile('selfie.png', b'selfie-image', content_type='image/png'),
            },
            format='multipart',
        )
        self.assertEqual(accepted_response.status_code, 200)
        self.assertEqual(accepted_response.data['status'], IdentityVerification.STATUS_SUBMITTED)


@override_settings(ATONIXCORP_API_ENVIRONMENT='sandbox')
class CoreFinancialAPIV1Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='v1-owner',
            email='v1-owner@example.com',
            password='strong-pass-123',
        )
        self.organization = Organization.objects.create(
            owner=self.user,
            name='LGX Demo LLC',
            slug='lgx-demo-llc',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='LGX Demo LLC',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
        )
        self.client = APIClient(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)

    def _issue_api_token(self, scopes, *, client_id='scoped-client', client_secret='scoped-secret'):
        app = OAuthApplication.objects.create(
            organization=self.organization,
            name='Scoped Client',
            client_id=client_id,
            client_secret_hash=hashlib.sha256(client_secret.encode()).hexdigest(),
            scopes=scopes,
            environment='sandbox',
            created_by=self.user,
            updated_by=self.user,
            source_metadata={'source': 'test'},
        )
        auth_client = APIClient(HTTP_HOST='localhost')
        token_response = auth_client.post(
            '/v1/auth/token',
            {
                'client_id': app.client_id,
                'client_secret': client_secret,
                'grant_type': 'client_credentials',
            },
            format='json',
        )
        self.assertEqual(token_response.status_code, 200)
        return token_response.data['access_token']

    def test_api_key_lifecycle(self):
        create_response = self.client.post(
            '/v1/api-keys',
            {
                'name': 'Integration Key',
                'scopes': ['ledger:write', 'reports:read'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )

        self.assertEqual(create_response.status_code, 201)
        self.assertIn('client_secret', create_response.data)
        self.assertIn('api_key', create_response.data)
        self.assertEqual(create_response.data['environment'], 'sandbox')
        self.assertEqual(create_response.data['scopes'], ['ledger:write', 'reports:read'])

        list_response = self.client.get(
            '/v1/api-keys',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)

        rotate_response = self.client.post(
            f"/v1/api-keys/{create_response.data['id']}/rotate",
            {},
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(rotate_response.status_code, 200)
        self.assertIn('client_secret', rotate_response.data)
        self.assertIn('api_key', rotate_response.data)
        self.assertNotEqual(rotate_response.data['client_secret'], create_response.data['client_secret'])

        revoke_response = self.client.post(
            f"/v1/api-keys/{create_response.data['id']}/revoke",
            {},
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(revoke_response.status_code, 200)
        self.assertEqual(revoke_response.data['status'], 'revoked')

        application = OAuthApplication.objects.get(pk=int(create_response.data['id'].split('_', 1)[1]))
        self.assertFalse(application.is_active)

    def test_global_workspace_invite_creates_pending_membership_without_role(self):
        workspace = WorkspaceService.create_workspace(self.user, {'name': 'Global Invite Workspace'})
        invitee = User.objects.create_user(
            username='global-invitee',
            email='global-invitee@example.com',
            password='strong-pass-123',
        )

        response = self.client.post(
            '/api/global/invite',
            {
                'email': invitee.email,
                'workspace_id': str(workspace.id),
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'invited')
        self.assertIsNone(response.data['role'])

        membership = WorkspaceMember.objects.get(workspace=workspace, user=invitee)
        self.assertEqual(membership.status, 'invited')
        self.assertIsNone(membership.role)

    def test_global_organization_invite_requires_owner_and_records_audit(self):
        invitee = User.objects.create_user(
            username='global-org-invitee',
            email='global-org-invitee@example.com',
            password='strong-pass-123',
        )

        response = self.client.post(
            '/api/global/invite',
            {
                'email': invitee.email,
                'organization_id': self.organization.id,
                'role_code': 'VIEWER',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['organization_id'], self.organization.id)
        self.assertTrue(response.data['invitation_sent'])
        membership = TeamMember.objects.get(organization=self.organization, user=invitee)
        self.assertEqual(membership.role.code, 'VIEWER')
        self.assertIsNone(membership.accepted_at)
        self.assertTrue(AuditLog.objects.filter(
            organization=self.organization,
            action='invite',
            model_name='TeamMember',
            object_id=str(membership.pk),
        ).exists())

    def test_global_organization_invite_rejects_non_owner(self):
        non_owner = User.objects.create_user(
            username='global-org-non-owner',
            email='global-org-non-owner@example.com',
            password='strong-pass-123',
        )
        client = APIClient()
        client.force_authenticate(non_owner)

        response = client.post(
            '/api/global/invite',
            {
                'email': 'blocked-invitee@example.com',
                'organization_id': self.organization.id,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(TeamMember.objects.filter(
            organization=self.organization,
            user__email='blocked-invitee@example.com',
        ).exists())

    def test_cli_login_refresh_and_me_endpoints(self):
        create_response = self.client.post(
            '/v1/api-keys',
            {
                'name': 'CLI Integration Key',
                'scopes': ['reports:read'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(create_response.status_code, 201)

        public_client = APIClient(HTTP_HOST='localhost')
        login_response = public_client.post(
            '/auth/cli-login',
            {
                'api_key': create_response.data['api_key'],
                'organization_id': f'org_{self.organization.pk}',
            },
            format='json',
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertEqual(login_response.data['organization_id'], f'org_{self.organization.pk}')
        self.assertEqual(login_response.data['user']['email'], self.user.email)

        access_token = login_response.data['access_token']
        token_hash = hashlib.sha256(access_token.encode()).hexdigest()
        self.assertTrue(APIKey.objects.filter(token_hash=token_hash, source_metadata__source='cli_login').exists())

        me_response = public_client.get(
            '/auth/me',
            HTTP_AUTHORIZATION=f'Bearer {access_token}',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(me_response.status_code, 200)
        self.assertEqual(me_response.data['organization']['name'], self.organization.name)

        refresh_response = public_client.post(
            '/auth/refresh',
            {'api_key': create_response.data['api_key']},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertNotEqual(refresh_response.data['access_token'], access_token)

        self.assertTrue(
            AuditLog.objects.filter(
                organization=self.organization,
                model_name='CLIAuthSession',
            ).count() >= 2
        )

    def test_cli_login_returns_standard_errors(self):
        public_client = APIClient(HTTP_HOST='localhost')

        missing_response = public_client.post('/auth/cli-login', {}, format='json')
        self.assertEqual(missing_response.status_code, 400)
        self.assertEqual(missing_response.data['error']['code'], 'INVALID_REQUEST')

        invalid_key_response = public_client.post(
            '/auth/cli-login',
            {
                'api_key': 'invalid-key',
                'organization_id': f'org_{self.organization.pk}',
            },
            format='json',
        )
        self.assertEqual(invalid_key_response.status_code, 401)
        self.assertEqual(invalid_key_response.data['error']['code'], 'INVALID_API_KEY')

    def test_openapi_and_redoc_endpoints_are_served(self):
        public_client = APIClient(HTTP_HOST='localhost')

        schema_response = public_client.get('/v1/openapi.yaml')
        self.assertEqual(schema_response.status_code, 200)
        self.assertIn('openapi: 3.0.3', schema_response.content.decode('utf-8'))
        self.assertIn('/auth/cli-login', schema_response.content.decode('utf-8'))

        docs_response = public_client.get('/v1/docs')
        self.assertEqual(docs_response.status_code, 200)
        self.assertIn('redoc', docs_response.content.decode('utf-8').lower())

        swagger_response = public_client.get('/v1/swagger')
        self.assertEqual(swagger_response.status_code, 200)
        self.assertIn('swagger-ui', swagger_response.content.decode('utf-8').lower())

    def test_v1_errors_use_standard_error_envelope(self):
        public_client = APIClient(HTTP_HOST='localhost')
        token_response = public_client.post(
            '/v1/auth/token',
            {
                'client_id': 'missing',
                'client_secret': 'missing',
                'grant_type': 'password',
            },
            format='json',
        )
        self.assertEqual(token_response.status_code, 400)
        self.assertEqual(token_response.data['error']['code'], 'INVALID_REQUEST')

        masked_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_err',
                'name': 'Unsafe Account',
                'currency': 'USD',
                'account_number_masked': '123456789',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(masked_response.status_code, 400)
        self.assertEqual(masked_response.data['error']['code'], 'INVALID_REQUEST')
        self.assertIn('Full account numbers', masked_response.data['error']['message'])

    def test_token_exchange_and_bank_import_post_ledger_entries(self):
        app = OAuthApplication.objects.create(
            organization=self.organization,
            name='Sandbox Client',
            client_id='sandbox-client-001',
            client_secret_hash=hashlib.sha256('wrong-secret'.encode()).hexdigest(),
            scopes=['banking:write'],
            environment='sandbox',
            created_by=self.user,
            updated_by=self.user,
            source_metadata={'source': 'test'},
        )

        auth_client = APIClient(HTTP_HOST='localhost')
        token_response = auth_client.post(
            '/v1/auth/token',
            {
                'client_id': app.client_id,
                'client_secret': 'secret-123',
                'grant_type': 'client_credentials',
            },
            format='json',
        )

        self.assertEqual(token_response.status_code, 401)

        app.client_secret_hash = hashlib.sha256('bank-secret'.encode()).hexdigest()
        app.save(update_fields=['client_secret_hash', 'updated_at'])

        token_response = auth_client.post(
            '/v1/auth/token',
            {
                'client_id': app.client_id,
                'client_secret': 'bank-secret',
                'grant_type': 'client_credentials',
            },
            format='json',
        )
        self.assertEqual(token_response.status_code, 200)

        bank_account_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_123',
                'name': 'Operating Account',
                'currency': 'USD',
                'account_number_masked': '****1234',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(bank_account_response.status_code, 201)

        bearer_client = APIClient(HTTP_HOST='localhost')
        import_payload = {
            'transactions': [
                {
                    'external_id': 'txn_001',
                    'date': '2026-03-14',
                    'amount': -250.00,
                    'currency': 'USD',
                    'description': 'Vendor Payment',
                }
            ]
        }
        import_response = bearer_client.post(
            f"/v1/bank-accounts/{bank_account_response.data['id']}/transactions",
            import_payload,
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access_token']}",
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='bank-import-001',
        )

        self.assertEqual(import_response.status_code, 201)
        self.assertEqual(import_response.data['imported_count'], 1)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(GeneralLedger.objects.count(), 1)

        repeat_response = bearer_client.post(
            f"/v1/bank-accounts/{bank_account_response.data['id']}/transactions",
            import_payload,
            format='json',
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access_token']}",
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='bank-import-001',
        )
        self.assertEqual(repeat_response.status_code, 201)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(GeneralLedger.objects.count(), 1)

    def test_api_key_scopes_are_enforced_for_v1_views(self):
        token = self._issue_api_token(['reports:read'], client_id='reports-only', client_secret='reports-only-secret')
        bearer_client = APIClient(HTTP_HOST='localhost')

        allowed_response = bearer_client.get(
            '/v1/reports/trial-balance',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(allowed_response.status_code, 200)

        forbidden_response = bearer_client.get(
            '/v1/accounts',
            HTTP_AUTHORIZATION=f'Bearer {token}',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(forbidden_response.status_code, 403)
        self.assertEqual(forbidden_response.data['error']['code'], 'INSUFFICIENT_SCOPE')
        self.assertIn('accounts:read', forbidden_response.data['error']['message'])

    def test_bank_account_linking_masks_numbers_and_supports_listing(self):
        rejected_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_reject',
                'name': 'Unsafe Account',
                'currency': 'USD',
                'account_number_masked': '123456789',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(rejected_response.status_code, 400)

        create_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_masked',
                'name': 'Treasury Account',
                'currency': 'USD',
                'account_number_masked': '1234',
                'verification_status': 'verified',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.data['account_number_masked'], '****1234')
        self.assertEqual(create_response.data['verification_status'], 'verified')

        linked_account = BankAccount.objects.get(provider_account_id='pld_masked')
        self.assertEqual(linked_account.account_number, '****1234')

        list_response = self.client.get(
            '/v1/bank-accounts',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.data), 1)
        self.assertEqual(list_response.data[0]['provider'], 'plaid')
        self.assertEqual(list_response.data[0]['verification_status'], 'verified')

    def test_roles_and_team_member_invitation_and_deactivation(self):
        roles_response = self.client.get(
            '/v1/roles',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(roles_response.status_code, 200)
        self.assertTrue(any(role['code'] == 'CFO' for role in roles_response.data))

        permissions_response = self.client.get(
            '/v1/permissions',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(permissions_response.status_code, 200)
        self.assertTrue(any(permission['code'] == 'manage_team' for permission in permissions_response.data))

        create_member_response = self.client.post(
            '/v1/team-members/invitations',
            {
                'email': 'advisor@example.com',
                'first_name': 'Ada',
                'last_name': 'Advisor',
                'role_code': 'EXTERNAL_ADVISOR',
                'scoped_entity_ids': [f'ent_{self.entity.pk}'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(create_member_response.status_code, 201)
        self.assertEqual(create_member_response.data['role']['code'], 'EXTERNAL_ADVISOR')
        self.assertEqual(len(create_member_response.data['scoped_entities']), 1)
        self.assertEqual(create_member_response.data['invitation_status'], 'pending')
        self.assertIsNone(create_member_response.data['accepted_at'])

        members_response = self.client.get(
            '/v1/team-members',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(members_response.status_code, 200)
        self.assertEqual(len(members_response.data), 1)
        self.assertEqual(members_response.data[0]['invitation_status'], 'pending')
        self.assertEqual(TeamMember.objects.count(), 1)

        deactivate_response = self.client.post(
            f"/v1/team-members/{create_member_response.data['id']}/deactivate",
            {},
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(deactivate_response.status_code, 200)
        self.assertFalse(deactivate_response.data['is_active'])

    def test_historical_financials_import_balances_into_retained_earnings(self):
        payload = {
            'as_of_date': '2025-12-31',
            'currency': 'USD',
            'reference': 'HIST-2025',
            'balance_sheet': [
                {
                    'account_code': '1000',
                    'account_name': 'Cash',
                    'account_type': 'asset',
                    'side': 'debit',
                    'amount': 1000,
                },
                {
                    'account_code': '2000',
                    'account_name': 'Accounts Payable',
                    'account_type': 'liability',
                    'side': 'credit',
                    'amount': 400,
                },
                {
                    'account_code': '3000',
                    'account_name': 'Owner Equity',
                    'account_type': 'equity',
                    'side': 'credit',
                    'amount': 200,
                },
            ],
            'profit_and_loss': [
                {
                    'account_code': '4000',
                    'account_name': 'Service Revenue',
                    'account_type': 'revenue',
                    'amount': 600,
                },
                {
                    'account_code': '5000',
                    'account_name': 'Operating Expense',
                    'account_type': 'expense',
                    'amount': 200,
                },
            ],
        }

        response = self.client.post(
            '/v1/migration/historical-financials',
            payload,
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='historical-001',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['retained_earnings_direction'], 'credit')
        self.assertEqual(response.data['retained_earnings_amount'], 400.0)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(GeneralLedger.objects.count(), 3)

        repeat_response = self.client.post(
            '/v1/migration/historical-financials',
            payload,
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='historical-001',
        )
        self.assertEqual(repeat_response.status_code, 201)
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(GeneralLedger.objects.count(), 3)

    def test_balance_sheet_and_cash_flow_reports_are_ledger_driven(self):
        customer = Customer.objects.create(
            entity=self.entity,
            customer_code='CUS-REPORT',
            customer_name='Reports Customer',
            email='reports@example.com',
            address='123 Main St',
            city='New York',
            country='US',
            postal_code='10001',
            currency='USD',
            status='active',
        )

        invoice_response = self.client.post(
            '/v1/invoices',
            {
                'customer_id': f'cus_{customer.pk}',
                'issue_date': '2026-03-15',
                'due_date': '2026-03-20',
                'currency': 'USD',
                'line_items': [
                    {
                        'description': 'Reporting services',
                        'quantity': 1,
                        'unit_price': 1000,
                    }
                ],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='reports-invoice-001',
        )
        self.assertEqual(invoice_response.status_code, 201)

        bank_account_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_report',
                'name': 'Reporting Cash',
                'currency': 'USD',
                'account_number_masked': '****4321',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(bank_account_response.status_code, 201)

        payment_response = self.client.post(
            f"/v1/invoices/{invoice_response.data['id']}/payments",
            {
                'payment_date': '2026-03-16',
                'amount': 1000,
                'currency': 'USD',
                'payment_method': 'bank_transfer',
                'bank_account_id': bank_account_response.data['id'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='reports-payment-001',
        )
        self.assertEqual(payment_response.status_code, 201)

        balance_sheet_response = self.client.get(
            '/v1/reports/balance-sheet?as_of_date=2026-03-31&currency=USD',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(balance_sheet_response.status_code, 200)
        self.assertTrue(any(line['account_code'] == '1000' for line in balance_sheet_response.data['assets']))

        cash_flow_response = self.client.get(
            '/v1/reports/cash-flow?from_date=2026-03-01&to_date=2026-03-31&currency=USD',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(cash_flow_response.status_code, 200)
        self.assertTrue(any(line['section'] == 'operating' for line in cash_flow_response.data['lines']))
        self.assertNotEqual(cash_flow_response.data['net_cash_flow'], 0.0)

    def test_bills_and_bill_payments_post_to_ledger(self):
        vendor = Vendor.objects.create(
            entity=self.entity,
            vendor_code='VEN-001',
            vendor_name='Office Vendor',
            email='vendor@example.com',
            address='1 Market St',
            city='New York',
            country='US',
            postal_code='10001',
            currency='USD',
            status='active',
        )

        bill_response = self.client.post(
            '/v1/bills',
            {
                'vendor_id': f'ven_{vendor.pk}',
                'issue_date': '2026-03-15',
                'due_date': '2026-03-30',
                'currency': 'USD',
                'line_items': [
                    {
                        'description': 'Hosting services',
                        'quantity': 2,
                        'unit_price': 150,
                    }
                ],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='bill-create-001',
        )
        self.assertEqual(bill_response.status_code, 201)
        self.assertEqual(bill_response.data['status'], 'posted')
        self.assertEqual(JournalEntry.objects.count(), 1)
        self.assertEqual(GeneralLedger.objects.count(), 1)

        bank_account_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_bill',
                'name': 'Payables Account',
                'currency': 'USD',
                'account_number_masked': '****7777',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(bank_account_response.status_code, 201)

        payment_response = self.client.post(
            f"/v1/bills/{bill_response.data['id']}/payments",
            {
                'payment_date': '2026-03-20',
                'amount': 300,
                'currency': 'USD',
                'payment_method': 'bank_transfer',
                'bank_account_id': bank_account_response.data['id'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='bill-pay-001',
        )
        self.assertEqual(payment_response.status_code, 201)
        self.assertEqual(payment_response.data['status'], 'paid')
        self.assertEqual(JournalEntry.objects.count(), 2)
        self.assertEqual(GeneralLedger.objects.count(), 2)

    @patch('finances.v1_views.urlopen')
    def test_webhook_delivery_execution_and_signing(self, mocked_urlopen):
        mocked_response = mocked_urlopen.return_value.__enter__.return_value
        mocked_response.status = 200
        mocked_response.read.return_value = b'{"ok":true}'

        webhook_response = self.client.post(
            '/v1/webhooks/endpoints',
            {
                'url': 'https://client.example.com/webhooks',
                'events': ['invoice.created'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(webhook_response.status_code, 201)

        customer = Customer.objects.create(
            entity=self.entity,
            customer_code='CUS-001',
            customer_name='Acme Corp',
            email='billing@acme.com',
            address='123 Main St',
            city='New York',
            country='US',
            postal_code='10001',
            currency='USD',
            status='active',
        )

        invoice_response = self.client.post(
            '/v1/invoices',
            {
                'customer_id': f'cus_{customer.pk}',
                'issue_date': '2026-03-15',
                'due_date': '2026-03-30',
                'currency': 'USD',
                'line_items': [
                    {
                        'description': 'Consulting services',
                        'quantity': 10,
                        'unit_price': 100,
                    }
                ],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='invoice-webhook-001',
        )
        self.assertEqual(invoice_response.status_code, 201)
        self.assertEqual(mocked_urlopen.call_count, 1)

        request_obj = mocked_urlopen.call_args.args[0]
        self.assertEqual(request_obj.full_url, 'https://client.example.com/webhooks')
        self.assertEqual(request_obj.headers['X-lgx-event'], 'invoice.created')
        self.assertTrue(request_obj.headers['X-lgx-signature-sha256'].startswith('sha256='))

        delivery = WebhookDelivery.objects.get()
        self.assertEqual(delivery.status, 'delivered')
        self.assertEqual(delivery.response_status, 200)

    @patch('finances.v1_views.urlopen')
    def test_reconciliation_matching_exposes_events_and_supports_replay(self, mocked_urlopen):
        mocked_response = mocked_urlopen.return_value.__enter__.return_value
        mocked_response.status = 200
        mocked_response.read.return_value = b'{"ok":true}'

        webhook_response = self.client.post(
            '/v1/webhooks/endpoints',
            {
                'url': 'https://client.example.com/reconciliation-webhooks',
                'events': ['reconciliation.matched'],
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(webhook_response.status_code, 201)

        bank_account_response = self.client.post(
            '/v1/bank-accounts',
            {
                'provider': 'plaid',
                'provider_account_id': 'pld_reconcile',
                'name': 'Reconciliation Account',
                'currency': 'USD',
                'account_number_masked': '****9999',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(bank_account_response.status_code, 201)

        import_response = self.client.post(
            f"/v1/bank-accounts/{bank_account_response.data['id']}/transactions",
            {
                'transactions': [
                    {
                        'external_id': 'txn_reconcile_001',
                        'date': '2026-03-14',
                        'amount': -250.00,
                        'currency': 'USD',
                        'description': 'Vendor Payment',
                        'raw_data': {'source': 'plaid'},
                    }
                ]
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
            HTTP_X_IDEMPOTENCY_KEY='bank-reconcile-001',
        )
        self.assertEqual(import_response.status_code, 201)
        self.assertEqual(BankingTransaction.objects.count(), 1)

        cash_account = ChartOfAccounts.objects.create(
            entity=self.entity,
            account_code='1010',
            account_name='Ops Cash',
            account_type='asset',
            currency='USD',
            status='active',
        )
        expense_account = ChartOfAccounts.objects.create(
            entity=self.entity,
            account_code='5100',
            account_name='Vendor Expense',
            account_type='expense',
            currency='USD',
            status='active',
        )
        journal_entry = JournalEntry.objects.create(
            entity=self.entity,
            entry_type='manual',
            reference_number='REC-001',
            description='Reconciliation candidate',
            posting_date=timezone.datetime(2026, 3, 14).date(),
            status='posted',
            created_by=self.user,
            approved_by=self.user,
            approved_at=timezone.now(),
        )
        GeneralLedger.objects.create(
            entity=self.entity,
            debit_account=expense_account,
            credit_account=cash_account,
            debit_amount=Decimal('250.00'),
            credit_amount=Decimal('250.00'),
            description='Reconciliation candidate',
            reference_number='REC-001',
            posting_date=timezone.datetime(2026, 3, 14).date(),
            journal_entry=journal_entry,
            posting_status='posted',
        )

        bank_transaction_id = import_response.data['transactions'][0]['id']
        match_response = self.client.post(
            '/v1/reconciliation/matches',
            {
                'bank_transaction_id': bank_transaction_id,
                'ledger_entry_id': f'je_{journal_entry.pk}',
                'match_type': 'exact',
            },
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(match_response.status_code, 201)
        self.assertEqual(match_response.data['status'], 'reconciled')
        self.assertGreaterEqual(mocked_urlopen.call_count, 1)

        transactions_response = self.client.get(
            f"/v1/bank-accounts/{bank_account_response.data['id']}/transactions?status=reconciled",
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(transactions_response.status_code, 200)
        self.assertEqual(len(transactions_response.data), 1)
        self.assertEqual(transactions_response.data[0]['matched_ledger_entry_id'], f'je_{journal_entry.pk}')

        events_response = self.client.get(
            '/v1/events?event_type=reconciliation.matched',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(events_response.status_code, 200)
        self.assertEqual(len(events_response.data), 1)
        self.assertEqual(SystemEvent.objects.count(), 2)

        replay_response = self.client.post(
            f"/v1/webhooks/events/{events_response.data[0]['id']}/replay",
            {},
            format='json',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(replay_response.status_code, 200)
        self.assertEqual(replay_response.data['replayed_count'], 1)
        self.assertGreaterEqual(mocked_urlopen.call_count, 2)

        deliveries_response = self.client.get(
            '/v1/webhooks/deliveries',
            HTTP_X_ORGANIZATION_ID=f'org_{self.organization.pk}',
        )
        self.assertEqual(deliveries_response.status_code, 200)
        self.assertGreaterEqual(len(deliveries_response.data), 2)


class GovernanceConfigurationAPITests(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_export_and_import_restore_governance_structure(self):
        owner = User.objects.create_user(username='governance-owner', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Recovery Org',
            slug='recovery-org',
            primary_country='US',
            primary_currency='USD',
        )
        entity = Entity.objects.create(
            organization=organization,
            name='Recovery Company',
            country='US',
            entity_type='corporation',
            local_currency='USD',
        )
        department = EntityDepartment.objects.create(
            entity=entity,
            name='Finance Office',
            code='REC-FIN',
        )
        permission = Permission.objects.create(code='manage_org_settings')
        role = EntityRole.objects.create(
            entity=entity,
            department=department,
            name='Chief Financial Officer',
            code='REC-CFO',
        )
        role.permissions.add(permission)

        client = APIClient()
        client.force_authenticate(owner)
        export_response = client.get(f'/api/organizations/{organization.id}/export_governance_yaml/')

        self.assertEqual(export_response.status_code, 200)
        exported_yaml = b''.join(export_response.streaming_content)
        self.assertIn(b'schema_version: v1', exported_yaml)
        self.assertIn(b'Finance Office', exported_yaml)

        department.delete()
        self.assertFalse(EntityDepartment.objects.filter(entity=entity, code='REC-FIN').exists())

        import_response = client.post(
            f'/api/organizations/{organization.id}/import_governance_yaml/',
            {'file': SimpleUploadedFile('org-config.yml', exported_yaml, content_type='application/x-yaml')},
            format='multipart',
        )

        self.assertEqual(import_response.status_code, 200)
        restored_department = EntityDepartment.objects.get(entity=entity, code='REC-FIN')
        restored_role = EntityRole.objects.get(entity=entity, code='REC-CFO')
        self.assertEqual(restored_role.department, restored_department)
        self.assertTrue(restored_role.permissions.filter(code='manage_org_settings').exists())
        self.assertGreater(organization.governance_configuration.revision, 0)

    def test_import_rejects_tampered_signed_governance_document(self):
        owner = User.objects.create_user(username='governance-tamper-owner', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Tamper Recovery Org',
            slug='tamper-recovery-org',
            primary_country='US',
            primary_currency='USD',
        )
        client = APIClient()
        client.force_authenticate(owner)
        export_response = client.get(f'/api/organizations/{organization.id}/export_governance_yaml/')
        document = yaml.safe_load(b''.join(export_response.streaming_content))
        document['organization']['name'] = 'Tampered Organization'

        import_response = client.post(
            f'/api/organizations/{organization.id}/import_governance_yaml/',
            {'file': SimpleUploadedFile('tampered.yml', yaml.safe_dump(document).encode('utf-8'), content_type='application/x-yaml')},
            format='multipart',
        )

        self.assertEqual(import_response.status_code, 400)
        organization.refresh_from_db()
        self.assertEqual(organization.name, 'Tamper Recovery Org')


class OrganizationDirectoryAPITests(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_directory_role_assignment_is_owner_controlled_and_company_scoped(self):
        owner = User.objects.create_user(username='directory-owner', email='owner@example.com', password='pass')
        member_user = User.objects.create_user(username='directory-member', email='member@example.com', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Directory Organization',
            slug='directory-organization',
            primary_country='US',
        )
        other_organization = Organization.objects.create(
            owner=User.objects.create_user(username='other-owner', password='pass'),
            name='Other Organization',
            slug='other-organization',
            primary_country='US',
        )
        entity = Entity.objects.create(
            organization=organization,
            name='Directory Entity',
            country='US',
            entity_type='corporation',
        )

        client = APIClient()
        client.force_authenticate(owner)
        assignment_response = client.post(
            f'/api/organizations/{organization.id}/assign_directory_role/',
            {'user_id': member_user.id, 'role_code': 'CEO', 'scoped_entity_ids': [entity.id]},
            format='json',
        )

        self.assertEqual(assignment_response.status_code, 201)
        member = TeamMember.objects.get(organization=organization, user=member_user)
        self.assertEqual(member.role.code, 'CEO')
        self.assertEqual(list(member.scoped_entities.values_list('id', flat=True)), [entity.id])
        founder_entry = organization.directory_entries.get(source_type='founder')
        member_entry = organization.directory_entries.get(source_type='team_member', source_id=str(member.id))
        self.assertEqual(founder_entry.role_code, 'FOUNDER')
        self.assertEqual(member_entry.uid, member_user.profile.secure_user_id)
        self.assertTrue(PlatformAuditEvent.objects.filter(
            organization=organization,
            event_type='directory.role_assigned',
            resource_id=str(member.id),
        ).exists())

        client.force_authenticate(member_user)
        self.assertEqual(client.get(f'/api/organizations/{organization.id}/directory/').status_code, 200)
        self.assertEqual(client.get(f'/api/organizations/{other_organization.id}/directory/').status_code, 404)
        self.assertEqual(client.post(
            f'/api/organizations/{organization.id}/assign_directory_role/',
            {'user_id': owner.id, 'role_code': 'CTO'},
            format='json',
        ).status_code, 403)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    def test_workspace_and_group_are_projected_as_office_and_unit(self):
        from workspaces.models import Workspace, WorkspaceGroup

        owner = User.objects.create_user(username='workspace-directory-owner', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Workspace Directory Organization',
            slug='workspace-directory-organization',
            primary_country='US',
        )
        entity = Entity.objects.create(
            organization=organization,
            name='Workspace Directory Entity',
            country='US',
            entity_type='corporation',
        )
        workspace = Workspace.objects.create(owner=owner, linked_entity=entity, name='Technology Office')
        group = WorkspaceGroup.objects.create(workspace=workspace, name='Platform Engineering')

        office = organization.directory_entries.get(source_type='workspace', source_id=str(workspace.id))
        unit = organization.directory_entries.get(source_type='workspace_group', source_id=str(group.id))
        self.assertEqual(office.node_type, 'office')
        self.assertEqual(unit.node_type, 'unit')
        self.assertEqual(unit.parent_id, office.id)


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class CompanyIdentityAPITests(TestCase):
    def test_unverified_account_cannot_create_an_organization(self):
        creator = User.objects.create_user(
            username='unverified-creator',
            email='unverified-creator@example.com',
            password='pass',
        )
        UserProfile.objects.create(user=creator, email_verified=False)
        client = APIClient()
        client.force_authenticate(creator)

        response = client.post('/api/organizations/', {
            'name': 'Blocked Organization',
            'registration_number': 'US-2026-100001',
            'primary_country': 'US',
            'primary_currency': 'USD',
        }, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Organization.objects.filter(name='Blocked Organization').exists())

    def test_company_identity_is_required_normalized_unique_and_audited(self):
        founder = User.objects.create_user(
            username='company-founder',
            email='founder@example.com',
            password='pass',
        )
        UserProfile.objects.create(user=founder, email_verified=True)
        other_user = User.objects.create_user(username='company-other-user', password='pass')
        client = APIClient()
        client.force_authenticate(founder)

        missing_identity_response = client.post('/api/organizations/', {
            'name': 'Missing Identity Company',
            'primary_country': 'ZA',
            'primary_currency': 'ZAR',
        }, format='json')
        self.assertEqual(missing_identity_response.status_code, 400)
        self.assertIn('registration_number', missing_identity_response.data)

        create_response = client.post('/api/organizations/', {
            'name': 'Atonix Governance Holdings',
            'registration_number': 'za-2024 / 123456',
            'primary_country': 'ZA',
            'primary_currency': 'ZAR',
        }, format='json')
        self.assertEqual(create_response.status_code, 201)
        organization = Organization.objects.get(pk=create_response.data['id'])
        self.assertEqual(organization.owner, founder)
        self.assertEqual(organization.owner.email, 'founder@example.com')
        self.assertEqual(organization.registration_number, 'ZA2024123456')
        self.assertTrue(PlatformAuditEvent.objects.filter(
            organization=organization,
            event_type='company.created',
            metadata__registration_number='ZA2024123456',
        ).exists())
        self.assertEqual(
            organization.directory_entries.get(source_type='founder').attributes['company_registration_number'],
            'ZA2024123456',
        )
        self.assertIn('o=za2024123456,dc=atonixcorp', organization.directory_entries.get(source_type='organization').dn)

        client.force_authenticate(other_user)
        duplicate_number_response = client.post('/api/organizations/', {
            'name': 'Different Company Name',
            'registration_number': 'ZA 2024-123456',
            'primary_country': 'ZA',
            'primary_currency': 'ZAR',
        }, format='json')
        self.assertEqual(duplicate_number_response.status_code, 400)
        self.assertIn('registration_number', duplicate_number_response.data)

        duplicate_name_response = client.post('/api/organizations/', {
            'name': 'atonix governance holdings',
            'registration_number': 'ZA-2024-654321',
            'primary_country': 'ZA',
            'primary_currency': 'ZAR',
        }, format='json')
        self.assertEqual(duplicate_name_response.status_code, 400)
        self.assertIn('name', duplicate_name_response.data)

        verification_response = client.post('/api/organizations/verify_registration_number/', {
            'name': 'Atonix Governance Holdings',
            'registration_number': 'ZA-2024-123456',
        }, format='json')
        self.assertEqual(verification_response.status_code, 200)
        self.assertTrue(verification_response.data['valid'])
        self.assertFalse(verification_response.data['name_available'])
        self.assertFalse(verification_response.data['available'])
        self.assertFalse(verification_response.data['external_registry_verified'])


class GovernanceCloudExportAPITests(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    @patch('atonixcorp.governance_cloud_exports.urlopen')
    def test_owner_can_export_to_s3_presigned_url_and_audit_delivery(self, mocked_urlopen):
        owner = User.objects.create_user(username='cloud-export-owner', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Cloud Export Organization',
            registration_number='US-2026-778899',
            slug='cloud-export-organization',
            primary_country='US',
        )
        mocked_urlopen.return_value.__enter__.return_value.read.return_value = b''
        mocked_urlopen.return_value.__enter__.return_value.headers = {}
        client = APIClient()
        client.force_authenticate(owner)

        response = client.post(
            f'/api/organizations/{organization.id}/export_governance_cloud/',
            {
                'provider': 'aws_s3',
                'file_name': 'governance-export.yml',
                'presigned_url': 'https://example-bucket.s3.amazonaws.com/governance-export.yml?X-Amz-Signature=secret',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['provider'], 'aws_s3')
        self.assertNotIn('X-Amz-Signature', response.data['remote_reference'])
        export_record = organization.governance_cloud_exports.get(pk=response.data['id'])
        self.assertEqual(export_record.status, 'completed')
        self.assertFalse(export_record.overwrite_confirmed)
        self.assertTrue(PlatformAuditEvent.objects.filter(
            organization=organization,
            event_type='governance.cloud_exported',
            resource_id=str(export_record.id),
        ).exists())
        self.assertEqual(client.get(f'/api/organizations/{organization.id}/governance_cloud_exports/').status_code, 200)

    @override_settings(MEDIA_ROOT=tempfile.gettempdir())
    @patch('atonixcorp.governance_cloud_exports._json_request')
    def test_google_drive_export_rejects_existing_file_without_overwrite(self, mocked_json_request):
        owner = User.objects.create_user(username='cloud-overwrite-owner', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Cloud Overwrite Organization',
            registration_number='US-2026-998877',
            slug='cloud-overwrite-organization',
            primary_country='US',
        )
        mocked_json_request.return_value = {'files': [{'id': 'existing-drive-file'}]}
        client = APIClient()
        client.force_authenticate(owner)

        response = client.post(
            f'/api/organizations/{organization.id}/export_governance_cloud/',
            {'provider': 'google_drive', 'oauth_access_token': 'temporary-token'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('destination', response.data)
        export_record = organization.governance_cloud_exports.get(provider='google_drive')
        self.assertEqual(export_record.status, 'failed')
        self.assertNotIn('temporary-token', export_record.error_message)

    def test_user_outside_company_cannot_export_governance_data(self):
        owner = User.objects.create_user(username='cloud-owner-access', password='pass')
        outsider = User.objects.create_user(username='cloud-outsider-access', password='pass')
        organization = Organization.objects.create(
            owner=owner,
            name='Cloud Access Organization',
            registration_number='US-2026-110022',
            slug='cloud-access-organization',
            primary_country='US',
        )
        client = APIClient()
        client.force_authenticate(outsider)

        response = client.post(
            f'/api/organizations/{organization.id}/export_governance_cloud/',
            {'provider': 'aws_s3', 'presigned_url': 'https://example.s3.amazonaws.com/export.yml'},
            format='json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(organization.governance_cloud_exports.exists())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SystemNotificationTemplateTests(TestCase):
    def test_marketing_template_renders_unsubscribe_link(self):
        from .email_template_service import render_email_template

        html_body, text_body = render_email_template('marketing_campaign', {
            'title': 'AtonixCorp product update',
            'content_html': '<p>New reporting features are available.</p>',
            'content_text': 'New reporting features are available.',
            'unsubscribe_url': 'https://atonixcorp.com/email-preferences?recipient=test@example.com',
        })

        self.assertIn('Unsubscribe', html_body)
        self.assertIn('email-preferences', html_body)
        self.assertIn('Unsubscribe:', text_body)

    def test_system_notification_uses_branded_transactional_template(self):
        from .organization_email_service import send_system_notification

        mail.outbox.clear()
        delivery = send_system_notification(
            recipient='notification-recipient@example.com',
            subject='Welcome to AtonixCorp',
            title='Welcome to AtonixCorp',
            message='Your account is ready.',
            event_type='account_registration',
        )

        self.assertEqual(delivery.status, 'sent')
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Welcome to AtonixCorp', mail.outbox[0].body)
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
        self.assertIn('background:#fc6d26', mail.outbox[0].alternatives[0].content)
        self.assertIn('automated AtonixCorp service notification', mail.outbox[0].alternatives[0].content)


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class OrganizationEmailServiceAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username='email-service-owner',
            email='email-service-owner@example.com',
            password='strong-pass-123',
        )
        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Email Service Organization',
            registration_number='US-2026-441122',
            slug='email-service-organization',
            primary_country='US',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def test_tiers_enforce_sender_provisioning_marketing_consent_and_delivery_audit(self):
        basic_provision = self.client.post(
            f'/api/organizations/{self.organization.id}/provision_email_account/',
            {'local_part': 'governance'},
            format='json',
        )
        self.assertEqual(basic_provision.status_code, 400)

        tier_response = self.client.post(
            f'/api/organizations/{self.organization.id}/configure_email_subscription/',
            {'tier': 'professional', 'billing_reference': 'test-email-plan'},
            format='json',
        )
        self.assertEqual(tier_response.status_code, 200)
        self.assertEqual(tier_response.data['subscription']['tier'], 'professional')

        provision_response = self.client.post(
            f'/api/organizations/{self.organization.id}/provision_email_account/',
            {'local_part': 'governance', 'display_name': 'Governance Office'},
            format='json',
        )
        self.assertEqual(provision_response.status_code, 201)
        account = OrganizationEmailAccount.objects.get(pk=provision_response.data['id'])
        email_count_before_campaign = len(mail.outbox)

        marketing_response = self.client.post(
            f'/api/organizations/{self.organization.id}/send_email_campaign/',
            {
                'sender_id': account.id,
                'campaign_type': 'marketing',
                'recipients': ['recipient@example.com'],
                'subject': 'Marketing update',
                'html_body': '<p>Update</p>',
                'consent_confirmed': True,
            },
            format='json',
        )
        self.assertEqual(marketing_response.status_code, 400)

        self.client.post(
            f'/api/organizations/{self.organization.id}/configure_email_subscription/',
            {'tier': 'enterprise'},
            format='json',
        )
        missing_consent_response = self.client.post(
            f'/api/organizations/{self.organization.id}/send_email_campaign/',
            {
                'sender_id': account.id,
                'campaign_type': 'marketing',
                'recipients': ['recipient@example.com'],
                'subject': 'Marketing update',
                'html_body': '<p>Update</p>',
                'consent_confirmed': False,
            },
            format='json',
        )
        self.assertEqual(missing_consent_response.status_code, 400)

        send_response = self.client.post(
            f'/api/organizations/{self.organization.id}/send_email_campaign/',
            {
                'sender_id': account.id,
                'campaign_type': 'marketing',
                'recipients': ['recipient@example.com'],
                'subject': 'Approved marketing update',
                'html_body': '<p>Update</p>',
                'consent_confirmed': True,
            },
            format='json',
        )
        self.assertEqual(send_response.status_code, 201)
        self.assertEqual(send_response.data['sent_count'], 1)
        self.assertEqual(len(mail.outbox), email_count_before_campaign + 1)
        campaign = OrganizationEmailCampaign.objects.get(pk=send_response.data['id'])
        self.assertEqual(campaign.status, 'sent')
        self.assertTrue(OrganizationEmailDelivery.objects.filter(campaign=campaign, status='sent').exists())
        self.assertTrue(PlatformAuditEvent.objects.filter(
            organization=self.organization,
            event_type='email.campaign_sent',
            resource_id=str(campaign.id),
        ).exists())
        self.assertEqual(OrganizationEmailSubscription.objects.get(organization=self.organization).tier, 'enterprise')

    def test_non_owner_cannot_access_email_service(self):
        outsider = User.objects.create_user(username='email-service-outsider', password='strong-pass-123')
        client = APIClient()
        client.force_authenticate(outsider)

        response = client.get(f'/api/organizations/{self.organization.id}/email_service/')

        self.assertEqual(response.status_code, 404)

    def test_workspace_creation_and_role_change_send_system_notifications(self):
        from workspaces.models import Workspace

        mail.outbox.clear()
        entity = Entity.objects.create(
            organization=self.organization,
            name='Email Service Entity',
            country='US',
            entity_type='corporation',
        )
        Workspace.objects.create(
            owner=self.owner,
            linked_entity=entity,
            name='Email Service Workspace',
        )
        self.assertTrue(OrganizationEmailDelivery.objects.filter(
            organization=self.organization,
            recipient=self.owner.email,
            event_type='workspace_created',
            status='sent',
        ).exists())

        Role.get_or_create_default_roles()
        team_user = User.objects.create_user(
            username='email-service-team-member',
            email='email-service-team-member@example.com',
            password='strong-pass-123',
        )
        member = TeamMember.objects.create(
            organization=self.organization,
            user=team_user,
            role=Role.objects.get(code='VIEWER'),
        )
        member.role = Role.objects.get(code='CFO')
        member.save(update_fields=['role', 'updated_at'])

        self.assertEqual(OrganizationEmailDelivery.objects.filter(
            organization=self.organization,
            recipient=team_user.email,
            event_type='role_assignment',
            status='sent',
        ).count(), 2)


class EntityViewSetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='entity-owner',
            email='entity-owner@example.com',
            password='strong-pass-123',
        )
        self.organization = Organization.objects.create(
            owner=self.user,
            name='AtonixCorp Holdings',
            slug='atonixcorp-holdings',
            primary_country='US',
            primary_currency='USD',
        )
        self.client = APIClient(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)

    def test_create_entity_accepts_holding_company_type(self):
        response = self.client.post(
            '/api/entities/',
            {
                'organization_id': self.organization.id,
                'name': 'AtonixCorp Parent Co',
                'country': 'US',
                'entity_type': 'holding_company',
                'status': 'active',
                'local_currency': 'USD',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['entity_type'], 'holding_company')
        self.assertTrue(
            Entity.objects.filter(name='AtonixCorp Parent Co', entity_type='holding_company').exists()
        )

    def test_selected_departments_are_provisioned_audited_and_exportable(self):
        response = self.client.post(
            '/api/entities/',
            {
                'organization_id': self.organization.id,
                'name': 'Department Provisioning Entity',
                'country': 'US',
                'entity_type': 'corporation',
                'status': 'active',
                'local_currency': 'USD',
                'department_selections': ['equity_governance', 'risk_audit'],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        entity = Entity.objects.get(pk=response.data['id'])
        self.assertTrue(entity.departments.filter(name='Equity and Governance').exists())
        self.assertTrue(entity.departments.filter(name='Risk and Audit').exists())
        self.assertTrue(entity.linked_workspace.groups.filter(name='Equity and Governance').exists())
        self.assertTrue(PlatformAuditEvent.objects.filter(
            organization=self.organization,
            event_type='department.provisioned',
            resource_id=str(entity.id),
        ).exists())

        from atonixcorp.governance_configurations import build_governance_document

        document = build_governance_document(self.organization)
        export_entity = next(item for item in document['entities'] if item['id'] == entity.id)
        self.assertIn('Equity and Governance', [department['name'] for department in export_entity['departments']])

    def test_department_mutation_requires_entity_management_access(self):
        entity = Entity.objects.create(
            organization=self.organization,
            name='Department Security Entity',
            country='US',
            entity_type='corporation',
            local_currency='USD',
        )
        viewer = User.objects.create_user(username='department-viewer', password='strong-pass-123')
        Role.get_or_create_default_roles()
        TeamMember.objects.create(
            organization=self.organization,
            user=viewer,
            role=Role.objects.get(code='VIEWER'),
        )
        viewer_client = APIClient(HTTP_HOST='localhost')
        viewer_client.force_authenticate(viewer)

        response = viewer_client.post(
            '/api/entity-departments/',
            {'entity': entity.id, 'name': 'Restricted Department', 'code': 'RESTRICTED'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(entity.departments.filter(code='RESTRICTED').exists())

    def test_equity_scenario_endpoints_reject_users_without_entity_access(self):
        outsider = User.objects.create_user(username='equity-scenario-outsider', password='strong-pass-123')
        outsider_client = APIClient(HTTP_HOST='localhost')
        outsider_client.force_authenticate(outsider)

        response = outsider_client.get(
            f'/api/entities/{Entity.objects.create(organization=self.organization, name="Restricted Equity Entity", country="US", entity_type="corporation").id}/equity/scenarios/overview'
        )

        self.assertEqual(response.status_code, 404)

    def test_permission_context_grants_owner_entity_access_without_seeded_permissions(self):
        response = self.client.get(f'/api/organizations/{self.organization.id}/permission_context/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['role_code'], 'ORG_OWNER')
        self.assertIn('view_entities', response.data['permission_codes'])
        self.assertIn('create_entity', response.data['permission_codes'])

    def test_workspace_type_registry_provisions_modules_and_hierarchy(self):
        parent_entity = Entity.objects.create(
            organization=self.organization,
            name='Parent Workspace',
            country='US',
            entity_type='other',
            status='active',
            local_currency='USD',
            workspace_mode='workspace',
        )

        response = self.client.post(
            '/api/entities/',
            {
                'organization_id': self.organization.id,
                'name': 'Engineering Delivery Hub',
                'country': 'US',
                'entity_type': 'other',
                'status': 'active',
                'local_currency': 'USD',
                'workspace_mode': 'workspace',
                'workspace_type': 'technology',
                'parent_entity': parent_entity.id,
                'hierarchy_metadata': {
                    'selected_branch': 'software_development',
                    'selected_branch_label': 'Software Development',
                    'selected_sub_branch': 'Frontend',
                    'selected_sub_branch_label': 'Frontend',
                    'departments_text': 'Platform, DevOps',
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['workspace_type'], 'technology')
        self.assertEqual(response.data['parent_entity'], parent_entity.id)
        self.assertEqual(response.data['hierarchy_metadata']['selected_branch_label'], 'Software Development')

        entity = Entity.objects.get(pk=response.data['id'])
        workspace = Workspace.objects.get(linked_entity=entity)
        module_keys = set(workspace.modules.values_list('module_key', flat=True))
        department_names = set(workspace.groups.values_list('name', flat=True))

        self.assertIn('project_tracking', module_keys)
        self.assertIn('code_repositories', module_keys)
        self.assertIn('Software Development', department_names)
        self.assertIn('Frontend', department_names)
        self.assertIn('Backend', department_names)
        self.assertIn('QA', department_names)
        self.assertIn('Platform', department_names)
        self.assertIn('DevOps', department_names)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='no-reply@atonixcorp.test',
    APPROVAL_NOTIFICATION_BASE_URL='https://console.atonixcorp.test',
)
class AccountingApprovalWorkflowAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='approval-owner', email='approval-owner@example.com', password='pass')
        self.reviewer = User.objects.create_user(username='approval-reviewer', email='approval-reviewer@example.com', password='pass')
        self.approver = User.objects.create_user(username='approval-approver', email='approval-approver@example.com', password='pass')
        self.delegate = User.objects.create_user(username='approval-delegate', email='approval-delegate@example.com', password='pass')

        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Approval Org',
            slug='approval-org',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Approval Entity',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
            workspace_mode='accounting',
        )
        self.entity.create_default_structure()

        finance_analyst_role, _ = Role.objects.get_or_create(code='FINANCE_ANALYST', defaults={'name': 'Finance Analyst', 'description': 'Finance analyst'})
        cfo_role, _ = Role.objects.get_or_create(code='CFO', defaults={'name': 'Chief Financial Officer', 'description': 'Chief Financial Officer'})
        advisor_role, _ = Role.objects.get_or_create(code='EXTERNAL_ADVISOR', defaults={'name': 'External Advisor', 'description': 'External advisor'})

        self.reviewer_membership = TeamMember.objects.create(organization=self.organization, user=self.reviewer, role=finance_analyst_role, is_active=True)
        self.reviewer_membership.scoped_entities.add(self.entity)
        self.approver_membership = TeamMember.objects.create(organization=self.organization, user=self.approver, role=cfo_role, is_active=True)
        self.approver_membership.scoped_entities.add(self.entity)
        self.delegate_membership = TeamMember.objects.create(organization=self.organization, user=self.delegate, role=advisor_role, is_active=True)
        self.delegate_membership.scoped_entities.add(self.entity)

        self.accountant_role = EntityRole.objects.get(entity=self.entity, name='Accountant')
        self.finance_manager_role = EntityRole.objects.get(entity=self.entity, name='Finance Manager')
        self.entity_cfo_role = EntityRole.objects.get(entity=self.entity, name='CFO')

        EntityStaff.objects.create(
            entity=self.entity,
            user=self.owner,
            employee_id='EMP-AP-OWNER',
            first_name='Prep',
            last_name='Owner',
            email=self.owner.email,
            department=self.accountant_role.department,
            role=self.accountant_role,
            hire_date=timezone.now().date(),
        )
        self.reviewer_staff = EntityStaff.objects.create(
            entity=self.entity,
            user=self.reviewer,
            employee_id='EMP-AP-REVIEW',
            first_name='Review',
            last_name='User',
            email=self.reviewer.email,
            department=self.finance_manager_role.department,
            role=self.finance_manager_role,
            hire_date=timezone.now().date(),
        )
        self.approver_staff = EntityStaff.objects.create(
            entity=self.entity,
            user=self.approver,
            employee_id='EMP-AP-APPROVE',
            first_name='Approve',
            last_name='User',
            email=self.approver.email,
            department=self.entity_cfo_role.department,
            role=self.entity_cfo_role,
            hire_date=timezone.now().date(),
        )
        self.delegate_staff = EntityStaff.objects.create(
            entity=self.entity,
            user=self.delegate,
            employee_id='EMP-AP-DELEGATE',
            first_name='Delegate',
            last_name='User',
            email=self.delegate.email,
            department=self.accountant_role.department,
            role=self.accountant_role,
            hire_date=timezone.now().date(),
        )

        self.vendor = Vendor.objects.create(
            entity=self.entity,
            vendor_code='VEN-AP-001',
            vendor_name='Approval Vendor',
            email='vendor@example.com',
            address='1 Main Street',
            city='New York',
            country='US',
            postal_code='10001',
            currency='USD',
            status='active',
        )
        self.customer = Customer.objects.create(
            entity=self.entity,
            customer_code='CUS-AP-001',
            customer_name='Approval Customer',
            email='customer@example.com',
            address='1 Main Street',
            city='New York',
            country='US',
            postal_code='10001',
            currency='USD',
            status='active',
        )

        NotificationPreference.objects.get_or_create(user=self.reviewer)
        NotificationPreference.objects.get_or_create(user=self.approver)
        NotificationPreference.objects.get_or_create(user=self.delegate)

        self.owner_client = APIClient()
        self.owner_client.force_authenticate(user=self.owner)
        self.reviewer_client = APIClient()
        self.reviewer_client.force_authenticate(user=self.reviewer)
        self.approver_client = APIClient()
        self.approver_client.force_authenticate(user=self.approver)
        self.delegate_client = APIClient()
        self.delegate_client.force_authenticate(user=self.delegate)

    def _create_bill(self, bill_number='BILL-AP-001', bill_date=None):
        bill_date = bill_date or timezone.now().date()
        return Bill.objects.create(
            entity=self.entity,
            vendor=self.vendor,
            bill_number=bill_number,
            bill_date=bill_date,
            due_date=bill_date,
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('1000.00'),
            paid_amount=Decimal('0.00'),
            outstanding_amount=Decimal('1000.00'),
            currency='USD',
            created_by=self.owner,
        )

    def _create_invoice(self):
        return Invoice.objects.create(
            entity=self.entity,
            customer=self.customer,
            invoice_number='INV-AP-001',
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date(),
            subtotal=Decimal('750.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('750.00'),
            paid_amount=Decimal('0.00'),
            outstanding_amount=Decimal('750.00'),
            currency='USD',
            status='posted',
            created_by=self.owner,
        )

    def _create_bill_matrix(self):
        return AccountingApprovalMatrix.objects.create(
            entity=self.entity,
            name='Bill Approval Matrix',
            object_type='bill',
            minimum_amount=Decimal('0.00'),
            preparer_role=self.accountant_role,
            reviewer_role=self.finance_manager_role,
            approver_role=self.entity_cfo_role,
            require_reviewer=True,
            require_approver=True,
        )

    def _create_payment_matrix(self):
        return AccountingApprovalMatrix.objects.create(
            entity=self.entity,
            name='Payment Approval Matrix',
            object_type='payment',
            minimum_amount=Decimal('0.00'),
            preparer_role=self.accountant_role,
            reviewer_role=self.finance_manager_role,
            approver_role=self.entity_cfo_role,
            require_reviewer=True,
            require_approver=True,
        )

    def test_bill_workflow_api_posts_after_final_approval_and_sends_emails(self):
        bill = self._create_bill()
        self._create_bill_matrix()
        mail.outbox = []

        response = self.owner_client.post(f'/api/bills/{bill.id}/submit/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        bill.refresh_from_db()
        self.assertEqual(bill.approval_status, 'pending_review')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.reviewer.email])
        self.assertIn('Review bill', mail.outbox[0].alternatives[0][0])
        self.assertIn(f'objectType=bill&amp;objectId={bill.id}', mail.outbox[0].alternatives[0][0])

        inbox_response = self.reviewer_client.get('/api/accounting-approval-inbox/', {'entity': self.entity.id})
        self.assertEqual(inbox_response.status_code, 200)
        self.assertEqual(len(inbox_response.data['pending']), 1)
        self.assertEqual(inbox_response.data['pending'][0]['object_type'], 'bill')

        review_response = self.reviewer_client.post(f'/api/bills/{bill.id}/approve/', {'comments': 'Reviewed'}, format='json')
        self.assertEqual(review_response.status_code, 200)
        bill.refresh_from_db()
        self.assertEqual(bill.approval_status, 'pending_approval')
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, [self.approver.email])

        approval_response = self.approver_client.post(f'/api/bills/{bill.id}/approve/', {'comments': 'Approved'}, format='json')
        self.assertEqual(approval_response.status_code, 200)
        bill.refresh_from_db()
        record = AccountingApprovalRecord.objects.get(object_type='bill', object_id=bill.id)
        self.assertEqual(bill.status, 'posted')
        self.assertEqual(bill.approval_status, 'approved')
        self.assertEqual(record.status, 'approved')
        self.assertEqual(Notification.objects.filter(notification_type='approval_request', related_content_type='bill').count(), 2)

    def test_payment_api_defers_invoice_effects_until_final_approval(self):
        invoice = self._create_invoice()
        payment = Payment.objects.create(
            entity=self.entity,
            invoice=invoice,
            customer=self.customer,
            payment_date=timezone.now().date(),
            amount=Decimal('250.00'),
            payment_method='bank_transfer',
            reference_number='PAY-AP-001',
            created_by=self.owner,
        )
        self._create_payment_matrix()

        submit_response = self.owner_client.post(f'/api/payments/{payment.id}/submit/', {}, format='json')
        self.assertEqual(submit_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('0.00'))
        self.assertEqual(invoice.outstanding_amount, Decimal('750.00'))

        review_response = self.reviewer_client.post(f'/api/payments/{payment.id}/approve/', {'comments': 'Reviewed'}, format='json')
        self.assertEqual(review_response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.paid_amount, Decimal('0.00'))

        approval_response = self.approver_client.post(f'/api/payments/{payment.id}/approve/', {'comments': 'Approved'}, format='json')
        self.assertEqual(approval_response.status_code, 200)
        invoice.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(payment.approval_status, 'approved')
        self.assertEqual(invoice.paid_amount, Decimal('250.00'))
        self.assertEqual(invoice.outstanding_amount, Decimal('500.00'))
        self.assertEqual(invoice.status, 'partially_paid')

    def test_bill_submit_api_rejects_locked_period(self):
        locked_date = timezone.now().date()
        bill = self._create_bill(bill_number='BILL-LOCK-001', bill_date=locked_date)
        self._create_bill_matrix()
        LedgerPeriod.objects.create(
            entity=self.entity,
            period_name='Locked Month',
            start_date=locked_date.replace(day=1),
            end_date=locked_date.replace(day=28),
            status='closed',
            no_posting_after=locked_date,
            closed_by=self.owner,
        )

        response = self.owner_client.post(f'/api/bills/{bill.id}/submit/', {}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('locked period', response.data['detail'].lower())

    def test_bill_api_allows_delegated_final_approval(self):
        bill = self._create_bill(bill_number='BILL-DELEGATE-001')
        self._create_bill_matrix()
        AccountingApprovalDelegation.objects.create(
            entity=self.entity,
            object_type='bill',
            delegator=self.approver_staff,
            delegate=self.delegate_staff,
            stage='approver',
            minimum_amount=Decimal('0.00'),
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            is_active=True,
            created_by=self.owner,
        )

        submit_response = self.owner_client.post(f'/api/bills/{bill.id}/submit/', {}, format='json')
        self.assertEqual(submit_response.status_code, 200)
        review_response = self.reviewer_client.post(f'/api/bills/{bill.id}/approve/', {'comments': 'Reviewed'}, format='json')
        self.assertEqual(review_response.status_code, 200)
        delegated_response = self.delegate_client.post(f'/api/bills/{bill.id}/approve/', {'comments': 'Delegated approval'}, format='json')
        self.assertEqual(delegated_response.status_code, 200)

        bill.refresh_from_db()
        record = AccountingApprovalRecord.objects.get(object_type='bill', object_id=bill.id)
        final_step = record.steps.get(stage='approver')
        self.assertEqual(bill.approval_status, 'approved')
        self.assertEqual(final_step.acted_by, self.delegate)
        self.assertIsNotNone(final_step.delegated_from)

    def test_approval_digest_command_sends_grouped_email(self):
        Notification.objects.create(
            user=self.reviewer,
            organization=self.organization,
            notification_type='approval_request',
            priority='high',
            title='Bill approval required',
            message='BILL-DIGEST-001 is awaiting reviewer approval.',
            related_entity=self.entity,
            related_content_type='bill',
            related_object_id='1',
            action_url='/enterprise/entity/1/approval-inbox',
        )
        Notification.objects.create(
            user=self.reviewer,
            organization=self.organization,
            notification_type='approval_request',
            priority='high',
            title='Payment approval required',
            message='PAY-DIGEST-001 is awaiting approver approval.',
            related_entity=self.entity,
            related_content_type='payment',
            related_object_id='2',
            action_url='/enterprise/entity/1/approval-inbox',
        )

        mail.outbox = []
        call_command('send_approval_notification_digest', hours=48)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.reviewer.email])
        self.assertIn('Bill approval required', mail.outbox[0].body)
        self.assertIn('Payment approval required', mail.outbox[0].body)
        self.assertIn('Open the full approval inbox', mail.outbox[0].alternatives[0][0])


class IntercompanyEngineAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='ic-owner', email='ic-owner@example.com', password='pass')
        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Intercompany Org',
            slug='intercompany-org',
            primary_country='US',
            primary_currency='USD',
        )
        self.parent_entity = Entity.objects.create(
            organization=self.organization,
            name='Parent HoldCo',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
            workspace_mode='accounting',
        )
        self.subsidiary_entity = Entity.objects.create(
            organization=self.organization,
            name='Operating Subsidiary',
            country='US',
            entity_type='subsidiary',
            status='active',
            local_currency='USD',
            workspace_mode='accounting',
            parent_entity=self.parent_entity,
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

        self.consolidation = Consolidation.objects.create(
            name='March Consolidation',
            organization=self.organization,
            consolidation_date=timezone.now().date(),
            reporting_currency='USD',
            eliminate_intercompany=True,
        )
        ConsolidationEntity.objects.create(consolidation=self.consolidation, entity=self.parent_entity, ownership_percentage=Decimal('100.0000'))
        ConsolidationEntity.objects.create(consolidation=self.consolidation, entity=self.subsidiary_entity, ownership_percentage=Decimal('100.0000'))

    def test_intercompany_invoice_posts_mirrored_documents_and_is_eliminated_in_consolidation(self):
        response = self.client.post(
            '/api/intercompany-transactions/',
            {
                'organization': self.organization.id,
                'source_entity': self.parent_entity.id,
                'destination_entity': self.subsidiary_entity.id,
                'transaction_type': 'invoice',
                'transaction_date': str(self.consolidation.consolidation_date),
                'due_date': str(self.consolidation.consolidation_date),
                'currency': 'USD',
                'amount': '1500.00',
                'description': 'Shared services allocation',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        transaction_record = IntercompanyTransaction.objects.get(id=response.data['id'])
        self.assertEqual(transaction_record.status, 'posted')
        self.assertIsNotNone(transaction_record.source_invoice_id)
        self.assertIsNotNone(transaction_record.destination_bill_id)
        self.assertIsNotNone(transaction_record.source_journal_entry_id)
        self.assertIsNotNone(transaction_record.destination_journal_entry_id)

        self.assertEqual(Invoice.objects.filter(id=transaction_record.source_invoice_id, status='posted').count(), 1)
        self.assertEqual(Bill.objects.filter(id=transaction_record.destination_bill_id, status='posted').count(), 1)
        self.assertEqual(GeneralLedger.objects.filter(journal_entry_id=transaction_record.source_journal_entry_id).count(), 1)
        self.assertEqual(GeneralLedger.objects.filter(journal_entry_id=transaction_record.destination_journal_entry_id).count(), 1)

        consolidation_response = self.client.post(f'/api/consolidations/{self.consolidation.id}/run_consolidation/')
        self.assertEqual(consolidation_response.status_code, 200)

        self.consolidation.refresh_from_db()
        transaction_record.refresh_from_db()
        self.assertEqual(self.consolidation.status, 'completed')
        self.assertEqual(transaction_record.status, 'eliminated')
        self.assertAlmostEqual(self.consolidation.consolidated_pnl['revenue'], 0.0)
        self.assertAlmostEqual(self.consolidation.consolidated_pnl['expenses'], 0.0)
        self.assertAlmostEqual(self.consolidation.consolidated_balance_sheet['assets'], 0.0)
        self.assertAlmostEqual(self.consolidation.consolidated_balance_sheet['liabilities'], 0.0)
        self.assertEqual(
            IntercompanyEliminationEntry.objects.filter(consolidation=self.consolidation, transaction=transaction_record).count(),
            2,
        )

    def test_intercompany_loan_creates_destination_loan_and_loan_balance_elimination(self):
        response = self.client.post(
            '/api/intercompany-transactions/',
            {
                'organization': self.organization.id,
                'source_entity': self.parent_entity.id,
                'destination_entity': self.subsidiary_entity.id,
                'transaction_type': 'loan',
                'transaction_date': str(self.consolidation.consolidation_date),
                'due_date': str(self.consolidation.consolidation_date),
                'currency': 'USD',
                'amount': '5000.00',
                'transfer_pricing_markup_percent': '5.0000',
                'description': 'Working capital facility',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        transaction_record = IntercompanyTransaction.objects.get(id=response.data['id'])
        self.assertEqual(transaction_record.status, 'posted')
        self.assertIsNotNone(transaction_record.destination_loan_id)
        self.assertEqual(transaction_record.destination_loan.principal_remaining, Decimal('5000.00'))

        consolidation_response = self.client.post(f'/api/consolidations/{self.consolidation.id}/run_consolidation/')
        self.assertEqual(consolidation_response.status_code, 200)

        self.assertEqual(
            IntercompanyEliminationEntry.objects.filter(
                consolidation=self.consolidation,
                transaction=transaction_record,
                elimination_type='loan_balance',
            ).count(),
            1,
        )


class EnterpriseReportingDashboardAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='report-owner', email='report-owner@example.com', password='pass')
        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Reporting Org',
            slug='reporting-org',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Reporting Entity',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
            workspace_mode='combined',
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

        income_category = BookkeepingCategory.objects.create(entity=self.entity, name='Revenue', type='income')
        expense_category = BookkeepingCategory.objects.create(entity=self.entity, name='Operations', type='expense')
        income_account = BookkeepingAccount.objects.create(entity=self.entity, name='Revenue Account', type='cash', currency='USD')
        expense_account = BookkeepingAccount.objects.create(entity=self.entity, name='Expense Account', type='cash', currency='USD')

        Transaction.objects.create(
            entity=self.entity,
            type='income',
            category=income_category,
            account=income_account,
            amount=Decimal('1500.00'),
            currency='USD',
            payment_method='bank',
            description='Consulting revenue',
            date=timezone.now().date(),
            created_by=self.owner,
        )
        Transaction.objects.create(
            entity=self.entity,
            type='expense',
            category=expense_category,
            account=expense_account,
            amount=Decimal('450.00'),
            currency='USD',
            payment_method='bank',
            description='Operating spend',
            date=timezone.now().date(),
            created_by=self.owner,
        )

        BankAccount.objects.create(
            entity=self.entity,
            provider='manual',
            provider_account_id='acct-1',
            account_name='Operating Account',
            account_number='1234',
            bank_name='Bank',
            currency='USD',
            balance=Decimal('5000.00'),
            available_balance=Decimal('5000.00'),
        )
        Budget.objects.create(entity=self.entity, category='Operations', limit=Decimal('1200.00'), spent=Decimal('300.00'), currency='USD')
        CashflowForecast.objects.create(
            entity=self.entity,
            month=timezone.now().date().replace(day=1),
            category='Operations',
            forecasted_amount=Decimal('400.00'),
            currency='USD',
        )
        ComplianceDeadline.objects.create(
            organization=self.organization,
            entity=self.entity,
            title='Federal filing',
            deadline_type='tax_filing',
            deadline_date=timezone.now().date() + timedelta(days=10),
            status='due_soon',
        )
        TaxExposure.objects.create(
            entity=self.entity,
            country='US',
            tax_type='Corporate Income Tax',
            period='annual',
            tax_year=timezone.now().year,
            period_start=timezone.now().date().replace(month=1, day=1),
            period_end=timezone.now().date().replace(month=12, day=31),
            estimated_amount=Decimal('900.00'),
            actual_amount=Decimal('850.00'),
            paid_amount=Decimal('300.00'),
            currency='USD',
            status='ready',
            filing_deadline=timezone.now().date() + timedelta(days=30),
            payment_deadline=timezone.now().date() + timedelta(days=45),
        )
        ComplianceDocument.objects.create(
            entity=self.entity,
            document_type='license',
            title='Business License',
            issuing_authority='State Authority',
            issue_date=timezone.now().date() - timedelta(days=30),
            expiry_date=timezone.now().date() + timedelta(days=365),
            status='active',
        )

        vendor = Vendor.objects.create(
            entity=self.entity,
            vendor_code='VEN-1',
            vendor_name='Vendor One',
            email='vendor@example.com',
            address='123 Street',
        )
        Bill.objects.create(
            entity=self.entity,
            vendor=vendor,
            bill_number='BILL-1',
            bill_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=15),
            subtotal=Decimal('200.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('200.00'),
            outstanding_amount=Decimal('200.00'),
            created_by=self.owner,
        )

        customer = Customer.objects.create(
            entity=self.entity,
            customer_code='CUS-1',
            customer_name='Customer One',
            email='customer@example.com',
            address='456 Street',
        )
        Invoice.objects.create(
            entity=self.entity,
            customer=customer,
            invoice_number='INV-1',
            invoice_date=timezone.now().date(),
            due_date=timezone.now().date() + timedelta(days=15),
            subtotal=Decimal('350.00'),
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('350.00'),
            outstanding_amount=Decimal('350.00'),
            created_by=self.owner,
        )

        from equity.models import (
            EquityFundingRound,
            EquityHolding,
            EquityShareClass,
            EquityShareholder,
            InstrumentType,
            ShareClassType,
            ShareholderType,
            WorkspaceEquityProfile,
        )

        WorkspaceEquityProfile.objects.create(workspace=self.entity, equity_enabled=True, workspace_type='combined')
        share_class = EquityShareClass.objects.create(
            workspace=self.entity,
            name='Series Seed Preferred',
            class_type=ShareClassType.PREFERRED,
            authorized_shares=1500000,
            issued_shares=1000000,
            liquidation_preference='1x non-participating',
            preference_multiple=Decimal('1.0'),
            liquidation_seniority=1,
            conversion_price=Decimal('1.25'),
            pro_rata_rights=True,
            currency='USD',
        )
        shareholder = EquityShareholder.objects.create(
            workspace=self.entity,
            name='Founder One',
            shareholder_type=ShareholderType.INDIVIDUAL,
            email='founder@example.com',
            created_by=self.owner,
        )
        EquityHolding.objects.create(
            workspace=self.entity,
            shareholder=shareholder,
            share_class=share_class,
            quantity=800000,
            diluted_quantity=800000,
            ownership_percent=Decimal('80.00'),
            issued_at=timezone.now().date() - timedelta(days=365),
            issue_price_per_share=Decimal('1.25'),
            invested_amount=Decimal('1000000.00'),
            pro_rata_eligible=True,
            pro_rata_take_up_percent=Decimal('100.00'),
        )
        EquityFundingRound.objects.create(
            workspace=self.entity,
            name='Series Seed',
            instrument_type=InstrumentType.EQUITY,
            share_class=share_class,
            announced_at=timezone.now().date() - timedelta(days=60),
            pre_money_valuation=Decimal('12000000.00'),
            post_money_valuation=Decimal('15000000.00'),
            amount_raised=Decimal('3000000.00'),
            price_per_share=Decimal('1.25'),
            new_shares_issued=240000,
            option_pool_top_up=0,
            apply_pro_rata=True,
        )

        from .models import FinancialModel, Scenario

        model = FinancialModel.objects.create(
            name='Base Operating Model',
            model_type='dcf',
            user=self.owner,
            organization=self.organization,
            status='completed',
        )
        Scenario.objects.create(
            name='Expansion Case',
            scenario_type='best',
            financial_model=model,
            enterprise_value=Decimal('12500000.00'),
            irr=Decimal('0.2200'),
            probability=Decimal('35.00'),
        )

    def test_dashboard_returns_consolidated_reporting_pack(self):
        response = self.client.get(
            '/api/enterprise-reporting/dashboard/',
            {
                'organization_id': self.organization.id,
                'start_date': timezone.now().date().replace(month=1, day=1).isoformat(),
                'end_date': timezone.now().date().isoformat(),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['organization']['id'], self.organization.id)
        self.assertEqual(response.data['summary']['entities_covered'], 1)
        self.assertEqual(response.data['summary']['revenue'], 1500.0)
        self.assertEqual(response.data['summary']['expenses'], 450.0)
        self.assertEqual(response.data['summary']['cash_on_hand'], 5000.0)
        self.assertEqual(response.data['budgeting_and_forecasting']['summary']['budget_limit'], 1200.0)
        self.assertEqual(response.data['scenario_dashboard']['count'], 1)
        self.assertEqual(response.data['equity_waterfalls']['enabled_entities'], 1)
        self.assertTrue(response.data['equity_waterfalls']['entities'][0]['fallback_generated'])
        self.assertGreater(len(response.data['equity_waterfalls']['entities'][0]['waterfalls']), 0)
        self.assertEqual(response.data['automated_compliance_reports']['status_counts']['due_soon'], 1)

    def test_export_endpoints_return_board_pack_files(self):
        pdf_response = self.client.get('/api/enterprise-reporting/export_pdf/', {'organization_id': self.organization.id})
        xlsx_response = self.client.get('/api/enterprise-reporting/export_xlsx/', {'organization_id': self.organization.id})

        self.assertEqual(pdf_response.status_code, 200)
        self.assertIn('application/pdf', pdf_response['Content-Type'])
        self.assertIn('.pdf', pdf_response['Content-Disposition'])
        self.assertGreater(len(pdf_response.content), 500)

        self.assertEqual(xlsx_response.status_code, 200)
        self.assertIn('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', xlsx_response['Content-Type'])
        self.assertIn('.xlsx', xlsx_response['Content-Disposition'])
        self.assertGreater(len(xlsx_response.content), 500)

    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
    def test_scheduled_automation_workflow_delivers_reporting_pack(self):
        mail.outbox.clear()
        workflow = AutomationWorkflow.objects.create(
            organization=self.organization,
            entity=self.entity,
            name='Monthly Board Pack',
            description='Deliver a monthly board pack to finance leadership.',
            trigger_type='schedule',
            trigger_config={
                'frequency': 'monthly',
                'next_run_at': (timezone.now() - timedelta(minutes=5)).isoformat(),
                'schedule_timezone': 'America/New_York',
                'retention_days': 45,
            },
            actions=[
                {
                    'type': 'enterprise_reporting_pack',
                    'format': 'pdf',
                    'months_back': 12,
                    'recipients': ['cfo@example.com'],
                    'subject': 'Monthly board pack',
                }
            ],
            is_active=True,
            created_by=self.owner,
        )

        call_command('run_scheduled_automation_workflows')

        workflow.refresh_from_db()
        execution = workflow.executions.first()
        self.assertIsNotNone(execution)
        self.assertEqual(execution.status, 'completed')
        self.assertEqual(execution.artifacts.count(), 1)
        artifact = execution.artifacts.first()
        self.assertTrue(artifact.file_name.endswith('.pdf'))
        self.assertEqual(artifact.export_format, 'pdf')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['cfo@example.com'])
        self.assertTrue(mail.outbox[0].attachments)
        self.assertTrue(mail.outbox[0].attachments[0][0].endswith('.pdf'))
        self.assertIn('next_run_at', workflow.trigger_config)
        self.assertEqual(workflow.trigger_config['schedule_timezone'], 'America/New_York')
        self.assertEqual(workflow.trigger_config['retention_days'], 45)

        artifact_response = self.client.get(f'/api/automation-artifacts/{artifact.id}/download/')
        self.assertEqual(artifact_response.status_code, 200)
        self.assertGreater(len(b''.join(artifact_response.streaming_content)), 500)

    def test_next_run_at_preserves_local_wall_clock_for_workflow_timezone(self):
        next_run = _next_run_at(
            {
                'frequency': 'weekly',
                'next_run_at': '2026-03-01T14:00:00+00:00',
                'schedule_timezone': 'America/New_York',
            }
        )

        self.assertEqual(next_run.isoformat(), '2026-03-08T13:00:00+00:00')

    def test_cleanup_command_removes_expired_automation_artifacts(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                workflow = AutomationWorkflow.objects.create(
                    organization=self.organization,
                    entity=self.entity,
                    name='Retention Policy Workflow',
                    description='Keep generated board packs briefly for test coverage.',
                    trigger_type='schedule',
                    trigger_config={
                        'frequency': 'monthly',
                        'next_run_at': timezone.now().isoformat(),
                        'schedule_timezone': 'UTC',
                        'retention_days': 1,
                    },
                    actions=[
                        {
                            'type': 'enterprise_reporting_pack',
                            'format': 'pdf',
                            'months_back': 12,
                            'recipients': ['cfo@example.com'],
                        }
                    ],
                    is_active=True,
                    created_by=self.owner,
                )
                execution = workflow.executions.create(status='completed', started_at=timezone.now(), completed_at=timezone.now())

                expired_artifact = AutomationArtifact(
                    workflow=workflow,
                    execution=execution,
                    organization=self.organization,
                    entity=self.entity,
                    artifact_type='enterprise_board_pack',
                    export_format='pdf',
                    file_name='expired-pack.pdf',
                    generated_by=self.owner,
                )
                expired_artifact.file_path.save('expired-pack.pdf', ContentFile(b'expired artifact bytes'), save=False)
                expired_artifact.save()
                AutomationArtifact.objects.filter(id=expired_artifact.id).update(created_at=timezone.now() - timedelta(days=5))
                expired_artifact.refresh_from_db()
                expired_path = expired_artifact.file_path.path

                retained_artifact = AutomationArtifact(
                    workflow=workflow,
                    execution=execution,
                    organization=self.organization,
                    entity=self.entity,
                    artifact_type='enterprise_board_pack',
                    export_format='pdf',
                    file_name='retained-pack.pdf',
                    generated_by=self.owner,
                )
                retained_artifact.file_path.save('retained-pack.pdf', ContentFile(b'retained artifact bytes'), save=False)
                retained_artifact.save()
                retained_path = retained_artifact.file_path.path

                call_command('cleanup_automation_artifacts')

                self.assertFalse(AutomationArtifact.objects.filter(id=expired_artifact.id).exists())
                self.assertFalse(os.path.exists(expired_path))
                self.assertTrue(AutomationArtifact.objects.filter(id=retained_artifact.id).exists())
                self.assertTrue(os.path.exists(retained_path))

    def test_cleanup_impact_endpoint_reports_upcoming_retention_exposure_by_workflow(self):
        with tempfile.TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                workflow = AutomationWorkflow.objects.create(
                    organization=self.organization,
                    entity=self.entity,
                    name='Exposure Workflow',
                    description='Forecast cleanup impact for finance ops.',
                    trigger_type='schedule',
                    trigger_config={
                        'frequency': 'monthly',
                        'next_run_at': timezone.now().isoformat(),
                        'schedule_timezone': 'Europe/London',
                        'retention_days': 10,
                    },
                    actions=[
                        {
                            'type': 'enterprise_reporting_pack',
                            'format': 'pdf',
                            'months_back': 12,
                            'recipients': ['cfo@example.com'],
                        }
                    ],
                    is_active=True,
                    created_by=self.owner,
                )
                execution = workflow.executions.create(status='completed', started_at=timezone.now(), completed_at=timezone.now())

                expiring_artifact = AutomationArtifact(
                    workflow=workflow,
                    execution=execution,
                    organization=self.organization,
                    entity=self.entity,
                    artifact_type='enterprise_board_pack',
                    export_format='pdf',
                    file_name='expiring-pack.pdf',
                    generated_by=self.owner,
                )
                expiring_artifact.file_path.save('expiring-pack.pdf', ContentFile(b'expiring artifact bytes'), save=False)
                expiring_artifact.save()
                AutomationArtifact.objects.filter(id=expiring_artifact.id).update(created_at=timezone.now() - timedelta(days=9))

                expired_artifact = AutomationArtifact(
                    workflow=workflow,
                    execution=execution,
                    organization=self.organization,
                    entity=self.entity,
                    artifact_type='enterprise_board_pack',
                    export_format='pdf',
                    file_name='expired-pack.pdf',
                    generated_by=self.owner,
                )
                expired_artifact.file_path.save('expired-pack.pdf', ContentFile(b'expired artifact bytes'), save=False)
                expired_artifact.save()
                AutomationArtifact.objects.filter(id=expired_artifact.id).update(created_at=timezone.now() - timedelta(days=15))

                response = self.client.get(
                    '/api/automation-workflows/cleanup_impact/',
                    {'organization': self.organization.id, 'days_ahead': 7},
                )

                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data['days_ahead'], 7)
                self.assertEqual(response.data['summary']['workflow_count'], 1)
                self.assertEqual(response.data['summary']['artifacts_expiring'], 2)
                self.assertEqual(response.data['summary']['artifacts_expired'], 1)
                self.assertGreater(response.data['summary']['bytes_expiring'], 0)
                self.assertEqual(len(response.data['workflows']), 1)
                workflow_row = response.data['workflows'][0]
                self.assertEqual(workflow_row['workflow_id'], workflow.id)
                self.assertEqual(workflow_row['schedule_timezone'], 'Europe/London')
                self.assertEqual(workflow_row['retention_days'], 10)
                self.assertEqual(workflow_row['total_artifacts'], 2)
                self.assertEqual(workflow_row['artifacts_expiring_within_window'], 2)
                self.assertEqual(workflow_row['artifacts_already_expired'], 1)
                self.assertIsNotNone(workflow_row['next_expiration_at'])


class PlatformFoundationAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='platform-owner', email='platform-owner@example.com', password='pass')
        self.department_owner = User.objects.create_user(username='department-owner', email='department-owner@example.com', password='pass')
        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Platform Org',
            slug='platform-org',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Platform Entity',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
            workspace_mode='combined',
        )
        self.workspace = WorkspaceService.create_workspace(self.owner, {'name': 'Platform Workspace'})
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.department_owner, role='admin')
        self.controllership = WorkspaceGroup.objects.get(workspace=self.workspace, name='Controllership')
        self.controllership.owner = self.department_owner
        self.controllership.save(update_fields=['owner'])
        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)

    def test_governance_commission_plan_calculates_and_audits_entry(self):
        plan_response = self.client.post(
            '/api/governance-commission-plans/',
            {
                'organization': self.organization.id,
                'role_code': 'CFO',
                'name': 'Financial transaction commission',
                'trigger_type': 'financial_transaction',
                'rate_percent': '2.5000',
            },
            format='json',
        )

        self.assertEqual(plan_response.status_code, 201)
        calculation_response = self.client.post(
            f"/api/governance-commission-plans/{plan_response.data['id']}/calculate/",
            {
                'recipient': self.department_owner.id,
                'source_reference': 'TXN-2026-001',
                'source_description': 'Approved treasury transfer',
                'base_amount': '1200.00',
                'currency': 'usd',
            },
            format='json',
        )

        self.assertEqual(calculation_response.status_code, 201)
        self.assertEqual(calculation_response.data['commission_amount'], '30.00')
        entry = GovernanceCommissionEntry.objects.get(pk=calculation_response.data['id'])
        self.assertEqual(entry.status, 'accrued')
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                domain='governance',
                event_type='commission_entry.calculated',
                resource_id=str(entry.id),
            ).exists()
        )

        update_response = self.client.patch(
            f'/api/governance-commission-entries/{entry.id}/',
            {'base_amount': '1.00', 'status': 'approved'},
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.base_amount, Decimal('1200.00'))
        self.assertEqual(entry.status, 'approved')

    def test_creating_task_request_creates_platform_task_and_audit_event(self):
        response = self.client.post(
            '/api/task-requests/',
            {
                'organization': self.organization.id,
                'entity': self.entity.id,
                'task_type': 'generate_statement',
                'priority': 'high',
                'payload': {
                    'description': 'Produce month-end income statement.',
                    'entity_id': self.entity.id,
                },
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        task_request_id = str(response.data['id'])
        platform_task = PlatformTask.objects.get(source_object_type='TaskRequest', source_object_id=task_request_id)
        self.assertEqual(platform_task.domain, 'finance')
        self.assertEqual(platform_task.status, 'open')
        self.assertEqual(platform_task.priority, 'high')
        self.assertEqual(platform_task.organization_id, self.organization.id)
        self.assertTrue(
            PlatformAuditEvent.objects.filter(
                domain='finance',
                event_type='task_request.created',
                resource_type='TaskRequest',
                resource_id=task_request_id,
            ).exists()
        )

        list_response = self.client.get('/api/platform-tasks/', {'organization': self.organization.id})
        self.assertEqual(list_response.status_code, 200)
        task_rows = list_response.data.get('results', list_response.data)
        self.assertEqual(len(task_rows), 1)

    def test_processing_task_request_updates_platform_task_and_emits_audit_events(self):
        create_response = self.client.post(
            '/api/task-requests/',
            {
                'organization': self.organization.id,
                'entity': self.entity.id,
                'task_type': 'custom',
                'priority': 'normal',
                'payload': {'description': 'Track custom ops request.'},
            },
            format='json',
        )
        task_request_id = create_response.data['id']

        response = self.client.post(f'/api/task-requests/{task_request_id}/process/')
        self.assertEqual(response.status_code, 200)

        platform_task = PlatformTask.objects.get(source_object_type='TaskRequest', source_object_id=str(task_request_id))
        self.assertEqual(platform_task.status, 'completed')
        event_types = set(
            PlatformAuditEvent.objects.filter(resource_type='TaskRequest', resource_id=str(task_request_id)).values_list('event_type', flat=True)
        )
        self.assertIn('task_request.processing_started', event_types)
        self.assertIn('task_request.completed', event_types)

    def test_workspace_logs_are_mirrored_into_platform_audit_stream(self):
        workspace = Workspace.objects.create(owner=self.owner, name='Ops Workspace')

        LogService.log(workspace.id, self.owner, 'file.uploaded', {'name': 'board-pack.pdf', 'file_id': 'file-123'})

        event = PlatformAuditEvent.objects.get(domain='workspace', event_type='file.uploaded')
        self.assertEqual(str(event.workspace_id), str(workspace.id))
        self.assertEqual(event.resource_type, 'File')
        self.assertEqual(event.resource_name, 'board-pack.pdf')

        response = self.client.get('/api/platform-audit-events/', {'workspace_id': str(workspace.id)})
        self.assertEqual(response.status_code, 200)
        rows = response.data.get('results', response.data)
        self.assertEqual(len(rows), 1)

    def test_platform_audit_api_exposes_canonical_fields_and_filters(self):
        workspace = Workspace.objects.create(owner=self.owner, name='Audit Workspace')

        LogService.log(workspace.id, self.owner, 'file.uploaded', {'name': 'cap-table.csv', 'file_id': 'file-456'})

        event = PlatformAuditEvent.objects.get(domain='workspace', event_type='file.uploaded')
        response = self.client.get(
            '/api/platform-audit-events/',
            {
                'action': 'file.uploaded',
                'subject_type': 'workspace',
                'subject_id': str(workspace.id),
            },
        )

        self.assertEqual(response.status_code, 200)
        rows = response.data.get('results', response.data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['actor_id'], str(self.owner.id))
        self.assertEqual(rows[0]['subject_type'], 'workspace')
        self.assertEqual(rows[0]['subject_id'], str(workspace.id))
        self.assertEqual(rows[0]['action'], 'file.uploaded')
        self.assertEqual(event.subject_type, 'workspace')

    def test_platform_task_actions_support_canonical_state_contract(self):
        create_response = self.client.post(
            '/api/platform-tasks/',
            {
                'organization': self.organization.id,
                'entity': self.entity.id,
                'workspace_id': str(self.workspace.id),
                'type': 'journal_entry_approval',
                'title': 'Approve journal 1001',
                'description': 'Review manual journal above threshold.',
                'state': 'open',
                'assignee_type': 'role',
                'assignee_id': '',
                'origin_type': 'journal_entry',
                'origin_id': '1001',
                'priority': 'high',
            },
            format='json',
        )

        self.assertEqual(create_response.status_code, 201)
        task_id = create_response.data['id']
        self.assertEqual(create_response.data['state'], 'open')
        self.assertEqual(create_response.data['type'], 'journal_entry_approval')
        self.assertEqual(create_response.data['origin_type'], 'journal_entry')
        self.assertEqual(create_response.data['department_name'], 'Controllership')
        self.assertEqual(create_response.data['cost_center'], 'FIN-CTRL-100')
        self.assertEqual(create_response.data['assignee_id'], str(self.department_owner.id))

        start_response = self.client.post(f'/api/platform-tasks/{task_id}/start/', format='json')
        self.assertEqual(start_response.status_code, 200)
        self.assertEqual(start_response.data['state'], 'in_progress')

        complete_response = self.client.post(f'/api/platform-tasks/{task_id}/complete/', {'completion_note': 'Approved'}, format='json')
        self.assertEqual(complete_response.status_code, 200)
        self.assertEqual(complete_response.data['state'], 'completed')

        filtered_response = self.client.get(
            '/api/platform-tasks/',
            {
                'assignee_id': self.department_owner.id,
                'state': 'completed',
                'department_name': 'Controllership',
                'cost_center': 'FIN-CTRL-100',
            },
        )
        self.assertEqual(filtered_response.status_code, 200)
        rows = filtered_response.data.get('results', filtered_response.data)
        self.assertEqual(len(rows), 1)

    def test_department_routing_tags_finance_sync_tasks_without_workspace_context(self):
        task = create_platform_task_record(
            {
                'organization': self.organization,
                'entity': self.entity,
                'type': 'document_request',
                'title': 'Review compliance package',
                'description': 'Document collection review',
                'origin_type': 'document_request',
                'origin_id': 'doc-100',
                'created_by': self.owner,
            },
            actor=self.owner,
        )
        self.assertEqual(task.metadata.get('department_name'), 'Risk, Audit, and Compliance')
        self.assertEqual(task.metadata.get('cost_center'), 'FIN-RISK-180')

    def test_entity_linked_workspace_routes_task_to_department_owner(self):
        self.workspace.linked_entity = self.entity
        self.workspace.save(update_fields=['linked_entity'])

        task = create_platform_task_record(
            {
                'organization': self.organization,
                'entity': self.entity,
                'type': 'journal_entry_approval',
                'title': 'Review entity-linked journal',
                'description': 'Should resolve through linked workspace.',
                'origin_type': 'journal_entry',
                'origin_id': 'journal-linked-1',
                'created_by': self.owner,
            },
            actor=self.owner,
        )

        self.assertEqual(str(task.workspace_id), str(self.workspace.id))
        self.assertEqual(task.assignee_id, str(self.department_owner.id))
        self.assertEqual(task.metadata.get('department_name'), 'Controllership')


class PayrollEngineAPITests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='payroll-owner', email='payroll-owner@example.com', password='pass')
        self.employee_user = User.objects.create_user(username='payroll-employee', email='employee@example.com', password='pass')

        self.organization = Organization.objects.create(
            owner=self.owner,
            name='Payroll Org',
            slug='payroll-org',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Payroll Entity',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
            workspace_mode='accounting',
        )
        self.department = EntityDepartment.objects.create(entity=self.entity, name='Operations', code='OPS-PAY')
        self.role = EntityRole.objects.create(entity=self.entity, name='Operations Lead', code='ROLE-PAY')
        self.owner_staff = EntityStaff.objects.create(
            entity=self.entity,
            user=self.owner,
            employee_id='EMP-PAY-OWNER',
            first_name='Olive',
            last_name='Owner',
            email='payroll-owner@example.com',
            department=self.department,
            role=self.role,
            employment_type='full_time',
            status='active',
            hire_date=timezone.now().date(),
            salary=Decimal('0.00'),
            currency='USD',
        )
        self.staff_member = EntityStaff.objects.create(
            entity=self.entity,
            user=self.employee_user,
            employee_id='EMP-PAY-001',
            first_name='Pat',
            last_name='Payroll',
            email='employee@example.com',
            department=self.department,
            role=self.role,
            employment_type='full_time',
            status='active',
            hire_date=timezone.now().date(),
            salary=Decimal('120000.00'),
            currency='USD',
        )
        StaffPayrollProfile.objects.create(
            staff_member=self.staff_member,
            entity=self.entity,
            pay_frequency='monthly',
            salary_basis='annual',
            base_salary=Decimal('120000.00'),
            income_tax_rate=Decimal('0.1000'),
            employee_tax_rate=Decimal('0.0500'),
            employer_tax_rate=Decimal('0.0750'),
            default_bank_account_name='Pat Payroll',
            default_bank_account_number='123456789',
            default_bank_routing_number='021000021',
            payment_reference='PAY-PAT',
            statutory_jurisdiction='US',
        )
        self.employer_benefit = PayrollComponent.objects.create(
            entity=self.entity,
            code='MED',
            name='Medical Plan',
            component_type='benefit',
            calculation_type='fixed',
            amount=Decimal('500.00'),
            taxable=False,
            employer_contribution=True,
        )
        self.deduction = PayrollComponent.objects.create(
            entity=self.entity,
            code='RET',
            name='Retirement Deduction',
            component_type='deduction',
            calculation_type='fixed',
            amount=Decimal('200.00'),
            taxable=False,
            employer_contribution=False,
        )
        StaffPayrollComponentAssignment.objects.create(staff_member=self.staff_member, component=self.employer_benefit)
        StaffPayrollComponentAssignment.objects.create(staff_member=self.staff_member, component=self.deduction)

        self.leave_type = LeaveType.objects.create(
            entity=self.entity,
            code='VAC',
            name='Vacation',
            accrual_hours_per_run=Decimal('10.00'),
            max_balance_hours=Decimal('120.00'),
            carryover_limit_hours=Decimal('40.00'),
            is_paid_leave=True,
        )
        self.leave_balance = LeaveBalance.objects.create(
            staff_member=self.staff_member,
            leave_type=self.leave_type,
            opening_balance_hours=Decimal('4.00'),
        )
        self.leave_request = LeaveRequest.objects.create(
            entity=self.entity,
            staff_member=self.staff_member,
            leave_type=self.leave_type,
            start_date=timezone.datetime(2025, 1, 3).date(),
            end_date=timezone.datetime(2025, 1, 4).date(),
            hours_requested=Decimal('8.00'),
            status='approved',
            approved_by=self.owner,
            approved_at=timezone.now(),
        )
        PayrollBankOriginatorProfile.objects.create(
            entity=self.entity,
            originator_name='Payroll Entity LLC',
            originator_identifier='WF-12345',
            originating_bank_name='Wells Fargo',
            debit_account_name='Payroll Operating',
            debit_account_number='987654321',
            debit_routing_number='021000021',
            debit_sort_code='12-34-56',
            debit_iban='DE89370400440532013000',
            debit_swift_code='DEUTDEFF',
            company_entry_description='PAYROLL',
            company_discretionary_data='MONTHLY',
            initiating_party_name='Payroll Entity LLC',
            initiating_party_identifier='INIT-001',
        )
        self.payroll_run = PayrollRun.objects.create(
            organization=self.organization,
            entity=self.entity,
            name='January 2025 Payroll',
            pay_frequency='monthly',
            requested_bank_file_format='aba',
            period_start=timezone.datetime(2025, 1, 1).date(),
            period_end=timezone.datetime(2025, 1, 31).date(),
            payment_date=timezone.datetime(2025, 1, 31).date(),
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.owner)
        self.employee_client = APIClient()
        self.employee_client.force_authenticate(user=self.employee_user)

    def test_create_payroll_run_defaults_country_specific_bank_format(self):
        response = self.client.post(
            '/api/payroll-runs/',
            {
                'organization': self.organization.id,
                'entity': self.entity.id,
                'name': 'February 2025 Payroll',
                'pay_frequency': 'monthly',
                'period_start': '2025-02-01',
                'period_end': '2025-02-28',
                'payment_date': '2025-02-28',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['requested_bank_file_format'], 'aba')
        self.assertEqual(response.data['requested_bank_institution'], 'wells_fargo')
        self.assertEqual(response.data['requested_bank_export_variant'], 'ppd')
        self.assertEqual(response.data['approval_status'], 'draft')

    def test_process_payroll_run_generates_outputs(self):
        response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/process/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.payroll_run.refresh_from_db()
        self.assertEqual(self.payroll_run.status, 'processed')
        self.assertEqual(self.payroll_run.employee_count, 1)
        self.assertEqual(self.payroll_run.gross_pay_total, Decimal('10000.00'))
        self.assertEqual(self.payroll_run.employer_benefits_total, Decimal('500.00'))
        self.assertEqual(self.payroll_run.deductions_total, Decimal('200.00'))
        self.assertEqual(self.payroll_run.tax_withholding_total, Decimal('1500.00'))
        self.assertEqual(self.payroll_run.employer_tax_total, Decimal('750.00'))
        self.assertEqual(self.payroll_run.net_pay_total, Decimal('8300.00'))
        self.assertIsNotNone(self.payroll_run.journal_entry)

        payslip = Payslip.objects.get(payroll_run=self.payroll_run, staff_member=self.staff_member)
        self.assertEqual(payslip.net_pay, Decimal('8300.00'))
        self.assertEqual(payslip.leave_accrued_hours, Decimal('10.00'))
        self.assertEqual(payslip.leave_used_hours, Decimal('8.00'))
        self.assertEqual(payslip.leave_balance_hours, Decimal('6.00'))
        self.assertEqual(payslip.line_items.count(), 6)

        self.leave_balance.refresh_from_db()
        self.leave_request.refresh_from_db()
        self.assertEqual(self.leave_balance.current_balance_hours, Decimal('6.00'))
        self.assertEqual(self.leave_request.status, 'processed')
        self.assertEqual(self.leave_request.payroll_run, self.payroll_run)

        self.assertEqual(PayrollStatutoryReport.objects.filter(payroll_run=self.payroll_run).count(), 3)
        payment_file = PayrollBankPaymentFile.objects.get(payroll_run=self.payroll_run)
        self.assertEqual(payment_file.file_format, 'aba')
        self.assertIn('wells_fargo_ppd', payment_file.file_name)
        self.assertIn('Payroll Entity LLC', payment_file.content)
        self.assertIn('PAYROLL', payment_file.content)
        self.assertIn('PAY-PAT', payment_file.content)
        self.assertIn('830000', payment_file.content)
        self.assertGreater(GeneralLedger.objects.filter(journal_entry=self.payroll_run.journal_entry).count(), 0)

    def test_process_payroll_run_validates_required_bank_fields_for_selected_variant(self):
        originator = PayrollBankOriginatorProfile.objects.get(entity=self.entity)
        originator.debit_iban = ''
        originator.debit_swift_code = ''
        originator.save(update_fields=['debit_iban', 'debit_swift_code', 'updated_at'])

        self.payroll_run.requested_bank_file_format = 'sepa'
        self.payroll_run.requested_bank_institution = 'deutsche_bank'
        self.payroll_run.requested_bank_export_variant = 'pain.001.001.03'
        self.payroll_run.save(update_fields=['requested_bank_file_format', 'requested_bank_institution', 'requested_bank_export_variant', 'updated_at'])

        response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/process/', {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('Bank export validation failed', response.data['detail'])
        self.assertIn('IBAN', response.data['detail'])
        self.assertIn('SWIFT/BIC', response.data['detail'])

    def test_process_payroll_run_validates_wells_fargo_originator_rules(self):
        originator = PayrollBankOriginatorProfile.objects.get(entity=self.entity)
        originator.originator_identifier = 'IDENTIFIER-TOO-LONG'
        originator.company_entry_description = 'PAYROLL-INVALID'
        originator.save(update_fields=['originator_identifier', 'company_entry_description', 'updated_at'])

        response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/process/', {}, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('originator identifier', response.data['detail'])
        self.assertIn('company entry description', response.data['detail'])

    def test_process_payroll_run_requires_approval_when_matrix_configured(self):
        AccountingApprovalMatrix.objects.create(
            entity=self.entity,
            name='Payroll Approval',
            object_type='payroll_run',
            minimum_amount=Decimal('0.00'),
            approver_role=self.role,
            require_reviewer=False,
            require_approver=True,
        )

        blocked_response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/process/', {}, format='json')
        self.assertEqual(blocked_response.status_code, 400)
        self.assertIn('must be fully approved', blocked_response.data['detail'])

        submit_response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/submit/', {}, format='json')
        self.assertEqual(submit_response.status_code, 200)
        self.payroll_run.refresh_from_db()
        self.assertEqual(self.payroll_run.approval_status, 'pending_approval')

        approve_response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/approve/', {'comments': 'Approved'}, format='json')
        self.assertEqual(approve_response.status_code, 200)
        self.payroll_run.refresh_from_db()
        self.assertEqual(self.payroll_run.approval_status, 'approved')

        process_response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/process/', {}, format='json')
        self.assertEqual(process_response.status_code, 200)
        self.payroll_run.refresh_from_db()
        self.assertEqual(self.payroll_run.status, 'processed')

    def test_mark_paid_updates_payroll_run_and_payslip_status(self):
        self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/process/', {}, format='json')

        response = self.client.post(f'/api/payroll-runs/{self.payroll_run.id}/mark_paid/', {}, format='json')

        self.assertEqual(response.status_code, 200)
        self.payroll_run.refresh_from_db()
        self.assertEqual(self.payroll_run.status, 'paid')
        self.assertEqual(Payslip.objects.get(payroll_run=self.payroll_run).status, 'paid')


class BankingIntegrationAutomationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='bank-owner',
            email='bank-owner@example.com',
            password='bank-pass-123',
        )
        self.organization = Organization.objects.create(
            owner=self.user,
            name='Bank Ops LLC',
            slug='bank-ops-llc',
            primary_country='US',
            primary_currency='USD',
        )
        self.entity = Entity.objects.create(
            organization=self.organization,
            name='Bank Ops Entity',
            country='US',
            entity_type='corporation',
            status='active',
            local_currency='USD',
        )
        self.client = APIClient(HTTP_HOST='localhost')
        self.client.force_authenticate(user=self.user)

    def test_consent_sync_and_override_flow_is_auditable(self):
        consent_response = self.client.post(
            '/api/banking-integrations/consent-session/',
            {
                'organization': self.organization.id,
                'entity': self.entity.id,
                'integration_type': 'financial_data',
                'provider_code': 'plaid',
                'provider_name': 'Plaid',
                'redirect_uri': 'http://localhost:3000/firm/integrations',
                'scopes': ['accounts:read', 'transactions:read'],
            },
            format='json',
        )

        self.assertEqual(consent_response.status_code, 201)
        integration_id = consent_response.data['integration']['id']
        state = consent_response.data['state']
        self.assertTrue(BankingConsentLog.objects.filter(integration_id=integration_id, state=state, status='requested').exists())

        complete_response = self.client.post(
            f'/api/banking-integrations/{integration_id}/complete-consent/',
            {
                'state': state,
                'authorization_code': 'demo-auth-code',
                'accounts': [
                    {
                        'account_id': 'acct_001',
                        'name': 'Operating Checking',
                        'bank_name': 'Chase',
                        'account_type': 'business',
                        'currency': 'USD',
                        'balance': '5000.00',
                        'available_balance': '4800.00',
                    }
                ],
                'transactions': [
                    {
                        'external_id': 'txn_001',
                        'account_id': 'acct_001',
                        'date': '2026-03-14',
                        'amount': '-14.25',
                        'currency': 'USD',
                        'merchant': 'Starbucks',
                        'description': 'STARBUCKS STORE 1234',
                        'raw_category': 'food_and_drink',
                    }
                ],
            },
            format='json',
        )

        self.assertEqual(complete_response.status_code, 200)
        integration = BankingIntegration.objects.get(id=integration_id)
        self.assertEqual(integration.status, 'active')
        self.assertTrue(integration.access_token_encrypted)
        self.assertEqual(BankAccount.objects.filter(entity=self.entity, provider_account_id='acct_001').count(), 1)

        banking_transaction = BankingTransaction.objects.get(transaction_id='txn_001')
        self.assertEqual(banking_transaction.normalized_category, 'Food & Beverage')
        self.assertEqual(banking_transaction.dashboard_bucket, 'Operating Expenses')

        override_response = self.client.post(
            f'/api/banking-transactions/{banking_transaction.id}/override-category/',
            {
                'category_name': 'Meals',
                'dashboard_bucket': 'People Ops',
                'explanation': 'Finance team reclassified this merchant.',
            },
            format='json',
        )

        self.assertEqual(override_response.status_code, 200)
        banking_transaction.refresh_from_db()
        self.assertEqual(banking_transaction.normalized_category, 'Meals')
        self.assertEqual(banking_transaction.dashboard_bucket, 'People Ops')
        self.assertTrue(AuditLog.objects.filter(model_name='BankingCategorizationDecision', object_id__isnull=False).exists())
