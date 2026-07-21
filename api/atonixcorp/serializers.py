from django.utils.text import slugify
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Count
from .models import (
    Expense, Income, Budget, UserProfile, Organization, Entity, Role, Permission,
    TeamMember, TaxExposure, TaxRegimeRegistry, TaxProfile, ComplianceDeadline, CashflowForecast, AuditLog, PlatformAuditEvent, PlatformTask,
    GovernancePolicy, GovernanceAmendment, GovernanceVote, GovernanceCommissionPlan, GovernanceCommissionEntry,
    ModelTemplate, FinancialModel, Scenario, SensitivityAnalysis, AIInsight,
    CustomKPI, KPICalculation, Report, Consolidation, ConsolidationEntity,
    IntercompanyTransaction, IntercompanyEliminationEntry,
    TaxCalculation, TaxFiling, TaxAuditLog, TaxRuleSetVersion, TaxRiskAlert, ACCOUNT_TYPE_PERSONAL, ACCOUNT_TYPE_ENTERPRISE,
    EntityDepartment, EntityRole, EntityStaff, BankAccount, Wallet, ComplianceDocument,
    StaffPayrollProfile, PayrollComponent, StaffPayrollComponentAssignment,
    LeaveType, LeaveBalance, LeaveRequest, PayrollBankOriginatorProfile, PayrollRun, Payslip, PayslipLineItem,
    PayrollStatutoryReport, PayrollBankPaymentFile,
    BookkeepingCategory, BookkeepingAccount, Transaction, BookkeepingAuditLog,
    RecurringTransaction, TaskRequest,
    # Core GL/COA models
    ChartOfAccounts, GeneralLedger, JournalEntry, JournalApprovalMatrix, JournalApprovalDelegation,
    JournalEntryApprovalStep, JournalEntryChangeLog, AccountingApprovalMatrix,
    AccountingApprovalDelegation, AccountingApprovalRecord, AccountingApprovalStep,
    AccountingApprovalChangeLog, RecurringJournalTemplate, LedgerPeriod,
    # AR models
    Customer, Invoice, InvoiceLineItem, CreditNote, Payment,
    # AP models
    Vendor, PurchaseOrder, Bill, BillPayment,
    # Inventory models
    InventoryItem, InventoryTransaction, InventoryCostOfGoodsSold,
    # Reconciliation models
    BankReconciliation,
    # Revenue Recognition models
    DeferredRevenue, RevenueRecognitionSchedule,
    # Period Close models
    PeriodCloseChecklist, PeriodCloseItem,
    # FX models
    ExchangeRate, FXGainLoss,
    # Notification models
    Notification, NotificationPreference,
    # NEW MODELS
    Client, ClientPortal, ClientMessage, ClientDocument, DocumentRequest, ApprovalRequest,
    DocumentTemplate, Loan, LoanPayment, KYCProfile, AMLTransaction, FirmService,
    ClientInvoice, ClientInvoiceLineItem, ClientSubscription, WhiteLabelBranding, DeveloperModuleInstallation,
    BankingIntegration, BankingTransaction, EmbeddedPayment, AutomationWorkflow,
    AutomationExecution, AutomationArtifact, FirmMetric, ClientMarketplaceIntegration
)
from .banking_security import mask_secret
from .tax_security import mask_json_payload, mask_tax_identifier, should_mask_tax_audit
from .company_identity import normalize_registration_number


# ============ User & Auth Serializers ============

class UserProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.ReadOnlyField(source='user.id')
    secure_user_id = serializers.ReadOnlyField()
    email = serializers.ReadOnlyField(source='user.email')
    username = serializers.ReadOnlyField(source='user.username')
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = ['user_id', 'secure_user_id', 'email', 'username', 'first_name', 'last_name', 'account_type', 'country', 'phone', 'tax_type', 'tax_rate', 'avatar_color', 'created_at']
        read_only_fields = ['created_at']

    def get_first_name(self, obj):
        return obj.user.first_name

    def get_last_name(self, obj):
        return obj.user.last_name


# ============ Organization Serializers ============

class OrganizationSerializer(serializers.ModelSerializer):
    owner_name = serializers.ReadOnlyField(source='owner.get_full_name')
    owner_email = serializers.ReadOnlyField(source='owner.email')
    # Backward-compatible aliases (frontend previously used `country`/`currency`)
    country = serializers.CharField(source='primary_country', required=False)
    currency = serializers.CharField(source='primary_currency', required=False)
    email = serializers.EmailField(source='settings.email', required=False, allow_blank=True)
    address = serializers.CharField(source='settings.address', required=False, allow_blank=True)
    service_time = serializers.CharField(source='settings.service_time', required=False, allow_blank=True)
    registration_number = serializers.CharField(required=False, allow_blank=False, max_length=64)

    class Meta:
        model = Organization
        fields = ['id', 'name', 'registration_number', 'slug', 'description', 'logo_url', 'industry', 'employee_count', 'primary_currency', 'primary_country', 'country', 'currency', 'email', 'address', 'service_time', 'settings', 'website', 'owner_name', 'owner_email', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            'slug': {'required': False, 'allow_blank': True},
        }

    def validate_registration_number(self, value):
        try:
            return normalize_registration_number(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages[0])

    def validate(self, attrs):
        name = str(attrs.get('name', getattr(self.instance, 'name', ''))).strip()
        if not name:
            raise serializers.ValidationError({'name': 'Company name is required.'})
        existing_names = Organization.objects.filter(name__iexact=name)
        if self.instance:
            existing_names = existing_names.exclude(pk=self.instance.pk)
        if existing_names.exists():
            raise serializers.ValidationError({'name': 'A company with this name already exists.'})
        if self.instance is None and not attrs.get('registration_number'):
            raise serializers.ValidationError({'registration_number': 'Company registration number is required.'})
        registration_number = attrs.get('registration_number')
        if registration_number:
            existing_registration_numbers = Organization.objects.filter(registration_number=registration_number)
            if self.instance:
                existing_registration_numbers = existing_registration_numbers.exclude(pk=self.instance.pk)
            if existing_registration_numbers.exists():
                raise serializers.ValidationError({
                    'registration_number': 'This company registration number is already in use.'
                })
        return attrs

    def _merge_settings(self, validated_data, instance=None):
        incoming_settings = validated_data.pop('settings', None) or {}
        existing_settings = dict(getattr(instance, 'settings', {}) or {}) if instance is not None else {}
        existing_settings.update(incoming_settings)
        validated_data['settings'] = existing_settings

    def create(self, validated_data):
        self._merge_settings(validated_data)
        validated_data['name'] = validated_data['name'].strip()
        slug = (validated_data.get('slug') or '').strip()
        if not slug:
            base_slug = slugify(validated_data.get('name') or '') or 'organization'
            slug = base_slug
            suffix = 2
            while Organization.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{suffix}'
                suffix += 1
            validated_data['slug'] = slug
        return super().create(validated_data)

    def update(self, instance, validated_data):
        self._merge_settings(validated_data, instance=instance)
        return super().update(instance, validated_data)


# ============ Entity Serializers ============

class EntitySerializer(serializers.ModelSerializer):
    child_entities = serializers.SerializerMethodField()
    registration_number_masked = serializers.SerializerMethodField()
    parent_entity_name = serializers.SerializerMethodField()

    class Meta:
        model = Entity
        fields = ['id', 'name', 'country', 'entity_type', 'status', 'registration_number', 'registration_number_masked', 'local_currency', 'main_bank', 'tax_authority_url', 'fiscal_year_end', 'next_filing_date', 'workspace_mode', 'industry', 'workspace_type', 'workspace_template_key', 'hierarchy_metadata', 'dashboard_config', 'rbac_config', 'enabled_modules', 'parent_entity', 'parent_entity_name', 'child_entities', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_child_entities(self, obj):
        children = obj.child_entities.all()
        return EntitySerializer(children, many=True).data

    def get_registration_number_masked(self, obj):
        return mask_tax_identifier(obj.registration_number)

    def get_parent_entity_name(self, obj):
        return getattr(obj.parent_entity, 'name', None)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['registration_number'] = mask_tax_identifier(data.get('registration_number'))
        return data


class EntityDetailSerializer(EntitySerializer):
    """Extended serializer with related data"""
    tax_exposures = serializers.SerializerMethodField()
    compliance_deadlines = serializers.SerializerMethodField()

    def get_tax_exposures(self, obj):
        exposures = obj.tax_exposures.all()
        return TaxExposureSerializer(exposures, many=True).data

    def get_compliance_deadlines(self, obj):
        deadlines = obj.compliance_deadlines.all()
        return ComplianceDeadlineSerializer(deadlines, many=True).data


# ============ Permission & Role Serializers ============

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'code', 'get_code_display']
        read_only_fields = ['code']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        source='permissions',
        many=True,
        write_only=True
    )

    class Meta:
        model = Role
        fields = ['id', 'name', 'code', 'description', 'permissions', 'permission_ids', 'created_at']
        read_only_fields = ['created_at', 'code']


# ============ Team Member Serializers ============

class TeamMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    role_name = serializers.ReadOnlyField(source='role.name')
    role_code = serializers.ReadOnlyField(source='role.code')

    class Meta:
        model = TeamMember
        fields = ['id', 'user_email', 'user_name', 'role', 'role_name', 'role_code', 'scoped_entities', 'is_active', 'invited_at', 'accepted_at', 'created_at', 'updated_at']
        read_only_fields = ['invited_at', 'accepted_at', 'created_at', 'updated_at']


# ============ Financial Data Serializers ============

class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ['id', 'user', 'entity', 'description', 'amount', 'category', 'date', 'currency', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = ['id', 'user', 'entity', 'source', 'amount', 'date', 'income_type', 'currency', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class BudgetSerializer(serializers.ModelSerializer):
    percentage_used = serializers.ReadOnlyField()
    remaining = serializers.ReadOnlyField()

    class Meta:
        model = Budget
        fields = ['id', 'user', 'entity', 'category', 'limit', 'spent', 'color', 'currency', 'percentage_used', 'remaining', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ Tax & Compliance Serializers ============

class TaxExposureSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxExposure
        fields = ['id', 'entity', 'country', 'tax_type', 'period', 'tax_year', 'period_start', 'period_end', 'estimated_amount', 'actual_amount', 'paid_amount', 'currency', 'status', 'filing_deadline', 'payment_deadline', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ComplianceDeadlineSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    responsible_user_name = serializers.ReadOnlyField(source='responsible_user.get_full_name')

    class Meta:
        model = ComplianceDeadline
        fields = ['id', 'organization', 'entity', 'entity_name', 'title', 'deadline_type', 'deadline_date', 'status', 'description', 'responsible_user', 'responsible_user_name', 'completed_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class CashflowForecastSerializer(serializers.ModelSerializer):
    class Meta:
        model = CashflowForecast
        fields = ['id', 'entity', 'month', 'category', 'forecasted_amount', 'actual_amount', 'currency', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaxProfileSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    registration_numbers_masked = serializers.SerializerMethodField()

    class Meta:
        model = TaxProfile
        fields = ['id', 'entity', 'entity_name', 'country', 'jurisdiction_code', 'status', 'effective_from', 'effective_to', 'tax_rules', 'registered_regimes', 'registration_numbers', 'registration_numbers_masked', 'filing_preferences', 'auto_update', 'residency_status', 'compliance_score', 'last_rule_update', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_registration_numbers_masked(self, obj):
        if not isinstance(obj.registration_numbers, dict):
            return {}
        return {key: mask_tax_identifier(value) for key, value in obj.registration_numbers.items()}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        registration_numbers = data.get('registration_numbers')
        if isinstance(registration_numbers, dict):
            data['registration_numbers'] = {key: mask_tax_identifier(value) for key, value in registration_numbers.items()}
        return data


class TaxRegimeRegistrySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRegimeRegistry
        fields = ['id', 'jurisdiction_code', 'country', 'regime_code', 'regime_name', 'tax_type', 'regime_category', 'filing_frequency', 'filing_form', 'required_forms', 'calculation_method', 'penalty_rules', 'rules_json', 'forms_json', 'penalty_rules_json', 'compliance_rules_json', 'effective_from', 'effective_to', 'rule_set', 'reference_links', 'is_active', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.get_full_name')

    class Meta:
        model = AuditLog
        fields = ['id', 'organization', 'user', 'user_name', 'action', 'model_name', 'object_id', 'changes', 'ip_address', 'created_at']
        read_only_fields = ['created_at']


class PlatformAuditEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    actor_id = serializers.SerializerMethodField()
    organization_name = serializers.ReadOnlyField(source='organization.name')
    entity_name = serializers.ReadOnlyField(source='entity.name')

    class Meta:
        model = PlatformAuditEvent
        fields = [
            'id', 'organization', 'organization_name', 'entity', 'entity_name', 'workspace_id',
            'actor', 'actor_name', 'actor_type', 'actor_id',
            'subject_type', 'subject_id', 'action', 'context', 'diff', 'correlation_id',
            'domain', 'event_type', 'resource_type', 'resource_id',
            'resource_name', 'summary', 'metadata', 'occurred_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor else 'System'

    def get_actor_id(self, obj):
        return obj.actor_identifier or str(obj.actor_id or '')


class GovernancePolicySerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    amendment_count = serializers.IntegerField(source='amendments.count', read_only=True)

    class Meta:
        model = GovernancePolicy
        fields = [
            'id', 'organization', 'policy_code', 'title', 'edition', 'status', 'summary', 'source_document',
            'effective_date', 'next_review_date', 'owner', 'owner_name', 'amendment_count', 'created_at', 'updated_at',
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def get_owner_name(self, obj):
        return obj.owner.get_full_name() if obj.owner else ''


class GovernanceAmendmentSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.SerializerMethodField()
    required_approval_percent = serializers.ReadOnlyField()
    vote_summary = serializers.SerializerMethodField()

    class Meta:
        model = GovernanceAmendment
        fields = [
            'id', 'policy', 'amendment_number', 'title', 'amendment_type', 'status', 'rationale', 'impact_analysis',
            'ethical_review', 'sovereignty_check', 'operational_feasibility', 'security_implications', 'implementation_timeline',
            'submitted_by', 'submitted_by_name', 'submitted_at', 'voting_opens_at', 'voting_closes_at', 'approved_at',
            'required_approval_percent', 'vote_summary', 'created_at', 'updated_at',
        ]
        read_only_fields = ['submitted_by', 'submitted_at', 'approved_at', 'created_at', 'updated_at']

    def get_submitted_by_name(self, obj):
        return obj.submitted_by.get_full_name() if obj.submitted_by else ''

    def get_vote_summary(self, obj):
        if not obj.pk:
            return {
                'approve': 0,
                'reject': 0,
                'abstain': 0,
                'approval_percent': 0,
                'meets_threshold': False,
            }
        votes = obj.votes.values('decision').annotate(total=Count('id'))
        summary = {item['decision']: item['total'] for item in votes}
        cast_votes = summary.get('approve', 0) + summary.get('reject', 0)
        approval_percent = round((summary.get('approve', 0) / cast_votes) * 100, 2) if cast_votes else 0
        return {
            'approve': summary.get('approve', 0),
            'reject': summary.get('reject', 0),
            'abstain': summary.get('abstain', 0),
            'approval_percent': approval_percent,
            'meets_threshold': approval_percent >= obj.required_approval_percent,
        }


class GovernanceVoteSerializer(serializers.ModelSerializer):
    voter_name = serializers.SerializerMethodField()

    class Meta:
        model = GovernanceVote
        fields = ['id', 'amendment', 'voter', 'voter_name', 'decision', 'comment', 'verified_at']
        read_only_fields = ['voter', 'verified_at']

    def get_voter_name(self, obj):
        return obj.voter.get_full_name() or obj.voter.username


class GovernanceCommissionPlanSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GovernanceCommissionPlan
        fields = [
            'id', 'organization', 'organization_name', 'role_code', 'name', 'trigger_type', 'rate_percent',
            'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def validate_rate_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('Commission rate must be between 0 and 100 percent.')
        return value

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else ''


class GovernanceCommissionEntrySerializer(serializers.ModelSerializer):
    plan_name = serializers.ReadOnlyField(source='plan.name')
    role_code = serializers.ReadOnlyField(source='plan.role_code')
    recipient_name = serializers.SerializerMethodField()

    class Meta:
        model = GovernanceCommissionEntry
        fields = [
            'id', 'plan', 'plan_name', 'role_code', 'recipient', 'recipient_name', 'source_reference',
            'source_description', 'base_amount', 'commission_amount', 'currency', 'status', 'calculated_by',
            'calculated_at', 'paid_at',
        ]
        read_only_fields = [
            'plan', 'recipient', 'source_reference', 'source_description', 'base_amount', 'commission_amount',
            'currency', 'calculated_by', 'calculated_at', 'paid_at',
        ]

    def get_recipient_name(self, obj):
        return obj.recipient.get_full_name() or obj.recipient.username


class GovernanceCommissionCalculationSerializer(serializers.Serializer):
    recipient = serializers.PrimaryKeyRelatedField(queryset=User.objects.all())
    source_reference = serializers.CharField(max_length=100)
    source_description = serializers.CharField(max_length=255, required=False, allow_blank=True)
    base_amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=0)
    currency = serializers.CharField(max_length=3, default='USD')

    def validate_currency(self, value):
        return value.upper()


# ============ Dashboard Summary Serializers ============

class OrgOverviewSerializer(serializers.Serializer):
    """Serializer for organization overview dashboard"""
    total_assets = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_liabilities = serializers.DecimalField(max_digits=15, decimal_places=2)
    net_position = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_cash_by_currency = serializers.DictField()
    total_tax_exposure = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_jurisdictions = serializers.IntegerField()
    active_entities = serializers.IntegerField()
    pending_tax_returns = serializers.IntegerField()
    missing_data_entities = serializers.IntegerField()
    tax_exposure_by_country = serializers.DictField()


class EntityHierarchySerializer(serializers.Serializer):
    """Serializer for entity hierarchy visualization"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    country = serializers.CharField()
    entity_type = serializers.CharField()
    status = serializers.CharField()
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        if hasattr(obj, 'child_entities'):
            return EntityHierarchySerializer(obj.child_entities.all(), many=True).data
        return []


class PersonalDashboardSerializer(serializers.Serializer):
    """Serializer for personal dashboard overview"""
    net_position = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_income = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_spending = serializers.DecimalField(max_digits=15, decimal_places=2)
    monthly_tax_provision = serializers.DecimalField(max_digits=15, decimal_places=2)
    active_countries = serializers.ListField(child=serializers.CharField())
    pending_insights = serializers.ListField(child=serializers.DictField())
    upcoming_deadlines = serializers.ListField(child=serializers.DictField())


# ============ FINANCIAL MODELING SERIALIZERS ============

class ModelTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelTemplate
        fields = ['id', 'name', 'template_type', 'description', 'industry', 'version', 'is_active', 'default_assumptions', 'calculation_logic', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class FinancialModelSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    organization_name = serializers.ReadOnlyField(source='organization.name')
    template_name = serializers.ReadOnlyField(source='template.name')

    class Meta:
        model = FinancialModel
        fields = ['id', 'name', 'model_type', 'status', 'user', 'user_name', 'organization', 'organization_name', 'template', 'template_name', 'input_data', 'assumptions', 'results', 'metadata', 'enterprise_value', 'equity_value', 'irr', 'moic', 'created_at', 'updated_at', 'calculated_at']
        read_only_fields = ['created_at', 'updated_at', 'calculated_at']


class FinancialModelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating financial models"""
    class Meta:
        model = FinancialModel
        fields = ['name', 'model_type', 'organization', 'template', 'input_data', 'assumptions']


class ScenarioSerializer(serializers.ModelSerializer):
    financial_model_name = serializers.ReadOnlyField(source='financial_model.name')

    class Meta:
        model = Scenario
        fields = ['id', 'name', 'scenario_type', 'financial_model', 'financial_model_name', 'assumptions_override', 'results', 'enterprise_value', 'irr', 'probability', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class SensitivityAnalysisSerializer(serializers.ModelSerializer):
    financial_model_name = serializers.ReadOnlyField(source='financial_model.name')

    class Meta:
        model = SensitivityAnalysis
        fields = ['id', 'financial_model', 'financial_model_name', 'variable_name', 'base_value', 'range_min', 'range_max', 'steps', 'results', 'created_at']
        read_only_fields = ['created_at']


class AIInsightSerializer(serializers.ModelSerializer):
    financial_model_name = serializers.ReadOnlyField(source='financial_model.name')

    class Meta:
        model = AIInsight
        fields = ['id', 'financial_model', 'financial_model_name', 'insight_type', 'priority', 'title', 'description', 'confidence_score', 'supporting_data', 'recommendations', 'is_read', 'created_at']
        read_only_fields = ['created_at']


class CustomKPISerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')

    class Meta:
        model = CustomKPI
        fields = ['id', 'organization', 'organization_name', 'name', 'formula', 'description', 'unit', 'target_value', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class KPICalculationSerializer(serializers.ModelSerializer):
    kpi_name = serializers.ReadOnlyField(source='kpi.name')
    financial_model_name = serializers.ReadOnlyField(source='financial_model.name')

    class Meta:
        model = KPICalculation
        fields = ['id', 'kpi', 'kpi_name', 'financial_model', 'financial_model_name', 'value', 'status', 'calculated_at']
        read_only_fields = ['calculated_at']


class ReportSerializer(serializers.ModelSerializer):
    financial_model_name = serializers.ReadOnlyField(source='financial_model.name')
    generated_by_name = serializers.ReadOnlyField(source='generated_by.get_full_name')

    class Meta:
        model = Report
        fields = ['id', 'title', 'report_type', 'financial_model', 'financial_model_name', 'content', 'summary', 'recommendations', 'export_format', 'file_path', 'generated_by', 'generated_by_name', 'is_public', 'version', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ConsolidationEntitySerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    entity_country = serializers.ReadOnlyField(source='entity.country')

    class Meta:
        model = ConsolidationEntity
        fields = ['id', 'consolidation', 'entity', 'entity_name', 'entity_country', 'ownership_percentage', 'acquisition_date', 'goodwill', 'pnl_data', 'balance_sheet_data', 'cashflow_data']


class IntercompanyEliminationEntrySerializer(serializers.ModelSerializer):
    transaction_reference = serializers.ReadOnlyField(source='transaction.reference_number')
    source_entity_name = serializers.ReadOnlyField(source='source_entity.name')
    destination_entity_name = serializers.ReadOnlyField(source='destination_entity.name')

    class Meta:
        model = IntercompanyEliminationEntry
        fields = [
            'id', 'consolidation', 'transaction', 'transaction_reference', 'elimination_type',
            'source_entity', 'source_entity_name', 'destination_entity', 'destination_entity_name',
            'amount', 'currency', 'adjustment_payload', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at']


class IntercompanyTransactionSerializer(serializers.ModelSerializer):
    source_entity_name = serializers.ReadOnlyField(source='source_entity.name')
    destination_entity_name = serializers.ReadOnlyField(source='destination_entity.name')
    source_invoice_number = serializers.ReadOnlyField(source='source_invoice.invoice_number')
    destination_bill_number = serializers.ReadOnlyField(source='destination_bill.bill_number')
    destination_loan_label = serializers.ReadOnlyField(source='destination_loan.lender_name')
    elimination_entries = IntercompanyEliminationEntrySerializer(many=True, read_only=True)

    class Meta:
        model = IntercompanyTransaction
        fields = [
            'id', 'organization', 'source_entity', 'source_entity_name', 'destination_entity', 'destination_entity_name',
            'transaction_type', 'reference_number', 'transaction_date', 'due_date', 'currency', 'amount',
            'transfer_pricing_markup_percent', 'status', 'description', 'notes',
            'source_invoice', 'source_invoice_number', 'destination_bill', 'destination_bill_number',
            'destination_loan', 'destination_loan_label', 'source_journal_entry', 'destination_journal_entry',
            'posted_at', 'created_by', 'created_at', 'updated_at', 'elimination_entries'
        ]
        read_only_fields = ['posted_at', 'created_at', 'updated_at', 'created_by']
        extra_kwargs = {
            'reference_number': {'required': False},
        }

    def validate(self, attrs):
        source_entity = attrs.get('source_entity') or getattr(self.instance, 'source_entity', None)
        destination_entity = attrs.get('destination_entity') or getattr(self.instance, 'destination_entity', None)
        organization = attrs.get('organization') or getattr(self.instance, 'organization', None)
        source_entity_id = getattr(source_entity, 'id', None)
        destination_entity_id = getattr(destination_entity, 'id', None)

        if source_entity and destination_entity and source_entity_id == destination_entity_id:
            raise serializers.ValidationError({'destination_entity': 'Source and destination entities must be different.'})

        if source_entity and destination_entity and source_entity.organization_id != destination_entity.organization_id:
            raise serializers.ValidationError({'destination_entity': 'Both entities must belong to the same organization.'})

        if organization and source_entity and organization.id != source_entity.organization_id:
            raise serializers.ValidationError({'organization': 'Organization must match the source entity organization.'})

        if organization and destination_entity and organization.id != destination_entity.organization_id:
            raise serializers.ValidationError({'organization': 'Organization must match the destination entity organization.'})

        return attrs


class ConsolidationSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    entities = ConsolidationEntitySerializer(source='entities.all', many=True, read_only=True)
    intercompany_eliminations = IntercompanyEliminationEntrySerializer(many=True, read_only=True)

    class Meta:
        model = Consolidation
        fields = ['id', 'name', 'organization', 'organization_name', 'status', 'consolidation_date', 'reporting_currency', 'include_minority_interest', 'eliminate_intercompany', 'consolidated_pnl', 'consolidated_balance_sheet', 'consolidated_cashflow', 'adjustments', 'total_assets', 'total_liabilities', 'shareholders_equity', 'entities', 'intercompany_eliminations', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaxCalculationSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')

    class Meta:
        model = TaxCalculation
        fields = ['id', 'entity', 'entity_name', 'tax_year', 'calculation_type', 'jurisdiction', 'regime_code', 'regime_name', 'period_start', 'period_end', 'calculation_json', 'liability_amount', 'status', 'taxable_income', 'tax_rate', 'deductions', 'credits', 'calculated_tax', 'effective_rate', 'breakdown', 'created_at']
        read_only_fields = ['created_at']


class TaxFilingSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    calculation_id = serializers.ReadOnlyField(source='calculation.id')

    class Meta:
        model = TaxFiling
        fields = ['id', 'entity', 'entity_name', 'tax_regime_code', 'period_start', 'period_end', 'form_type', 'form_json', 'calculation', 'calculation_id', 'submission_status', 'submitted_at', 'reference_number', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaxAuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.ReadOnlyField(source='user.get_full_name')
    entity_name = serializers.ReadOnlyField(source='entity.name')

    class Meta:
        model = TaxAuditLog
        fields = ['id', 'entity', 'entity_name', 'user', 'user_name', 'action_type', 'old_value_json', 'new_value_json', 'reason', 'country', 'device_metadata', 'timestamp', 'ip_address', 'previous_hash', 'event_hash']
        read_only_fields = ['timestamp']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')
        if request and should_mask_tax_audit(request.user, instance.entity.organization):
            data['old_value_json'] = mask_json_payload(data.get('old_value_json'))
            data['new_value_json'] = mask_json_payload(data.get('new_value_json'))
            data['device_metadata'] = {}
            data['ip_address'] = ''
        return data


class TaxRuleSetVersionSerializer(serializers.ModelSerializer):
    registry_name = serializers.ReadOnlyField(source='registry.regime_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')

    class Meta:
        model = TaxRuleSetVersion
        fields = ['id', 'registry', 'registry_name', 'version_number', 'effective_from', 'effective_to', 'change_log', 'approval_status', 'approved_by', 'approved_by_name', 'approved_at', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class TaxRiskAlertSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    resolved_by_name = serializers.ReadOnlyField(source='resolved_by.get_full_name')

    class Meta:
        model = TaxRiskAlert
        fields = ['id', 'entity', 'entity_name', 'alert_type', 'severity', 'title', 'details', 'source_model', 'source_id', 'detected_at', 'resolved_at', 'resolved_by', 'resolved_by_name']
        read_only_fields = ['detected_at']


# ============ Entity-Specific Serializers ============

class EntityDepartmentSerializer(serializers.ModelSerializer):
    head_name = serializers.ReadOnlyField(source='head_of_department.full_name')
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = EntityDepartment
        fields = ['id', 'entity', 'name', 'code', 'description', 'head_of_department', 'head_name', 'budget', 'currency', 'staff_count', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_staff_count(self, obj):
        return obj.staff.count()


class EntityRoleSerializer(serializers.ModelSerializer):
    department_name = serializers.ReadOnlyField(source='department.name')
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        source='permissions',
        many=True,
        write_only=True
    )
    staff_count = serializers.SerializerMethodField()

    class Meta:
        model = EntityRole
        fields = ['id', 'entity', 'name', 'code', 'department', 'department_name', 'description', 'salary_range_min', 'salary_range_max', 'currency', 'permissions', 'permission_ids', 'staff_count', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_staff_count(self, obj):
        return obj.staff.count()


class EntityStaffSerializer(serializers.ModelSerializer):
    user_email = serializers.ReadOnlyField(source='user.email')
    department_name = serializers.ReadOnlyField(source='department.name')
    role_name = serializers.ReadOnlyField(source='role.name')
    manager_name = serializers.ReadOnlyField(source='manager.full_name')
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = EntityStaff
        fields = ['id', 'entity', 'user', 'user_email', 'employee_id', 'first_name', 'last_name', 'full_name', 'email', 'phone', 'department', 'department_name', 'role', 'role_name', 'employment_type', 'status', 'hire_date', 'termination_date', 'salary', 'currency', 'manager', 'manager_name', 'address', 'emergency_contact', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class StaffPayrollProfileSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.ReadOnlyField(source='staff_member.full_name')

    class Meta:
        model = StaffPayrollProfile
        fields = [
            'id', 'staff_member', 'staff_member_name', 'entity', 'pay_frequency', 'salary_basis',
            'base_salary', 'standard_hours_per_period', 'income_tax_rate', 'employee_tax_rate',
            'employer_tax_rate', 'default_bank_account_name', 'default_bank_account_number',
            'default_bank_routing_number', 'default_bank_iban', 'default_bank_swift_code',
            'default_bank_sort_code', 'payment_reference', 'tax_identifier',
            'statutory_jurisdiction', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PayrollComponentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollComponent
        fields = [
            'id', 'entity', 'code', 'name', 'component_type', 'calculation_type', 'amount',
            'taxable', 'employer_contribution', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class StaffPayrollComponentAssignmentSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.ReadOnlyField(source='staff_member.full_name')
    component_name = serializers.ReadOnlyField(source='component.name')
    component_type = serializers.ReadOnlyField(source='component.component_type')

    class Meta:
        model = StaffPayrollComponentAssignment
        fields = [
            'id', 'staff_member', 'staff_member_name', 'component', 'component_name', 'component_type',
            'amount_override', 'is_active', 'effective_start', 'effective_end', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            'id', 'entity', 'code', 'name', 'accrual_hours_per_run', 'max_balance_hours',
            'carryover_limit_hours', 'is_paid_leave', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.ReadOnlyField(source='staff_member.full_name')
    leave_type_name = serializers.ReadOnlyField(source='leave_type.name')
    current_balance_hours = serializers.ReadOnlyField()

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'staff_member', 'staff_member_name', 'leave_type', 'leave_type_name',
            'opening_balance_hours', 'accrued_hours', 'used_hours', 'current_balance_hours',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'current_balance_hours']


class LeaveRequestSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.ReadOnlyField(source='staff_member.full_name')
    leave_type_name = serializers.ReadOnlyField(source='leave_type.name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'entity', 'staff_member', 'staff_member_name', 'leave_type', 'leave_type_name',
            'start_date', 'end_date', 'hours_requested', 'status', 'approved_by',
            'approved_by_name', 'approved_at', 'payroll_run', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['approved_by', 'approved_at', 'payroll_run', 'created_at', 'updated_at']


class PayrollBankOriginatorProfileSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')

    class Meta:
        model = PayrollBankOriginatorProfile
        fields = [
            'id', 'entity', 'entity_name', 'originator_name', 'originator_identifier', 'originating_bank_name',
            'debit_account_name', 'debit_account_number', 'debit_routing_number', 'debit_iban',
            'debit_swift_code', 'debit_sort_code', 'company_entry_description',
            'company_discretionary_data', 'initiating_party_name', 'initiating_party_identifier',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PayslipLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayslipLineItem
        fields = ['id', 'category', 'code', 'description', 'amount', 'taxable', 'metadata', 'created_at']
        read_only_fields = fields


class PayslipSerializer(serializers.ModelSerializer):
    staff_member_name = serializers.ReadOnlyField(source='staff_member.full_name')
    line_items = PayslipLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Payslip
        fields = [
            'id', 'payroll_run', 'staff_member', 'staff_member_name', 'payroll_profile', 'gross_pay',
            'employee_benefits_total', 'employer_benefits_total', 'deductions_total', 'taxable_pay',
            'tax_withholding', 'employer_tax', 'net_pay', 'leave_accrued_hours', 'leave_used_hours',
            'leave_balance_hours', 'bank_payment_reference', 'status', 'notes', 'line_items',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'line_items']


class PayrollStatutoryReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollStatutoryReport
        fields = ['id', 'payroll_run', 'report_type', 'jurisdiction', 'status', 'due_date', 'report_payload', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class PayrollBankPaymentFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayrollBankPaymentFile
        fields = ['id', 'payroll_run', 'file_format', 'file_name', 'content', 'status', 'generated_at', 'updated_at']
        read_only_fields = ['generated_at', 'updated_at']


class PayrollRunSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    organization_name = serializers.ReadOnlyField(source='organization.name')
    processed_by_name = serializers.ReadOnlyField(source='processed_by.get_full_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')
    payslips = PayslipSerializer(many=True, read_only=True)
    statutory_reports = PayrollStatutoryReportSerializer(many=True, read_only=True)
    bank_payment_file = PayrollBankPaymentFileSerializer(read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            'id', 'organization', 'organization_name', 'entity', 'entity_name', 'name', 'pay_frequency',
            'period_start', 'period_end', 'payment_date', 'status', 'approval_status', 'employee_count', 'gross_pay_total',
            'employee_benefits_total', 'employer_benefits_total', 'deductions_total',
            'tax_withholding_total', 'employer_tax_total', 'net_pay_total', 'statutory_summary',
            'requested_bank_file_format', 'requested_bank_institution', 'requested_bank_export_variant',
            'journal_entry', 'processed_by', 'processed_by_name', 'processed_at',
            'approved_by', 'approved_by_name', 'approval_submitted_at', 'approved_at', 'notes', 'payslips',
            'statutory_reports', 'bank_payment_file', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'employee_count', 'gross_pay_total', 'employee_benefits_total', 'employer_benefits_total',
            'deductions_total', 'tax_withholding_total', 'employer_tax_total', 'net_pay_total',
            'statutory_summary', 'journal_entry', 'processed_by', 'processed_at', 'approved_by',
            'approval_submitted_at', 'approved_at', 'created_at', 'updated_at',
        ]


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'entity', 'account_name', 'account_number', 'bank_name', 'account_type', 'currency', 'iban', 'swift_code', 'routing_number', 'balance', 'available_balance', 'is_active', 'last_synced', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ['id', 'entity', 'name', 'wallet_type', 'currency', 'balance', 'provider', 'account_id', 'is_active', 'last_synced', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ComplianceDocumentSerializer(serializers.ModelSerializer):
    responsible_user_name = serializers.ReadOnlyField(source='responsible_user.get_full_name')
    days_until_expiry = serializers.ReadOnlyField()
    is_expiring_soon = serializers.ReadOnlyField()

    class Meta:
        model = ComplianceDocument
        fields = ['id', 'entity', 'document_type', 'title', 'document_number', 'issuing_authority', 'issue_date', 'expiry_date', 'renewal_date', 'status', 'file_path', 'notes', 'reminder_days', 'responsible_user', 'responsible_user_name', 'days_until_expiry', 'is_expiring_soon', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============================================================================
# BOOKKEEPING SERIALIZERS
# ============================================================================

class BookkeepingCategorySerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = BookkeepingCategory
        fields = ['id', 'entity', 'name', 'type', 'description', 'is_default', 'transaction_count', 'total_amount', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_transaction_count(self, obj):
        return obj.transactions.count()
    
    def get_total_amount(self, obj):
        from django.db.models import Sum
        total = obj.transactions.aggregate(total=Sum('amount'))['total']
        return float(total) if total else 0.0


class BookkeepingAccountSerializer(serializers.ModelSerializer):
    transaction_count = serializers.SerializerMethodField()
    
    class Meta:
        model = BookkeepingAccount
        fields = ['id', 'entity', 'name', 'type', 'balance', 'currency', 'account_number', 'description', 'is_active', 'transaction_count', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']
    
    def get_transaction_count(self, obj):
        return obj.transactions.count()


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    staff_member_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Transaction
        fields = ['id', 'entity', 'type', 'category', 'category_name', 'account', 'account_name', 'amount', 'currency', 'payment_method', 'description', 'reference_number', 'date', 'attachment_url', 'staff_member', 'staff_member_name', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        """Basic duplicate-protection for transactions.

        Prevents creating an identical transaction for the same entity,
        account, amount and date with the same reference or description.
        """
        from .models import Transaction  # local import to avoid circulars

        entity = attrs.get('entity')
        account = attrs.get('account')
        amount = attrs.get('amount')
        date = attrs.get('date')
        description = (attrs.get('description') or '').strip()
        reference_number = (attrs.get('reference_number') or '').strip()

        if entity and account and amount is not None and date:
            qs = Transaction.objects.filter(
                entity=entity,
                account=account,
                amount=amount,
                date=date,
            )

            if reference_number:
                qs = qs.filter(reference_number__iexact=reference_number)
            elif description:
                qs = qs.filter(description__iexact=description)

            # When updating, ignore the current instance
            if self.instance is not None:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    'non_field_errors': [
                        'A similar transaction already exists for this account and date. Please confirm this is not a duplicate.'
                    ]
                })

        return attrs
    
    def get_staff_member_name(self, obj):
        return obj.staff_member.full_name if obj.staff_member else None
    
    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class BookkeepingAuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    
    class Meta:
        model = BookkeepingAuditLog
        fields = ['id', 'entity', 'action', 'user', 'user_name', 'old_value', 'new_value', 'timestamp', 'ip_address']
        read_only_fields = ['timestamp']
    
    def get_user_name(self, obj):
        return obj.user.get_full_name() if obj.user else 'System'


# ============================================================================
# WORKFLOW & TASK QUEUE SERIALIZERS
# ============================================================================

class RecurringTransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')
    account_name = serializers.ReadOnlyField(source='account.name')
    staff_member_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = RecurringTransaction
        fields = [
            'id', 'entity', 'account', 'account_name', 'category', 'category_name',
            'type', 'amount', 'currency', 'payment_method', 'description',
            'staff_member', 'staff_member_name', 'created_by', 'created_by_name',
            'frequency', 'next_run_date', 'end_date', 'max_occurrences',
            'occurrences_executed', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['occurrences_executed', 'created_at', 'updated_at']

    def get_staff_member_name(self, obj):
        return obj.staff_member.full_name if obj.staff_member else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class TaskRequestSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    entity_name = serializers.ReadOnlyField(source='entity.name')
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskRequest
        fields = [
            'id', 'organization', 'organization_name', 'entity', 'entity_name',
            'created_by', 'created_by_name', 'task_type', 'status', 'priority',
            'payload', 'result', 'error_message', 'created_at', 'started_at',
            'completed_at',
        ]
        read_only_fields = ['status', 'result', 'error_message', 'created_at', 'started_at', 'completed_at']

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None


class PlatformTaskSerializer(serializers.ModelSerializer):
    organization_name = serializers.ReadOnlyField(source='organization.name')
    entity_name = serializers.ReadOnlyField(source='entity.name')
    assigned_to_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    department_name = serializers.SerializerMethodField()
    department_owner_id = serializers.SerializerMethodField()
    cost_center = serializers.SerializerMethodField()
    state = serializers.CharField(source='status', required=False)
    type = serializers.CharField(source='task_type', required=False)

    class Meta:
        model = PlatformTask
        fields = [
            'id', 'organization', 'organization_name', 'entity', 'entity_name', 'workspace_id',
            'domain', 'task_type', 'type', 'title', 'description', 'status', 'state', 'priority',
            'assignee_type', 'assignee_id',
            'assigned_to', 'assigned_to_name', 'created_by', 'created_by_name',
            'department_name', 'department_owner_id', 'cost_center',
            'origin_type', 'origin_id', 'source_object_type', 'source_object_id', 'metadata', 'due_at',
            'started_at', 'completed_at', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_by_name', 'started_at', 'completed_at', 'created_at', 'updated_at']

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to else None

    def get_created_by_name(self, obj):
        return obj.created_by.get_full_name() if obj.created_by else None

    def get_department_name(self, obj):
        return (obj.metadata or {}).get('department_name', '')

    def get_department_owner_id(self, obj):
        return (obj.metadata or {}).get('department_owner_id', '')

    def get_cost_center(self, obj):
        return (obj.metadata or {}).get('cost_center', '')


# ============ COA & GL Serializers ============

class ChartOfAccountsSerializer(serializers.ModelSerializer):
    parent_account_name = serializers.ReadOnlyField(source='parent_account.account_name')

    class Meta:
        model = ChartOfAccounts
        fields = ['id', 'entity', 'account_code', 'account_name', 'account_type', 'parent_account', 'parent_account_name', 'currency', 'description', 'cost_center', 'status', 'opening_balance', 'current_balance', 'created_at', 'updated_at']
        read_only_fields = ['current_balance', 'created_at', 'updated_at']


class GeneralLedgerSerializer(serializers.ModelSerializer):
    debit_account_code = serializers.ReadOnlyField(source='debit_account.account_code')
    credit_account_code = serializers.ReadOnlyField(source='credit_account.account_code')

    class Meta:
        model = GeneralLedger
        fields = ['id', 'entity', 'debit_account', 'debit_account_code', 'credit_account', 'credit_account_code', 'debit_amount', 'credit_amount', 'description', 'reference_number', 'posting_date', 'journal_entry', 'posting_status', 'created_at']
        read_only_fields = ['created_at']


class JournalEntryApprovalStepSerializer(serializers.ModelSerializer):
    assigned_role_name = serializers.ReadOnlyField(source='assigned_role.name')
    assigned_staff_name = serializers.SerializerMethodField()
    acted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntryApprovalStep
        fields = [
            'id', 'step_order', 'stage', 'assigned_role', 'assigned_role_name',
            'assigned_staff', 'assigned_staff_name', 'status', 'acted_by',
            'acted_by_name', 'acted_at', 'comments', 'delegated_from',
        ]
        read_only_fields = fields

    def get_assigned_staff_name(self, obj):
        return obj.assigned_staff.full_name if obj.assigned_staff else None

    def get_acted_by_name(self, obj):
        return obj.acted_by.get_full_name() if obj.acted_by else None


class JournalEntryChangeLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntryChangeLog
        fields = ['id', 'action', 'stage', 'actor', 'actor_name', 'details', 'old_values', 'new_values', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor else 'System'


class AccountingApprovalStepSerializer(serializers.ModelSerializer):
    assigned_role_name = serializers.ReadOnlyField(source='assigned_role.name')
    assigned_staff_name = serializers.SerializerMethodField()
    acted_by_name = serializers.SerializerMethodField()

    class Meta:
        model = AccountingApprovalStep
        fields = [
            'id', 'step_order', 'stage', 'assigned_role', 'assigned_role_name',
            'assigned_staff', 'assigned_staff_name', 'status', 'acted_by',
            'acted_by_name', 'acted_at', 'comments', 'delegated_from',
        ]
        read_only_fields = fields

    def get_assigned_staff_name(self, obj):
        return obj.assigned_staff.full_name if obj.assigned_staff else None

    def get_acted_by_name(self, obj):
        return obj.acted_by.get_full_name() if obj.acted_by else None


class AccountingApprovalChangeLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = AccountingApprovalChangeLog
        fields = ['id', 'action', 'stage', 'actor', 'actor_name', 'details', 'old_values', 'new_values', 'created_at']
        read_only_fields = fields

    def get_actor_name(self, obj):
        return obj.actor.get_full_name() if obj.actor else 'System'


class AccountingApprovalMatrixSerializer(serializers.ModelSerializer):
    preparer_role_name = serializers.ReadOnlyField(source='preparer_role.name')
    reviewer_role_name = serializers.ReadOnlyField(source='reviewer_role.name')
    approver_role_name = serializers.ReadOnlyField(source='approver_role.name')

    class Meta:
        model = AccountingApprovalMatrix
        fields = [
            'id', 'entity', 'name', 'object_type', 'description', 'minimum_amount', 'maximum_amount',
            'preparer_role', 'preparer_role_name', 'reviewer_role', 'reviewer_role_name',
            'approver_role', 'approver_role_name', 'require_reviewer', 'require_approver',
            'allow_self_review', 'allow_self_approval', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        entity = attrs.get('entity') or getattr(self.instance, 'entity', None)
        object_type = attrs.get('object_type', getattr(self.instance, 'object_type', None))
        minimum_amount = attrs.get('minimum_amount', getattr(self.instance, 'minimum_amount', 0))
        maximum_amount = attrs.get('maximum_amount', getattr(self.instance, 'maximum_amount', None))

        for role_field in ['preparer_role', 'reviewer_role', 'approver_role']:
            role = attrs.get(role_field) or getattr(self.instance, role_field, None)
            if role and entity and role.entity_id != entity.id:
                raise serializers.ValidationError({role_field: 'Selected role must belong to the same entity.'})

        if maximum_amount is not None and maximum_amount < minimum_amount:
            raise serializers.ValidationError({'maximum_amount': 'Maximum amount must be greater than or equal to minimum amount.'})

        if entity and object_type:
            other_matrices = AccountingApprovalMatrix.objects.filter(entity=entity, object_type=object_type, is_active=True)
            if self.instance:
                other_matrices = other_matrices.exclude(id=self.instance.id)
            for other in other_matrices:
                other_minimum = other.minimum_amount or 0
                other_maximum = other.maximum_amount
                range_overlaps = (
                    (maximum_amount is None or other_minimum <= maximum_amount)
                    and (other_maximum is None or minimum_amount <= other_maximum)
                )
                if range_overlaps:
                    raise serializers.ValidationError({'minimum_amount': f'Active matrix "{other.name}" already covers an overlapping amount range for this object type.'})
        return attrs


class AccountingApprovalDelegationSerializer(serializers.ModelSerializer):
    delegator_name = serializers.ReadOnlyField(source='delegator.full_name')
    delegate_name = serializers.ReadOnlyField(source='delegate.full_name')

    class Meta:
        model = AccountingApprovalDelegation
        fields = [
            'id', 'entity', 'object_type', 'delegator', 'delegator_name', 'delegate', 'delegate_name',
            'stage', 'minimum_amount', 'maximum_amount', 'start_date', 'end_date', 'is_active',
            'notes', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        entity = attrs.get('entity') or getattr(self.instance, 'entity', None)
        delegator = attrs.get('delegator') or getattr(self.instance, 'delegator', None)
        delegate = attrs.get('delegate') or getattr(self.instance, 'delegate', None)
        if delegator and entity and delegator.entity_id != entity.id:
            raise serializers.ValidationError({'delegator': 'Delegator must belong to the same entity.'})
        if delegate and entity and delegate.entity_id != entity.id:
            raise serializers.ValidationError({'delegate': 'Delegate must belong to the same entity.'})
        if delegator and delegate and delegator.id == delegate.id:
            raise serializers.ValidationError({'delegate': 'Delegator and delegate must be different staff members.'})
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after the start date.'})
        minimum_amount = attrs.get('minimum_amount', getattr(self.instance, 'minimum_amount', 0))
        maximum_amount = attrs.get('maximum_amount', getattr(self.instance, 'maximum_amount', None))
        if maximum_amount is not None and maximum_amount < minimum_amount:
            raise serializers.ValidationError({'maximum_amount': 'Maximum amount must be greater than or equal to minimum amount.'})
        return attrs


class AccountingApprovalRecordSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()
    current_pending_stage = serializers.SerializerMethodField()
    steps = AccountingApprovalStepSerializer(many=True, read_only=True)
    change_logs = AccountingApprovalChangeLogSerializer(many=True, read_only=True)

    class Meta:
        model = AccountingApprovalRecord
        fields = [
            'id', 'entity', 'object_type', 'object_id', 'title', 'amount', 'status',
            'requested_by', 'requested_by_name', 'approved_by', 'approved_by_name',
            'submitted_at', 'approved_at', 'current_pending_stage', 'steps', 'change_logs',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_requested_by_name(self, obj):
        return obj.requested_by.get_full_name() if obj.requested_by else None

    def get_approved_by_name(self, obj):
        return obj.approved_by.get_full_name() if obj.approved_by else None

    def get_current_pending_stage(self, obj):
        step = obj.steps.filter(status='pending').order_by('step_order').first()
        return step.stage if step else None


class JournalApprovalMatrixSerializer(serializers.ModelSerializer):
    preparer_role_name = serializers.ReadOnlyField(source='preparer_role.name')
    reviewer_role_name = serializers.ReadOnlyField(source='reviewer_role.name')
    approver_role_name = serializers.ReadOnlyField(source='approver_role.name')

    class Meta:
        model = JournalApprovalMatrix
        fields = [
            'id', 'entity', 'name', 'description', 'entry_type', 'minimum_amount', 'maximum_amount',
            'preparer_role', 'preparer_role_name', 'reviewer_role', 'reviewer_role_name',
            'approver_role', 'approver_role_name', 'require_reviewer', 'require_approver',
            'allow_self_review', 'allow_self_approval', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate(self, attrs):
        entity = attrs.get('entity') or getattr(self.instance, 'entity', None)
        for role_field in ['preparer_role', 'reviewer_role', 'approver_role']:
            role = attrs.get(role_field) or getattr(self.instance, role_field, None)
            if role and entity and role.entity_id != entity.id:
                raise serializers.ValidationError({role_field: 'Selected role must belong to the same entity.'})

        minimum_amount = attrs.get('minimum_amount', getattr(self.instance, 'minimum_amount', 0))
        maximum_amount = attrs.get('maximum_amount', getattr(self.instance, 'maximum_amount', None))
        if maximum_amount is not None and maximum_amount < minimum_amount:
            raise serializers.ValidationError({'maximum_amount': 'Maximum amount must be greater than or equal to minimum amount.'})

        entry_type = attrs.get('entry_type', getattr(self.instance, 'entry_type', ''))
        if entity:
            other_matrices = JournalApprovalMatrix.objects.filter(entity=entity, is_active=True)
            if self.instance:
                other_matrices = other_matrices.exclude(id=self.instance.id)

            for other in other_matrices:
                type_overlap = (
                    not entry_type
                    or not other.entry_type
                    or other.entry_type == entry_type
                )
                if not type_overlap:
                    continue

                other_minimum = other.minimum_amount or 0
                other_maximum = other.maximum_amount
                range_overlaps = (
                    (maximum_amount is None or other_minimum <= maximum_amount)
                    and (other_maximum is None or minimum_amount <= other_maximum)
                )
                if range_overlaps:
                    raise serializers.ValidationError({
                        'minimum_amount': f'Active matrix "{other.name}" already covers an overlapping amount range for this entity and entry type.',
                    })
        return attrs


class JournalApprovalDelegationSerializer(serializers.ModelSerializer):
    delegator_name = serializers.ReadOnlyField(source='delegator.full_name')
    delegate_name = serializers.ReadOnlyField(source='delegate.full_name')

    class Meta:
        model = JournalApprovalDelegation
        fields = [
            'id', 'entity', 'delegator', 'delegator_name', 'delegate', 'delegate_name',
            'stage', 'minimum_amount', 'maximum_amount', 'start_date', 'end_date',
            'is_active', 'notes', 'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def validate(self, attrs):
        entity = attrs.get('entity') or getattr(self.instance, 'entity', None)
        delegator = attrs.get('delegator') or getattr(self.instance, 'delegator', None)
        delegate = attrs.get('delegate') or getattr(self.instance, 'delegate', None)
        if delegator and entity and delegator.entity_id != entity.id:
            raise serializers.ValidationError({'delegator': 'Delegator must belong to the same entity.'})
        if delegate and entity and delegate.entity_id != entity.id:
            raise serializers.ValidationError({'delegate': 'Delegate must belong to the same entity.'})
        if delegator and delegate and delegator.id == delegate.id:
            raise serializers.ValidationError({'delegate': 'Delegator and delegate must be different staff members.'})

        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': 'End date must be on or after the start date.'})

        minimum_amount = attrs.get('minimum_amount', getattr(self.instance, 'minimum_amount', 0))
        maximum_amount = attrs.get('maximum_amount', getattr(self.instance, 'maximum_amount', None))
        if maximum_amount is not None and maximum_amount < minimum_amount:
            raise serializers.ValidationError({'maximum_amount': 'Maximum amount must be greater than or equal to minimum amount.'})
        return attrs


class JournalEntrySerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')
    approval_steps = JournalEntryApprovalStepSerializer(many=True, read_only=True)
    change_logs = JournalEntryChangeLogSerializer(many=True, read_only=True)
    current_pending_stage = serializers.SerializerMethodField()
    approval_state = serializers.SerializerMethodField()

    class Meta:
        model = JournalEntry
        fields = [
            'id', 'entity', 'entry_type', 'reference_number', 'description', 'posting_date', 'memo',
            'amount_total', 'status', 'created_by', 'created_by_name', 'approved_by', 'approved_by_name',
            'approved_at', 'submitted_at', 'is_recurring', 'recurring_template', 'reversing_entry',
            'original_entry', 'approval_steps', 'change_logs', 'current_pending_stage', 'approval_state',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'approved_at', 'submitted_at']

    def get_current_pending_stage(self, obj):
        step = obj.approval_steps.filter(status='pending').order_by('step_order').first()
        return step.stage if step else None

    def get_approval_state(self, obj):
        steps = list(obj.approval_steps.all())
        return {
            'total_steps': len(steps),
            'completed_steps': len([step for step in steps if step.status == 'approved']),
            'rejected_steps': len([step for step in steps if step.status == 'rejected']),
            'current_stage': self.get_current_pending_stage(obj),
        }


class RecurringJournalTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')

    class Meta:
        model = RecurringJournalTemplate
        fields = ['id', 'entity', 'name', 'description', 'frequency', 'next_posting_date', 'end_date', 'is_active', 'journal_lines', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LedgerPeriodSerializer(serializers.ModelSerializer):
    closed_by_name = serializers.ReadOnlyField(source='closed_by.get_full_name')

    class Meta:
        model = LedgerPeriod
        fields = ['id', 'entity', 'period_name', 'start_date', 'end_date', 'status', 'no_posting_after', 'created_at', 'closed_at', 'closed_by', 'closed_by_name']
        read_only_fields = ['created_at', 'closed_at']


# ============ AR Serializers ============

class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ['id', 'entity', 'customer_code', 'customer_name', 'email', 'phone', 'address', 'city', 'country', 'postal_code', 'contact_person', 'tax_id', 'payment_terms', 'currency', 'credit_limit', 'status', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceLineItem
        fields = ['id', 'invoice', 'description', 'quantity', 'unit_price', 'tax_rate', 'line_amount']


class InvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.customer_name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = ['id', 'entity', 'customer', 'customer_name', 'invoice_number', 'invoice_date', 'due_date', 'subtotal', 'tax_amount', 'total_amount', 'paid_amount', 'outstanding_amount', 'currency', 'status', 'description', 'notes', 'created_by', 'created_by_name', 'line_items', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'outstanding_amount']


class CreditNoteSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.customer_name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')

    class Meta:
        model = CreditNote
        fields = ['id', 'entity', 'invoice', 'customer', 'customer_name', 'credit_note_number', 'credit_date', 'reason', 'total_amount', 'currency', 'status', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_at']


class PaymentSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.customer_name')
    invoice_number = serializers.ReadOnlyField(source='invoice.invoice_number')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')

    class Meta:
        model = Payment
        fields = ['id', 'entity', 'invoice', 'invoice_number', 'customer', 'customer_name', 'payment_date', 'amount', 'payment_method', 'reference_number', 'approval_status', 'approval_submitted_at', 'created_by', 'created_by_name', 'approved_by', 'approved_by_name', 'approved_at', 'created_at']
        read_only_fields = ['created_at']


# ============ AP Serializers ============

class VendorSerializer(serializers.ModelSerializer):
    vendor_code = serializers.CharField(read_only=True)

    class Meta:
        model = Vendor
        fields = ['id', 'entity', 'vendor_code', 'vendor_name', 'email', 'phone', 'address', 'city', 'country', 'postal_code', 'contact_person', 'tax_id', 'website', 'service_description', 'payment_terms', 'currency', 'status', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class PurchaseOrderSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.vendor_name')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')

    class Meta:
        model = PurchaseOrder
        fields = ['id', 'entity', 'vendor', 'vendor_name', 'po_number', 'po_date', 'expected_delivery_date', 'subtotal', 'tax_amount', 'total_amount', 'currency', 'status', 'approval_status', 'approval_submitted_at', 'created_by', 'created_by_name', 'approved_by', 'approved_by_name', 'approved_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class BillSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.vendor_name')
    po_number = serializers.ReadOnlyField(source='purchase_order.po_number')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')

    class Meta:
        model = Bill
        fields = ['id', 'entity', 'vendor', 'vendor_name', 'purchase_order', 'po_number', 'bill_number', 'bill_date', 'due_date', 'subtotal', 'tax_amount', 'total_amount', 'paid_amount', 'outstanding_amount', 'currency', 'status', 'approval_status', 'approval_submitted_at', 'description', 'notes', 'created_by', 'created_by_name', 'approved_by', 'approved_by_name', 'approved_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'outstanding_amount']


class BillPaymentSerializer(serializers.ModelSerializer):
    vendor_name = serializers.ReadOnlyField(source='vendor.vendor_name')
    bill_number = serializers.ReadOnlyField(source='bill.bill_number')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')
    approved_by_name = serializers.ReadOnlyField(source='approved_by.get_full_name')

    class Meta:
        model = BillPayment
        fields = ['id', 'entity', 'bill', 'bill_number', 'vendor', 'vendor_name', 'payment_date', 'amount', 'payment_method', 'reference_number', 'approval_status', 'approval_submitted_at', 'created_by', 'created_by_name', 'approved_by', 'approved_by_name', 'approved_at', 'created_at']
        read_only_fields = ['created_at']


# ============ Inventory Serializers ============

class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ['id', 'entity', 'sku', 'item_name', 'item_code', 'description', 'category', 'unit_of_measure', 'quantity_on_hand', 'reorder_level', 'reorder_quantity', 'unit_cost', 'valuation_method', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class InventoryTransactionSerializer(serializers.ModelSerializer):
    inventory_item_sku = serializers.ReadOnlyField(source='inventory_item.sku')
    created_by_name = serializers.ReadOnlyField(source='created_by.get_full_name')

    class Meta:
        model = InventoryTransaction
        fields = ['id', 'entity', 'inventory_item', 'inventory_item_sku', 'transaction_type', 'transaction_date', 'quantity_before', 'quantity', 'quantity_after', 'unit_cost', 'total_cost', 'reference_number', 'notes', 'created_by', 'created_by_name', 'created_at']
        read_only_fields = ['created_at', 'quantity_before', 'quantity_after', 'unit_cost', 'total_cost']


class InventoryCostOfGoodsSoldSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryCostOfGoodsSold
        fields = ['id', 'entity', 'period_start', 'period_end', 'opening_inventory', 'purchases', 'closing_inventory', 'cogs', 'created_at']
        read_only_fields = ['created_at', 'cogs']


# ============ Reconciliation Serializers ============

class BankReconciliationSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.ReadOnlyField(source='bank_account.account_name')
    reconciled_by_name = serializers.ReadOnlyField(source='reconciled_by.get_full_name')

    class Meta:
        model = BankReconciliation
        fields = ['id', 'entity', 'bank_account', 'bank_account_name', 'reconciliation_date', 'bank_statement_balance', 'book_balance', 'status', 'variance', 'notes', 'reconciled_by', 'reconciled_by_name', 'reconciled_at', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'variance']


# ============ Revenue Recognition Serializers ============

class RevenueRecognitionScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueRecognitionSchedule
        fields = ['id', 'deferred_revenue', 'recognition_period_start', 'recognition_period_end', 'recognition_date', 'amount_to_recognize', 'is_recognized', 'recognized_date']


class DeferredRevenueSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.customer_name')
    recognition_schedule = RevenueRecognitionScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = DeferredRevenue
        fields = ['id', 'entity', 'customer', 'customer_name', 'contract_number', 'contract_start_date', 'contract_end_date', 'total_amount', 'currency', 'recognized_amount', 'remaining_amount', 'status', 'description', 'recognition_schedule', 'created_at']
        read_only_fields = ['created_at', 'recognized_amount', 'remaining_amount']


# ============ Period Close Serializers ============

class PeriodCloseItemSerializer(serializers.ModelSerializer):
    responsible_user_name = serializers.ReadOnlyField(source='responsible_user.get_full_name')

    class Meta:
        model = PeriodCloseItem
        fields = ['id', 'checklist', 'task_name', 'description', 'sequence', 'status', 'responsible_user', 'responsible_user_name', 'completed_at']


class PeriodCloseChecklistSerializer(serializers.ModelSerializer):
    items = PeriodCloseItemSerializer(many=True, read_only=True)

    class Meta:
        model = PeriodCloseChecklist
        fields = ['id', 'entity', 'period', 'status', 'created_at', 'started_at', 'completed_at', 'items']
        read_only_fields = ['created_at']


# ============ FX Serializers ============

class ExchangeRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeRate
        fields = ['id', 'from_currency', 'to_currency', 'rate', 'rate_date', 'source', 'created_at']
        read_only_fields = ['created_at']


class FXGainLossSerializer(serializers.ModelSerializer):
    transaction_reference = serializers.ReadOnlyField(source='transaction.description')

    class Meta:
        model = FXGainLoss
        fields = ['id', 'entity', 'transaction', 'transaction_reference', 'from_currency', 'to_currency', 'original_amount', 'original_rate', 'original_value', 'current_rate', 'current_value', 'gain_loss_amount', 'gain_type', 'transaction_date', 'created_at']
        read_only_fields = ['created_at']


# ============ Notification Serializers ============

class NotificationSerializer(serializers.ModelSerializer):
    related_entity_name = serializers.ReadOnlyField(source='related_entity.name')

    class Meta:
        model = Notification
        fields = ['id', 'user', 'organization', 'notification_type', 'priority', 'status', 'title', 'message', 'related_entity', 'related_entity_name', 'related_content_type', 'related_object_id', 'action_url', 'read_at', 'sent_at']
        read_only_fields = ['sent_at']


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'user', 'email_budget_alerts', 'email_deadline_reminders', 'email_payment_due', 'email_approval_requests', 'sms_budget_alerts', 'sms_deadline_reminders', 'sms_payment_due', 'in_app_all', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ CLIENT MANAGEMENT SERIALIZERS ============

class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ['id', 'organization', 'name', 'email', 'phone', 'address', 'country', 'industry', 'registration_number', 'tax_id', 'contact_person', 'contact_email', 'contact_phone', 'website', 'status', 'assigned_accountant', 'monthly_fee', 'currency', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientPortalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientPortal
        fields = ['id', 'client', 'user', 'portal_slug', 'is_active', 'last_login', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientMessage
        fields = ['id', 'client', 'from_user', 'to_user', 'message_type', 'subject', 'content', 'is_read', 'read_at', 'is_urgent', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'read_at']


class ClientDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientDocument
        fields = ['id', 'client', 'organization', 'document_type', 'name', 'description', 'file_url', 'file_size', 'status', 'uploaded_by', 'reviewed_by', 'review_notes', 'tags', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'file_size']


class DocumentRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentRequest
        fields = ['id', 'client', 'organization', 'requested_by', 'document_type', 'description', 'status', 'due_date', 'reminder_sent', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ApprovalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRequest
        fields = ['id', 'client', 'organization', 'request_type', 'request_data', 'status', 'requested_by', 'approved_by', 'rejection_reason', 'due_date', 'email_sent', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ DOCUMENT MANAGEMENT SERIALIZERS ============

class DocumentTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentTemplate
        fields = ['id', 'organization', 'name', 'description', 'template_content', 'category', 'is_active', 'created_by', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ LOAN MANAGEMENT SERIALIZERS ============

class LoanPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LoanPayment
        fields = ['id', 'loan', 'payment_number', 'payment_date', 'principal_paid', 'interest_paid', 'total_paid', 'principal_remaining', 'status', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LoanSerializer(serializers.ModelSerializer):
    payments = LoanPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Loan
        fields = ['id', 'entity', 'organization', 'lender_name', 'loan_type', 'loan_amount', 'currency', 'interest_rate', 'start_date', 'maturity_date', 'status', 'principal_remaining', 'monthly_payment', 'payments', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ COMPLIANCE & KYC/AML SERIALIZERS ============

class KYCProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYCProfile
        fields = ['id', 'entity', 'client', 'organization', 'status', 'beneficial_owners', 'verification_date', 'verified_by', 'expiry_date', 'id_document_url', 'proof_of_address_url', 'business_registration_url', 'rejection_reason', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class AMLTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMLTransaction
        fields = ['id', 'entity', 'transaction', 'organization', 'amount', 'currency', 'transaction_date', 'transaction_type', 'risk_level', 'status', 'reason', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ BILLING & FIRM MANAGEMENT SERIALIZERS ============

class FirmServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirmService
        fields = ['id', 'organization', 'name', 'description', 'price', 'currency', 'billing_frequency', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientInvoiceLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientInvoiceLineItem
        fields = ['id', 'invoice', 'service', 'description', 'quantity', 'unit_price', 'total_price']


class ClientInvoiceSerializer(serializers.ModelSerializer):
    line_items = ClientInvoiceLineItemSerializer(many=True, read_only=True)

    class Meta:
        model = ClientInvoice
        fields = ['id', 'organization', 'client', 'invoice_number', 'currency', 'issue_date', 'due_date', 'subtotal', 'tax_amount', 'total_amount', 'status', 'payment_received', 'payment_date', 'description', 'notes', 'sent_at', 'viewed_at', 'created_by', 'line_items', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ClientSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientSubscription
        fields = ['id', 'organization', 'client', 'service', 'status', 'start_date', 'end_date', 'next_billing_date', 'auto_renew', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ WHITE-LABELING SERIALIZERS ============

class WhiteLabelBrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhiteLabelBranding
        fields = ['id', 'organization', 'primary_color', 'secondary_color', 'accent_color', 'logo_url', 'logo_light_url', 'logo_dark_url', 'favicon_url', 'custom_domain', 'portal_name', 'portal_description', 'support_email', 'support_phone', 'font_family', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


# ============ EMBEDDED BANKING & PAYMENTS SERIALIZERS ============

class BankingIntegrationSerializer(serializers.ModelSerializer):
    entity_name = serializers.ReadOnlyField(source='entity.name')
    has_access_token = serializers.ReadOnlyField()
    masked_api_key = serializers.SerializerMethodField()
    api_key = serializers.CharField(write_only=True, required=False, allow_blank=True)
    api_secret = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = BankingIntegration
        fields = [
            'id', 'organization', 'entity', 'entity_name', 'integration_type', 'provider_code', 'provider_name',
            'status', 'is_active', 'webhook_url', 'last_sync', 'last_webhook_at', 'consent_reference',
            'consent_scopes', 'consent_granted_at', 'token_expires_at', 'token_last_rotated_at', 'failure_count',
            'has_access_token', 'masked_api_key', 'api_key', 'api_secret', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'last_webhook_at', 'consent_reference', 'consent_scopes',
            'consent_granted_at', 'token_expires_at', 'token_last_rotated_at', 'failure_count',
            'has_access_token', 'masked_api_key'
        ]

    def get_masked_api_key(self, obj):
        return mask_secret(obj.get_api_key())

    def create(self, validated_data):
        api_key = validated_data.pop('api_key', '')
        api_secret = validated_data.pop('api_secret', '')
        instance = super().create(validated_data)
        if api_key:
            instance.set_api_key(api_key)
        if api_secret:
            instance.set_api_secret(api_secret)
        if api_key or api_secret:
            instance.save(update_fields=['api_key', 'api_secret', 'updated_at'])
        return instance

    def update(self, instance, validated_data):
        api_key = validated_data.pop('api_key', None)
        api_secret = validated_data.pop('api_secret', None)
        instance = super().update(instance, validated_data)
        updated_fields = []
        if api_key is not None:
            instance.set_api_key(api_key)
            updated_fields.append('api_key')
        if api_secret is not None:
            instance.set_api_secret(api_secret)
            updated_fields.append('api_secret')
        if updated_fields:
            updated_fields.append('updated_at')
            instance.save(update_fields=updated_fields)
        return instance


class BankingTransactionSerializer(serializers.ModelSerializer):
    bank_account_name = serializers.ReadOnlyField(source='bank_account.account_name')

    class Meta:
        model = BankingTransaction
        fields = [
            'id', 'entity', 'integration', 'bank_account', 'bank_account_name', 'transaction_id', 'transaction_date',
            'amount', 'currency', 'description', 'merchant_name', 'raw_category', 'normalized_category',
            'dashboard_bucket', 'categorization_source', 'categorization_confidence', 'counterparty_name',
            'counterparty_account', 'transaction_type', 'status', 'is_matched', 'matched_transaction',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class EmbeddedPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmbeddedPayment
        fields = ['id', 'organization', 'client', 'invoice', 'amount', 'currency', 'payment_method', 'status', 'payment_link', 'payment_ref', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'payment_ref']


# ============ WORKFLOW AUTOMATION SERIALIZERS ============

class AutomationArtifactSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = AutomationArtifact
        fields = ['id', 'workflow', 'execution', 'organization', 'entity', 'artifact_type', 'export_format', 'file_name', 'metadata', 'download_url', 'created_at']
        read_only_fields = fields

    def get_download_url(self, obj):
        request = self.context.get('request')
        relative_url = f'/api/automation-artifacts/{obj.id}/download/'
        return request.build_absolute_uri(relative_url) if request else relative_url

class AutomationExecutionSerializer(serializers.ModelSerializer):
    artifacts = AutomationArtifactSerializer(many=True, read_only=True)

    class Meta:
        model = AutomationExecution
        fields = ['id', 'workflow', 'status', 'triggered_at', 'started_at', 'completed_at', 'execution_result', 'error_message', 'artifacts']
        read_only_fields = ['triggered_at', 'started_at', 'completed_at']


class AutomationWorkflowSerializer(serializers.ModelSerializer):
    executions = AutomationExecutionSerializer(many=True, read_only=True)

    class Meta:
        model = AutomationWorkflow
        fields = ['id', 'organization', 'entity', 'name', 'description', 'trigger_type', 'trigger_config', 'actions', 'is_active', 'created_by', 'created_at', 'updated_at', 'executions']
        read_only_fields = ['created_by', 'created_at', 'updated_at']


# ============ FIRM DASHBOARD & BUSINESS INTELLIGENCE SERIALIZERS ============

class FirmMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirmMetric
        fields = ['id', 'organization', 'metric_name', 'metric_key', 'value', 'value_type', 'period', 'period_date', 'previous_value', 'change_percentage', 'created_at']
        read_only_fields = ['created_at']


class ClientMarketplaceIntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientMarketplaceIntegration
        fields = ['id', 'organization', 'client', 'name', 'category', 'provider', 'description', 'icon_url', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at', 'api_key']


class DeveloperModuleInstallationSerializer(serializers.ModelSerializer):
    installed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = DeveloperModuleInstallation
        fields = [
            'id', 'organization', 'module_key', 'module_name', 'category', 'version', 'required_tier',
            'status', 'configuration', 'installed_by', 'installed_by_name', 'installed_at', 'updated_at',
        ]
        read_only_fields = ['installed_by', 'installed_at', 'updated_at']

    def get_installed_by_name(self, obj):
        return obj.installed_by.get_full_name() if obj.installed_by else ''
