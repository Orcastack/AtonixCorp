"""
Enterprise-specific viewsets and views
"""
from rest_framework import status as drf_status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import User
from django.http import FileResponse
from django.http import HttpResponse
from django.db.models import Sum, Q, Count
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta
from collections import defaultdict
from functools import lru_cache
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone
from django.db import connection
from workspaces.models import Workspace

from .governance_configurations import restore_governance_document
from .governance_cloud_exports import export_governance_yaml
from .company_identity import normalize_registration_number
from .department_provisioning import provision_selected_departments, validate_department_selections
from .organization_email_service import provision_email_account, send_campaign, set_subscription_tier, subscription_summary
from .services.domain_verification import verify_organization_domains

from .models import (
    Organization, OrganizationDirectoryEntry, GovernanceCloudExport, OrganizationEmailAccount, OrganizationEmailCampaign, OrganizationEmailDelivery, Entity, TeamMember, Role, Permission, TaxExposure, UserProfile, ROLE_ORG_OWNER, ROLE_CFO,
    ROLE_FINANCE_ANALYST, ROLE_VIEWER, ROLE_EXTERNAL_ADVISOR,
    TaxProfile, TaxRegimeRegistry, TaxCalculation, TaxFiling, TaxAuditLog, TaxRuleSetVersion, TaxRiskAlert, ComplianceDeadline, CashflowForecast, AuditLog, PlatformAuditEvent, PlatformTask, EntityDepartment, DashboardAccessGrant,
    GovernancePolicy, GovernanceAmendment, GovernanceVote, GovernanceCommissionPlan, GovernanceCommissionEntry,
    Budget, Scenario, Consolidation,
    EntityRole, EntityStaff, BankAccount, Wallet, ComplianceDocument,
    StaffPayrollProfile, PayrollComponent, StaffPayrollComponentAssignment,
    LeaveType, LeaveBalance, LeaveRequest, PayrollBankOriginatorProfile, PayrollRun, Payslip, PayrollStatutoryReport,
    PayrollBankPaymentFile,
    BookkeepingCategory, BookkeepingAccount, Transaction, BookkeepingAuditLog,
    RecurringTransaction, TaskRequest, FixedAsset, AccrualEntry,
    # New models
    ChartOfAccounts, GeneralLedger, JournalEntry, JournalApprovalMatrix, JournalApprovalDelegation,
    JournalEntryApprovalStep, JournalEntryChangeLog, AccountingApprovalMatrix,
    AccountingApprovalDelegation, AccountingApprovalRecord, AccountingApprovalStep,
    AccountingApprovalChangeLog, RecurringJournalTemplate, LedgerPeriod,
    Customer, Invoice, InvoiceLineItem, CreditNote, Payment,
    Vendor, PurchaseOrder, Bill, BillPayment,
    InventoryItem, InventoryTransaction, InventoryCostOfGoodsSold,
    BankReconciliation,
    DeferredRevenue, RevenueRecognitionSchedule,
    PeriodCloseChecklist, PeriodCloseItem,
    ExchangeRate, FXGainLoss,
    Notification, NotificationPreference,
    IntercompanyTransaction, IntercompanyEliminationEntry,
    # NEW MODELS
    Client, ClientPortal, ClientMessage, ClientDocument, DocumentRequest, ApprovalRequest,
    DocumentTemplate, Loan, LoanPayment, KYCProfile, AMLTransaction, FirmService,
    ClientInvoice, ClientInvoiceLineItem, ClientSubscription, WhiteLabelBranding,
    BankingIntegration, BankingTransaction, BankingConsentLog, BankingSyncRun,
    BankingCategorizationRule, BankingCategorizationDecision, EmbeddedPayment, AutomationWorkflow,
    AutomationExecution, AutomationArtifact, FirmMetric, ClientMarketplaceIntegration, DeveloperModuleInstallation
)
from .serializers import (
    OrganizationSerializer, EntitySerializer, EntityDetailSerializer,
    TeamMemberSerializer, RoleSerializer, PermissionSerializer,
    TaxExposureSerializer, TaxProfileSerializer, ComplianceDeadlineSerializer,
    CashflowForecastSerializer, AuditLogSerializer, PlatformAuditEventSerializer, GovernancePolicySerializer,
    GovernanceAmendmentSerializer, GovernanceVoteSerializer, GovernanceCommissionPlanSerializer,
    GovernanceCommissionEntrySerializer, GovernanceCommissionCalculationSerializer, OrgOverviewSerializer,
    EntityDepartmentSerializer, EntityRoleSerializer, EntityStaffSerializer,
    StaffPayrollProfileSerializer, PayrollComponentSerializer, StaffPayrollComponentAssignmentSerializer,
    LeaveTypeSerializer, LeaveBalanceSerializer, LeaveRequestSerializer, PayrollBankOriginatorProfileSerializer, PayrollRunSerializer,
    PayslipSerializer, PayrollStatutoryReportSerializer, PayrollBankPaymentFileSerializer,
    BankAccountSerializer, WalletSerializer, ComplianceDocumentSerializer,
    BookkeepingCategorySerializer, BookkeepingAccountSerializer, TransactionSerializer, BookkeepingAuditLogSerializer,
    RecurringTransactionSerializer, TaskRequestSerializer, PlatformTaskSerializer,
    TaxRegimeRegistrySerializer, TaxCalculationSerializer, TaxFilingSerializer, TaxAuditLogSerializer, TaxRuleSetVersionSerializer, TaxRiskAlertSerializer,
    # New serializers
    ChartOfAccountsSerializer, GeneralLedgerSerializer, JournalApprovalMatrixSerializer,
    JournalApprovalDelegationSerializer, JournalEntryApprovalStepSerializer,
    JournalEntryChangeLogSerializer, JournalEntrySerializer,
    AccountingApprovalMatrixSerializer, AccountingApprovalDelegationSerializer,
    AccountingApprovalRecordSerializer, AccountingApprovalStepSerializer,
    AccountingApprovalChangeLogSerializer,
    RecurringJournalTemplateSerializer, LedgerPeriodSerializer,
    CustomerSerializer, InvoiceSerializer, InvoiceLineItemSerializer, CreditNoteSerializer, PaymentSerializer,
    VendorSerializer, PurchaseOrderSerializer, BillSerializer, BillPaymentSerializer,
    InventoryItemSerializer, InventoryTransactionSerializer, InventoryCostOfGoodsSoldSerializer,
    BankReconciliationSerializer,
    DeferredRevenueSerializer, RevenueRecognitionScheduleSerializer,
    PeriodCloseChecklistSerializer, PeriodCloseItemSerializer,
    ExchangeRateSerializer, FXGainLossSerializer,
    NotificationSerializer, NotificationPreferenceSerializer,
    IntercompanyTransactionSerializer, IntercompanyEliminationEntrySerializer,
    # NEW SERIALIZERS
    ClientSerializer, ClientPortalSerializer, ClientMessageSerializer, ClientDocumentSerializer,
    DocumentRequestSerializer, ApprovalRequestSerializer, DocumentTemplateSerializer, LoanSerializer,
    LoanPaymentSerializer, KYCProfileSerializer, AMLTransactionSerializer, FirmServiceSerializer,
    ClientInvoiceSerializer, ClientInvoiceLineItemSerializer, ClientSubscriptionSerializer,
    WhiteLabelBrandingSerializer, BankingIntegrationSerializer, BankingTransactionSerializer,
    EmbeddedPaymentSerializer, AutomationWorkflowSerializer, AutomationExecutionSerializer, AutomationArtifactSerializer,
    FirmMetricSerializer, ClientMarketplaceIntegrationSerializer, DeveloperModuleInstallationSerializer
)
from .banking_services import (
    complete_oauth_consent,
    handle_banking_webhook,
    override_banking_transaction_category,
    prepare_oauth_consent,
    sync_banking_integration,
)
from .accounting_controls import (
    approve_journal_entry,
    build_journal_inbox_items,
    ensure_period_is_open,
    log_journal_change,
    reject_journal_entry,
    snapshot_journal_entry,
    submit_journal_entry,
)
from .payroll_engine import mark_payroll_run_paid, process_payroll_run
from .accounting_object_controls import (
    approve_accounting_object,
    build_accounting_inbox_items,
    get_matching_accounting_matrix,
    get_accounting_object,
    infer_accounting_object_type,
    reject_accounting_object,
    submit_accounting_object,
)
from .intercompany_engine import post_intercompany_transaction
from .platform_foundation import log_platform_audit_event
from .payroll_bank_exports import list_bank_export_options
from .tax_regimes import build_regime_rules, build_regime_payload, resolve_regime_code
from .tax_engine import persist_tax_calculation, build_tax_filing, log_tax_audit
from .tax_security import build_device_metadata, can_manage_global_tax_rules, can_manage_tax_rule_sets, can_view_full_tax_audit, can_view_partial_tax_audit
from .payroll_presets import (
    get_payroll_country_preset,
    list_payroll_country_presets,
    resolve_bank_export_variant,
    resolve_bank_file_format,
    resolve_bank_institution,
)
from .permissions import PermissionChecker
from equity.models import EquityReport, WorkspaceEquityProfile
from workspaces.accounting_permissions import ORG_ROLE_CATEGORY_LEVELS, PERMISSION_CATEGORY_LEVELS, CATEGORY_KEYS, LEVEL_LABELS
from equity.scenario_services import get_scenario_overview
from .enterprise_reporting import (
    build_automation_cleanup_impact_report,
    build_enterprise_reporting_dashboard,
    execute_automation_workflow,
    export_enterprise_reporting_payload,
    normalize_schedule_trigger_config,
    run_due_automation_workflows,
)
from .platform_foundation import (
    cancel_platform_tasks_for_origin,
    log_platform_audit_event,
    sync_compliance_deadline_to_platform_task,
    sync_document_request_to_platform_task,
    sync_task_request_to_platform_task,
)
from .platform_tasks import create_task as create_platform_task_record, update_task as update_platform_task_record, transition_task as transition_platform_task



@lru_cache(maxsize=1)
def _teammember_invite_code_schema_ready():
    table_name = TeamMember._meta.db_table
    try:
        with connection.cursor() as cursor:
            columns = {column.name for column in connection.introspection.get_table_description(cursor, table_name)}
    except Exception:
        return False
    return {'invite_code_hash', 'invite_code_issued_at'}.issubset(columns)

def _accessible_organizations_queryset(user):
    if not user or not user.is_authenticated:
        return Organization.objects.none()

    return Organization.objects.filter(
        Q(owner=user) | Q(team_members__user=user, team_members__is_active=True)
    ).distinct()


def _has_global_dashboard_access(user):
    profile = getattr(user, 'profile', None)
    return bool(user and user.is_authenticated and (
        user.is_superuser or getattr(profile, 'platform_role', '') == 'admin'
    ))


def _is_department_scoped_employee(user):
    return bool(
        user and user.is_authenticated
        and UserProfile.objects.filter(user=user, platform_role=UserProfile.PLATFORM_ROLE_EMPLOYEE).exists()
    )


def _active_dashboard_grants_queryset(user, branch=None):
    queryset = DashboardAccessGrant.objects.filter(user=user, revoked_at__isnull=True).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now())
    ).filter(
        Q(invitation__isnull=True) | Q(invitation__accepted_at__isnull=False, invitation__is_active=True)
    )
    return queryset.filter(branch=branch) if branch else queryset


def _accessible_entities_queryset(user, organization=None):
    if not user or not user.is_authenticated:
        return Entity.objects.none()

    base_qs = Entity.objects.all()
    if organization is not None:
        base_qs = base_qs.filter(organization=organization)

    if _has_global_dashboard_access(user):
        return base_qs

    if _is_department_scoped_employee(user):
        granted_entity_ids = _active_dashboard_grants_queryset(user).filter(
            branch__in=[DashboardAccessGrant.BRANCH_ENTITY, DashboardAccessGrant.BRANCH_EQUITY]
        ).values_list('entity_id', flat=True)
        return base_qs.filter(id__in=granted_entity_ids).distinct()

    if organization is not None and organization.owner_id == user.id:
        return base_qs

    memberships = TeamMember.objects.filter(user=user, is_active=True)
    if organization is not None:
        memberships = memberships.filter(organization=organization)

    unrestricted_org_ids = []
    scoped_entity_ids = []
    for membership in memberships.prefetch_related('scoped_entities'):
        scoped_ids = list(membership.scoped_entities.values_list('id', flat=True))
        if scoped_ids:
            scoped_entity_ids.extend(scoped_ids)
        else:
            unrestricted_org_ids.append(membership.organization_id)

    return base_qs.filter(
        Q(organization__owner=user)
        | Q(organization_id__in=unrestricted_org_ids)
        | Q(id__in=scoped_entity_ids)
    ).distinct()


def _accessible_workspaces_queryset(user):
    if not user or not user.is_authenticated:
        return Workspace.objects.none()

    if _has_global_dashboard_access(user):
        return Workspace.objects.all()

    workspace_ids = _active_dashboard_grants_queryset(user, DashboardAccessGrant.BRANCH_WORKSPACE).values_list('workspace_id', flat=True)
    return Workspace.objects.filter(Q(owner=user) | Q(members__user=user) | Q(id__in=workspace_ids)).distinct()


def _fallback_permission_codes_for_role(role_code):
    all_permission_codes = [code for code, _ in Permission.PERMISSION_CHOICES]
    role_permission_map = {
        ROLE_ORG_OWNER: all_permission_codes,
        ROLE_CFO: [code for code in all_permission_codes if code != 'manage_billing'],
        ROLE_FINANCE_ANALYST: [
            'view_org_overview',
            'view_entities',
            'create_entity',
            'edit_entity',
            'view_tax_compliance',
            'edit_tax_compliance',
            'view_cashflow',
            'edit_cashflow',
            'view_risk_exposure',
            'view_reports',
            'generate_reports',
        ],
        ROLE_VIEWER: [
            'view_org_overview',
            'view_entities',
            'view_tax_compliance',
            'view_cashflow',
            'view_risk_exposure',
            'view_reports',
        ],
        ROLE_EXTERNAL_ADVISOR: [
            'view_tax_compliance',
            'view_reports',
        ],
    }
    return role_permission_map.get(role_code, [])


def _resolve_permission_codes(role_code, role=None):
    if role is not None:
        codes = list(role.permissions.values_list('code', flat=True))
        if codes:
            return codes
    return _fallback_permission_codes_for_role(role_code)


def _get_accessible_entity_or_404(user, entity_id, organization=None):
    return get_object_or_404(_accessible_entities_queryset(user, organization), id=entity_id)


def _filter_queryset_by_entity_scope(queryset, user, entity_relation='entity'):
    return queryset.filter(**{f'{entity_relation}__in': _accessible_entities_queryset(user)}).distinct()


def _assert_can_manage_entity_departments(user, entity):
    if entity.organization.owner_id == user.id:
        return
    membership = TeamMember.objects.filter(
        organization=entity.organization,
        user=user,
        is_active=True,
    ).select_related('role').first()
    permission_codes = _resolve_permission_codes(membership.role.code, membership.role) if membership else []
    if 'edit_entity' not in permission_codes:
        raise PermissionDenied('Department management requires entity management access.')


def _request_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def _verify_organization_domains_for_request(request):
    payload = request.data or {}
    settings_data = payload.get('settings') if isinstance(payload.get('settings'), dict) else {}
    email = payload.get('email') or settings_data.get('email')
    website = payload.get('website')
    result = verify_organization_domains(email, website)
    log_platform_audit_event(
        domain='identity',
        event_type='organization.domain_verification',
        action='organization_domain_verification',
        actor=request.user,
        resource_type='OrganizationDomainVerification',
        resource_id='',
        resource_name=result.get('website', {}).get('domain', ''),
        summary='Organization domain verification passed.' if result['status'] == 'success' else 'Organization domain verification failed.',
        metadata={
            'status': result['status'],
            'reason': result['reason'],
            'email_domain': result.get('email', {}).get('domain', ''),
            'website_domain': result.get('website', {}).get('domain', ''),
        },
    )
    if result['status'] == 'success':
        return

    errors = {}
    if result['email']['status'] != 'success':
        errors['email'] = [result['email']['reason']]
    if result['website']['status'] != 'success':
        errors['website'] = [result['website']['reason']]
    if result['match']['status'] != 'success' and result['email']['status'] == 'success' and result['website']['status'] == 'success':
        errors['website'] = [result['match']['reason']]
    raise ValidationError(errors or {'detail': result['reason']})


class OrganizationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing organizations"""
    serializer_class = OrganizationSerializer
    permission_classes = [IsAuthenticated]
    ORGANIZATION_DELETE_BLOCKERS = [
        ('entities', 'entities'),
        ('team_members', 'team members'),
        ('payroll_runs', 'payroll runs'),
        ('compliance_deadlines', 'compliance deadlines'),
        ('custom_kpis', 'custom KPIs'),
        ('consolidations', 'consolidations'),
        ('intercompany_transactions', 'intercompany transactions'),
        ('task_requests', 'task requests'),
        ('clients', 'clients'),
        ('client_documents', 'client documents'),
        ('document_templates', 'document templates'),
        ('services', 'services'),
        ('white_label_branding', 'white-label branding'),
        ('banking_integrations', 'banking integrations'),
        ('banking_consent_logs', 'banking consent logs'),
        ('automation_workflows', 'automation workflows'),
        ('automation_artifacts', 'automation artifacts'),
        ('firm_metrics', 'firm metrics'),
    ]

    def get_queryset(self):
        """Return organizations the user can access"""
        return _accessible_organizations_queryset(self.request.user)

    def create(self, request, *args, **kwargs):
        _verify_organization_domains_for_request(request)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """Create an organization for the authenticated user as its owner."""
        organization = serializer.save(owner=self.request.user)
        selected_tier = (organization.settings or {}).get('subscription_tier', 'basic')
        if selected_tier in {'basic', 'professional', 'enterprise'}:
            set_subscription_tier(organization, selected_tier)
        log_platform_audit_event(
            domain='identity',
            event_type='company.created',
            action='company_created',
            actor=self.request.user,
            organization=organization,
            resource_type='Organization',
            resource_id=str(organization.id),
            resource_name=organization.name,
            summary=f'Created company {organization.name}',
            metadata={
                'registration_number': organization.registration_number,
                'founder_id': self.request.user.id,
                'subscription_tier': selected_tier,
            },
        )

    @action(detail=False, methods=['post'])
    def verify_registration_number(self, request):
        """Validate an optional canonical company identity when one is supplied."""
        raw_registration_number = str(request.data.get('registration_number') or '').strip()
        try:
            registration_number = normalize_registration_number(raw_registration_number) if raw_registration_number else ''
        except Exception as error:
            raise ValidationError({'registration_number': str(error)})
        company_name = str(request.data.get('name') or '').strip()
        if not company_name:
            raise ValidationError({'name': 'Company name is required for identity verification.'})
        if not registration_number:
            return Response({
                'name': company_name,
                'name_available': not Organization.objects.filter(name__iexact=company_name).exists(),
                'registration_number': '',
                'valid': True,
                'available': True,
                'verification_source': 'not_provided',
                'external_registry_verified': False,
            })
        return Response({
            'name': company_name,
            'name_available': not Organization.objects.filter(name__iexact=company_name).exists(),
            'registration_number': registration_number,
            'valid': True,
            'available': not Organization.objects.filter(registration_number=registration_number).exists(),
            'verification_source': 'syntax',
            'external_registry_verified': False,
        })

    def _get_organization_delete_blockers(self, organization):
        blockers = []
        for accessor_name, label in self.ORGANIZATION_DELETE_BLOCKERS:
            relation = getattr(organization, accessor_name, None)
            if relation is None:
                continue

            if hasattr(relation, 'exists') and relation.exists():
                blockers.append(label)
                continue

            if hasattr(relation, 'pk') and relation.pk:
                blockers.append(label)

        return blockers

    def destroy(self, request, *args, **kwargs):
        organization = self.get_object()
        blockers = self._get_organization_delete_blockers(organization)

        if blockers:
            blocker_text = ', '.join(blockers)
            return Response(
                {
                    'detail': (
                        'This organization cannot be deleted because it still contains data. '
                        f'Remove the existing {blocker_text} first.'
                    ),
                    'blockers': blockers,
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=['get'])
    def permission_context(self, request, pk=None):
        organization = self.get_object()
        is_org_owner = organization.owner_id == request.user.id
        team_member = None
        if not is_org_owner:
            team_member = TeamMember.objects.select_related('role').prefetch_related('role__permissions', 'scoped_entities').filter(
                organization=organization,
                user=request.user,
                is_active=True,
            ).first()

        role_code = ROLE_ORG_OWNER if is_org_owner else getattr(getattr(team_member, 'role', None), 'code', None)
        role_name = 'Organization Owner' if is_org_owner else getattr(getattr(team_member, 'role', None), 'name', None)
        permission_codes = _resolve_permission_codes(role_code, getattr(team_member, 'role', None))

        levels = {key: 0 for key in CATEGORY_KEYS}
        for key, value in ORG_ROLE_CATEGORY_LEVELS.get(role_code, {}).items():
            levels[key] = max(levels[key], value)
        for permission_code in permission_codes:
            for key, value in PERMISSION_CATEGORY_LEVELS.get(permission_code, {}).items():
                levels[key] = max(levels[key], value)

        return Response({
            'organization_id': organization.id,
            'role_code': role_code,
            'role_name': role_name,
            'permission_codes': sorted(set(permission_codes)),
            'scoped_entity_ids': list(team_member.scoped_entities.values_list('id', flat=True)) if team_member else [],
            'categories': {
                key: {
                    'level': LEVEL_LABELS[levels[key]],
                    'read': levels[key] >= 1,
                    'write': levels[key] >= 2,
                    'manage': levels[key] >= 3,
                    'decide': levels[key] >= 4,
                }
                for key in CATEGORY_KEYS
            },
        })

    @action(detail=False, methods=['get'])
    def my_organizations(self, request):
        """Get all organizations current user owns"""
        organizations = self.get_queryset()
        serializer = self.get_serializer(organizations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def lobby(self, request):
        """Return all lobby tiles relevant to the current user."""
        if request.user.is_superuser:
            organizations = Organization.objects.all().select_related('owner')
        else:
            organizations = Organization.objects.filter(
                Q(owner=request.user) | Q(team_members__user=request.user)
            ).distinct().select_related('owner')

        organization_list = list(organizations.order_by('-created_at'))
        departments_by_organization = {}
        granted_department_ids = None
        if _is_department_scoped_employee(request.user):
            granted_department_ids = set(_active_dashboard_grants_queryset(request.user).filter(
                branch__in=[DashboardAccessGrant.BRANCH_ENTITY, DashboardAccessGrant.BRANCH_EQUITY],
                department__isnull=False,
            ).values_list('department_id', flat=True))
        if organization_list:
            department_queryset = EntityDepartment.objects.filter(
                entity__organization__in=organization_list,
                is_active=True,
            )
            if granted_department_ids is not None:
                department_queryset = department_queryset.filter(id__in=granted_department_ids)
            for department in department_queryset.select_related('entity').order_by('name'):
                departments_by_organization.setdefault(department.entity.organization_id, []).append({
                    'id': department.id,
                    'name': department.name,
                    'department_code': department.department_code,
                    'entity_id': department.entity_id,
                    'entity_name': department.entity.name,
                })
        invite_schema_ready = _teammember_invite_code_schema_ready()
        membership_rows = {}
        if organization_list:
            membership_queryset = TeamMember.objects.filter(
                organization__in=organization_list,
                user=request.user,
            ).values('organization_id', 'is_active', 'accepted_at')
            if invite_schema_ready:
                membership_queryset = membership_queryset.values('organization_id', 'is_active', 'accepted_at', 'role__code')
            membership_rows = {row['organization_id']: row for row in membership_queryset}

        items = []
        for organization in organization_list:
            membership = membership_rows.get(organization.id)
            if request.user.is_superuser or organization.owner_id == request.user.id:
                status_label = 'active'
            elif membership and membership.get('accepted_at') and membership.get('is_active'):
                status_label = 'active'
            elif membership:
                status_label = 'invited'
            else:
                status_label = 'locked'

            item = OrganizationSerializer(organization, context={'request': request}).data
            item.update({
                'status': status_label,
                'role_code': membership.get('role__code') if membership else ('ORG_OWNER' if organization.owner_id == request.user.id else None),
                'has_invite_code': False,
                'can_unlock': False,
                'can_manage': bool(request.user.is_superuser or organization.owner_id == request.user.id),
                'departments': departments_by_organization.get(organization.id, []),
            })
            items.append(item)

        return Response({
            'role': 'SUPER_USER' if request.user.is_superuser else 'MEMBER',
            'items': items,
        })

    @action(detail=False, methods=['post'], url_path='dashboard-entry')
    def dashboard_entry(self, request):
        """Authorize and audit movement into an isolated dashboard branch."""
        payload = request.data or {}
        branch = str(payload.get('branch') or '').strip().lower()
        if branch not in dict(DashboardAccessGrant.BRANCH_CHOICES):
            raise ValidationError({'branch': 'Branch must be workspace, entity, or equity.'})

        organization = None
        entity = None
        workspace_id = None
        department = None
        if branch in {DashboardAccessGrant.BRANCH_ENTITY, DashboardAccessGrant.BRANCH_EQUITY}:
            entity = _get_accessible_entity_or_404(request.user, payload.get('entity_id'))
            organization = entity.organization
            department_id = payload.get('department_id')
            if department_id not in (None, ''):
                department = get_object_or_404(EntityDepartment, id=department_id, entity=entity, is_active=True)
                if _is_department_scoped_employee(request.user) and not _active_dashboard_grants_queryset(request.user, branch).filter(
                    entity=entity,
                    department=department,
                ).exists():
                    raise PermissionDenied('This dashboard is not granted for the selected department.')
        else:
            workspace = get_object_or_404(_accessible_workspaces_queryset(request.user), id=payload.get('workspace_id'))
            workspace_id = workspace.id
            organization = workspace.linked_entity.organization if workspace.linked_entity_id else None

        log_platform_audit_event(
            domain='identity',
            event_type='dashboard.entered',
            action='dashboard_entered',
            actor=request.user,
            organization=organization,
            entity=entity,
            workspace_id=workspace_id,
            resource_type='Dashboard',
            resource_id=str(entity.id if entity else workspace_id),
            resource_name=branch,
            summary=f'{request.user.get_username()} entered the {branch} dashboard',
            metadata={
                'branch': branch,
                'department_code': department.department_code if department else '',
                'actor_public_user_id': getattr(getattr(request.user, 'profile', None), 'public_user_id', ''),
            },
        )
        return Response({'allowed': True, 'branch': branch})

    @action(detail=False, methods=['post'])
    def unlock(self, request):
        """Accept a pending lobby invitation using the issued code."""
        if not _teammember_invite_code_schema_ready():
            raise ValidationError({'detail': 'Invite code unlocking requires the latest database migration.'})

        payload = request.data or {}
        organization_id = payload.get('organization_id')
        invite_code = str(payload.get('code') or '').strip()
        if not organization_id or not invite_code:
            raise ValidationError({'detail': 'organization_id and code are required.'})

        organization = get_object_or_404(
            Organization.objects.select_related('owner'),
            pk=organization_id,
        )
        member = get_object_or_404(
            TeamMember.objects.select_related('role', 'user'),
            organization=organization,
            user=request.user,
        )

        if member.accepted_at and member.is_active:
            return Response({'status': 'active', 'organization_id': organization.id})

        if not member.check_invite_code(invite_code):
            return Response({'detail': 'Invalid code.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        member.is_active = True
        member.accepted_at = timezone.now()
        member.save(update_fields=['is_active', 'accepted_at', 'updated_at'])
        log_platform_audit_event(
            domain='identity',
            event_type='organization.invitation_accepted',
            action='organization_invitation_accepted',
            actor=request.user,
            organization=organization,
            resource_type='TeamMember',
            resource_id=str(member.id),
            resource_name=organization.name,
            summary=f'{request.user.email} unlocked access to {organization.name}',
            metadata={'organization_id': organization.id, 'role_code': member.role.code},
        )
        return Response({
            'status': 'active',
            'organization_id': organization.id,
            'organization': OrganizationSerializer(organization, context={'request': request}).data,
        })

    def _require_governance_configuration_owner(self, organization, user):
        if organization.owner_id != user.id:
            raise PermissionDenied('Only the organization owner can export or restore governance configuration.')

    @action(detail=True, methods=['get'])
    def directory(self, request, pk=None):
        organization = self.get_object()
        from .directory_service import sync_organization_directory

        sync_organization_directory(organization)
        return Response([
            {
                'id': entry.id,
                'dn': entry.dn,
                'uid': entry.uid,
                'cn': entry.cn,
                'node_type': entry.node_type,
                'role_code': entry.role_code,
                'permissions': entry.permissions,
                'parent_id': entry.parent_id,
                'entity_id': entry.entity_id,
                'user_id': entry.user_id,
                'attributes': entry.attributes,
                'is_active': entry.is_active,
            }
            for entry in organization.directory_entries.select_related('parent').order_by('dn')
        ])

    @action(detail=True, methods=['post'])
    def create_directory_office(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        from django.utils.text import slugify
        from .directory_service import _organization_dn, sync_organization_directory

        office_name = str(request.data.get('name') or '').strip()
        office_key = slugify(office_name)
        if not office_key:
            raise ValidationError({'name': 'An office name is required.'})
        root = sync_organization_directory(organization)
        entry, created = OrganizationDirectoryEntry.objects.get_or_create(
            organization=organization,
            source_type='manual_office',
            source_id=office_key,
            defaults={
                'parent': root,
                'node_type': 'office',
                'dn': f'ou={office_key},{_organization_dn(organization)}',
                'cn': office_name,
                'attributes': {'office_key': office_key},
            },
        )
        if not created:
            raise ValidationError({'name': 'An office with this name already exists.'})
        log_platform_audit_event(
            domain='identity', event_type='directory.office_created', action='directory_office_created',
            actor=request.user, organization=organization, resource_type='OrganizationDirectoryEntry',
            resource_id=str(entry.id), resource_name=entry.cn,
            summary=f'Created directory office: {entry.cn}', metadata={'dn': entry.dn},
        )
        return Response({'id': entry.id, 'dn': entry.dn, 'cn': entry.cn}, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def assign_directory_role(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        from .directory_service import ensure_governance_roles

        user_id = request.data.get('user_id')
        role_code = str(request.data.get('role_code') or '').upper()
        if not user_id or not role_code:
            raise ValidationError({'detail': 'user_id and role_code are required.'})
        member_user = get_object_or_404(User, pk=user_id)
        if member_user.id == organization.owner_id:
            raise ValidationError({'user_id': 'The founder role is bound to the organization owner and cannot be reassigned.'})

        ensure_governance_roles()
        role = get_object_or_404(Role, code=role_code)
        if role.code in {'ORG_OWNER', 'FOUNDER'}:
            raise ValidationError({'role_code': 'Founder and organization-owner roles are reserved.'})
        member, created = TeamMember.objects.update_or_create(
            organization=organization,
            user=member_user,
            defaults={'role': role, 'is_active': True, 'accepted_at': timezone.now()},
        )
        scoped_entity_ids = request.data.get('scoped_entity_ids') or []
        if scoped_entity_ids:
            member.scoped_entities.set(Entity.objects.filter(organization=organization, id__in=scoped_entity_ids))
        else:
            member.scoped_entities.clear()

        log_platform_audit_event(
            domain='identity', event_type='directory.role_assigned', action='directory_role_assigned',
            actor=request.user, organization=organization, resource_type='TeamMember', resource_id=str(member.id),
            resource_name=member_user.get_full_name() or member_user.username,
            summary=f'Assigned {role.code} in {organization.name}',
            metadata={'user_id': member_user.id, 'role_code': role.code, 'created': created},
        )
        return Response({
            'user_id': member_user.id,
            'role_code': role.code,
            'scoped_entity_ids': list(member.scoped_entities.values_list('id', flat=True)),
        }, status=drf_status.HTTP_201_CREATED if created else drf_status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def export_governance_yaml(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        from .directory_service import sync_organization_directory
        from .governance_configurations import refresh_governance_configuration

        sync_organization_directory(organization)
        configuration = refresh_governance_configuration(organization)
        GovernanceCloudExport.objects.create(
            organization=organization,
            requested_by=request.user,
            provider='local_download',
            status='completed',
            file_name=f'org-{organization.id}-config.yml',
            checksum=configuration.checksum,
            destination='Local download',
        )
        log_platform_audit_event(
            domain='governance', event_type='governance.exported', action='governance_exported',
            actor=request.user, organization=organization, resource_type='GovernanceConfiguration',
            resource_id=str(configuration.id), resource_name=configuration.configuration_file.name,
            summary=f'Exported governance YAML for {organization.name}', metadata={'provider': 'local_download'},
        )
        response = FileResponse(configuration.configuration_file.open('rb'), content_type='application/x-yaml')
        response['Content-Disposition'] = f'attachment; filename="org-{organization.id}-config.yml"'
        return response

    @action(detail=True, methods=['post'])
    def export_governance_cloud(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        from .directory_service import sync_organization_directory

        sync_organization_directory(organization)
        export_record = export_governance_yaml(organization, request.user, request.data or {})
        log_platform_audit_event(
            domain='governance', event_type='governance.cloud_exported', action='governance_cloud_exported',
            actor=request.user, organization=organization, resource_type='GovernanceCloudExport',
            resource_id=str(export_record.id), resource_name=export_record.file_name,
            summary=f'Exported governance YAML to {export_record.get_provider_display()}',
            metadata={'provider': export_record.provider, 'destination': export_record.destination, 'checksum': export_record.checksum},
        )
        return Response({
            'id': export_record.id,
            'provider': export_record.provider,
            'file_name': export_record.file_name,
            'destination': export_record.destination,
            'remote_reference': export_record.remote_reference,
            'checksum': export_record.checksum,
            'created_at': export_record.created_at,
        }, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def governance_cloud_exports(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        return Response([
            {
                'id': export_record.id,
                'provider': export_record.provider,
                'status': export_record.status,
                'file_name': export_record.file_name,
                'destination': export_record.destination,
                'remote_reference': export_record.remote_reference,
                'overwrite_confirmed': export_record.overwrite_confirmed,
                'created_at': export_record.created_at,
            }
            for export_record in organization.governance_cloud_exports.select_related('requested_by')[:50]
        ])

    @action(detail=True, methods=['get'])
    def email_service(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        accounts = organization.email_accounts.filter(is_active=True)
        campaigns = organization.email_campaigns.select_related('sender').all()[:25]
        deliveries = organization.email_deliveries.select_related('campaign', 'sender').all()[:50]
        return Response({
            'subscription': subscription_summary(organization),
            'accounts': [
                {
                    'id': account.id,
                    'address': account.address,
                    'display_name': account.display_name,
                    'is_active': account.is_active,
                    'created_at': account.created_at,
                }
                for account in accounts
            ],
            'campaigns': [
                {
                    'id': campaign.id,
                    'campaign_type': campaign.campaign_type,
                    'sender_id': campaign.sender_id,
                    'sender_address': campaign.sender.address,
                    'subject': campaign.subject,
                    'recipient_count': len(campaign.recipients or []),
                    'consent_confirmed': campaign.consent_confirmed,
                    'status': campaign.status,
                    'sent_at': campaign.sent_at,
                    'created_at': campaign.created_at,
                }
                for campaign in campaigns
            ],
            'deliveries': [
                {
                    'id': delivery.id,
                    'campaign_id': delivery.campaign_id,
                    'sender_address': delivery.sender.address if delivery.sender else '',
                    'recipient': delivery.recipient,
                    'subject': delivery.subject,
                    'event_type': delivery.event_type,
                    'status': delivery.status,
                    'opened_at': delivery.opened_at,
                    'sent_at': delivery.sent_at,
                    'created_at': delivery.created_at,
                }
                for delivery in deliveries
            ],
        })

    @action(detail=True, methods=['post'])
    def configure_email_subscription(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        subscription = set_subscription_tier(
            organization,
            str(request.data.get('tier') or '').lower(),
            request.data.get('billing_reference'),
        )
        log_platform_audit_event(
            domain='email', event_type='email.subscription_configured', action='email_subscription_configured',
            actor=request.user, organization=organization, resource_type='OrganizationEmailSubscription',
            resource_id=str(subscription.id), resource_name=subscription.get_tier_display(),
            summary=f'Configured {subscription.get_tier_display()} email service tier',
            metadata={'tier': subscription.tier, 'billing_reference_present': bool(subscription.billing_reference)},
        )
        return Response({'subscription': subscription_summary(organization)})

    @action(detail=True, methods=['post'])
    def provision_email_account(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        account = provision_email_account(
            organization,
            request.user,
            request.data.get('local_part'),
            request.data.get('display_name'),
        )
        return Response({
            'id': account.id,
            'address': account.address,
            'display_name': account.display_name,
            'is_active': account.is_active,
            'created_at': account.created_at,
        }, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def send_email_campaign(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        campaign, deliveries = send_campaign(organization, request.user, request.data or {})
        return Response({
            'id': campaign.id,
            'status': campaign.status,
            'recipient_count': len(deliveries),
            'sent_count': sum(delivery.status == 'sent' for delivery in deliveries),
            'failed_count': sum(delivery.status == 'failed' for delivery in deliveries),
            'sent_at': campaign.sent_at,
        }, status=drf_status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def import_governance_yaml(self, request, pk=None):
        organization = self.get_object()
        self._require_governance_configuration_owner(organization, request.user)
        uploaded_file = request.FILES.get('file')
        if uploaded_file is None:
            raise ValidationError({'file': 'A YAML configuration file is required.'})
        if uploaded_file.size > 5 * 1024 * 1024:
            raise ValidationError({'file': 'Configuration files must not exceed 5 MB.'})

        import yaml
        try:
            document = yaml.safe_load(uploaded_file.read().decode('utf-8'))
        except (UnicodeDecodeError, yaml.YAMLError) as error:
            raise ValidationError({'file': 'Upload a valid UTF-8 YAML configuration file.'}) from error

        configuration = restore_governance_document(organization, document)
        return Response({
            'schema_version': configuration.schema_version,
            'revision': configuration.revision,
            'generated_at': configuration.generated_at,
        })

    @action(detail=True, methods=['get'])
    def workspaces(self, request, pk=None):
        """Return the current user's accessible workspaces for an organization."""
        organization = self.get_object()
        from workspaces.models import Workspace
        from workspaces.serializers import WorkspaceSerializer

        queryset = (
            Workspace.objects.filter(linked_entity__organization=organization)
            .filter(members__user=request.user)
            .exclude(status='deleted')
            .select_related('linked_entity', 'owner')
            .distinct()
        )
        serializer = WorkspaceSerializer(queryset, many=True)
        return Response({
            'count': len(serializer.data),
            'results': serializer.data,
        })

    @action(detail=True, methods=['get'])
    def overview(self, request, pk=None):
        """Get organization overview/dashboard data"""
        organization = self.get_object()
        accessible_entities = _accessible_entities_queryset(request.user, organization)
        entities = accessible_entities.filter(status='active')
        
        # Gather data
        total_entities = entities.count()
        total_jurisdictions = entities.values('country').distinct().count()

        # Tax exposure
        tax_exposures = TaxExposure.objects.filter(entity__in=accessible_entities)
        total_tax_exposure = tax_exposures.aggregate(
            total=Sum('estimated_amount')
        )['total'] or 0

        # Compliance
        pending_returns = ComplianceDeadline.objects.filter(
            entity__in=accessible_entities,
            status__in=['upcoming', 'overdue']
        ).count()
        
        missing_data = entities.filter(registration_number='').count()

        # Tax by country
        tax_by_country = {}
        for exposure in tax_exposures:
            key = exposure.country
            if key not in tax_by_country:
                tax_by_country[key] = 0
            tax_by_country[key] += float(exposure.estimated_amount or 0)

        overview_data = {
            'total_assets': 0,
            'total_liabilities': 0,
            'net_position': 0,
            'total_cash_by_currency': {},
            'total_tax_exposure': float(total_tax_exposure),
            'active_jurisdictions': total_jurisdictions,
            'active_entities': total_entities,
            'pending_tax_returns': pending_returns,
            'missing_data_entities': missing_data,
            'tax_exposure_by_country': tax_by_country,
        }

        serializer = OrgOverviewSerializer(overview_data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def accounting_dashboard(self, request, pk=None):
        """Return a consolidated financial accounting dashboard payload.

        This endpoint is optimized for the new overview dashboard and replaces
        the client-side fan-out/aggregation pattern with one organization-scoped
        response.
        """
        organization = self.get_object()
        accessible_entities = _accessible_entities_queryset(request.user, organization)
        today = timezone.now().date()
        month_start = today.replace(day=1)
        previous_month_start = (month_start - timedelta(days=1)).replace(day=1)
        year_start = today.replace(month=1, day=1)

        def _safe_float(value):
            return float(value or 0)

        def _format_currency(value, currency='USD'):
            amount = Decimal(str(value or 0))
            if currency == 'USD':
                if abs(amount) >= Decimal('1000000'):
                    return f"${float(amount) / 1000000:.2f}M"
                return f"${float(amount):,.0f}"
            if abs(amount) >= Decimal('1000000'):
                return f"{currency} {float(amount) / 1000000:.2f}M"
            return f"{currency} {float(amount):,.0f}"

        def _format_count(value):
            return f"{int(value or 0):,}"

        def _capitalize(value):
            return (value or '').replace('_', ' ').title()

        def _trend(current, previous, invert=False):
            current = _safe_float(current)
            previous = _safe_float(previous)
            delta = current - previous

            if previous == 0:
                if current == 0:
                    return {'direction': 'flat', 'value': '0%'}
                return {'direction': 'down' if invert else 'up', 'value': 'New'}

            percentage = abs((delta / previous) * 100)
            if percentage < 0.5:
                return {'direction': 'flat', 'value': f'{percentage:.1f}%'}

            rising = delta > 0
            direction = ('down' if rising else 'up') if invert else ('up' if rising else 'down')
            return {'direction': direction, 'value': f'{percentage:.1f}%'}

        def _days_between(later, earlier):
            if not later or not earlier:
                return 0
            return max(0, (later - earlier).days)

        def _relative_time(value):
            if not value:
                return 'Recently'

            if isinstance(value, datetime):
                dt = value
            else:
                dt = datetime.combine(value, datetime.min.time())

            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())

            seconds = max(0, int((timezone.now() - dt).total_seconds()))
            if seconds < 60:
                return f'{seconds}s ago'
            minutes = seconds // 60
            if minutes < 60:
                return f'{minutes}m ago'
            hours = minutes // 60
            if hours < 24:
                return f'{hours}h ago'
            return f'{hours // 24}d ago'

        def _health_score(overdue_invoices, overdue_bills, pending_deadlines, recon_exceptions, missing_docs):
            overdue_ar_penalty = min(20, overdue_invoices * 2.5)
            ap_penalty = min(15, overdue_bills * 1.2)
            deadline_penalty = min(20, pending_deadlines * 4)
            recon_penalty = min(20, recon_exceptions * 5)
            doc_penalty = min(10, missing_docs * 2)
            return max(0, round(100 - overdue_ar_penalty - ap_penalty - deadline_penalty - recon_penalty - doc_penalty))

        def _build_series(rows, period):
            buckets = []
            bucket_keys = []

            if period == 'weekly':
                start = today - timedelta(days=6)
                for offset in range(7):
                    key = (start + timedelta(days=offset)).isoformat()
                    bucket_keys.append(key)
                    buckets.append({'inflows': 0.0, 'outflows': 0.0})

                def bucket_index(date_value):
                    diff = (date_value - start).days
                    if diff < 0 or diff > 6:
                        return None
                    return diff

            elif period == 'monthly':
                start = today - timedelta(days=49)
                for offset in range(8):
                    key = (start + timedelta(days=offset * 7)).isoformat()
                    bucket_keys.append(key)
                    buckets.append({'inflows': 0.0, 'outflows': 0.0})

                def bucket_index(date_value):
                    diff = (date_value - start).days
                    if diff < 0:
                        return None
                    return min(7, diff // 7)

            else:
                start = month_start
                for offset in range(5, -1, -1):
                    month_cursor = (start.replace(day=1) - timedelta(days=offset * 31)).replace(day=1)
                    key = month_cursor.strftime('%Y-%m')
                    if key not in bucket_keys:
                        bucket_keys.append(key)
                        buckets.append({'inflows': 0.0, 'outflows': 0.0})

                lookup = {key: index for index, key in enumerate(bucket_keys)}

                def bucket_index(date_value):
                    key = date_value.strftime('%Y-%m')
                    return lookup.get(key)

            for row in rows:
                tx_date = row['date']
                index = bucket_index(tx_date)
                if index is None:
                    continue
                amount = _safe_float(row['amount'])
                if row['type'] == 'income':
                    buckets[index]['inflows'] += amount
                elif row['type'] == 'expense':
                    buckets[index]['outflows'] += amount

            inflow = [round(bucket['inflows'], 2) for bucket in buckets]
            outflow = [round(bucket['outflows'], 2) for bucket in buckets]
            forecast = []
            for index in range(len(inflow)):
                start_index = max(0, index - 2)
                sample = inflow[start_index:index + 1]
                average = sum(sample) / max(1, len(sample))
                forecast.append(round(average, 2))

            return {'inflow': inflow, 'outflow': outflow, 'forecast': forecast}

        entities = list(accessible_entities.filter(status='active').values('id', 'name'))
        entity_name_by_id = {entity['id']: entity['name'] for entity in entities}
        entity_count = len(entities)

        bank_accounts = list(
            BankAccount.objects.filter(entity__in=accessible_entities, is_active=True).values(
                'id', 'entity_id', 'account_name', 'currency', 'balance'
            )
        )
        wallets = list(
            Wallet.objects.filter(entity__in=accessible_entities, is_active=True).values(
                'id', 'entity_id', 'name', 'currency', 'balance'
            )
        )
        transactions = list(
            Transaction.objects.filter(entity__in=accessible_entities, date__gte=year_start).values(
                'id', 'entity_id', 'type', 'amount', 'currency', 'description', 'date', 'created_at'
            )
        )
        journals = list(
            JournalEntry.objects.filter(entity__in=accessible_entities).order_by('-created_at').values(
                'id', 'entity_id', 'reference_number', 'description', 'posting_date', 'status', 'created_at'
            )[:20]
        )
        invoices = []
        for inv in Invoice.objects.filter(entity__in=accessible_entities).select_related('customer').order_by('-invoice_date')[:50]:
            invoices.append({
                'id': inv.id,
                'entity_id': inv.entity_id,
                'customer_name': inv.customer.name if inv.customer else 'N/A',
                'invoice_number': inv.invoice_number,
                'invoice_date': inv.invoice_date,
                'due_date': inv.due_date,
                'total_amount': inv.total_amount,
                'outstanding_amount': inv.outstanding_amount,
                'currency': inv.currency,
                'status': inv.status,
            })
        
        bills = []
        for bill in Bill.objects.filter(entity__in=accessible_entities).select_related('vendor').order_by('-bill_date')[:50]:
            bills.append({
                'id': bill.id,
                'entity_id': bill.entity_id,
                'vendor_name': bill.vendor.name if bill.vendor else 'N/A',
                'bill_number': bill.bill_number,
                'bill_date': bill.bill_date,
                'due_date': bill.due_date,
                'total_amount': bill.total_amount,
                'outstanding_amount': bill.outstanding_amount,
                'currency': bill.currency,
                'status': bill.status,
            })
        reconciliations = list(
            BankReconciliation.objects.filter(entity__in=accessible_entities)
            .select_related('bank_account')
            .order_by('bank_account_id', '-reconciliation_date')
            .values(
                'id', 'entity_id', 'bank_account_id', 'bank_account__account_name', 'reconciliation_date',
                'status', 'variance', 'reconciled_at'
            )
        )
        task_requests = list(
            TaskRequest.objects.filter(
                Q(organization=organization, entity__isnull=True) | Q(entity__in=accessible_entities)
            ).order_by('-created_at').values(
                'id', 'entity_id', 'task_type', 'status', 'priority', 'created_at'
            )[:20]
        )
        notifications = list(
            Notification.objects.filter(user=request.user, organization=organization, status='unread')
            .order_by('-sent_at')
            .values('id', 'notification_type', 'priority', 'title', 'message', 'sent_at')[:20]
        )
        documents = list(
            ComplianceDocument.objects.filter(entity__in=accessible_entities).order_by('expiry_date').values(
                'id', 'entity_id', 'title', 'document_type', 'issuing_authority', 'status', 'file_path', 'expiry_date'
            )[:20]
        )
        close_checklists = list(
            PeriodCloseChecklist.objects.filter(entity__in=accessible_entities)
            .select_related('period')
            .order_by('-created_at')
            .values('id', 'entity_id', 'period__period_name', 'status')[:20]
        )
        deadlines = list(
            ComplianceDeadline.objects.filter(
                Q(organization=organization, entity__isnull=True) | Q(entity__in=accessible_entities),
                status__in=['upcoming', 'overdue']
            )
            .order_by('deadline_date')
            .values('id', 'entity_id', 'title', 'deadline_date', 'status')[:20]
        )

        cash_by_currency = defaultdict(float)
        for account in bank_accounts:
            cash_by_currency[account['currency'] or 'USD'] += _safe_float(account['balance'])
        for wallet in wallets:
            cash_by_currency[wallet['currency'] or 'USD'] += _safe_float(wallet['balance'])

        total_cash = sum(cash_by_currency.values())

        open_invoices = [invoice for invoice in invoices if invoice['status'] not in ['paid', 'cancelled']]
        open_bills = [bill for bill in bills if bill['status'] not in ['paid', 'cancelled']]
        overdue_invoices = [invoice for invoice in open_invoices if invoice['status'] == 'overdue' or invoice['due_date'] < today]
        overdue_bills = [bill for bill in open_bills if bill['status'] == 'overdue' or bill['due_date'] < today]

        ar_outstanding = sum(_safe_float(invoice.get('outstanding_amount') or invoice.get('total_amount')) for invoice in open_invoices)
        ap_outstanding = sum(_safe_float(bill.get('outstanding_amount') or bill.get('total_amount')) for bill in open_bills)
        overdue_ar_amount = sum(_safe_float(invoice.get('outstanding_amount') or invoice.get('total_amount')) for invoice in overdue_invoices)
        overdue_ap_amount = sum(_safe_float(bill.get('outstanding_amount') or bill.get('total_amount')) for bill in overdue_bills)

        receivable_dso = round(
            sum(_days_between(today, invoice['invoice_date']) for invoice in open_invoices) / max(1, len(open_invoices))
        ) if open_invoices else 0
        payable_dpo = round(
            sum(_days_between(today, bill['bill_date']) for bill in open_bills) / max(1, len(open_bills))
        ) if open_bills else 0

        mtd_transactions = [row for row in transactions if row['date'] >= month_start]
        previous_month_transactions = [
            row for row in transactions if previous_month_start <= row['date'] < month_start
        ]

        total_income_mtd = sum(_safe_float(row['amount']) for row in mtd_transactions if row['type'] == 'income')
        total_expense_mtd = sum(_safe_float(row['amount']) for row in mtd_transactions if row['type'] == 'expense')
        total_income_previous = sum(_safe_float(row['amount']) for row in previous_month_transactions if row['type'] == 'income')
        total_expense_previous = sum(_safe_float(row['amount']) for row in previous_month_transactions if row['type'] == 'expense')
        total_income_ytd = sum(_safe_float(row['amount']) for row in transactions if row['type'] == 'income')
        total_expense_ytd = sum(_safe_float(row['amount']) for row in transactions if row['type'] == 'expense')
        net_income_mtd = total_income_mtd - total_expense_mtd
        net_income_previous = total_income_previous - total_expense_previous
        net_income_ytd = total_income_ytd - total_expense_ytd
        treasury_net_cashflow = total_income_mtd - total_expense_mtd
        prior_cash_position = max(0, total_cash - treasury_net_cashflow)

        reconciliation_by_bank = {}
        for item in reconciliations:
            bank_id = item['bank_account_id']
            if bank_id not in reconciliation_by_bank:
                reconciliation_by_bank[bank_id] = item

        reconciliation_items = []
        for account in bank_accounts[:4]:
            latest = reconciliation_by_bank.get(account['id'])
            if not latest:
                reconciliation_items.append({
                    'name': account['account_name'],
                    'status': f"No reconciliation recorded for {entity_name_by_id.get(account['entity_id'], 'entity')}",
                    'badge': 'Pending',
                    'tone': 'pending',
                })
                continue

            variance = _safe_float(latest['variance'])
            if variance > 0:
                reconciliation_items.append({
                    'name': latest['bank_account__account_name'] or account['account_name'],
                    'status': f"{_format_currency(variance, account['currency'] or 'USD')} variance requires review",
                    'badge': 'Review',
                    'tone': 'error',
                })
            elif latest['status'] == 'reconciled':
                reconciliation_items.append({
                    'name': latest['bank_account__account_name'] or account['account_name'],
                    'status': f"Reconciled {_relative_time(latest['reconciled_at'] or latest['reconciliation_date'])}",
                    'badge': 'OK',
                    'tone': 'ok',
                })
            else:
                reconciliation_items.append({
                    'name': latest['bank_account__account_name'] or account['account_name'],
                    'status': f"Status: {_capitalize(latest['status'])}",
                    'badge': 'Pending',
                    'tone': 'pending',
                })

        reconciliation_exceptions = sum(1 for item in reconciliation_items if item['tone'] == 'error')
        pending_deadlines = len(deadlines)
        missing_documents = sum(1 for document in documents if not document['file_path'])
        health_score = _health_score(len(overdue_invoices), len(overdue_bills), pending_deadlines, reconciliation_exceptions, missing_documents)

        health_badges = [
            {'label': 'Liquidity stable' if health_score >= 80 else 'Liquidity watch', 'tone': 'ok' if health_score >= 80 else 'warn'},
            {'label': 'AR follow-up required' if overdue_ar_amount > 0 else 'AR current', 'tone': 'warn' if overdue_ar_amount > 0 else 'ok'},
            {'label': 'Compliance open' if pending_deadlines > 0 else 'Compliance current', 'tone': 'danger' if pending_deadlines > 0 else 'ok'},
        ]

        chart_series = {
            'weekly': _build_series(transactions, 'weekly'),
            'monthly': _build_series(transactions, 'monthly'),
            'quarterly': _build_series(transactions, 'quarterly'),
        }

        kpis = [
            {
                'id': 'cash',
                'label': 'Total Cash Position',
                'value': _format_currency(total_cash),
                'sublabel': f"{_format_count(len(bank_accounts) + len(wallets))} cash accounts",
                'trend': _trend(total_cash, prior_cash_position),
                'iconKey': 'wallet',
                'details': [
                    {'label': currency, 'value': _format_currency(amount, currency)}
                    for currency, amount in list(cash_by_currency.items())[:2]
                ],
            },
            {
                'id': 'ar',
                'label': 'Accounts Receivable',
                'value': _format_currency(ar_outstanding),
                'sublabel': f"{_format_count(len(open_invoices))} open invoices",
                'trend': _trend(ar_outstanding, overdue_ar_amount or (ar_outstanding * 0.8), invert=True),
                'iconKey': 'file',
                'details': [
                    {'label': 'Overdue', 'value': _format_currency(overdue_ar_amount), 'tone': 'danger' if overdue_ar_amount > 0 else ''},
                    {'label': 'DSO', 'value': f'{receivable_dso} days', 'tone': 'warning' if receivable_dso > 45 else ''},
                ],
            },
            {
                'id': 'ap',
                'label': 'Accounts Payable',
                'value': _format_currency(ap_outstanding),
                'sublabel': f"{_format_count(len(open_bills))} unpaid bills",
                'trend': _trend(ap_outstanding, overdue_ap_amount or (ap_outstanding * 0.85), invert=True),
                'iconKey': 'clock',
                'details': [
                    {'label': 'Overdue', 'value': _format_currency(overdue_ap_amount), 'tone': 'danger' if overdue_ap_amount > 0 else ''},
                    {'label': 'DPO', 'value': f'{payable_dpo} days', 'tone': 'warning' if payable_dpo > 35 else ''},
                ],
            },
            {
                'id': 'income',
                'label': 'Net Income',
                'value': _format_currency(net_income_mtd),
                'sublabel': f"MTD / YTD {_format_currency(net_income_ytd)}",
                'trend': _trend(net_income_mtd, net_income_previous),
                'iconKey': 'arrowUp',
                'details': [
                    {'label': 'Revenue', 'value': _format_currency(total_income_mtd)},
                    {'label': 'Expenses', 'value': _format_currency(total_expense_mtd)},
                ],
            },
            {
                'id': 'cashflow',
                'label': 'Operating Cash Flow',
                'value': _format_currency(treasury_net_cashflow),
                'sublabel': 'Current operating period',
                'trend': _trend(treasury_net_cashflow, net_income_previous or (treasury_net_cashflow * 0.9)),
                'iconKey': 'exchange',
                'details': [
                    {'label': 'Inflows', 'value': _format_currency(total_income_mtd)},
                    {'label': 'Outflows', 'value': _format_currency(total_expense_mtd)},
                ],
            },
            {
                'id': 'health',
                'label': 'Financial Health Score',
                'value': f'{health_score} / 100',
                'sublabel': f'{pending_deadlines + reconciliation_exceptions} active risk signals',
                'trend': {'direction': 'up' if health_score >= 80 else 'flat' if health_score >= 65 else 'down', 'value': 'Stable' if health_score >= 80 else 'Moderate' if health_score >= 65 else 'Elevated'},
                'iconKey': 'robot',
                'score': health_score,
                'badges': health_badges,
            },
        ]

        feed_items = []
        for transaction in transactions:
            feed_items.append({
                'id': f"txn-{transaction['id']}",
                'type': 'Bank',
                'title': transaction['description'] or f"{_capitalize(transaction['type'])} transaction",
                'meta': f"{entity_name_by_id.get(transaction['entity_id'], 'Entity')} · {_relative_time(transaction['created_at'] or transaction['date'])}",
                'amount': f"{'-' if transaction['type'] == 'expense' else '+'}{_format_currency(transaction['amount'], transaction['currency'] or 'USD')}",
                'tone': 'negative' if transaction['type'] == 'expense' else 'positive',
                'context': 'cash',
                'sort_at': transaction['created_at'] or datetime.combine(transaction['date'], datetime.min.time()),
            })

        for journal in journals:
            feed_items.append({
                'id': f"je-{journal['id']}",
                'type': 'Journals',
                'title': journal['description'] or f"Journal {journal['reference_number']}",
                'meta': f"{entity_name_by_id.get(journal['entity_id'], 'Entity')} · {_capitalize(journal['status'])} · {_relative_time(journal['created_at'] or journal['posting_date'])}",
                'amount': _capitalize(journal['status']),
                'tone': 'positive' if journal['status'] == 'posted' else 'neutral',
                'context': 'income',
                'sort_at': journal['created_at'] or datetime.combine(journal['posting_date'], datetime.min.time()),
            })

        for invoice in invoices:
            feed_items.append({
                'id': f"ar-{invoice['id']}",
                'type': 'AR',
                'title': f"{invoice['invoice_number']} · {invoice['customer_name']}",
                'meta': f"{_capitalize(invoice['status'])} · Due {invoice['due_date'].isoformat()}",
                'amount': _format_currency(invoice.get('outstanding_amount') or invoice.get('total_amount'), invoice['currency'] or 'USD'),
                'tone': 'negative' if invoice['status'] == 'overdue' or invoice['due_date'] < today else 'positive',
                'context': 'ar',
                'sort_at': datetime.combine(invoice['invoice_date'], datetime.min.time()),
            })

        for bill in bills:
            feed_items.append({
                'id': f"ap-{bill['id']}",
                'type': 'AP',
                'title': f"{bill['bill_number']} · {bill['vendor_name']}",
                'meta': f"{_capitalize(bill['status'])} · Due {bill['due_date'].isoformat()}",
                'amount': _format_currency(bill.get('outstanding_amount') or bill.get('total_amount'), bill['currency'] or 'USD'),
                'tone': 'negative' if bill['status'] == 'overdue' or bill['due_date'] < today else 'neutral',
                'context': 'ap',
                'sort_at': datetime.combine(bill['bill_date'], datetime.min.time()),
            })

        feed_items = sorted(feed_items, key=lambda item: item['sort_at'], reverse=True)[:12]
        for item in feed_items:
            item.pop('sort_at', None)

        task_items = []
        for task in task_requests[:6]:
            task_items.append({
                'id': f"task-{task['id']}",
                'title': _capitalize(task['task_type']),
                'sub': f"{entity_name_by_id.get(task['entity_id'], organization.name)} · {_capitalize(task['status'])}",
                'priority': 'urgent' if task['priority'] in ['urgent', 'high'] else 'normal' if task['priority'] == 'normal' else 'pending',
                'badgeLabel': _capitalize(task['priority'] or task['status']),
                'done': task['status'] == 'completed',
                'context': 'cash' if task['task_type'] == 'import_bank_feed' else 'income' if task['task_type'] == 'generate_statement' else 'health',
            })

        for invoice in invoices:
            if len(task_items) >= 6:
                break
            if invoice['status'] == 'draft':
                task_items.append({
                    'id': f"invoice-{invoice['id']}",
                    'title': f"Send invoice {invoice['invoice_number']}",
                    'sub': f"{invoice['customer_name']} · Draft invoice",
                    'priority': 'normal',
                    'badgeLabel': 'Normal',
                    'done': False,
                    'context': 'ar',
                })

        for bill in bills:
            if len(task_items) >= 6:
                break
            if bill['status'] == 'draft':
                task_items.append({
                    'id': f"bill-{bill['id']}",
                    'title': f"Approve bill {bill['bill_number']}",
                    'sub': f"{bill['vendor_name']} · Draft bill",
                    'priority': 'pending',
                    'badgeLabel': 'Pending',
                    'done': False,
                    'context': 'ap',
                })

        for checklist in close_checklists:
            if len(task_items) >= 6:
                break
            if checklist['status'] != 'completed':
                task_items.append({
                    'id': f"close-{checklist['id']}",
                    'title': f"Close period {checklist['period__period_name']}",
                    'sub': f"{entity_name_by_id.get(checklist['entity_id'], organization.name)} · {_capitalize(checklist['status'])}",
                    'priority': 'urgent' if checklist['status'] == 'in_progress' else 'pending',
                    'badgeLabel': _capitalize(checklist['status']),
                    'done': False,
                    'context': 'health',
                })

        alert_items = []
        for deadline in deadlines:
            alert_items.append({
                'id': f"deadline-{deadline['id']}",
                'title': deadline['title'],
                'desc': f"{entity_name_by_id.get(deadline['entity_id'], organization.name)} · due {deadline['deadline_date'].isoformat()}",
                'level': 'error' if deadline['status'] == 'overdue' or deadline['deadline_date'] < today else 'warning',
                'action': 'Open deadline',
                'context': 'health',
            })

        for notification in notifications:
            if len(alert_items) >= 6:
                break
            level = 'error' if notification['priority'] in ['critical', 'high'] else 'warning' if notification['priority'] == 'medium' else 'info'
            alert_items.append({
                'id': f"notification-{notification['id']}",
                'title': notification['title'],
                'desc': notification['message'],
                'level': level,
                'action': 'Review',
                'context': 'income' if notification['notification_type'] == 'approval_request' else 'health',
            })

        for index, recon in enumerate(reconciliation_items):
            if len(alert_items) >= 6:
                break
            if recon['tone'] == 'error':
                alert_items.append({
                    'id': f"recon-{index}",
                    'title': f"{recon['name']} exception",
                    'desc': recon['status'],
                    'level': 'error',
                    'action': 'Review',
                    'context': 'cash',
                })

        document_items = []
        for document in documents[:6]:
            if not document['file_path']:
                status = 'pending'
                context = 'health'
            elif document['status'] == 'expired' or (document['expiry_date'] and document['expiry_date'] < today):
                status = 'overdue'
                context = 'health'
            else:
                status = 'completed'
                context = 'cash'

            document_items.append({
                'id': f"document-{document['id']}",
                'name': document['title'],
                'sub': f"{entity_name_by_id.get(document['entity_id'], organization.name)} · {document['issuing_authority'] or _capitalize(document['document_type'])}",
                'status': status,
                'context': context,
            })

        top_customer = sorted(overdue_invoices, key=lambda invoice: _safe_float(invoice.get('outstanding_amount') or invoice.get('total_amount')), reverse=True)[0] if overdue_invoices else None
        top_vendor = sorted(overdue_bills, key=lambda bill: _safe_float(bill.get('outstanding_amount') or bill.get('total_amount')), reverse=True)[0] if overdue_bills else None
        largest_cash_account = sorted(
            [
                {'name': account['account_name'], 'balance': account['balance'], 'currency': account['currency']}
                for account in bank_accounts
            ] + [
                {'name': wallet['name'], 'balance': wallet['balance'], 'currency': wallet['currency']}
                for wallet in wallets
            ],
            key=lambda item: _safe_float(item['balance']),
            reverse=True
        )[0] if (bank_accounts or wallets) else None

        right_panel_content = {
            'cash': {
                'title': 'Cash Context',
                'stats': [
                    {'label': 'Largest account', 'value': f"{largest_cash_account['name']} · {_format_currency(largest_cash_account['balance'], largest_cash_account['currency'] or 'USD')}" if largest_cash_account else 'No cash accounts'},
                    {'label': '7-day forecast', 'value': _format_currency(total_cash + chart_series['weekly']['forecast'][-1])},
                    {'label': 'Exceptions', 'value': _format_count(reconciliation_exceptions)},
                ],
                'insight': 'Cash is funded, but unresolved reconciliation variance is suppressing confidence in the reported bank position.' if reconciliation_exceptions else 'Cash coverage is healthy and reconciliations are largely under control.',
                'nextStep': 'Resolve reconciliation exceptions' if reconciliation_exceptions else 'Review cash forecast sensitivity',
                'route': '/app/subledgers/cash-bank',
            },
            'ar': {
                'title': 'Receivables Context',
                'stats': [
                    {'label': 'Open invoices', 'value': _format_count(len(open_invoices))},
                    {'label': 'Top overdue customer', 'value': top_customer['customer_name'] if top_customer else 'None'},
                    {'label': 'Overdue exposure', 'value': _format_currency(overdue_ar_amount)},
                ],
                'insight': 'Collections pressure is concentrated in a small number of overdue invoices and should be escalated before the next close cut-off.' if overdue_ar_amount else 'Receivables are broadly current with no material overdue concentration.',
                'nextStep': 'Initiate customer collections follow-up' if overdue_ar_amount else 'Review invoice pipeline',
                'route': '/app/billing/invoices',
            },
            'ap': {
                'title': 'Payables Context',
                'stats': [
                    {'label': 'Unpaid bills', 'value': _format_count(len(open_bills))},
                    {'label': 'Largest overdue vendor', 'value': top_vendor['vendor_name'] if top_vendor else 'None'},
                    {'label': 'Overdue exposure', 'value': _format_currency(overdue_ap_amount)},
                ],
                'insight': 'Outstanding vendor balances are approaching policy thresholds and may affect service continuity if approvals slip further.' if overdue_ap_amount else 'Payables remain within terms and do not currently signal vendor stress.',
                'nextStep': 'Approve next vendor payment batch' if overdue_ap_amount else 'Review AP scheduling',
                'route': '/app/billing/bills',
            },
            'income': {
                'title': 'Earnings Context',
                'stats': [
                    {'label': 'MTD revenue', 'value': _format_currency(total_income_mtd)},
                    {'label': 'MTD expense', 'value': _format_currency(total_expense_mtd)},
                    {'label': 'YTD net income', 'value': _format_currency(net_income_ytd)},
                ],
                'insight': 'The current period remains profitable, with earnings supported by real transaction volume rather than placeholder values.' if net_income_mtd >= 0 else 'The current period is loss-making and expense control needs immediate attention.',
                'nextStep': 'Review journal approvals and margin drivers',
                'route': '/app/accounting/journal-entries',
            },
            'cashflow': {
                'title': 'Cash Flow Context',
                'stats': [
                    {'label': 'Current inflows', 'value': _format_currency(total_income_mtd)},
                    {'label': 'Current outflows', 'value': _format_currency(total_expense_mtd)},
                    {'label': 'Net operating cash', 'value': _format_currency(treasury_net_cashflow)},
                ],
                'insight': 'Operating cash generation is positive and aligned with recent transaction activity.' if treasury_net_cashflow >= 0 else 'Operating cash flow is negative in the current period and requires treasury intervention.',
                'nextStep': 'Validate short-term forecast and large disbursements',
                'route': '/app/reporting/analytics',
            },
            'health': {
                'title': 'Health Context',
                'stats': [
                    {'label': 'Health score', 'value': f'{health_score} / 100'},
                    {'label': 'Open compliance items', 'value': _format_count(pending_deadlines)},
                    {'label': 'Unread alerts', 'value': _format_count(len(notifications))},
                ],
                'insight': 'The operating posture is controlled, with remaining risk concentrated in routine compliance and approval queues.' if health_score >= 80 else 'The health score is being dragged down by overdue receivables, unresolved deadlines, or bank exceptions that need action.',
                'nextStep': 'Clear highest-risk queue first',
                'route': '/app/compliance/tax-center',
            },
        }

        return Response({
            'summary': {
                'financialHealth': 'Stable with contained risk exposure' if health_score >= 80 else 'Stable with moderate operational risk' if health_score >= 65 else 'Elevated risk requires immediate review',
                'immediateAttention': f"{_format_count(len(alert_items))} alerts and {_format_count(sum(1 for item in task_items if not item['done']))} open workflow items",
                'liveActivity': f"{_format_count(len(feed_items))} material accounting events across {_format_count(entity_count)} entities",
                'nextAction': next((item['title'] for item in task_items if not item['done']), 'No urgent workflow blockers'),
            },
            'kpis': kpis,
            'chartSeries': chart_series,
            'reconciliationItems': reconciliation_items,
            'feedItems': feed_items,
            'taskItems': task_items,
            'alertItems': alert_items,
            'documentItems': document_items,
            'rightPanelContent': right_panel_content,
            'metadata': {
                'organizationName': organization.name,
                'defaultContext': 'cash',
                'lastUpdated': timezone.now().isoformat(),
                'entityCount': entity_count,
            },
        })


class PlatformTaskViewSet(viewsets.ModelViewSet):
    """Unified task API for cross-domain work queues."""

    serializer_class = PlatformTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        accessible_workspaces = _accessible_workspaces_queryset(self.request.user).values_list('id', flat=True)
        queryset = PlatformTask.objects.filter(
            Q(organization__in=accessible_orgs)
            | Q(workspace_id__in=accessible_workspaces)
            | Q(assigned_to=self.request.user)
            | Q(created_by=self.request.user)
        ).select_related('organization', 'entity', 'assigned_to', 'created_by').distinct()

        organization_id = self.request.query_params.get('organization') or self.request.query_params.get('organization_id')
        entity_id = self.request.query_params.get('entity') or self.request.query_params.get('entity_id')
        workspace_id = self.request.query_params.get('workspace_id')
        status_filter = self.request.query_params.get('state') or self.request.query_params.get('status')
        assigned_to = self.request.query_params.get('assignee_id') or self.request.query_params.get('assigned_to')
        domain = self.request.query_params.get('domain')
        task_type = self.request.query_params.get('type') or self.request.query_params.get('task_type')
        department_name = self.request.query_params.get('department_name') or self.request.query_params.get('department')
        cost_center = self.request.query_params.get('cost_center')
        origin_type = self.request.query_params.get('origin_type') or self.request.query_params.get('source_object_type')
        origin_id = self.request.query_params.get('origin_id') or self.request.query_params.get('source_object_id')
        search_query = self.request.query_params.get('q')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if assigned_to:
            queryset = queryset.filter(assignee_id=str(assigned_to))
        if domain:
            queryset = queryset.filter(domain=domain)
        if task_type:
            queryset = queryset.filter(task_type=task_type)
        if department_name:
            queryset = queryset.filter(metadata__department_name=department_name)
        if cost_center:
            queryset = queryset.filter(metadata__cost_center=cost_center)
        if origin_type:
            queryset = queryset.filter(origin_type=origin_type)
        if origin_id:
            queryset = queryset.filter(origin_id=str(origin_id))
        if search_query:
            queryset = queryset.filter(Q(title__icontains=search_query) | Q(description__icontains=search_query))
        return queryset

    def create(self, request, *args, **kwargs):
        organization = None
        entity = None
        workspace = None

        org_id = self.request.data.get('organization') or self.request.data.get('organization_id')
        entity_id = self.request.data.get('entity') or self.request.data.get('entity_id')
        workspace_id = self.request.data.get('workspace_id')

        if entity_id:
            entity = _get_accessible_entity_or_404(self.request.user, entity_id)
            organization = entity.organization
        elif org_id:
            organization = get_object_or_404(_accessible_organizations_queryset(self.request.user), id=org_id)

        if workspace_id:
            workspace = get_object_or_404(_accessible_workspaces_queryset(self.request.user), id=workspace_id)

        task = create_platform_task_record(
            {
                **request.data,
                'organization': organization,
                'entity': entity,
                'workspace_id': getattr(workspace, 'id', None),
                'created_by': self.request.user,
            },
            actor=self.request.user,
        )
        serializer = self.get_serializer(task)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=drf_status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        task = self.get_object()
        task = update_platform_task_record(task, request.data, actor=request.user)
        return Response(self.get_serializer(task).data)

    def partial_update(self, request, *args, **kwargs):
        task = self.get_object()
        task = update_platform_task_record(task, request.data, actor=request.user)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        task = self.get_object()
        task = transition_platform_task(task, 'in_progress', actor=request.user)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        task = self.get_object()
        task = transition_platform_task(task, 'completed', actor=request.user, metadata_patch={'completion_note': request.data.get('completion_note')} if request.data.get('completion_note') else None)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        task = self.get_object()
        task = transition_platform_task(task, 'cancelled', actor=request.user)
        return Response(self.get_serializer(task).data)

    @action(detail=True, methods=['get'])
    def firm_dashboard(self, request, pk=None):
        """Comprehensive firm dashboard: clients, workload, staff performance"""
        organization = self.get_object()
        accessible_entities = _accessible_entities_queryset(request.user, organization)
        now = timezone.now()

        # ── Clients ──────────────────────────────────────────────────────────
        clients_qs = Client.objects.filter(organization=organization)
        total_clients = clients_qs.count()
        active_clients = clients_qs.filter(status='active').count()
        inactive_clients = clients_qs.filter(status='inactive').count()
        prospect_clients = clients_qs.filter(status='prospect').count()
        recent_clients = list(
            clients_qs.order_by('-created_at').values(
                'id', 'name', 'status', 'email', 'industry', 'created_at'
            )[:10]
        )
        for c in recent_clients:
            if c.get('created_at'):
                c['created_at'] = c['created_at'].isoformat()

        # ── Workload ──────────────────────────────────────────────────────────
        tasks_qs = TaskRequest.objects.filter(entity__in=accessible_entities)
        workload = {
            'total': tasks_qs.count(),
            'pending': tasks_qs.filter(status='pending').count(),
            'in_progress': tasks_qs.filter(status='in_progress').count(),
            'completed': tasks_qs.filter(status='completed').count(),
            'overdue': tasks_qs.filter(
                status__in=['pending', 'in_progress'],
                due_date__lt=now.date()
            ).count(),
        }
        # Tasks by entity
        workload_by_entity = list(
            tasks_qs.values('entity__name').annotate(count=Count('id')).order_by('-count')[:10]
        )

        # ── Staff Performance ─────────────────────────────────────────────────
        staff_qs = EntityStaff.objects.filter(entity__in=accessible_entities)
        total_staff = staff_qs.count()
        # tasks assigned per staff member
        staff_performance = []
        for staff in staff_qs.select_related('entity')[:20]:
            assigned = TaskRequest.objects.filter(
                entity=staff.entity,
                assigned_to=staff.user if staff.user else None,
                status__in=['pending', 'in_progress']
            ).count()
            completed = TaskRequest.objects.filter(
                entity=staff.entity,
                assigned_to=staff.user if staff.user else None,
                status='completed'
            ).count()
            staff_performance.append({
                'id': staff.id,
                'name': staff.name or (staff.user.get_full_name() if staff.user else ''),
                'email': staff.email or (staff.user.email if staff.user else ''),
                'role': staff.role.name if staff.role else '',
                'entity': staff.entity.name,
                'tasks_assigned': assigned,
                'tasks_completed': completed,
                'is_active': staff.is_active,
            })

        # ── Billing summary ────────────────────────────────────────────────────
        invoices_qs = ClientInvoice.objects.filter(organization=organization)
        billing = {
            'total_invoiced': float(invoices_qs.aggregate(t=Sum('total_amount'))['t'] or 0),
            'total_paid': float(invoices_qs.filter(status='paid').aggregate(t=Sum('total_amount'))['t'] or 0),
            'overdue_count': invoices_qs.filter(status='overdue').count(),
        }

        return Response({
            'clients': {
                'total': total_clients,
                'active': active_clients,
                'inactive': inactive_clients,
                'prospects': prospect_clients,
                'recent': recent_clients,
            },
            'workload': {
                **workload,
                'by_entity': workload_by_entity,
            },
            'staff': {
                'total': total_staff,
                'performance': staff_performance,
            },
            'billing': billing,
        })

    @action(detail=True, methods=['get'])
    def risk_exposure(self, request, pk=None):
        """Risk & Exposure dashboard computed from real data.

        Returns a stable shape with zero/empty defaults when no data exists.
        """
        organization = self.get_object()
        accessible_entities = _accessible_entities_queryset(request.user, organization)

        exposures_qs = TaxExposure.objects.filter(entity__in=accessible_entities)
        totals_by_country = list(
            exposures_qs.values('country')
            .annotate(total=Sum('estimated_amount'))
            .order_by('-total')
        )

        total_tax_exposure = Decimal('0')
        for row in totals_by_country:
            total_tax_exposure += (row.get('total') or Decimal('0'))

        # Compliance deadline counts (used for alerts + risk scores)
        deadline_counts = defaultdict(int)
        deadlines_qs = ComplianceDeadline.objects.filter(
            entity__in=accessible_entities,
            status__in=['upcoming', 'due_soon', 'overdue'],
        )
        for row in (
            deadlines_qs.values('entity__country', 'status')
            .annotate(count=Count('id'))
        ):
            country = row.get('entity__country') or ''
            status = row.get('status') or ''
            if country and status:
                deadline_counts[(country, status)] += int(row.get('count') or 0)

        # Concentration risk: top 3 countries share
        top_rows = totals_by_country[:3]
        top_total = Decimal('0')
        for row in top_rows:
            top_total += (row.get('total') or Decimal('0'))

        if total_tax_exposure > 0:
            top3_percentage = int(round((top_total / total_tax_exposure) * 100))
        else:
            top3_percentage = 0

        largest_exposures = []
        for row in top_rows:
            amount = row.get('total') or Decimal('0')
            if total_tax_exposure > 0:
                pct = int(round((amount / total_tax_exposure) * 100))
            else:
                pct = 0
            largest_exposures.append({
                'country': row.get('country') or '',
                'percentage': pct,
                'amount': float(amount),
            })

        # Country risks list
        country_risks = []
        for row in totals_by_country:
            country = row.get('country') or ''
            exposure_amount = row.get('total') or Decimal('0')
            if not country:
                continue

            share_pct = float((exposure_amount / total_tax_exposure) * 100) if total_tax_exposure > 0 else 0.0
            overdue = deadline_counts.get((country, 'overdue'), 0)
            due_soon = deadline_counts.get((country, 'due_soon'), 0)
            upcoming = deadline_counts.get((country, 'upcoming'), 0)

            # Simple, explainable scoring: exposure share + compliance pressure.
            # Scale is 0-100; thresholds match the frontend legend.
            risk_score = int(round(min(100.0, (share_pct * 1.2) + (overdue * 20) + (due_soon * 12) + (upcoming * 6))))
            if risk_score < 20:
                status = 'low'
            elif risk_score < 30:
                status = 'medium'
            else:
                status = 'high'

            alerts = int(overdue + due_soon + upcoming)
            country_risks.append({
                'country': country,
                'exposure': float(exposure_amount),
                'risk_score': risk_score,
                'status': status,
                'alerts': alerts,
            })

        # Compliance alerts list (overdue + upcoming next 30 days)
        today = timezone.now().date()
        window_end = today + timedelta(days=30)
        alerts_qs = ComplianceDeadline.objects.filter(entity__in=accessible_entities).exclude(status='completed')
        alerts_qs = alerts_qs.filter(Q(status='overdue') | Q(deadline_date__lte=window_end))
        alerts_qs = alerts_qs.filter(status__in=['upcoming', 'due_soon', 'overdue']).order_by('deadline_date')

        compliance_alerts = []
        for deadline in alerts_qs:
            if deadline.status == 'overdue':
                alert_type = 'Overdue Filing'
                severity = 'high'
            elif deadline.status == 'due_soon':
                alert_type = 'Filing Deadline'
                severity = 'medium'
            else:
                alert_type = 'Filing Deadline'
                severity = 'medium'

            compliance_alerts.append({
                'id': deadline.id,
                'country': getattr(deadline.entity, 'country', '') or '',
                'type': alert_type,
                'description': deadline.description or deadline.title,
                'severity': severity,
            })

        # FX exposure from bank accounts + wallets (by currency)
        balances_by_currency = defaultdict(Decimal)
        for acct in BankAccount.objects.filter(entity__in=accessible_entities, is_active=True):
            currency = acct.currency or 'USD'
            balances_by_currency[currency] += (acct.balance or Decimal('0'))

        for wallet in Wallet.objects.filter(entity__in=accessible_entities, is_active=True):
            currency = wallet.currency or 'USD'
            balances_by_currency[currency] += (wallet.balance or Decimal('0'))

        total_fx_exposure = Decimal('0')
        for amt in balances_by_currency.values():
            total_fx_exposure += (amt or Decimal('0'))

        fx_by_currency = []
        for currency, amount in sorted(balances_by_currency.items(), key=lambda kv: kv[1], reverse=True):
            if total_fx_exposure > 0:
                concentration = int(round((amount / total_fx_exposure) * 100))
            else:
                concentration = 0
            fx_by_currency.append({
                'currency': currency,
                'exposure': float(amount),
                'concentration': concentration,
            })

        dashboard = {
            'concentration_risk': {
                'top3_percentage': top3_percentage,
                'countries_with_exposure': len(totals_by_country),
                'largest_exposures': largest_exposures,
            },
            'country_risks': country_risks,
            'compliance_alerts': compliance_alerts,
            'fx_exposure': {
                'total_exposure': float(total_fx_exposure),
                'by_currency': fx_by_currency,
            },
        }

        return Response(dashboard)


class EntityViewSet(viewsets.ModelViewSet):
    """ViewSet for managing entities"""
    serializer_class = EntitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return entities accessible to the user."""
        queryset = _accessible_entities_queryset(self.request.user)
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset

    def perform_create(self, serializer):
        """Create entity for organization"""
        from django.db import IntegrityError
        from rest_framework.exceptions import ValidationError
        from equity.models import WorkspaceEquityProfile
        from workspaces.services import WorkspaceService
        from workspaces.type_registry import get_workspace_type_definition
        
        org_id = self.request.data.get('organization_id')
        if not org_id:
            raise ValidationError({'organization_id': 'This field is required.'})

        requested_workspace_type = (self.request.data.get('workspace_type') or '').strip()
        workspace_type_definition = get_workspace_type_definition(requested_workspace_type)
        department_selections = validate_department_selections(self.request.data.get('department_selections'))

        enabled_modules = self.request.data.get('enabled_modules') or [
            'overview', 'members', 'groups', 'meetings', 'calendar',
            'files', 'permissions', 'settings', 'email', 'marketing',
        ]
        if workspace_type_definition:
            enabled_modules = list(dict.fromkeys([*workspace_type_definition['modules'], *enabled_modules]))
        
        # Get the organization owned by the current user
        organization = get_object_or_404(Organization, id=org_id, owner=self.request.user)

        # Validate registration number uniqueness per country (NOT name)
        registration_number = (self.request.data.get('registration_number') or '').strip()
        country = (self.request.data.get('country') or '').strip()
        if registration_number and country:
            if Entity.objects.filter(registration_number=registration_number, country=country).exists():
                raise ValidationError({
                    'detail': 'This registration number is already used for an entity in this country.'
                })

        try:
            parent_entity = None
            parent_entity_id = self.request.data.get('parent_entity') or self.request.data.get('parent_entity_id')
            if parent_entity_id not in (None, ''):
                parent_entity = get_object_or_404(Entity, pk=parent_entity_id, organization=organization)

            hierarchy_metadata = self.request.data.get('hierarchy_metadata') or {}
            if workspace_type_definition:
                hierarchy_metadata = {
                    **hierarchy_metadata,
                    'workspace_type': requested_workspace_type,
                    'workspace_type_label': workspace_type_definition['label'],
                    'template_key': workspace_type_definition['template_key'],
                    'available_branches': workspace_type_definition['branches'],
                }

            entity = serializer.save(
                organization=organization,
                enabled_modules=enabled_modules,
                parent_entity=parent_entity,
                industry=(self.request.data.get('industry') or (workspace_type_definition or {}).get('industry_label') or '').strip(),
                workspace_type=requested_workspace_type,
                workspace_template_key=(workspace_type_definition or {}).get('template_key', ''),
                hierarchy_metadata=hierarchy_metadata,
                dashboard_config=self.request.data.get('dashboard_config') or ({'dashboards': workspace_type_definition['dashboards']} if workspace_type_definition else {}),
                rbac_config=self.request.data.get('rbac_config') or ((workspace_type_definition or {}).get('rbac') or {}),
            )
            # Create default structure for the new entity
            entity.create_default_structure()
            WorkspaceService.ensure_workspace_for_entity(entity)
            provision_selected_departments(entity, self.request.user, department_selections)

            # Create a default tax profile for the entity country
            regime_defaults = build_regime_rules(entity.country)
            TaxProfile.objects.get_or_create(
                entity=entity,
                country=entity.country,
                defaults={
                    'status': 'active',
                    'compliance_score': 0,
                    'jurisdiction_code': regime_defaults['jurisdiction_code'],
                    'tax_rules': regime_defaults['tax_rules'],
                    'registered_regimes': regime_defaults['regime_codes'],
                    'registration_numbers': regime_defaults['registration_numbers'],
                    'filing_preferences': regime_defaults['filing_preferences'],
                    'auto_update': True,
                    'residency_status': 'detected',
                },
            )

            WorkspaceEquityProfile.objects.get_or_create(
                workspace=entity,
                defaults={
                    'workspace_type': entity.workspace_mode,
                    'equity_enabled': any(str(module).startswith('equity_') for module in enabled_modules),
                    'ownership_registry_enabled': 'equity_registry' in enabled_modules,
                    'cap_table_enabled': 'equity_cap_table' in enabled_modules,
                    'valuation_enabled': 'equity_valuation' in enabled_modules,
                    'equity_transactions_enabled': 'equity_transactions' in enabled_modules,
                    'governance_reporting_enabled': 'equity_governance' in enabled_modules,
                },
            )
        except IntegrityError:
            raise ValidationError({
                'detail': 'Entity could not be created due to a data conflict. Please check your input and try again.'
            })

    @action(detail=True, methods=['get'])
    def hierarchy(self, request, pk=None):
        """Get entity details"""
        entity = self.get_object()
        serializer = EntityDetailSerializer(entity)
        return Response(serializer.data)


class TeamMemberViewSet(viewsets.ModelViewSet):
    """ViewSet for managing team members"""
    serializer_class = TeamMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return team members for organizations the user owns, or the user's own membership."""
        queryset = TeamMember.objects.filter(
            Q(organization__owner=self.request.user) | Q(user=self.request.user)
        ).distinct()
        org_id = self.request.query_params.get('organization_id')
        if org_id:
            queryset = queryset.filter(organization_id=org_id)
        return queryset

    def perform_create(self, serializer):
        """Add team member"""
        org_id = self.request.data.get('organization_id')
        organization = get_object_or_404(Organization, id=org_id, owner=self.request.user)
        serializer.save(organization=organization)


class TaxExposureViewSet(viewsets.ModelViewSet):
    """ViewSet for tax exposure tracking"""
    serializer_class = TaxExposureSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return tax exposures for user's organizations"""
        qs = _filter_queryset_by_entity_scope(TaxExposure.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class TaxProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for managing entity tax profiles"""
    serializer_class = TaxProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = _filter_queryset_by_entity_scope(TaxProfile.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity') or self.request.data.get('entity_id')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        request_regime_codes = self.request.data.get('registered_regimes') or self.request.data.get('regime_codes') or []
        defaults = build_regime_rules(entity.country, regime_codes=request_regime_codes)
        serializer.save(
            entity=entity,
            country=self.request.data.get('country') or entity.country,
            jurisdiction_code=self.request.data.get('jurisdiction_code') or defaults['jurisdiction_code'],
            effective_from=parse_date(self.request.data.get('effective_from')) if self.request.data.get('effective_from') else None,
            effective_to=parse_date(self.request.data.get('effective_to')) if self.request.data.get('effective_to') else None,
            tax_rules=self.request.data.get('tax_rules') or defaults['tax_rules'],
            registered_regimes=request_regime_codes or defaults['regime_codes'],
            registration_numbers=self.request.data.get('registration_numbers') or defaults['registration_numbers'],
            filing_preferences=self.request.data.get('filing_preferences') or defaults['filing_preferences'],
        )

    @action(detail=False, methods=['get'])
    def by_country(self, request):
        """Get tax exposure grouped by country"""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id required'}, status=400)
            
        organization = get_object_or_404(_accessible_organizations_queryset(request.user), id=org_id)
        
        exposures = TaxExposure.objects.filter(entity__in=_accessible_entities_queryset(request.user, organization))
        grouped = {}
        for exposure in exposures:
            country = exposure.country
            if country not in grouped:
                grouped[country] = {'total': 0, 'count': 0, 'entities': []}
            grouped[country]['total'] += float(exposure.estimated_amount or 0)
            grouped[country]['count'] += 1
            grouped[country]['entities'].append(exposure.entity.name)

        return Response(grouped)


class TaxRegimeRegistryViewSet(viewsets.ModelViewSet):
    """Global registry of tax regimes by jurisdiction."""

    serializer_class = TaxRegimeRegistrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = TaxRegimeRegistry.objects.all().order_by('jurisdiction_code', 'regime_name')
        country = self.request.query_params.get('country')
        jurisdiction_code = self.request.query_params.get('jurisdiction_code')
        regime_code = self.request.query_params.get('regime_code')
        tax_type = self.request.query_params.get('tax_type')
        is_active = self.request.query_params.get('is_active')

        if country:
            qs = qs.filter(country__iexact=country)
        if jurisdiction_code:
            qs = qs.filter(jurisdiction_code__iexact=jurisdiction_code)
        if regime_code:
            qs = qs.filter(regime_code__iexact=regime_code)
        if tax_type:
            qs = qs.filter(tax_type__iexact=tax_type)
        if is_active in {'true', 'false'}:
            qs = qs.filter(is_active=is_active == 'true')
        return qs

    def perform_create(self, serializer):
        if not can_manage_global_tax_rules(self.request.user):
            raise PermissionDenied('User does not have permission to manage global tax rules.')
        serializer.save()

    def perform_update(self, serializer):
        if not can_manage_global_tax_rules(self.request.user):
            raise PermissionDenied('User does not have permission to manage global tax rules.')
        serializer.save()

    def perform_destroy(self, instance):
        if not can_manage_global_tax_rules(self.request.user):
            raise PermissionDenied('User does not have permission to manage global tax rules.')
        super().perform_destroy(instance)

    def perform_destroy(self, instance):
        if not can_manage_global_tax_rules(self.request.user):
            raise PermissionDenied('User does not have permission to manage global tax rules.')
        super().perform_destroy(instance)


class TaxCalculationHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaxCalculationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = _filter_queryset_by_entity_scope(TaxCalculation.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class TaxFilingViewSet(viewsets.ModelViewSet):
    serializer_class = TaxFilingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = _filter_queryset_by_entity_scope(TaxFiling.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('entity') or self.request.data.get('entity_id'))
        serializer.save(entity=entity)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        filing = self.get_object()
        filing.submission_status = request.data.get('submission_status') or 'submitted'
        if filing.submission_status == 'submitted' and filing.submitted_at is None:
            filing.submitted_at = request.data.get('submitted_at') or timezone.now()
        if request.data.get('reference_number'):
            filing.reference_number = request.data.get('reference_number')
        filing.save(update_fields=['submission_status', 'submitted_at', 'reference_number', 'updated_at'])

        log_tax_audit(
            entity=filing.entity,
            user=request.user,
            action_type='submit',
            new_value_json={
                'tax_filing_id': str(filing.id),
                'submission_status': filing.submission_status,
            },
            reason='Tax filing submitted through the enterprise API.',
            ip_address=request.META.get('REMOTE_ADDR'),
            device_metadata=build_device_metadata(request),
        )

        return Response(TaxFilingSerializer(filing).data)


class TaxAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TaxAuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        organization_id = self.request.query_params.get('organization_id')
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        organization = None
        if organization_id:
            organization = get_object_or_404(_accessible_organizations_queryset(self.request.user), id=organization_id)
        elif entity_id:
            entity = _get_accessible_entity_or_404(self.request.user, entity_id)
            organization = entity.organization
        else:
            organization = _accessible_organizations_queryset(self.request.user).first()

        if organization is None or not can_view_partial_tax_audit(self.request.user, organization):
            raise PermissionDenied('User does not have tax audit visibility.')
        qs = _filter_queryset_by_entity_scope(TaxAuditLog.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class TaxRuleSetVersionViewSet(viewsets.ModelViewSet):
    serializer_class = TaxRuleSetVersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_countries = list(_accessible_entities_queryset(self.request.user).values_list('country', flat=True).distinct())
        qs = TaxRuleSetVersion.objects.select_related('registry', 'approved_by', 'created_by').all()
        if accessible_countries:
            qs = qs.filter(registry__country__in=accessible_countries)
        registry_id = self.request.query_params.get('registry_id')
        if registry_id:
            qs = qs.filter(registry_id=registry_id)
        status_filter = self.request.query_params.get('approval_status')
        if status_filter:
            qs = qs.filter(approval_status=status_filter)
        return qs

    def perform_create(self, serializer):
        registry = serializer.validated_data['registry']
        organization = _accessible_organizations_queryset(self.request.user).filter(entities__country=registry.country).first()
        if organization is None or not can_manage_tax_rule_sets(self.request.user, organization):
            raise PermissionDenied('User does not have permission to manage tax rule sets.')
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = self.get_object()
        organization = _accessible_organizations_queryset(self.request.user).filter(entities__country=instance.registry.country).first()
        if organization is None or not can_manage_tax_rule_sets(self.request.user, organization):
            raise PermissionDenied('User does not have permission to manage tax rule sets.')
        serializer.save()


class TaxRiskAlertViewSet(viewsets.ModelViewSet):
    serializer_class = TaxRiskAlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = _filter_queryset_by_entity_scope(TaxRiskAlert.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        status_filter = self.request.query_params.get('resolved')
        if status_filter == 'true':
            qs = qs.filter(resolved_at__isnull=False)
        elif status_filter == 'false':
            qs = qs.filter(resolved_at__isnull=True)
        return qs

    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        alert = self.get_object()
        if not can_view_full_tax_audit(request.user, alert.entity.organization):
            raise PermissionDenied('User does not have permission to resolve tax risk alerts.')
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save(update_fields=['resolved_at', 'resolved_by'])
        return Response(TaxRiskAlertSerializer(alert).data)


class ComplianceDeadlineViewSet(viewsets.ModelViewSet):
    """ViewSet for compliance deadline tracking"""
    serializer_class = ComplianceDeadlineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return compliance deadlines for user's organizations"""
        qs = _filter_queryset_by_entity_scope(ComplianceDeadline.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('entity'))
        deadline = serializer.save(entity=entity)
        sync_compliance_deadline_to_platform_task(deadline)
        log_platform_audit_event(
            domain='compliance',
            actor=self.request.user,
            organization=entity.organization,
            entity=entity,
            event_type='compliance_deadline.created',
            action='deadline_created',
            resource_type='ComplianceDeadline',
            resource_id=str(deadline.id),
            subject_type='compliance_deadline',
            subject_id=str(deadline.id),
            resource_name=deadline.title,
            summary=f'Created compliance deadline: {deadline.title}',
            context={'status': deadline.status, 'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None},
        )

    def perform_update(self, serializer):
        previous = self.get_object()
        before = {
            'status': previous.status,
            'deadline_date': previous.deadline_date.isoformat() if previous.deadline_date else None,
            'title': previous.title,
        }
        deadline = serializer.save()
        sync_compliance_deadline_to_platform_task(deadline)
        log_platform_audit_event(
            domain='compliance',
            actor=self.request.user,
            organization=deadline.entity.organization,
            entity=deadline.entity,
            event_type='compliance_deadline.updated',
            action='deadline_updated',
            resource_type='ComplianceDeadline',
            resource_id=str(deadline.id),
            subject_type='compliance_deadline',
            subject_id=str(deadline.id),
            resource_name=deadline.title,
            summary=f'Updated compliance deadline: {deadline.title}',
            diff={'before': before, 'after': {'status': deadline.status, 'deadline_date': deadline.deadline_date.isoformat() if deadline.deadline_date else None, 'title': deadline.title}},
        )

    def perform_destroy(self, instance):
        log_platform_audit_event(
            domain='compliance',
            actor=self.request.user,
            organization=instance.entity.organization,
            entity=instance.entity,
            event_type='compliance_deadline.deleted',
            action='deadline_deleted',
            resource_type='ComplianceDeadline',
            resource_id=str(instance.id),
            subject_type='compliance_deadline',
            subject_id=str(instance.id),
            resource_name=instance.title,
            summary=f'Deleted compliance deadline: {instance.title}',
        )
        cancel_platform_tasks_for_origin(origin_type='compliance_deadline', origin_id=instance.id)
        super().perform_destroy(instance)

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        """Get upcoming compliance deadlines (next 30 days)"""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id required'}, status=400)
            
        organization = get_object_or_404(_accessible_organizations_queryset(request.user), id=org_id)
        accessible_entities = _accessible_entities_queryset(request.user, organization)
        
        now = datetime.now().date()
        upcoming = ComplianceDeadline.objects.filter(
            entity__in=accessible_entities,
            deadline_date__gte=now,
            deadline_date__lte=now + timedelta(days=30),
            status__in=['upcoming', 'overdue']
        ).order_by('deadline_date')

        serializer = self.get_serializer(upcoming, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue compliance deadlines"""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id required'}, status=400)
            
        organization = get_object_or_404(_accessible_organizations_queryset(request.user), id=org_id)
        accessible_entities = _accessible_entities_queryset(request.user, organization)
        
        now = datetime.now().date()
        overdue = ComplianceDeadline.objects.filter(
            entity__in=accessible_entities,
            deadline_date__lt=now,
            status__in=['upcoming', 'overdue']
        ).order_by('deadline_date')

        serializer = self.get_serializer(overdue, many=True)
        return Response(serializer.data)


class CashflowForecastViewSet(viewsets.ModelViewSet):
    """ViewSet for cashflow forecasting"""
    serializer_class = CashflowForecastSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return cashflow forecasts for user's organizations"""
        return _filter_queryset_by_entity_scope(CashflowForecast.objects.all(), self.request.user)

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get cashflow grouped by category for current month"""
        org_id = request.query_params.get('organization_id')
        if not org_id:
            return Response({'error': 'organization_id required'}, status=400)
            
        organization = get_object_or_404(_accessible_organizations_queryset(request.user), id=org_id)
        accessible_entities = _accessible_entities_queryset(request.user, organization)
        
        now = datetime.now()
        current_month = now.replace(day=1)

        forecasts = CashflowForecast.objects.filter(
            entity__in=accessible_entities,
            month=current_month
        )
        grouped = forecasts.values('category').annotate(
            total_forecasted=Sum('forecasted_amount'),
            total_actual=Sum('actual_amount')
        ).order_by('category')

        return Response(list(grouped))


class RoleViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing available roles"""
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing available permissions"""
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs"""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return audit logs for user's organizations"""
        return AuditLog.objects.filter(organization__in=_accessible_organizations_queryset(self.request.user))


class PlatformAuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """Cross-domain audit stream across finance and workspace activity."""

    serializer_class = PlatformAuditEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        accessible_workspaces = _accessible_workspaces_queryset(self.request.user).values_list('id', flat=True)
        queryset = PlatformAuditEvent.objects.filter(
            Q(organization__in=accessible_orgs) | Q(workspace_id__in=accessible_workspaces)
        ).select_related('organization', 'entity', 'actor')

        organization_id = self.request.query_params.get('organization') or self.request.query_params.get('organization_id')
        entity_id = self.request.query_params.get('entity') or self.request.query_params.get('entity_id')
        workspace_id = self.request.query_params.get('workspace_id')
        domain = self.request.query_params.get('domain')
        event_type = self.request.query_params.get('event_type')
        action = self.request.query_params.get('action')
        actor_id = self.request.query_params.get('actor') or self.request.query_params.get('actor_id')
        subject_type = self.request.query_params.get('subject_type')
        subject_id = self.request.query_params.get('subject_id')
        correlation_id = self.request.query_params.get('correlation_id')
        from_value = self.request.query_params.get('from')
        to_value = self.request.query_params.get('to')
        search_query = self.request.query_params.get('q')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if workspace_id:
            queryset = queryset.filter(workspace_id=workspace_id)
        if domain:
            queryset = queryset.filter(domain=domain)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if action:
            queryset = queryset.filter(action=action)
        if actor_id:
            queryset = queryset.filter(Q(actor_id=actor_id) | Q(actor_identifier=str(actor_id)))
        if subject_type:
            queryset = queryset.filter(subject_type=subject_type)
        if subject_id:
            queryset = queryset.filter(subject_id=str(subject_id))
        if correlation_id:
            queryset = queryset.filter(correlation_id=correlation_id)
        if from_value:
            parsed_from = datetime.fromisoformat(from_value.replace('Z', '+00:00'))
            queryset = queryset.filter(occurred_at__gte=parsed_from)
        if to_value:
            parsed_to = datetime.fromisoformat(to_value.replace('Z', '+00:00'))
            queryset = queryset.filter(occurred_at__lte=parsed_to)
        if search_query:
            queryset = queryset.filter(
                Q(summary__icontains=search_query)
                | Q(resource_name__icontains=search_query)
                | Q(resource_type__icontains=search_query)
                | Q(subject_type__icontains=search_query)
                | Q(action__icontains=search_query)
                | Q(search_text__icontains=search_query)
            )
        return queryset


class GovernancePolicyViewSet(viewsets.ModelViewSet):
    serializer_class = GovernancePolicySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GovernancePolicy.objects.filter(
            organization__in=_accessible_organizations_queryset(self.request.user)
        ).select_related('organization', 'owner').prefetch_related('amendments')

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        if not _accessible_organizations_queryset(self.request.user).filter(pk=organization.pk).exists():
            raise PermissionDenied('You do not have access to this organization.')
        serializer.save(owner=self.request.user)


class GovernanceAmendmentViewSet(viewsets.ModelViewSet):
    serializer_class = GovernanceAmendmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GovernanceAmendment.objects.filter(
            policy__organization__in=_accessible_organizations_queryset(self.request.user)
        ).select_related('policy', 'submitted_by').prefetch_related('votes')

    def perform_create(self, serializer):
        policy = serializer.validated_data['policy']
        if not GovernancePolicy.objects.filter(
            pk=policy.pk,
            organization__in=_accessible_organizations_queryset(self.request.user),
        ).exists():
            raise PermissionDenied('You do not have access to this policy.')
        serializer.save(submitted_by=self.request.user, submitted_at=timezone.now())


class GovernanceVoteViewSet(viewsets.ModelViewSet):
    serializer_class = GovernanceVoteSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return GovernanceVote.objects.filter(
            amendment__policy__organization__in=_accessible_organizations_queryset(self.request.user)
        ).select_related('amendment', 'voter')

    def perform_create(self, serializer):
        amendment = serializer.validated_data['amendment']
        if not GovernanceAmendment.objects.filter(
            pk=amendment.pk,
            policy__organization__in=_accessible_organizations_queryset(self.request.user),
        ).exists():
            raise PermissionDenied('You do not have access to this amendment.')
        now = timezone.now()
        if amendment.status != 'voting':
            raise ValidationError('Votes are only accepted while an amendment is in voting.')
        if amendment.voting_opens_at and now < amendment.voting_opens_at:
            raise ValidationError('The voting window has not opened.')
        if amendment.voting_closes_at and now > amendment.voting_closes_at:
            raise ValidationError('The voting window has closed.')
        serializer.save(voter=self.request.user)


class GovernanceCommissionPlanViewSet(viewsets.ModelViewSet):
    serializer_class = GovernanceCommissionPlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return GovernanceCommissionPlan.objects.filter(
            organization__in=_accessible_organizations_queryset(self.request.user)
        ).select_related('organization', 'created_by')

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        if not _accessible_organizations_queryset(self.request.user).filter(pk=organization.pk).exists():
            raise PermissionDenied('You do not have access to this organization.')
        plan = serializer.save(created_by=self.request.user)
        log_platform_audit_event(
            domain='governance', event_type='commission_plan.created', action='commission_plan_created',
            actor=self.request.user, organization=organization, resource_type='GovernanceCommissionPlan',
            resource_id=str(plan.id), resource_name=plan.name, summary=f'Created commission plan {plan.name}',
            metadata={'role_code': plan.role_code, 'trigger_type': plan.trigger_type, 'rate_percent': str(plan.rate_percent)},
        )

    @action(detail=True, methods=['post'])
    def calculate(self, request, pk=None):
        plan = self.get_object()
        if not plan.is_active:
            raise ValidationError('Inactive commission plans cannot calculate entries.')
        calculation_serializer = GovernanceCommissionCalculationSerializer(data=request.data)
        calculation_serializer.is_valid(raise_exception=True)
        values = calculation_serializer.validated_data
        commission_amount = (values['base_amount'] * plan.rate_percent / Decimal('100')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP,
        )
        entry = GovernanceCommissionEntry.objects.create(
            plan=plan, recipient=values['recipient'], source_reference=values['source_reference'],
            source_description=values.get('source_description', ''), base_amount=values['base_amount'],
            commission_amount=commission_amount, currency=values['currency'], calculated_by=request.user,
        )
        log_platform_audit_event(
            domain='governance', event_type='commission_entry.calculated', action='commission_calculated',
            actor=request.user, organization=plan.organization, resource_type='GovernanceCommissionEntry',
            resource_id=str(entry.id), resource_name=plan.name,
            summary=f'Calculated {entry.commission_amount} {entry.currency} commission for {entry.recipient.username}',
            metadata={'plan_id': plan.id, 'source_reference': entry.source_reference, 'base_amount': str(entry.base_amount), 'commission_amount': str(entry.commission_amount)},
        )
        return Response(GovernanceCommissionEntrySerializer(entry).data, status=drf_status.HTTP_201_CREATED)


class GovernanceCommissionEntryViewSet(viewsets.ModelViewSet):
    serializer_class = GovernanceCommissionEntrySerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        return GovernanceCommissionEntry.objects.filter(
            plan__organization__in=_accessible_organizations_queryset(self.request.user)
        ).select_related('plan', 'plan__organization', 'recipient', 'calculated_by')

    def perform_update(self, serializer):
        entry = serializer.save(paid_at=timezone.now() if serializer.validated_data.get('status') == 'paid' else serializer.instance.paid_at)
        log_platform_audit_event(
            domain='governance', event_type='commission_entry.status_updated', action='commission_status_updated',
            actor=self.request.user, organization=entry.plan.organization, resource_type='GovernanceCommissionEntry',
            resource_id=str(entry.id), resource_name=entry.plan.name,
            summary=f'Updated commission entry {entry.source_reference} to {entry.status}', metadata={'status': entry.status},
        )


# ============ Entity-Specific ViewSets ============

class EntityDepartmentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing entity departments"""
    serializer_class = EntityDepartmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return departments for user's entities"""
        return _filter_queryset_by_entity_scope(EntityDepartment.objects.all(), self.request.user)

    def perform_create(self, serializer):
        """Create department for entity"""
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        _assert_can_manage_entity_departments(self.request.user, entity)
        department = serializer.save(entity=entity)
        log_platform_audit_event(
            domain='governance', event_type='department.created', action='department_created',
            actor=self.request.user, organization=entity.organization, entity=entity,
            resource_type='EntityDepartment', resource_id=str(department.id), resource_name=department.name,
            summary=f'Created department {department.name} for {entity.name}', metadata={'code': department.code},
        )

    def perform_update(self, serializer):
        department = serializer.instance
        _assert_can_manage_entity_departments(self.request.user, department.entity)
        previous_values = {'name': department.name, 'code': department.code, 'is_active': department.is_active}
        department = serializer.save()
        log_platform_audit_event(
            domain='governance', event_type='department.updated', action='department_updated',
            actor=self.request.user, organization=department.entity.organization, entity=department.entity,
            resource_type='EntityDepartment', resource_id=str(department.id), resource_name=department.name,
            summary=f'Updated department {department.name} for {department.entity.name}',
            metadata={'before': previous_values, 'after': {'name': department.name, 'code': department.code, 'is_active': department.is_active}},
        )

    def perform_destroy(self, instance):
        _assert_can_manage_entity_departments(self.request.user, instance.entity)
        entity = instance.entity
        department_name = instance.name
        department_id = instance.id
        instance.delete()
        log_platform_audit_event(
            domain='governance', event_type='department.deleted', action='department_deleted',
            actor=self.request.user, organization=entity.organization, entity=entity,
            resource_type='EntityDepartment', resource_id=str(department_id), resource_name=department_name,
            summary=f'Removed department {department_name} from {entity.name}', metadata={},
        )


class EntityRoleViewSet(viewsets.ModelViewSet):
    """ViewSet for managing entity roles"""
    serializer_class = EntityRoleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return roles for user's entities"""
        return _filter_queryset_by_entity_scope(EntityRole.objects.all(), self.request.user)

    def perform_create(self, serializer):
        """Create role for entity"""
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class EntityStaffViewSet(viewsets.ModelViewSet):
    """ViewSet for managing entity staff"""
    serializer_class = EntityStaffSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return staff for user's entities"""
        return _filter_queryset_by_entity_scope(EntityStaff.objects.all(), self.request.user)

    def perform_create(self, serializer):
        """Create staff member — resolves user by email if user PK not supplied"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)

        user_id = self.request.data.get('user')
        if not user_id:
            email = self.request.data.get('email', '')
            if email:
                try:
                    linked_user = User.objects.get(email=email)
                except User.DoesNotExist:
                    from rest_framework.exceptions import ValidationError
                    raise ValidationError({'email': f'No user account found with email "{email}". The staff member must have a registered user account.'})
            else:
                linked_user = self.request.user
        else:
            linked_user = get_object_or_404(User, id=user_id)

        serializer.save(entity=entity, user=linked_user)


class StaffPayrollProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StaffPayrollProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(StaffPayrollProfile.objects.select_related('staff_member', 'entity'), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset

    def perform_create(self, serializer):
        staff_member = get_object_or_404(_filter_queryset_by_entity_scope(EntityStaff.objects.all(), self.request.user), id=self.request.data.get('staff_member'))
        preset = get_payroll_country_preset(staff_member.entity.country)
        serializer.save(
            entity=staff_member.entity,
            staff_member=staff_member,
            income_tax_rate=self.request.data.get('income_tax_rate', preset['income_tax_rate']),
            employee_tax_rate=self.request.data.get('employee_tax_rate', preset['employee_tax_rate']),
            employer_tax_rate=self.request.data.get('employer_tax_rate', preset['employer_tax_rate']),
            statutory_jurisdiction=self.request.data.get('statutory_jurisdiction', preset['statutory_jurisdiction']),
        )

    @action(detail=False, methods=['get'])
    def presets(self, request):
        country = request.query_params.get('country')
        if country:
            return Response(get_payroll_country_preset(country))
        return Response({'results': list_payroll_country_presets()})

    @action(detail=True, methods=['post'])
    def apply_country_preset(self, request, pk=None):
        profile = self.get_object()
        preset = get_payroll_country_preset(profile.entity.country)
        profile.income_tax_rate = preset['income_tax_rate']
        profile.employee_tax_rate = preset['employee_tax_rate']
        profile.employer_tax_rate = preset['employer_tax_rate']
        profile.statutory_jurisdiction = preset['statutory_jurisdiction']
        profile.save(update_fields=['income_tax_rate', 'employee_tax_rate', 'employer_tax_rate', 'statutory_jurisdiction', 'updated_at'])
        return Response(self.get_serializer(profile).data)


class PayrollComponentViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollComponentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(PayrollComponent.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        component_type = self.request.query_params.get('component_type')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if component_type:
            queryset = queryset.filter(component_type=component_type)
        return queryset

    def perform_create(self, serializer):
        entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('entity'))
        serializer.save(entity=entity)


class StaffPayrollComponentAssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = StaffPayrollComponentAssignmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(
            StaffPayrollComponentAssignment.objects.select_related('staff_member', 'component'),
            self.request.user,
            entity_relation='staff_member__entity',
        )
        staff_member_id = self.request.query_params.get('staff_member')
        if staff_member_id:
            queryset = queryset.filter(staff_member_id=staff_member_id)
        return queryset

    def perform_create(self, serializer):
        staff_member = get_object_or_404(_filter_queryset_by_entity_scope(EntityStaff.objects.all(), self.request.user), id=self.request.data.get('staff_member'))
        component = get_object_or_404(_filter_queryset_by_entity_scope(PayrollComponent.objects.all(), self.request.user), id=self.request.data.get('component'))
        if component.entity_id != staff_member.entity_id:
            raise ValidationError({'component': 'Payroll component must belong to the same entity as the staff member.'})
        serializer.save(staff_member=staff_member, component=component)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(LeaveType.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset

    def perform_create(self, serializer):
        entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('entity'))
        serializer.save(entity=entity)


class LeaveBalanceViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(
            LeaveBalance.objects.select_related('staff_member', 'leave_type'),
            self.request.user,
            entity_relation='staff_member__entity',
        )
        staff_member_id = self.request.query_params.get('staff_member')
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if staff_member_id:
            queryset = queryset.filter(staff_member_id=staff_member_id)
        if entity_id:
            queryset = queryset.filter(staff_member__entity_id=entity_id)
        return queryset

    def perform_create(self, serializer):
        staff_member = get_object_or_404(_filter_queryset_by_entity_scope(EntityStaff.objects.all(), self.request.user), id=self.request.data.get('staff_member'))
        leave_type = get_object_or_404(_filter_queryset_by_entity_scope(LeaveType.objects.all(), self.request.user), id=self.request.data.get('leave_type'))
        if leave_type.entity_id != staff_member.entity_id:
            raise ValidationError({'leave_type': 'Leave policy must belong to the same entity as the staff member.'})
        serializer.save(staff_member=staff_member, leave_type=leave_type)


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(LeaveRequest.objects.select_related('staff_member', 'leave_type', 'approved_by'), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        staff_member_id = self.request.query_params.get('staff_member')
        status_filter = self.request.query_params.get('status')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if staff_member_id:
            queryset = queryset.filter(staff_member_id=staff_member_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        staff_member = get_object_or_404(_filter_queryset_by_entity_scope(EntityStaff.objects.all(), self.request.user), id=self.request.data.get('staff_member'))
        leave_type = get_object_or_404(_filter_queryset_by_entity_scope(LeaveType.objects.all(), self.request.user), id=self.request.data.get('leave_type'))
        if leave_type.entity_id != staff_member.entity_id:
            raise ValidationError({'leave_type': 'Leave policy must belong to the same entity as the staff member.'})
        serializer.save(entity=staff_member.entity, staff_member=staff_member, leave_type=leave_type)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        leave_request = self.get_object()
        leave_request.status = 'approved'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(self.get_serializer(leave_request).data)


class PayrollBankOriginatorProfileViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollBankOriginatorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(PayrollBankOriginatorProfile.objects.select_related('entity'), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset

    def perform_create(self, serializer):
        entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('entity'))
        serializer.save(entity=entity)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        leave_request = self.get_object()
        leave_request.status = 'rejected'
        leave_request.approved_by = request.user
        leave_request.approved_at = timezone.now()
        leave_request.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_at'])
        return Response(self.get_serializer(leave_request).data)


class PayrollRunViewSet(viewsets.ModelViewSet):
    serializer_class = PayrollRunSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = PayrollRun.objects.filter(organization__in=_accessible_organizations_queryset(self.request.user)).select_related('organization', 'entity', 'processed_by', 'journal_entry').prefetch_related('payslips__line_items', 'statutory_reports', 'bank_payment_file')
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        organization_id = self.request.query_params.get('organization_id') or self.request.query_params.get('organization')
        status_filter = self.request.query_params.get('status')
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset

    def perform_create(self, serializer):
        entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('entity'))
        organization = get_object_or_404(_accessible_organizations_queryset(self.request.user), id=self.request.data.get('organization') or entity.organization_id)
        if entity.organization_id != organization.id:
            raise ValidationError({'organization': 'Selected organization must own the payroll entity.'})
        serializer.save(
            entity=entity,
            organization=organization,
            requested_bank_file_format=resolve_bank_file_format(entity.country, self.request.data.get('requested_bank_file_format', '')),
            requested_bank_institution=resolve_bank_institution(entity.country, self.request.data.get('requested_bank_institution', '')),
            requested_bank_export_variant=resolve_bank_export_variant(entity.country, self.request.data.get('requested_bank_export_variant', '')),
        )

    @action(detail=False, methods=['get'])
    def export_options(self, request):
        entity_id = request.query_params.get('entity_id') or request.query_params.get('entity')
        country = request.query_params.get('country')
        if entity_id and not country:
            entity = _get_accessible_entity_or_404(request.user, entity_id)
            country = entity.country
        return Response({'results': list_bank_export_options(country)})

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        payroll_run = self.get_object()
        try:
            record = submit_accounting_object(payroll_run, request.user, object_type='payroll_run')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        payroll_run.refresh_from_db()
        return Response({'approval': record.id, 'payroll_run': self.get_serializer(payroll_run).data})

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        payroll_run = self.get_object()
        try:
            record = approve_accounting_object(
                AccountingApprovalRecord.objects.get(object_type='payroll_run', object_id=payroll_run.id),
                request.user,
                comments=request.data.get('comments', ''),
            )
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'This payroll run has not been submitted for approval.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        payroll_run.refresh_from_db()
        return Response({'approval': record.id, 'payroll_run': self.get_serializer(payroll_run).data})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        payroll_run = self.get_object()
        try:
            record = reject_accounting_object(
                AccountingApprovalRecord.objects.get(object_type='payroll_run', object_id=payroll_run.id),
                request.user,
                comments=request.data.get('comments', ''),
            )
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'This payroll run has not been submitted for approval.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        payroll_run.refresh_from_db()
        return Response({'approval': record.id, 'payroll_run': self.get_serializer(payroll_run).data})

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        payroll_run = self.get_object()
        if get_matching_accounting_matrix(payroll_run, object_type='payroll_run') and payroll_run.approval_status != 'approved':
            return Response({'detail': 'This payroll run must be fully approved before it can be processed.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        try:
            process_payroll_run(payroll_run, request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        payroll_run.refresh_from_db()
        return Response(self.get_serializer(payroll_run).data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        payroll_run = self.get_object()
        mark_payroll_run_paid(payroll_run)
        payroll_run.refresh_from_db()
        return Response(self.get_serializer(payroll_run).data)


class PayslipViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayslipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(Payslip.objects.select_related('payroll_run', 'staff_member', 'payroll_profile').prefetch_related('line_items'), self.request.user, entity_relation='payroll_run__entity')
        payroll_run_id = self.request.query_params.get('payroll_run')
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if payroll_run_id:
            queryset = queryset.filter(payroll_run_id=payroll_run_id)
        if entity_id:
            queryset = queryset.filter(payroll_run__entity_id=entity_id)
        return queryset


class PayrollStatutoryReportViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayrollStatutoryReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(PayrollStatutoryReport.objects.select_related('payroll_run'), self.request.user, entity_relation='payroll_run__entity')
        payroll_run_id = self.request.query_params.get('payroll_run')
        if payroll_run_id:
            queryset = queryset.filter(payroll_run_id=payroll_run_id)
        return queryset


class PayrollBankPaymentFileViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PayrollBankPaymentFileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = _filter_queryset_by_entity_scope(PayrollBankPaymentFile.objects.select_related('payroll_run'), self.request.user, entity_relation='payroll_run__entity')
        payroll_run_id = self.request.query_params.get('payroll_run')
        if payroll_run_id:
            queryset = queryset.filter(payroll_run_id=payroll_run_id)
        return queryset


class BankAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for managing bank accounts"""
    serializer_class = BankAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return bank accounts for user's entities"""
        qs = _filter_queryset_by_entity_scope(BankAccount.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        """Create bank account for entity"""
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class WalletViewSet(viewsets.ModelViewSet):
    """ViewSet for managing wallets"""
    serializer_class = WalletSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return wallets for user's entities"""
        return _filter_queryset_by_entity_scope(Wallet.objects.all(), self.request.user)

    def perform_create(self, serializer):
        """Create wallet for entity"""
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class ComplianceDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing compliance documents"""
    serializer_class = ComplianceDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return compliance documents for user's entities"""
        qs = _filter_queryset_by_entity_scope(ComplianceDocument.objects.all(), self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        """Create compliance document for entity"""
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        document = serializer.save(entity=entity)
        log_platform_audit_event(
            domain='document',
            actor=self.request.user,
            organization=entity.organization,
            entity=entity,
            event_type='compliance_document.created',
            action='document_created',
            resource_type='ComplianceDocument',
            resource_id=str(document.id),
            subject_type='document',
            subject_id=str(document.id),
            resource_name=document.title,
            summary=f'Created compliance document: {document.title}',
            context={'document_type': document.document_type, 'status': document.status},
        )

    def perform_update(self, serializer):
        previous = self.get_object()
        before = {'status': previous.status, 'title': previous.title, 'expiry_date': previous.expiry_date.isoformat() if previous.expiry_date else None}
        document = serializer.save()
        log_platform_audit_event(
            domain='document',
            actor=self.request.user,
            organization=document.entity.organization,
            entity=document.entity,
            event_type='compliance_document.updated',
            action='document_updated',
            resource_type='ComplianceDocument',
            resource_id=str(document.id),
            subject_type='document',
            subject_id=str(document.id),
            resource_name=document.title,
            summary=f'Updated compliance document: {document.title}',
            diff={'before': before, 'after': {'status': document.status, 'title': document.title, 'expiry_date': document.expiry_date.isoformat() if document.expiry_date else None}},
        )

    def perform_destroy(self, instance):
        log_platform_audit_event(
            domain='document',
            actor=self.request.user,
            organization=instance.entity.organization,
            entity=instance.entity,
            event_type='compliance_document.deleted',
            action='document_deleted',
            resource_type='ComplianceDocument',
            resource_id=str(instance.id),
            subject_type='document',
            subject_id=str(instance.id),
            resource_name=instance.title,
            summary=f'Deleted compliance document: {instance.title}',
        )
        super().perform_destroy(instance)

    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get documents expiring soon"""
        entity_id = request.query_params.get('entity_id')
        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)
            
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        
        documents = ComplianceDocument.objects.filter(
            entity=entity,
            expiry_date__isnull=False
        ).exclude(status='expired')
        
        expiring_soon = [doc for doc in documents if doc.is_expiring_soon]
        serializer = self.get_serializer(expiring_soon, many=True)
        return Response(serializer.data)


# ============================================================================
# BOOKKEEPING VIEWSETS
# ============================================================================

class BookkeepingCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for bookkeeping categories"""
    serializer_class = BookkeepingCategorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return categories for specific entity"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(BookkeepingCategory.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    @action(detail=False, methods=['post'])
    def create_defaults(self, request):
        """Create default categories for an entity"""
        entity_id = request.data.get('entity_id')
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        
        # Default income categories
        income_categories = [
            'Sales Revenue', 'Service Fees', 'Retainers', 'Investment Income',
            'Loan Repayments', 'Miscellaneous Income'
        ]
        
        # Default expense categories
        expense_categories = [
            'Staff Salaries', 'Contractor Payments', 'Rent', 'Utilities',
            'Car/Vehicle Expenses', 'Shipments & Logistics', 'Software Subscriptions',
            'Taxes', 'Insurance', 'Legal Fees', 'Marketing', 'Asset Purchases'
        ]
        
        created_categories = []
        
        for name in income_categories:
            cat, created = BookkeepingCategory.objects.get_or_create(
                entity=entity,
                name=name,
                type='income',
                defaults={'is_default': True}
            )
            if created:
                created_categories.append(cat)
        
        for name in expense_categories:
            cat, created = BookkeepingCategory.objects.get_or_create(
                entity=entity,
                name=name,
                type='expense',
                defaults={'is_default': True}
            )
            if created:
                created_categories.append(cat)
        
        serializer = self.get_serializer(created_categories, many=True)
        return Response({'created': len(created_categories), 'categories': serializer.data})


class BookkeepingAccountViewSet(viewsets.ModelViewSet):
    """ViewSet for bookkeeping accounts"""
    serializer_class = BookkeepingAccountSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return accounts for specific entity"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(BookkeepingAccount.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class TransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for transactions with calculations"""
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return transactions for specific entity with filters"""
        entity_id = self.request.query_params.get('entity_id')
        queryset = _filter_queryset_by_entity_scope(Transaction.objects.all(), self.request.user)
        
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        
        # Filters
        transaction_type = self.request.query_params.get('type')
        if transaction_type:
            queryset = queryset.filter(type=transaction_type)
        
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        account_id = self.request.query_params.get('account_id')
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        
        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        return queryset
    
    def perform_create(self, serializer):
        """Create transaction and log action"""
        transaction = serializer.save(created_by=self.request.user)
        
        # Log action
        BookkeepingAuditLog.objects.create(
            entity=transaction.entity,
            action='create_transaction',
            user=transaction.created_by,
            new_value={
                'id': transaction.id,
                'type': transaction.type,
                'amount': str(transaction.amount),
                'description': transaction.description
            }
        )
    
    def perform_update(self, serializer):
        """Update transaction and log action"""
        old_transaction = self.get_object()
        old_value = {
            'amount': str(old_transaction.amount),
            'type': old_transaction.type,
            'category': old_transaction.category.name,
            'account': old_transaction.account.name
        }
        
        transaction = serializer.save()
        
        # Log action
        BookkeepingAuditLog.objects.create(
            entity=transaction.entity,
            action='edit_transaction',
            user=self.request.user if hasattr(self.request, 'user') and self.request.user.is_authenticated else None,
            old_value=old_value,
            new_value={
                'amount': str(transaction.amount),
                'type': transaction.type,
                'category': transaction.category.name,
                'account': transaction.account.name
            }
        )
    
    def perform_destroy(self, instance):
        """Delete transaction and log action"""
        BookkeepingAuditLog.objects.create(
            entity=instance.entity,
            action='delete_transaction',
            user=self.request.user if hasattr(self.request, 'user') and self.request.user.is_authenticated else None,
            old_value={
                'id': instance.id,
                'type': instance.type,
                'amount': str(instance.amount),
                'description': instance.description
            }
        )
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get financial summary for entity"""
        from django.db.models import Sum, Count
        from datetime import datetime, timedelta
        
        entity_id = request.query_params.get('entity_id')
        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)
        _get_accessible_entity_or_404(request.user, entity_id)
        
        # Date filters
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        queryset = Transaction.objects.filter(entity_id=entity_id)
        
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        
        # Calculate totals
        income_total = queryset.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense_total = queryset.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        
        # Payroll total (staff salaries)
        payroll_total = queryset.filter(
            type='expense',
            category__name__icontains='salary'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Category breakdown
        category_breakdown = queryset.values(
            'category__name', 'category__type'
        ).annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('-total')[:10]
        
        # Monthly trend (last 6 months)
        six_months_ago = datetime.now().date() - timedelta(days=180)
        monthly_data = queryset.filter(date__gte=six_months_ago).extra(
            select={'month': "strftime('%%Y-%%m', date)"}
        ).values('month', 'type').annotate(
            total=Sum('amount')
        ).order_by('month')
        
        return Response({
            'total_income': float(income_total),
            'total_expense': float(expense_total),
            'net_profit': float(income_total - expense_total),
            'payroll_total': float(payroll_total),
            'transaction_count': queryset.count(),
            'category_breakdown': list(category_breakdown),
            'monthly_trend': list(monthly_data)
        })

    @action(detail=False, methods=['get'])
    def anomalies(self, request):
        """Detect basic anomalies in transaction amounts for an entity.

        Flags transactions whose absolute amount is far from the mean
        (simple z-score over the entity's transactions in a period).

        Query params:
        - entity_id (required)
        - lookback_days (optional, default 180)
        - z_threshold (optional, default 3.0)
        """
        from math import sqrt

        entity_id = request.query_params.get('entity_id')
        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)
        _get_accessible_entity_or_404(request.user, entity_id)

        lookback_days = int(request.query_params.get('lookback_days', 180))
        z_threshold = float(request.query_params.get('z_threshold', 3.0))

        from datetime import datetime, timedelta
        cutoff = datetime.now().date() - timedelta(days=lookback_days)

        qs = Transaction.objects.filter(entity_id=entity_id, date__gte=cutoff)
        amounts = [abs(float(t.amount)) for t in qs]

        if len(amounts) < 5:
            return Response({'message': 'Not enough data to perform anomaly detection.', 'count': len(amounts)})

        mean = sum(amounts) / len(amounts)
        variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
        std = sqrt(variance) if variance > 0 else 0

        if std == 0:
            return Response({'message': 'No variability detected; all amounts are similar.', 'count': len(amounts)})

        flagged = []
        for t in qs:
            amt = abs(float(t.amount))
            z = (amt - mean) / std
            if abs(z) >= z_threshold:
                flagged.append({
                    'id': t.id,
                    'date': t.date,
                    'amount': float(t.amount),
                    'type': t.type,
                    'category': t.category.name,
                    'account': t.account.name,
                    'z_score': round(z, 2),
                    'reason': 'Amount is an outlier compared to recent history.'
                })

        return Response({
            'entity_id': int(entity_id),
            'lookback_days': lookback_days,
            'mean_amount': round(mean, 2),
            'std_amount': round(std, 2),
            'threshold': z_threshold,
            'flagged_count': len(flagged),
            'flagged_transactions': flagged,
        })

    @action(detail=False, methods=['post'])
    def import_external(self, request):
        """Bulk-import transactions from external sources (e.g. bank feeds).

        Expects a JSON payload of the form:

        {
          "transactions": [
            {"entity": 1, "account": 2, "type": "income", ...},
            ...
          ]
        }

        Each item is validated using the normal TransactionSerializer,
        including duplicate detection, and created if valid.
        """
        transactions_data = request.data.get('transactions')
        if not isinstance(transactions_data, list):
            return Response({'error': 'transactions must be a list'}, status=400)

        created_ids = []
        errors = []

        for index, item in enumerate(transactions_data):
            serializer = self.get_serializer(data=item)
            serializer.context['request'] = request
            if serializer.is_valid():
                transaction = serializer.save(
                    created_by=request.user if hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False) else None
                )
                created_ids.append(transaction.id)
            else:
                errors.append({'index': index, 'errors': serializer.errors})

        status_code = 201 if created_ids else 400
        return Response({'created_ids': created_ids, 'errors': errors}, status=status_code)


class BookkeepingAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for bookkeeping audit logs (read-only)"""
    serializer_class = BookkeepingAuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return audit logs for specific entity"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(BookkeepingAuditLog.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class FinancialStatementsViewSet(viewsets.ViewSet):
    """ViewSet for generating Balance Sheet, Income Statement, and Cash Flow Statement"""

    @action(detail=False, methods=['get'])
    def balance_sheet(self, request):
        """Generate balance sheet for an entity as of a specific date"""
        entity_id = request.query_params.get('entity_id')
        as_of_date = request.query_params.get('as_of_date')
        
        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)
        
        from datetime import datetime
        if as_of_date:
            try:
                as_of = datetime.strptime(as_of_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid date format (use YYYY-MM-DD)'}, status=400)
        else:
            as_of = datetime.now().date()
        
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        
        # Get all transactions up to the as_of date
        transactions = Transaction.objects.filter(entity=entity, date__lte=as_of)
        
        # Calculate assets (bank accounts + wallets + receivables)
        current_assets = {}
        for account in entity.bookkeeping_accounts.filter(type__in=['bank', 'cash']):
            txns = transactions.filter(account=account)
            balance = account.balance
            current_assets[account.name] = float(balance)
        
        total_current_assets = sum(current_assets.values())
        
        # Fixed assets (at book value)
        fixed_assets = {}
        for asset in entity.fixed_assets.filter(is_active=True):
            book_val = float(asset.cost - asset.accumulated_depreciation)
            fixed_assets[asset.name] = book_val
        
        total_fixed_assets = sum(fixed_assets.values())
        total_assets = total_current_assets + total_fixed_assets
        
        # Liabilities (placeholder: could extend to track payables)
        total_liabilities = 0
        
        # Equity (Assets - Liabilities)
        total_equity = total_assets - total_liabilities
        
        return Response({
            'entity_id': int(entity_id),
            'as_of_date': str(as_of),
            'assets': {
                'current_assets': current_assets,
                'total_current_assets': total_current_assets,
                'fixed_assets': fixed_assets,
                'total_fixed_assets': total_fixed_assets,
                'total_assets': total_assets,
            },
            'liabilities': {
                'total_liabilities': total_liabilities,
            },
            'equity': {
                'total_equity': total_equity,
            },
            'check': f"Assets ({total_assets}) = Liabilities ({total_liabilities}) + Equity ({total_equity})"
        })

    @action(detail=False, methods=['get'])
    def income_statement(self, request):
        """Generate income statement (P&L) for a period"""
        entity_id = request.query_params.get('entity_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)
        
        from datetime import datetime, timedelta
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid end_date format (use YYYY-MM-DD)'}, status=400)
        else:
            end = datetime.now().date()
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid start_date format (use YYYY-MM-DD)'}, status=400)
        else:
            start = end - timedelta(days=365)
        
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        
        # Get all transactions in the period
        txns = Transaction.objects.filter(entity=entity, date__gte=start, date__lte=end)
        
        # Revenue (Income)
        from django.db.models import Sum
        revenue = txns.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        
        # Expenses
        expenses = txns.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0
        
        # Add depreciation expense (for the period)
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        depreciation_expense = 0
        for asset in entity.fixed_assets.filter(is_active=True):
            annual_deprec = asset.calculate_depreciation()
            depreciation_expense += float(annual_deprec) * (months / 12.0)
        
        # Add accrual expenses for the period
        accrual_expenses = entity.accrual_entries.filter(
            accrual_type='expense',
            accrual_date__gte=start,
            accrual_date__lte=end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Accrual revenue
        accrual_revenue = entity.accrual_entries.filter(
            accrual_type='revenue',
            accrual_date__gte=start,
            accrual_date__lte=end
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_revenue = float(revenue) + float(accrual_revenue)
        total_expenses = float(expenses) + depreciation_expense + float(accrual_expenses)
        net_income = total_revenue - total_expenses
        
        return Response({
            'entity_id': int(entity_id),
            'period': f"{start} to {end}",
            'revenue': {
                'operating_revenue': float(revenue),
                'accrual_revenue': float(accrual_revenue),
                'total_revenue': total_revenue,
            },
            'expenses': {
                'operating_expenses': float(expenses),
                'depreciation_expense': round(depreciation_expense, 2),
                'accrual_expenses': float(accrual_expenses),
                'total_expenses': total_expenses,
            },
            'net_income': round(net_income, 2),
        })

    @action(detail=False, methods=['get'])
    def cash_flow_statement(self, request):
        """Generate cash flow statement (simplified: only transaction-based)"""
        entity_id = request.query_params.get('entity_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)
        
        from datetime import datetime, timedelta
        if end_date:
            try:
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid end_date format (use YYYY-MM-DD)'}, status=400)
        else:
            end = datetime.now().date()
        
        if start_date:
            try:
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Invalid start_date format (use YYYY-MM-DD)'}, status=400)
        else:
            start = end - timedelta(days=365)
        
        entity = _get_accessible_entity_or_404(request.user, entity_id)
        
        # Get all transactions in the period
        from django.db.models import Sum
        txns = Transaction.objects.filter(entity=entity, date__gte=start, date__lte=end)
        
        # Operating activities (net income simplified from transactions)
        net_cash_from_operations = txns.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        net_cash_from_operations -= (txns.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0)
        
        # Investing activities (fixed asset purchases, simplified)
        investing_outflows = 0
        for asset in entity.fixed_assets.filter(purchase_date__gte=start, purchase_date__lte=end):
            investing_outflows += float(asset.cost)
        
        # Financing activities (not yet implemented; placeholder)
        net_cash_from_financing = 0
        
        net_change_in_cash = float(net_cash_from_operations) - investing_outflows + net_cash_from_financing
        
        return Response({
            'entity_id': int(entity_id),
            'period': f"{start} to {end}",
            'operating_activities': {
                'net_cash_from_operations': round(float(net_cash_from_operations), 2),
            },
            'investing_activities': {
                'fixed_asset_purchases': -investing_outflows,
                'net_cash_from_investing': -investing_outflows,
            },
            'financing_activities': {
                'net_cash_from_financing': net_cash_from_financing,
            },
            'net_change_in_cash': round(net_change_in_cash, 2),
        })


class EnterpriseReportingViewSet(viewsets.ViewSet):
    """Organization-scoped enterprise reporting and automation payloads."""

    permission_classes = [IsAuthenticated]

    def _parse_date(self, value):
        if not value:
            return None
        try:
            return datetime.strptime(value, '%Y-%m-%d').date()
        except ValueError as exc:
            raise ValidationError({'detail': f'Invalid date format: {value}. Use YYYY-MM-DD.'}) from exc

    def _get_reporting_context(self, request):
        organization_id = request.query_params.get('organization_id') or request.query_params.get('organization')
        if not organization_id:
            raise ValidationError({'detail': 'organization_id required'})
        organization = get_object_or_404(_accessible_organizations_queryset(request.user), id=organization_id)
        end = self._parse_date(request.query_params.get('end_date')) or timezone.now().date()
        start = self._parse_date(request.query_params.get('start_date')) or (end - timedelta(days=365))
        entities = list(_accessible_entities_queryset(request.user, organization=organization).select_related('organization'))
        return organization, entities, start, end

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        organization, entities, start, end = self._get_reporting_context(request)
        payload = build_enterprise_reporting_dashboard(organization, entities, start, end)
        return Response(payload)

    def _export(self, request, export_format):
        organization, entities, start, end = self._get_reporting_context(request)
        payload = build_enterprise_reporting_dashboard(organization, entities, start, end)
        content, content_type, filename = export_enterprise_reporting_payload(payload, export_format)
        response = HttpResponse(content, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=False, methods=['get'])
    def export_pdf(self, request):
        return self._export(request, 'pdf')

    @action(detail=False, methods=['get'])
    def export_xlsx(self, request):
        return self._export(request, 'xlsx')

    @action(detail=False, methods=['get'])
    def export_json(self, request):
        return self._export(request, 'json')


class CashflowTreasuryViewSet(viewsets.ViewSet):
    """ViewSet for cashflow and treasury data"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Get comprehensive cashflow and treasury dashboard data"""
        entity_id = request.query_params.get('entity_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        currency = request.query_params.get('currency', 'USD')

        if not entity_id:
            return Response({'error': 'entity_id required'}, status=400)

        entity = _get_accessible_entity_or_404(request.user, entity_id)

        from datetime import date
        from django.db.models import Sum
        from django.db.models.functions import TruncMonth

        def _parse_date(value):
            if not value:
                return None
            try:
                return date.fromisoformat(value)
            except ValueError:
                return None

        start = _parse_date(start_date)
        end = _parse_date(end_date)
        today = date.today()

        if end is None:
            end = today
        if start is None:
            start = (end.replace(day=1) - timedelta(days=180)).replace(day=1)

        bank_accounts = BankAccount.objects.filter(entity=entity)
        wallets = Wallet.objects.filter(entity=entity)

        cash_on_hand = float(bank_accounts.aggregate(total=Sum('balance'))['total'] or 0) + float(
            wallets.aggregate(total=Sum('balance'))['total'] or 0
        )

        txns = Transaction.objects.filter(entity=entity, date__gte=start, date__lte=end)
        inflows = float(txns.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0)
        outflows = float(txns.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0)
        net_cashflow = inflows - outflows

        monthly_rows = (
            txns.annotate(month=TruncMonth('date'))
            .values('month', 'type')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )
        monthly_map = {}
        for row in monthly_rows:
            month_key = row['month'].strftime('%b') if row.get('month') else ''
            if month_key not in monthly_map:
                monthly_map[month_key] = {'month': month_key, 'inflows': 0.0, 'outflows': 0.0, 'forecast': 0.0}
            if row['type'] == 'income':
                monthly_map[month_key]['inflows'] = float(row['total'] or 0)
            elif row['type'] == 'expense':
                monthly_map[month_key]['outflows'] = float(row['total'] or 0)

        monthly = list(monthly_map.values())
        months_count = max(1, len(monthly))
        burn_rate = net_cashflow / months_count
        runway_days = 0
        if burn_rate < 0:
            runway_days = int((cash_on_hand / abs(burn_rate)) * 30) if abs(burn_rate) > 0 else 0

        return Response({
            'kpis': {
                'cashOnHand': round(cash_on_hand, 2),
                'netCashflow': round(net_cashflow, 2),
                'liquidityRatio': 0,
                'burnRate': round(burn_rate, 2),
                'runway': runway_days,
            },
            'cashflowTimeline': {
                'monthly': monthly,
            },
            'bankAccounts': [
                {
                    'id': a.id,
                    'name': a.account_name,
                    'bank': getattr(a, 'bank_name', None) or getattr(a, 'bank', None),
                    'balance': float(a.balance or 0),
                    'currency': getattr(a, 'currency', currency),
                    'type': getattr(a, 'type', None),
                }
                for a in bank_accounts
            ],
            'accountsPayable': {'upcoming': [], 'overdue': []},
            'accountsReceivable': {'expected': [], 'aging': {}},
            'insights': [],
            'alerts': [],
        })

    @action(detail=False, methods=['post'])
    def transfer(self, request):
        """Execute internal transfer between bank accounts of the same currency."""
        from django.db import transaction as db_transaction

        entity_id = request.data.get('entity_id')
        from_account_id = request.data.get('from_account_id')
        to_account_id = request.data.get('to_account_id')
        raw_amount = request.data.get('amount')
        description = request.data.get('description', 'Internal Transfer')

        if not all([entity_id, from_account_id, to_account_id, raw_amount]):
            return Response({'error': 'entity_id, from_account_id, to_account_id, and amount are required.'}, status=400)

        try:
            amount = Decimal(str(raw_amount))
            if amount <= 0:
                return Response({'error': 'Amount must be greater than zero.'}, status=400)
        except Exception:
            return Response({'error': 'Invalid amount.'}, status=400)

        entity = _get_accessible_entity_or_404(request.user, entity_id)

        try:
            from_acct = BankAccount.objects.get(id=from_account_id, entity=entity)
            to_acct = BankAccount.objects.get(id=to_account_id, entity=entity)
        except BankAccount.DoesNotExist:
            return Response({'error': 'Account not found or not accessible.'}, status=404)

        if from_acct.id == to_acct.id:
            return Response({'error': 'Source and destination accounts must be different.'}, status=400)

        if from_acct.currency != to_acct.currency:
            return Response(
                {'error': f'Accounts have different currencies ({from_acct.currency} vs {to_acct.currency}). Use FX Conversion instead.'},
                status=400,
            )

        if Decimal(str(from_acct.available_balance)) < amount:
            return Response({'error': 'Insufficient available balance.'}, status=400)

        with db_transaction.atomic():
            from_acct.balance = Decimal(str(from_acct.balance)) - amount
            from_acct.available_balance = Decimal(str(from_acct.available_balance)) - amount
            from_acct.save(update_fields=['balance', 'available_balance', 'updated_at'])

            to_acct.balance = Decimal(str(to_acct.balance)) + amount
            to_acct.available_balance = Decimal(str(to_acct.available_balance)) + amount
            to_acct.save(update_fields=['balance', 'available_balance', 'updated_at'])

        return Response({
            'success': True,
            'message': f'Transferred {amount} {from_acct.currency} from "{from_acct.account_name}" to "{to_acct.account_name}".',
            'from_account': from_acct.account_name,
            'to_account': to_acct.account_name,
            'amount': str(amount),
            'currency': from_acct.currency,
            'from_balance': str(from_acct.balance),
            'to_balance': str(to_acct.balance),
        })

    @action(detail=False, methods=['post'])
    def fx_conversion(self, request):
        """Execute FX conversion between accounts with different currencies."""
        from django.db import transaction as db_transaction

        entity_id = request.data.get('entity_id')
        from_account_id = request.data.get('from_account_id')
        to_account_id = request.data.get('to_account_id')
        raw_amount = request.data.get('amount')
        raw_rate = request.data.get('exchange_rate')
        description = request.data.get('description', 'FX Conversion')

        if not all([entity_id, from_account_id, to_account_id, raw_amount]):
            return Response({'error': 'entity_id, from_account_id, to_account_id, and amount are required.'}, status=400)

        try:
            amount = Decimal(str(raw_amount))
            if amount <= 0:
                return Response({'error': 'Amount must be greater than zero.'}, status=400)
        except Exception:
            return Response({'error': 'Invalid amount.'}, status=400)

        entity = _get_accessible_entity_or_404(request.user, entity_id)

        try:
            from_acct = BankAccount.objects.get(id=from_account_id, entity=entity)
            to_acct = BankAccount.objects.get(id=to_account_id, entity=entity)
        except BankAccount.DoesNotExist:
            return Response({'error': 'Account not found or not accessible.'}, status=404)

        if from_acct.currency == to_acct.currency:
            return Response({'error': 'Both accounts share the same currency. Use Internal Transfer instead.'}, status=400)

        if raw_rate:
            try:
                rate = Decimal(str(raw_rate))
                if rate <= 0:
                    return Response({'error': 'Exchange rate must be greater than zero.'}, status=400)
            except Exception:
                return Response({'error': 'Invalid exchange rate.'}, status=400)
        else:
            er = ExchangeRate.objects.filter(
                from_currency=from_acct.currency,
                to_currency=to_acct.currency,
            ).order_by('-rate_date').first()
            if er:
                rate = Decimal(str(er.rate))
            else:
                er_rev = ExchangeRate.objects.filter(
                    from_currency=to_acct.currency,
                    to_currency=from_acct.currency,
                ).order_by('-rate_date').first()
                if er_rev:
                    rate = (Decimal('1') / Decimal(str(er_rev.rate))).quantize(Decimal('0.000001'))
                else:
                    return Response(
                        {'error': f'No exchange rate found for {from_acct.currency}/{to_acct.currency}. Please enter the rate manually.'},
                        status=400,
                    )

        converted_amount = (amount * rate).quantize(Decimal('0.01'))

        if Decimal(str(from_acct.available_balance)) < amount:
            return Response({'error': 'Insufficient available balance.'}, status=400)

        with db_transaction.atomic():
            from_acct.balance = Decimal(str(from_acct.balance)) - amount
            from_acct.available_balance = Decimal(str(from_acct.available_balance)) - amount
            from_acct.save(update_fields=['balance', 'available_balance', 'updated_at'])

            to_acct.balance = Decimal(str(to_acct.balance)) + converted_amount
            to_acct.available_balance = Decimal(str(to_acct.available_balance)) + converted_amount
            to_acct.save(update_fields=['balance', 'available_balance', 'updated_at'])

        return Response({
            'success': True,
            'message': f'Converted {amount} {from_acct.currency} → {converted_amount} {to_acct.currency} at rate {rate}.',
            'from_amount': str(amount),
            'from_currency': from_acct.currency,
            'to_amount': str(converted_amount),
            'to_currency': to_acct.currency,
            'exchange_rate': str(rate),
        })

    @action(detail=False, methods=['post'])
    def investment_allocation(self, request):
        """Deduct funds from a bank account and record an investment allocation."""
        from django.db import transaction as db_transaction

        entity_id = request.data.get('entity_id')
        from_account_id = request.data.get('from_account_id')
        raw_amount = request.data.get('amount')
        instrument = request.data.get('instrument', '')
        allocation_type = request.data.get('allocation_type', 'general')
        description = request.data.get('description', '')

        if not all([entity_id, from_account_id, raw_amount]):
            return Response({'error': 'entity_id, from_account_id, and amount are required.'}, status=400)

        try:
            amount = Decimal(str(raw_amount))
            if amount <= 0:
                return Response({'error': 'Amount must be greater than zero.'}, status=400)
        except Exception:
            return Response({'error': 'Invalid amount.'}, status=400)

        entity = _get_accessible_entity_or_404(request.user, entity_id)

        try:
            from_acct = BankAccount.objects.get(id=from_account_id, entity=entity)
        except BankAccount.DoesNotExist:
            return Response({'error': 'Account not found or not accessible.'}, status=404)

        if Decimal(str(from_acct.available_balance)) < amount:
            return Response({'error': 'Insufficient available balance.'}, status=400)

        with db_transaction.atomic():
            from_acct.balance = Decimal(str(from_acct.balance)) - amount
            from_acct.available_balance = Decimal(str(from_acct.available_balance)) - amount
            from_acct.save(update_fields=['balance', 'available_balance', 'updated_at'])

        label = instrument or allocation_type
        return Response({
            'success': True,
            'message': f'Allocated {amount} {from_acct.currency} to "{label}".',
            'instrument': label,
            'amount': str(amount),
            'currency': from_acct.currency,
            'remaining_balance': str(from_acct.balance),
        })


# ============================================================================
# WORKFLOW & TASK QUEUE VIEWSETS
# ============================================================================


class RecurringTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing recurring bookkeeping transactions."""

    serializer_class = RecurringTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(RecurringTransaction.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity') or self.request.data.get('entity_id')
        if entity_id:
            entity = _get_accessible_entity_or_404(self.request.user, entity_id)
            serializer.save(created_by=self.request.user, entity=entity)
        else:
            serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def run_due(self, request):
        """Generate transactions for all due recurring templates as of today."""
        from datetime import date

        as_of_str = request.data.get('as_of_date')
        if as_of_str:
            try:
                as_of = date.fromisoformat(as_of_str)
            except ValueError:
                return Response({'error': 'Invalid as_of_date, expected YYYY-MM-DD'}, status=400)
        else:
            as_of = date.today()

        created = []
        for rt in _filter_queryset_by_entity_scope(RecurringTransaction.objects.all(), request.user):
            if rt.is_due(as_of):
                tx = rt.create_transaction(run_date=as_of)
                if tx is not None:
                    created.append(tx.id)

        return Response({'created_transaction_ids': created, 'count': len(created), 'as_of_date': as_of.isoformat()})


class TaskRequestViewSet(viewsets.ModelViewSet):
    """Queue-based task management for digital workflows."""

    serializer_class = TaskRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = TaskRequest.objects.filter(organization__in=_accessible_organizations_queryset(self.request.user))
        org_id = self.request.query_params.get('organization_id')
        entity_id = self.request.query_params.get('entity_id')
        status_filter = self.request.query_params.get('status')

        if org_id:
            qs = qs.filter(organization_id=org_id)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    def perform_create(self, serializer):
        org_id = self.request.data.get('organization') or self.request.data.get('organization_id')
        entity_id = self.request.data.get('entity') or self.request.data.get('entity_id')

        organization = None
        entity = None

        if entity_id:
            entity = _get_accessible_entity_or_404(self.request.user, entity_id)
            organization = entity.organization

        if org_id:
            organization = get_object_or_404(_accessible_organizations_queryset(self.request.user), id=org_id)

        task_request = serializer.save(created_by=self.request.user, organization=organization, entity=entity)
        sync_task_request_to_platform_task(task_request)
        log_platform_audit_event(
            domain='finance',
            actor=self.request.user,
            organization=task_request.organization,
            entity=task_request.entity,
            event_type='task_request.created',
            resource_type='TaskRequest',
            resource_id=str(task_request.id),
            resource_name=task_request.get_task_type_display(),
            summary=f"Created task request: {task_request.get_task_type_display()}",
            metadata={'status': task_request.status, 'priority': task_request.priority},
        )

    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Process a queued task synchronously.

        In production this would be delegated to a background worker (Celery,
        etc.). Here we execute lightweight logic inline and update status.
        """

        task = self.get_object()
        if task.status not in ['queued', 'failed']:
            return Response({'detail': f'Task is already {task.status}.'}, status=400)

        task.mark_processing()
        sync_task_request_to_platform_task(task)
        log_platform_audit_event(
            domain='finance',
            actor=request.user,
            organization=task.organization,
            entity=task.entity,
            event_type='task_request.processing_started',
            resource_type='TaskRequest',
            resource_id=str(task.id),
            resource_name=task.get_task_type_display(),
            summary=f"Started task request: {task.get_task_type_display()}",
            metadata={'status': task.status},
        )

        try:
            if task.task_type == 'generate_statement':
                result = self._generate_statement(task)
            else:
                result = {
                    'message': 'Task recorded. Detailed processing to be implemented.',
                    'task_type': task.task_type,
                }

            task.mark_completed(result=result)
            sync_task_request_to_platform_task(task)
            log_platform_audit_event(
                domain='finance',
                actor=request.user,
                organization=task.organization,
                entity=task.entity,
                event_type='task_request.completed',
                resource_type='TaskRequest',
                resource_id=str(task.id),
                resource_name=task.get_task_type_display(),
                summary=f"Completed task request: {task.get_task_type_display()}",
                metadata={'status': task.status},
            )
        except Exception as exc:  # pragma: no cover - defensive
            task.mark_failed(error_message=str(exc))
            sync_task_request_to_platform_task(task)
            log_platform_audit_event(
                domain='finance',
                actor=request.user,
                organization=task.organization,
                entity=task.entity,
                event_type='task_request.failed',
                resource_type='TaskRequest',
                resource_id=str(task.id),
                resource_name=task.get_task_type_display(),
                summary=f"Failed task request: {task.get_task_type_display()}",
                metadata={'status': task.status, 'error_message': task.error_message},
            )
            return Response({'detail': 'Task processing failed', 'error': str(exc)}, status=500)

        serializer = self.get_serializer(task)
        return Response(serializer.data)

    def _generate_statement(self, task):
        """Build a simple income statement from bookkeeping transactions."""
        from django.db.models import Sum

        payload = task.payload or {}
        entity_id = payload.get('entity_id') or (task.entity_id if task.entity_id else None)
        if not entity_id:
            return {'error': 'entity_id is required in payload to generate a statement.'}

        entity = _get_accessible_entity_or_404(self.request.user, entity_id)

        start_date = payload.get('start_date')
        end_date = payload.get('end_date')

        qs = Transaction.objects.filter(entity=entity)
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        income_total = qs.filter(type='income').aggregate(total=Sum('amount'))['total'] or 0
        expense_total = qs.filter(type='expense').aggregate(total=Sum('amount'))['total'] or 0

        by_category = list(
            qs.values('category__name', 'type')
            .annotate(total=Sum('amount'))
            .order_by('-total')
        )

        return {
            'entity_id': entity_id,
            'start_date': start_date,
            'end_date': end_date,
            'total_income': float(income_total),
            'total_expense': float(expense_total),
            'net_profit': float(income_total - expense_total),
            'by_category': by_category,
        }


# ============================================================================
# NEW FINANCIAL ACCOUNTING SYSTEM VIEWSETS (COA, GL, AR, AP, etc.)
# ============================================================================

class ChartOfAccountsViewSet(viewsets.ModelViewSet):
    """ViewSet for Chart of Accounts management"""
    serializer_class = ChartOfAccountsSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return COA for user's entities"""
        qs = _filter_queryset_by_entity_scope(ChartOfAccounts.objects.all(), self.request.user)
        entity_id = (
            self.request.query_params.get('entity')
            or self.request.query_params.get('entity_id')
        )
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class GeneralLedgerViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing General Ledger"""
    serializer_class = GeneralLedgerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return GL entries for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(GeneralLedger.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs


class JournalEntryViewSet(viewsets.ModelViewSet):
    """ViewSet for Journal Entries (double-entry bookkeeping)"""
    serializer_class = JournalEntrySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return journal entries for user's entities"""
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(
            JournalEntry.objects.all(),
            self.request.user,
        ).select_related('entity', 'created_by', 'approved_by').prefetch_related(
            'approval_steps__assigned_role',
            'approval_steps__assigned_staff',
            'approval_steps__acted_by',
            'change_logs__actor',
        )
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        posting_date = serializer.validated_data.get('posting_date')
        ensure_period_is_open(entity, posting_date)
        entry = serializer.save(entity=entity, created_by=self.request.user)
        log_journal_change(
            entry,
            'created',
            actor=self.request.user,
            new_values=snapshot_journal_entry(entry),
            details='Journal entry created in draft state.',
        )

    def perform_update(self, serializer):
        entry = serializer.instance
        if entry.status not in ['draft', 'rejected']:
            raise ValueError('Only draft or rejected journal entries can be edited.')

        previous = snapshot_journal_entry(entry)
        posting_date = serializer.validated_data.get('posting_date', entry.posting_date)
        ensure_period_is_open(entry.entity, posting_date, entry=entry, actor=self.request.user)
        updated_entry = serializer.save()
        log_journal_change(
            updated_entry,
            'updated',
            actor=self.request.user,
            old_values=previous,
            new_values=snapshot_journal_entry(updated_entry),
            details='Journal entry updated before approval.',
        )

    def perform_destroy(self, instance):
        if instance.status not in ['draft', 'rejected']:
            raise ValueError('Only draft or rejected journal entries can be deleted.')
        log_journal_change(
            instance,
            'updated',
            actor=self.request.user,
            old_values=snapshot_journal_entry(instance),
            details='Journal entry deleted before approval.',
        )
        instance.delete()

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        journal_entry = self.get_object()
        try:
            submit_journal_entry(journal_entry, request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(journal_entry)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Advance the next approval step for a journal entry"""
        journal_entry = self.get_object()
        try:
            approve_journal_entry(journal_entry, request.user, comments=request.data.get('comments', ''))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(journal_entry)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject the current journal approval step"""
        journal_entry = self.get_object()
        try:
            reject_journal_entry(journal_entry, request.user, comments=request.data.get('comments', ''))
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(journal_entry)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def reverse(self, request, pk=None):
        """Create a reversal journal entry"""
        original_entry = self.get_object()
        if original_entry.status != 'posted':
            return Response({'detail': 'Only posted journal entries can be reversed.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        try:
            ensure_period_is_open(original_entry.entity, timezone.now().date(), entry=original_entry, actor=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        
        reversal = JournalEntry.objects.create(
            entity=original_entry.entity,
            entry_type='reversal',
            reference_number=f"{original_entry.reference_number}-REV",
            description=f"Reversal of {original_entry.reference_number}",
            posting_date=timezone.now().date(),
            status='draft',
            amount_total=original_entry.amount_total,
            created_by=request.user,
            original_entry=original_entry,
        )
        
        original_entry.reversing_entry = reversal
        original_entry.save(update_fields=['reversing_entry'])
        log_journal_change(
            original_entry,
            'reversed',
            actor=request.user,
            details=f'Reversal draft {reversal.reference_number} created.',
            new_values={'reversal_entry': reversal.id, 'reference_number': reversal.reference_number},
        )
        log_journal_change(
            reversal,
            'created',
            actor=request.user,
            details=f'Reversal draft created from {original_entry.reference_number}.',
            new_values=snapshot_journal_entry(reversal),
        )
        
        serializer = self.get_serializer(reversal)
        return Response(serializer.data)


class JournalApprovalMatrixViewSet(viewsets.ModelViewSet):
    """ViewSet for journal entry approval matrix configuration."""

    serializer_class = JournalApprovalMatrixSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(JournalApprovalMatrix.objects.all(), self.request.user).select_related(
            'entity', 'preparer_role', 'reviewer_role', 'approver_role'
        )
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class JournalApprovalDelegationViewSet(viewsets.ModelViewSet):
    """ViewSet for delegated approval authority."""

    serializer_class = JournalApprovalDelegationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(JournalApprovalDelegation.objects.all(), self.request.user).select_related(
            'entity', 'delegator', 'delegate', 'created_by'
        )
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity, created_by=self.request.user)


class JournalEntryApprovalStepViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to journal approval steps."""

    serializer_class = JournalEntryApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(
            JournalEntryApprovalStep.objects.all(),
            self.request.user,
            entity_relation='journal_entry__entity',
        ).select_related('assigned_role', 'assigned_staff', 'acted_by', 'journal_entry')
        if entity_id:
            qs = qs.filter(journal_entry__entity_id=entity_id)
        journal_entry_id = self.request.query_params.get('journal_entry')
        if journal_entry_id:
            qs = qs.filter(journal_entry_id=journal_entry_id)
        return qs


class JournalEntryChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to journal workflow and change logs."""

    serializer_class = JournalEntryChangeLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(
            JournalEntryChangeLog.objects.all(),
            self.request.user,
            entity_relation='entity',
        ).select_related('actor', 'journal_entry', 'entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        journal_entry_id = self.request.query_params.get('journal_entry')
        if journal_entry_id:
            qs = qs.filter(journal_entry_id=journal_entry_id)
        return qs


class AccountingApprovalMatrixViewSet(viewsets.ModelViewSet):
    """ViewSet for accounting object approval matrix configuration."""

    serializer_class = AccountingApprovalMatrixSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        object_type = self.request.query_params.get('object_type')
        qs = _filter_queryset_by_entity_scope(AccountingApprovalMatrix.objects.all(), self.request.user).select_related(
            'entity', 'preparer_role', 'reviewer_role', 'approver_role'
        )
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if object_type:
            qs = qs.filter(object_type=object_type)
        return qs

    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class AccountingApprovalDelegationViewSet(viewsets.ModelViewSet):
    """ViewSet for delegated authority on supported accounting objects."""

    serializer_class = AccountingApprovalDelegationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        object_type = self.request.query_params.get('object_type')
        qs = _filter_queryset_by_entity_scope(AccountingApprovalDelegation.objects.all(), self.request.user).select_related(
            'entity', 'delegator', 'delegate', 'created_by'
        )
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if object_type is not None:
            qs = qs.filter(object_type=object_type)
        return qs

    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity, created_by=self.request.user)


class AccountingApprovalRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to accounting approval records."""

    serializer_class = AccountingApprovalRecordSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(AccountingApprovalRecord.objects.all(), self.request.user).select_related(
            'entity', 'requested_by', 'approved_by'
        ).prefetch_related('steps__assigned_role', 'steps__assigned_staff', 'steps__acted_by', 'change_logs__actor')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        object_type = self.request.query_params.get('object_type')
        if object_type:
            qs = qs.filter(object_type=object_type)
        return qs


class AccountingApprovalStepViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to accounting approval steps."""

    serializer_class = AccountingApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(
            AccountingApprovalStep.objects.all(),
            self.request.user,
            entity_relation='approval__entity',
        ).select_related('approval', 'assigned_role', 'assigned_staff', 'acted_by')
        if entity_id:
            qs = qs.filter(approval__entity_id=entity_id)
        approval_id = self.request.query_params.get('approval')
        if approval_id:
            qs = qs.filter(approval_id=approval_id)
        return qs


class AccountingApprovalChangeLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to accounting approval change logs."""

    serializer_class = AccountingApprovalChangeLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        qs = _filter_queryset_by_entity_scope(
            AccountingApprovalChangeLog.objects.all(),
            self.request.user,
            entity_relation='entity',
        ).select_related('approval', 'actor', 'entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        approval_id = self.request.query_params.get('approval')
        if approval_id:
            qs = qs.filter(approval_id=approval_id)
        return qs


class AccountingApprovalInboxViewSet(viewsets.ViewSet):
    """Unified inbox for journal and accounting object approvals."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        entity_id = request.query_params.get('entity_id') or request.query_params.get('entity')
        entity = _get_accessible_entity_or_404(request.user, entity_id) if entity_id else None
        items = build_journal_inbox_items(request.user, entity=entity) + build_accounting_inbox_items(request.user, entity=entity)
        items.sort(key=lambda item: item.get('submitted_at') or '', reverse=True)
        return Response({
            'pending': [item for item in items if item.get('status') in ['pending_review', 'pending_approval']],
            'history': [item for item in items if item.get('status') in ['approved', 'posted', 'rejected']],
            'summary': {
                'pending_count': len([item for item in items if item.get('status') in ['pending_review', 'pending_approval']]),
                'history_count': len([item for item in items if item.get('status') in ['approved', 'posted', 'rejected']]),
            },
        })


class RecurringJournalTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for Recurring Journal Entry Templates"""
    serializer_class = RecurringJournalTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return templates for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(RecurringJournalTemplate.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity, created_by=self.request.user)


class LedgerPeriodViewSet(viewsets.ModelViewSet):
    """ViewSet for managing accounting periods"""
    serializer_class = LedgerPeriodSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return periods for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(LedgerPeriod.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """Close an accounting period"""
        period = self.get_object()
        period.status = 'closed'
        if not period.no_posting_after:
            period.no_posting_after = period.end_date
        period.closed_at = timezone.now()
        period.closed_by = request.user
        period.save(update_fields=['status', 'no_posting_after', 'closed_at', 'closed_by'])
        
        serializer = self.get_serializer(period)
        return Response(serializer.data)


# ============================================================================
# ACCOUNTS RECEIVABLE (AR) VIEWSETS
# ============================================================================

class CustomerViewSet(viewsets.ModelViewSet):
    """ViewSet for customer management"""
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return customers for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(Customer.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class InvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for invoicing"""
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return invoices for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(Invoice.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        subtotal = Decimal(str(self.request.data.get('subtotal') or '0'))
        tax_amount = Decimal(str(self.request.data.get('tax_amount') or '0'))
        total_amount = Decimal(str(self.request.data.get('total_amount') or (subtotal + tax_amount)))
        serializer.save(
            entity=entity,
            created_by=self.request.user,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            outstanding_amount=total_amount,
        )

    def perform_update(self, serializer):
        subtotal = Decimal(str(self.request.data.get('subtotal') or serializer.instance.subtotal or '0'))
        tax_amount = Decimal(str(self.request.data.get('tax_amount') or serializer.instance.tax_amount or '0'))
        total_amount = Decimal(str(self.request.data.get('total_amount') or (subtotal + tax_amount)))
        paid_amount = serializer.instance.paid_amount or Decimal('0')
        outstanding_amount = max(total_amount - paid_amount, Decimal('0'))

        status = serializer.validated_data.get('status', serializer.instance.status)
        if status != 'cancelled':
            if outstanding_amount == 0 and paid_amount > 0:
                status = 'paid'
            elif paid_amount > 0:
                status = 'partially_paid'

        serializer.save(
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            outstanding_amount=outstanding_amount,
            status=status,
        )
    
    @action(detail=True, methods=['post'])
    def post(self, request, pk=None):
        """Post an invoice"""
        invoice = self.get_object()
        invoice.status = 'posted'
        invoice.save()
        serializer = self.get_serializer(invoice)
        return Response(serializer.data)


class CreditNoteViewSet(viewsets.ModelViewSet):
    """ViewSet for credit notes"""
    serializer_class = CreditNoteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return credit notes for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(CreditNote.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity, created_by=self.request.user)


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for customer payments"""
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return payments for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(Payment.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        invoice = serializer.validated_data['invoice']
        customer = serializer.validated_data.get('customer') or invoice.customer
        try:
            ensure_period_is_open(entity, serializer.validated_data['payment_date'])
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        serializer.save(entity=entity, customer=customer, created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected payments can be edited.'})
        try:
            ensure_period_is_open(serializer.instance.entity, serializer.validated_data.get('payment_date', serializer.instance.payment_date))
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected payments can be deleted.'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        payment = self.get_object()
        try:
            record = submit_accounting_object(payment, request.user, object_type='payment')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        payment = self.get_object()
        try:
            record = approve_accounting_object(AccountingApprovalRecord.objects.get(object_type='payment', object_id=payment.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this payment.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        payment = self.get_object()
        try:
            record = reject_accounting_object(AccountingApprovalRecord.objects.get(object_type='payment', object_id=payment.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this payment.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)


# ============================================================================
# ACCOUNTS PAYABLE (AP) VIEWSETS
# ============================================================================

class VendorViewSet(viewsets.ModelViewSet):
    """ViewSet for vendor management"""
    serializer_class = VendorSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return vendors for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(Vendor.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    """ViewSet for purchase orders"""
    serializer_class = PurchaseOrderSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return purchase orders for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(PurchaseOrder.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        subtotal = Decimal(str(self.request.data.get('subtotal') or '0'))
        tax_amount = Decimal(str(self.request.data.get('tax_amount') or '0'))
        total_amount = Decimal(str(self.request.data.get('total_amount') or (subtotal + tax_amount)))
        try:
            ensure_period_is_open(entity, serializer.validated_data['po_date'])
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        serializer.save(entity=entity, created_by=self.request.user, total_amount=total_amount)

    def perform_update(self, serializer):
        if serializer.instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected purchase orders can be edited.'})
        try:
            ensure_period_is_open(serializer.instance.entity, serializer.validated_data.get('po_date', serializer.instance.po_date))
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        subtotal = Decimal(str(self.request.data.get('subtotal') or serializer.instance.subtotal or '0'))
        tax_amount = Decimal(str(self.request.data.get('tax_amount') or serializer.instance.tax_amount or '0'))
        total_amount = Decimal(str(self.request.data.get('total_amount') or (subtotal + tax_amount)))
        serializer.save(subtotal=subtotal, tax_amount=tax_amount, total_amount=total_amount)

    def perform_destroy(self, instance):
        if instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected purchase orders can be deleted.'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        purchase_order = self.get_object()
        try:
            record = submit_accounting_object(purchase_order, request.user, object_type='purchase_order')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        purchase_order = self.get_object()
        try:
            record = approve_accounting_object(AccountingApprovalRecord.objects.get(object_type='purchase_order', object_id=purchase_order.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this purchase order.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        purchase_order = self.get_object()
        try:
            record = reject_accounting_object(AccountingApprovalRecord.objects.get(object_type='purchase_order', object_id=purchase_order.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this purchase order.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)


class BillViewSet(viewsets.ModelViewSet):
    """ViewSet for supplier bills"""
    serializer_class = BillSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return bills for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(Bill.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        subtotal = Decimal(str(self.request.data.get('subtotal') or '0'))
        tax_amount = Decimal(str(self.request.data.get('tax_amount') or '0'))
        total_amount = Decimal(str(self.request.data.get('total_amount') or (subtotal + tax_amount)))
        try:
            ensure_period_is_open(entity, serializer.validated_data['bill_date'])
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        serializer.save(entity=entity, created_by=self.request.user, subtotal=subtotal, tax_amount=tax_amount, total_amount=total_amount, outstanding_amount=total_amount)

    def perform_update(self, serializer):
        if serializer.instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected bills can be edited.'})
        try:
            ensure_period_is_open(serializer.instance.entity, serializer.validated_data.get('bill_date', serializer.instance.bill_date))
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        subtotal = Decimal(str(self.request.data.get('subtotal') or serializer.instance.subtotal or '0'))
        tax_amount = Decimal(str(self.request.data.get('tax_amount') or serializer.instance.tax_amount or '0'))
        total_amount = Decimal(str(self.request.data.get('total_amount') or (subtotal + tax_amount)))
        paid_amount = serializer.instance.paid_amount or Decimal('0')
        outstanding_amount = max(total_amount - paid_amount, Decimal('0'))

        status = serializer.validated_data.get('status', serializer.instance.status)
        if status != 'cancelled':
            if outstanding_amount == 0 and paid_amount > 0:
                status = 'paid'
            elif paid_amount > 0:
                status = 'partially_paid'

        serializer.save(
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            outstanding_amount=outstanding_amount,
            status=status,
        )

    def perform_destroy(self, instance):
        if instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected bills can be deleted.'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        bill = self.get_object()
        try:
            record = submit_accounting_object(bill, request.user, object_type='bill')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        bill = self.get_object()
        try:
            record = approve_accounting_object(AccountingApprovalRecord.objects.get(object_type='bill', object_id=bill.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this bill.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        bill = self.get_object()
        try:
            record = reject_accounting_object(AccountingApprovalRecord.objects.get(object_type='bill', object_id=bill.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this bill.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)


class BillPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for bill payments"""
    serializer_class = BillPaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return bill payments for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(BillPayment.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        bill = serializer.validated_data['bill']
        vendor = serializer.validated_data.get('vendor') or bill.vendor
        try:
            ensure_period_is_open(entity, serializer.validated_data['payment_date'])
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        serializer.save(entity=entity, vendor=vendor, created_by=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected bill payments can be edited.'})
        try:
            ensure_period_is_open(serializer.instance.entity, serializer.validated_data.get('payment_date', serializer.instance.payment_date))
        except ValueError as exc:
            raise ValidationError({'detail': str(exc)})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.approval_status not in ['draft', 'rejected']:
            raise ValidationError({'detail': 'Only draft or rejected bill payments can be deleted.'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        bill_payment = self.get_object()
        try:
            record = submit_accounting_object(bill_payment, request.user, object_type='bill_payment')
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        bill_payment = self.get_object()
        try:
            record = approve_accounting_object(AccountingApprovalRecord.objects.get(object_type='bill_payment', object_id=bill_payment.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this bill payment.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        bill_payment = self.get_object()
        try:
            record = reject_accounting_object(AccountingApprovalRecord.objects.get(object_type='bill_payment', object_id=bill_payment.id), request.user, comments=request.data.get('comments', ''))
        except AccountingApprovalRecord.DoesNotExist:
            return Response({'detail': 'No approval workflow exists for this bill payment.'}, status=drf_status.HTTP_400_BAD_REQUEST)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        return Response(AccountingApprovalRecordSerializer(record).data)


# ============================================================================
# INVENTORY VIEWSETS
# ============================================================================

class InventoryItemViewSet(viewsets.ModelViewSet):
    """ViewSet for inventory item management"""
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return inventory items for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(InventoryItem.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class InventoryTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for inventory transactions"""
    serializer_class = InventoryTransactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return inventory transactions for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(InventoryTransaction.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        item = serializer.validated_data['inventory_item']
        quantity_before = item.quantity_on_hand
        quantity = serializer.validated_data['quantity']
        unit_cost = serializer.validated_data.get('unit_cost') or item.unit_cost
        quantity_after = quantity_before + quantity
        total_cost = serializer.validated_data.get('total_cost') or (quantity * unit_cost)
        instance = serializer.save(
            entity=entity,
            created_by=self.request.user,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            unit_cost=unit_cost,
            total_cost=total_cost,
        )
        
        # Update inventory quantity
        item.quantity_on_hand = instance.quantity_after
        item.save()


class InventoryCOGSViewSet(viewsets.ModelViewSet):
    """ViewSet for COGS calculations"""
    serializer_class = InventoryCostOfGoodsSoldSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return COGS for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(InventoryCostOfGoodsSold.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


# ============================================================================
# RECONCILIATION VIEWSETS
# ============================================================================

class BankReconciliationViewSet(viewsets.ModelViewSet):
    """ViewSet for bank reconciliation"""
    serializer_class = BankReconciliationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return bank reconciliations for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(BankReconciliation.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        bank_statement_balance = Decimal(str(self.request.data.get('bank_statement_balance') or '0'))
        book_balance = Decimal(str(self.request.data.get('book_balance') or '0'))
        variance = abs(bank_statement_balance - book_balance)
        serializer.save(entity=entity, variance=variance)

    def perform_update(self, serializer):
        bank_statement_balance = Decimal(str(self.request.data.get('bank_statement_balance') or serializer.instance.bank_statement_balance or '0'))
        book_balance = Decimal(str(self.request.data.get('book_balance') or serializer.instance.book_balance or '0'))
        variance = abs(bank_statement_balance - book_balance)
        serializer.save(variance=variance)
    
    @action(detail=True, methods=['post'])
    def reconcile(self, request, pk=None):
        """Mark reconciliation as complete"""
        reconciliation = self.get_object()
        reconciliation.status = 'reconciled'
        reconciliation.reconciled_by = request.user
        reconciliation.reconciled_at = timezone.now()
        reconciliation.variance = abs(reconciliation.bank_statement_balance - reconciliation.book_balance)
        reconciliation.save()
        
        serializer = self.get_serializer(reconciliation)
        return Response(serializer.data)


# ============================================================================
# REVENUE RECOGNITION & DEFERRED REVENUE VIEWSETS
# ============================================================================

class DeferredRevenueViewSet(viewsets.ModelViewSet):
    """ViewSet for deferred revenue management"""
    serializer_class = DeferredRevenueSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return deferred revenues for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(DeferredRevenue.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class RevenueRecognitionScheduleViewSet(viewsets.ModelViewSet):
    """ViewSet for revenue recognition schedules"""
    serializer_class = RevenueRecognitionScheduleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return revenue recognition schedules"""
        return _filter_queryset_by_entity_scope(
            RevenueRecognitionSchedule.objects.all(),
            self.request.user,
            entity_relation='deferred_revenue__entity'
        )
    
    @action(detail=True, methods=['post'])
    def recognize(self, request, pk=None):
        """Recognize revenue for this schedule period"""
        schedule = self.get_object()
        schedule.is_recognized = True
        schedule.recognized_date = timezone.now()
        schedule.save()
        
        # Update deferred revenue
        deferred = schedule.deferred_revenue
        deferred.recognized_amount += schedule.amount_to_recognize
        deferred.remaining_amount = deferred.total_amount - deferred.recognized_amount
        if deferred.remaining_amount <= 0:
            deferred.status = 'recognized'
        else:
            deferred.status = 'recognizing'
        deferred.save()
        
        serializer = self.get_serializer(schedule)
        return Response(serializer.data)


# ============================================================================
# PERIOD CLOSE VIEWSETS
# ============================================================================

class PeriodCloseChecklistViewSet(viewsets.ModelViewSet):
    """ViewSet for period close checklists"""
    serializer_class = PeriodCloseChecklistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return close checklists for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(PeriodCloseChecklist.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


class PeriodCloseItemViewSet(viewsets.ModelViewSet):
    """ViewSet for period close items"""
    serializer_class = PeriodCloseItemSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return close items for user's entities"""
        return _filter_queryset_by_entity_scope(
            PeriodCloseItem.objects.all(),
            self.request.user,
            entity_relation='checklist__entity'
        )


# ============================================================================
# FX & MULTI-CURRENCY VIEWSETS
# ============================================================================

class ExchangeRateViewSet(viewsets.ModelViewSet):
    """ViewSet for exchange rates"""
    serializer_class = ExchangeRateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return exchange rates"""
        return ExchangeRate.objects.all().order_by('-rate_date')


class FXGainLossViewSet(viewsets.ModelViewSet):
    """ViewSet for FX gains/losses"""
    serializer_class = FXGainLossSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return FX gains/losses for user's entities"""
        entity_id = self.request.query_params.get('entity_id')
        qs = _filter_queryset_by_entity_scope(FXGainLoss.objects.all(), self.request.user)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs
    
    def perform_create(self, serializer):
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id)
        serializer.save(entity=entity)


# ============================================================================
# NOTIFICATION VIEWSETS
# ============================================================================

class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for user notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return notifications for current user"""
        qs = Notification.objects.filter(user=self.request.user)
        entity_id = self.request.query_params.get('entity_id') or self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(related_entity_id=entity_id)
        return qs
    
    @action(detail=False, methods=['get'])
    def unread(self, request):
        """Get unread notifications"""
        notifications = Notification.objects.filter(
            user=request.user,
            status='unread'
        ).order_by('-sent_at')
        entity_id = request.query_params.get('entity_id') or request.query_params.get('entity')
        if entity_id:
            notifications = notifications.filter(related_entity_id=entity_id)
        
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark notification as read"""
        notification = self.get_object()
        notification.status = 'read'
        notification.read_at = timezone.now()
        notification.save()
        
        serializer = self.get_serializer(notification)
        return Response(serializer.data)


class NotificationPreferenceViewSet(viewsets.ViewSet):
    """ViewSet for notification preferences"""
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationPreferenceSerializer
    
    def list(self, request):
        """Get user's notification preferences"""
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.serializer_class(prefs)
        return Response(serializer.data)
    
    def update(self, request, pk=None):
        """Update notification preferences"""
        prefs, _ = NotificationPreference.objects.get_or_create(user=request.user)
        serializer = self.serializer_class(prefs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)


# ============ CLIENT MANAGEMENT VIEWSETS ============

class ClientViewSet(viewsets.ModelViewSet):
    """ViewSet for managing clients"""
    serializer_class = ClientSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return Client.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return Client.objects.filter(organization__in=accessible_orgs)


class ClientPortalViewSet(viewsets.ModelViewSet):
    """ViewSet for client portal management"""
    serializer_class = ClientPortalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClientPortal.objects.filter(user=self.request.user)


class ClientMessageViewSet(viewsets.ModelViewSet):
    """ViewSet for client messaging"""
    serializer_class = ClientMessageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ClientMessage.objects.filter(Q(from_user=self.request.user) | Q(to_user=self.request.user))


class ClientDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for client documents"""
    serializer_class = ClientDocumentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return ClientDocument.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return ClientDocument.objects.filter(organization__in=accessible_orgs)


class DocumentRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for document requests"""
    serializer_class = DocumentRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return DocumentRequest.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return DocumentRequest.objects.filter(organization__in=accessible_orgs)

    def perform_create(self, serializer):
        organization = get_object_or_404(_accessible_organizations_queryset(self.request.user), id=self.request.data.get('organization'))
        document_request = serializer.save(organization=organization, requested_by=self.request.user)
        sync_document_request_to_platform_task(document_request)
        log_platform_audit_event(
            domain='document',
            actor=self.request.user,
            organization=organization,
            event_type='document_request.created',
            action='document_review_requested',
            resource_type='DocumentRequest',
            resource_id=str(document_request.id),
            subject_type='document_request',
            subject_id=str(document_request.id),
            resource_name=document_request.document_type,
            summary=f'Created document request for {document_request.document_type}',
            context={'client_id': document_request.client_id, 'status': document_request.status},
        )

    def perform_update(self, serializer):
        previous = self.get_object()
        before = {'status': previous.status, 'due_date': previous.due_date.isoformat() if previous.due_date else None}
        document_request = serializer.save()
        sync_document_request_to_platform_task(document_request)
        log_platform_audit_event(
            domain='document',
            actor=self.request.user,
            organization=document_request.organization,
            event_type='document_request.updated',
            action='document_request_updated',
            resource_type='DocumentRequest',
            resource_id=str(document_request.id),
            subject_type='document_request',
            subject_id=str(document_request.id),
            resource_name=document_request.document_type,
            summary=f'Updated document request for {document_request.document_type}',
            diff={'before': before, 'after': {'status': document_request.status, 'due_date': document_request.due_date.isoformat() if document_request.due_date else None}},
        )

    def perform_destroy(self, instance):
        log_platform_audit_event(
            domain='document',
            actor=self.request.user,
            organization=instance.organization,
            event_type='document_request.deleted',
            action='document_request_deleted',
            resource_type='DocumentRequest',
            resource_id=str(instance.id),
            subject_type='document_request',
            subject_id=str(instance.id),
            resource_name=instance.document_type,
            summary=f'Deleted document request for {instance.document_type}',
        )
        cancel_platform_tasks_for_origin(origin_type='document_request', origin_id=instance.id)
        super().perform_destroy(instance)


class ApprovalRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for approval requests"""
    serializer_class = ApprovalRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return ApprovalRequest.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return ApprovalRequest.objects.filter(organization__in=accessible_orgs)


# ============ DOCUMENT TEMPLATE VIEWSETS ============

class DocumentTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for document templates"""
    serializer_class = DocumentTemplateSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return DocumentTemplate.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return DocumentTemplate.objects.filter(organization__in=accessible_orgs)


# ============ LOAN MANAGEMENT VIEWSETS ============

class IntercompanyTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for mirrored intercompany accounting workflows."""

    serializer_class = IntercompanyTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        queryset = IntercompanyTransaction.objects.filter(organization__in=accessible_orgs)
        organization_id = self.request.query_params.get('organization')
        entity_id = self.request.query_params.get('entity')
        status_filter = self.request.query_params.get('status')

        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)
        if entity_id:
            queryset = queryset.filter(Q(source_entity_id=entity_id) | Q(destination_entity_id=entity_id))
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset.select_related(
            'organization',
            'source_entity',
            'destination_entity',
            'source_invoice',
            'destination_bill',
            'destination_loan',
        )

    def perform_create(self, serializer):
        source_entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('source_entity'))
        destination_entity = _get_accessible_entity_or_404(self.request.user, self.request.data.get('destination_entity'))

        if source_entity.organization_id != destination_entity.organization_id:
            raise ValidationError({'destination_entity': 'Both entities must belong to the same organization.'})
        if source_entity.id == destination_entity.id:
            raise ValidationError({'destination_entity': 'Source and destination entities must be different.'})

        organization = get_object_or_404(
            _accessible_organizations_queryset(self.request.user),
            id=self.request.data.get('organization') or source_entity.organization_id,
        )
        if organization.id != source_entity.organization_id:
            raise ValidationError({'organization': 'Organization must match the selected entities.'})

        reference_number = self.request.data.get('reference_number') or (
            f"IC-{organization.id}-{timezone.now().strftime('%Y%m%d%H%M%S%f')}"
        )
        transaction_record = serializer.save(
            organization=organization,
            source_entity=source_entity,
            destination_entity=destination_entity,
            reference_number=reference_number,
            created_by=self.request.user,
        )

        auto_post = str(self.request.data.get('auto_post', 'true')).lower() not in {'0', 'false', 'no'}
        if auto_post:
            try:
                post_intercompany_transaction(transaction_record, acting_user=self.request.user)
            except ValueError as exc:
                raise ValidationError({'detail': str(exc)})

    def perform_update(self, serializer):
        if serializer.instance.status != 'draft':
            raise ValidationError({'detail': 'Only draft intercompany transactions can be edited.'})
        serializer.save()

    def perform_destroy(self, instance):
        if instance.status != 'draft':
            raise ValidationError({'detail': 'Only draft intercompany transactions can be deleted.'})
        instance.delete()

    @action(detail=True, methods=['post'])
    def post(self, request, pk=None):
        transaction_record = self.get_object()
        try:
            post_intercompany_transaction(transaction_record, acting_user=request.user)
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(transaction_record)
        return Response(serializer.data)


class IntercompanyEliminationEntryViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for consolidation elimination outputs."""

    serializer_class = IntercompanyEliminationEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        queryset = IntercompanyEliminationEntry.objects.filter(
            consolidation__organization__in=accessible_orgs
        )
        consolidation_id = self.request.query_params.get('consolidation')
        if consolidation_id:
            queryset = queryset.filter(consolidation_id=consolidation_id)
        return queryset.select_related('transaction', 'source_entity', 'destination_entity', 'consolidation')


# ============ LOAN MANAGEMENT VIEWSETS ============

class LoanViewSet(viewsets.ModelViewSet):
    """ViewSet for loan management"""
    serializer_class = LoanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return Loan.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return Loan.objects.filter(organization__in=accessible_orgs)


class LoanPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for loan payments"""
    serializer_class = LoanPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        loan_id = self.request.query_params.get('loan')
        if loan_id:
            return LoanPayment.objects.filter(loan__organization__in=accessible_orgs, loan_id=loan_id)
        return LoanPayment.objects.filter(loan__organization__in=accessible_orgs)


# ============ COMPLIANCE & KYC/AML VIEWSETS ============

class KYCProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for KYC profiles"""
    serializer_class = KYCProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return KYCProfile.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return KYCProfile.objects.filter(organization__in=accessible_orgs)

    def _require_verified_email_for_document_upload(self):
        document_fields = {'id_document_url', 'proof_of_address_url', 'business_registration_url'}
        if document_fields.intersection(self.request.data) and not getattr(getattr(self.request.user, 'profile', None), 'email_verified', False):
            raise PermissionDenied('Please verify your email first.')

    def perform_create(self, serializer):
        self._require_verified_email_for_document_upload()
        serializer.save()

    def perform_update(self, serializer):
        self._require_verified_email_for_document_upload()
        serializer.save()


class AMLTransactionViewSet(viewsets.ModelViewSet):
    """ViewSet for AML transactions"""
    serializer_class = AMLTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return AMLTransaction.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return AMLTransaction.objects.filter(organization__in=accessible_orgs)


# ============ BILLING & FIRM MANAGEMENT VIEWSETS ============

class FirmServiceViewSet(viewsets.ModelViewSet):
    """ViewSet for firm services"""
    serializer_class = FirmServiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return FirmService.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return FirmService.objects.filter(organization__in=accessible_orgs)


class ClientInvoiceViewSet(viewsets.ModelViewSet):
    """ViewSet for client invoices"""
    serializer_class = ClientInvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return ClientInvoice.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return ClientInvoice.objects.filter(organization__in=accessible_orgs)


class ClientInvoiceLineItemViewSet(viewsets.ModelViewSet):
    """ViewSet for invoice line items"""
    serializer_class = ClientInvoiceLineItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        invoice_id = self.request.query_params.get('invoice')
        if invoice_id:
            return ClientInvoiceLineItem.objects.filter(invoice__organization__in=accessible_orgs, invoice_id=invoice_id)
        return ClientInvoiceLineItem.objects.filter(invoice__organization__in=accessible_orgs)


class ClientSubscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet for client subscriptions"""
    serializer_class = ClientSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return ClientSubscription.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return ClientSubscription.objects.filter(organization__in=accessible_orgs)


# ============ WHITE-LABELING VIEWSETS ============

class WhiteLabelBrandingViewSet(viewsets.ModelViewSet):
    """ViewSet for white-label branding"""
    serializer_class = WhiteLabelBrandingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return WhiteLabelBranding.objects.filter(organization__in=_accessible_organizations_queryset(self.request.user))


# ============ EMBEDDED BANKING & PAYMENTS VIEWSETS ============

class BankingIntegrationViewSet(viewsets.ModelViewSet):
    """ViewSet for banking integrations"""
    serializer_class = BankingIntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        entity_id = self.request.query_params.get('entity') or self.request.query_params.get('entity_id')
        if org_id:
            queryset = BankingIntegration.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        else:
            queryset = BankingIntegration.objects.filter(organization__in=accessible_orgs)
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
        return queryset.select_related('organization', 'entity')

    def perform_create(self, serializer):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        organization = get_object_or_404(accessible_orgs, id=self.request.data.get('organization'))
        entity_id = self.request.data.get('entity')
        entity = _get_accessible_entity_or_404(self.request.user, entity_id, organization=organization) if entity_id else None
        serializer.save(organization=organization, entity=entity)

    @action(detail=False, methods=['post'], url_path='consent-session')
    def consent_session(self, request):
        accessible_orgs = _accessible_organizations_queryset(request.user)
        organization = get_object_or_404(accessible_orgs, id=request.data.get('organization'))
        entity_id = request.data.get('entity')
        entity = _get_accessible_entity_or_404(request.user, entity_id, organization=organization) if entity_id else None

        integration_id = request.data.get('integration_id')
        if integration_id:
            integration = get_object_or_404(self.get_queryset(), id=integration_id)
            integration.entity = entity
            integration.integration_type = request.data.get('integration_type', integration.integration_type)
            integration.provider_code = request.data.get('provider_code', integration.provider_code)
            integration.provider_name = request.data.get('provider_name', integration.provider_name)
            integration.webhook_url = request.data.get('webhook_url', integration.webhook_url)
            api_key = request.data.get('api_key')
            api_secret = request.data.get('api_secret')
            if api_key is not None:
                integration.set_api_key(api_key)
            if api_secret is not None:
                integration.set_api_secret(api_secret)
            integration.save()
        else:
            integration = BankingIntegration(
                organization=organization,
                entity=entity,
                integration_type=request.data.get('integration_type', 'open_banking'),
                provider_code=request.data.get('provider_code', 'custom'),
                provider_name=request.data.get('provider_name') or request.data.get('provider_code', 'Custom').title(),
                webhook_url=request.data.get('webhook_url', ''),
                status='pending',
                is_active=True,
            )
            integration.set_api_key(request.data.get('api_key', ''))
            integration.set_api_secret(request.data.get('api_secret', ''))
            integration.save()

        session = prepare_oauth_consent(
            integration,
            redirect_uri=request.data.get('redirect_uri', ''),
            scopes=request.data.get('scopes') or None,
            requested_by=request.user,
            ip_address=_request_ip(request),
        )

        return Response(
            {
                **session,
                'integration': self.get_serializer(integration).data,
            },
            status=drf_status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'], url_path='complete-consent')
    def complete_consent(self, request, pk=None):
        integration = self.get_object()
        try:
            result = complete_oauth_consent(
                integration,
                authorization_code=request.data.get('authorization_code') or request.data.get('code') or '',
                state=request.data.get('state', ''),
                requested_by=request.user,
                ip_address=_request_ip(request),
                access_token=request.data.get('access_token', ''),
                refresh_token=request.data.get('refresh_token', ''),
                expires_in=request.data.get('expires_in', 3600),
                consent_reference=request.data.get('consent_reference', ''),
                metadata=request.data.get('metadata') or {},
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

        sync_summary = None
        if request.data.get('accounts') or request.data.get('transactions'):
            sync_run = sync_banking_integration(
                integration,
                payload=request.data,
                initiated_by=request.user,
                trigger_type='manual',
            )
            sync_summary = {
                'sync_run_id': sync_run.id,
                'transactions_processed': sync_run.transactions_processed,
                'accounts_processed': sync_run.accounts_processed,
                'status': sync_run.status,
            }

        return Response(
            {
                'integration': self.get_serializer(integration).data,
                'consent': result,
                'sync': sync_summary,
            },
            status=drf_status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='sync')
    def sync(self, request, pk=None):
        integration = self.get_object()
        try:
            sync_run = sync_banking_integration(
                integration,
                payload=request.data or {},
                initiated_by=request.user,
                trigger_type='manual',
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=drf_status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                'sync_run_id': sync_run.id,
                'status': sync_run.status,
                'accounts_processed': sync_run.accounts_processed,
                'transactions_processed': sync_run.transactions_processed,
                'completed_at': sync_run.completed_at,
                'response_payload': sync_run.response_payload,
            },
            status=drf_status.HTTP_200_OK,
        )

    @action(detail=False, methods=['post'], url_path=r'webhooks/(?P<provider_code>[^/.]+)', permission_classes=[AllowAny])
    def webhook(self, request, provider_code=None):
        result = handle_banking_webhook(
            provider_code,
            request.data or {},
            signature=request.headers.get('X-Bank-Signature', ''),
        )
        status_code = drf_status.HTTP_202_ACCEPTED if result['accepted'] else drf_status.HTTP_400_BAD_REQUEST
        return Response(result, status=status_code)


class BankingTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for banking transactions (read-only)"""
    serializer_class = BankingTransactionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = _filter_queryset_by_entity_scope(
            BankingTransaction.objects.select_related('bank_account', 'integration', 'entity'),
            self.request.user,
        )
        entity_id = self.request.query_params.get('entity')
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        integration_id = self.request.query_params.get('integration')
        if integration_id:
            qs = qs.filter(integration_id=integration_id)
        merchant = self.request.query_params.get('merchant')
        if merchant:
            qs = qs.filter(Q(merchant_name__icontains=merchant) | Q(description__icontains=merchant))
        category_name = self.request.query_params.get('category')
        if category_name:
            qs = qs.filter(normalized_category__iexact=category_name)
        bank_account_id = self.request.query_params.get('bank_account')
        if bank_account_id:
            qs = qs.filter(bank_account_id=bank_account_id)
        start_date = self.request.query_params.get('start_date')
        if start_date:
            qs = qs.filter(transaction_date__date__gte=start_date)
        end_date = self.request.query_params.get('end_date')
        if end_date:
            qs = qs.filter(transaction_date__date__lte=end_date)
        return qs

    @action(detail=True, methods=['post'], url_path='override-category')
    def override_category(self, request, pk=None):
        banking_transaction = self.get_object()
        category_name = request.data.get('category_name') or request.data.get('normalized_category')
        if not category_name:
            return Response({'detail': 'category_name is required.'}, status=drf_status.HTTP_400_BAD_REQUEST)

        override_banking_transaction_category(
            banking_transaction,
            category_name=category_name,
            dashboard_bucket=request.data.get('dashboard_bucket', ''),
            explanation=request.data.get('explanation', ''),
            user=request.user,
            learn=bool(request.data.get('learn', True)),
        )
        banking_transaction.refresh_from_db()
        return Response(self.get_serializer(banking_transaction).data, status=drf_status.HTTP_200_OK)


class EmbeddedPaymentViewSet(viewsets.ModelViewSet):
    """ViewSet for embedded payments"""
    serializer_class = EmbeddedPaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return EmbeddedPayment.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return EmbeddedPayment.objects.filter(organization__in=accessible_orgs)


# ============ WORKFLOW AUTOMATION VIEWSETS ============

class AutomationWorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for automation workflows"""
    serializer_class = AutomationWorkflowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return AutomationWorkflow.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return AutomationWorkflow.objects.filter(organization__in=accessible_orgs)

    def perform_create(self, serializer):
        organization = get_object_or_404(
            _accessible_organizations_queryset(self.request.user),
            id=self.request.data.get('organization'),
        )
        entity_id = self.request.data.get('entity')
        entity = None
        if entity_id:
            entity = get_object_or_404(_accessible_entities_queryset(self.request.user, organization=organization), id=entity_id)
        trigger_config = serializer.validated_data.get('trigger_config')
        if serializer.validated_data.get('trigger_type') == 'schedule':
            trigger_config = normalize_schedule_trigger_config(trigger_config)
        serializer.save(organization=organization, entity=entity, created_by=self.request.user, trigger_config=trigger_config)

    def perform_update(self, serializer):
        organization = get_object_or_404(
            _accessible_organizations_queryset(self.request.user),
            id=self.request.data.get('organization') or serializer.instance.organization_id,
        )
        entity_id = self.request.data.get('entity')
        entity = None
        if entity_id:
            entity = get_object_or_404(_accessible_entities_queryset(self.request.user, organization=organization), id=entity_id)
        trigger_type = serializer.validated_data.get('trigger_type', serializer.instance.trigger_type)
        trigger_config = serializer.validated_data.get('trigger_config', serializer.instance.trigger_config)
        if trigger_type == 'schedule':
            trigger_config = normalize_schedule_trigger_config(trigger_config)
        serializer.save(organization=organization, entity=entity, trigger_config=trigger_config)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        workflow = self.get_object()
        execution = execute_automation_workflow(workflow, initiated_by=request.user, trigger_type='manual')
        return Response(self.get_serializer(workflow).data | {'last_execution': AutomationExecutionSerializer(execution).data})

    @action(detail=False, methods=['post'])
    def run_due(self, request):
        results = run_due_automation_workflows()
        return Response(results)

    @action(detail=False, methods=['get'])
    def cleanup_impact(self, request):
        report = build_automation_cleanup_impact_report(
            workflows=self.get_queryset().select_related('entity'),
            days_ahead=request.query_params.get('days_ahead', 30),
        )
        return Response(report)


class AutomationExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for automation executions"""
    serializer_class = AutomationExecutionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            return AutomationExecution.objects.filter(workflow__organization__in=accessible_orgs, workflow_id=workflow_id)
        return AutomationExecution.objects.filter(workflow__organization__in=accessible_orgs)


class AutomationArtifactViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for persisted automation artifacts."""

    serializer_class = AutomationArtifactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        queryset = AutomationArtifact.objects.filter(organization__in=accessible_orgs)
        workflow_id = self.request.query_params.get('workflow')
        execution_id = self.request.query_params.get('execution')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        if execution_id:
            queryset = queryset.filter(execution_id=execution_id)
        return queryset.select_related('workflow', 'execution', 'organization', 'entity')

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        artifact = self.get_object()
        response = FileResponse(artifact.file_path.open('rb'), as_attachment=True, filename=artifact.file_name)
        response['Content-Type'] = 'application/octet-stream'
        return response


# ============ FIRM DASHBOARD & BUSINESS INTELLIGENCE VIEWSETS ============

class FirmMetricViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for firm metrics"""
    serializer_class = FirmMetricSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return FirmMetric.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return FirmMetric.objects.filter(organization__in=accessible_orgs)


class ClientMarketplaceIntegrationViewSet(viewsets.ModelViewSet):
    """ViewSet for client marketplace integrations"""
    serializer_class = ClientMarketplaceIntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        org_id = self.request.query_params.get('organization')
        if org_id:
            return ClientMarketplaceIntegration.objects.filter(organization__in=accessible_orgs, organization_id=org_id)
        return ClientMarketplaceIntegration.objects.filter(organization__in=accessible_orgs)


class DeveloperModuleInstallationViewSet(viewsets.ModelViewSet):
    """Deploy governed modules and retain each installation in the platform audit stream."""

    serializer_class = DeveloperModuleInstallationSerializer
    permission_classes = [IsAuthenticated]
    TIER_ORDER = {'basic': 0, 'professional': 1, 'enterprise': 2, 'institutional': 3}

    def get_queryset(self):
        accessible_orgs = _accessible_organizations_queryset(self.request.user)
        organization_id = self.request.query_params.get('organization')
        queryset = DeveloperModuleInstallation.objects.filter(organization__in=accessible_orgs)
        return queryset.filter(organization_id=organization_id) if organization_id else queryset

    def _organization_tier(self, organization):
        return (organization.settings or {}).get('subscription_tier', 'basic').lower()

    def perform_create(self, serializer):
        organization = serializer.validated_data['organization']
        required_tier = serializer.validated_data.get('required_tier', 'basic')
        current_tier = self._organization_tier(organization)
        if self.TIER_ORDER.get(current_tier, 0) < self.TIER_ORDER[required_tier]:
            raise ValidationError({'required_tier': f'{required_tier.title()} subscription required for this module.'})
        installation = serializer.save(installed_by=self.request.user)
        log_platform_audit_event(
            domain='developer_marketplace', event_type='module.deployed', action='module.deployed',
            resource_type='DeveloperModuleInstallation', resource_id=installation.id, resource_name=installation.module_name,
            summary=f'Deployed {installation.module_name}', actor=self.request.user, organization=organization,
            metadata={'module_key': installation.module_key, 'version': installation.version, 'required_tier': required_tier},
        )

    def perform_update(self, serializer):
        installation = serializer.save()
        log_platform_audit_event(
            domain='developer_marketplace', event_type='module.updated', action='module.updated',
            resource_type='DeveloperModuleInstallation', resource_id=installation.id, resource_name=installation.module_name,
            summary=f'Updated {installation.module_name}', actor=self.request.user, organization=installation.organization,
            metadata={'module_key': installation.module_key, 'version': installation.version, 'status': installation.status},
        )
