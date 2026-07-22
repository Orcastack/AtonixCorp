import secrets
import uuid
import re
from decimal import Decimal

from django.db import models
from django.db import transaction
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from django.core.validators import URLValidator
from django.db.models.functions import Lower
from django.utils import timezone

from .company_identity import normalize_registration_number

# Role constants
ROLE_ORG_OWNER = 'ORG_OWNER'
ROLE_CFO = 'CFO'
ROLE_FINANCE_ANALYST = 'FINANCE_ANALYST'
ROLE_VIEWER = 'VIEWER'
ROLE_EXTERNAL_ADVISOR = 'EXTERNAL_ADVISOR'
ROLE_COMPLIANCE_OFFICER = 'COMPLIANCE_OFFICER'
ROLE_FOUNDER = 'FOUNDER'
ROLE_CEO = 'CEO'
ROLE_CTO = 'CTO'
ROLE_CSO = 'CSO'
ROLE_BOARD = 'BOARD'
ROLE_DEPARTMENT_HEAD = 'DEPARTMENT_HEAD'
ROLE_UNIT_MEMBER = 'UNIT_MEMBER'

ROLE_CHOICES = [
    (ROLE_ORG_OWNER, 'Organization Owner'),
    (ROLE_CFO, 'Chief Financial Officer'),
    (ROLE_FINANCE_ANALYST, 'Finance Analyst'),
    (ROLE_VIEWER, 'Viewer'),
    (ROLE_EXTERNAL_ADVISOR, 'External Advisor'),
    (ROLE_COMPLIANCE_OFFICER, 'Compliance Officer'),
    (ROLE_FOUNDER, 'Founder'),
    (ROLE_CEO, 'Chief Executive Officer'),
    (ROLE_CTO, 'Chief Technology Officer'),
    (ROLE_CSO, 'Chief Security Officer'),
    (ROLE_BOARD, 'Board Member'),
    (ROLE_DEPARTMENT_HEAD, 'Department Head'),
    (ROLE_UNIT_MEMBER, 'Unit Member'),
]

# Account type constants
ACCOUNT_TYPE_PERSONAL = 'personal'
ACCOUNT_TYPE_ENTERPRISE = 'enterprise'

ACCOUNT_TYPE_CHOICES = [
    (ACCOUNT_TYPE_PERSONAL, 'Personal'),
    (ACCOUNT_TYPE_ENTERPRISE, 'Enterprise'),
]


class IdentityCodeSequence(models.Model):
    """Per-year sequence backing immutable public identity codes."""

    code_type = models.CharField(max_length=3)
    year = models.PositiveIntegerField()
    last_value = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['code_type', 'year'], name='unique_identity_code_sequence'),
        ]


def generate_identity_code(code_type):
    """Generate a monotonic public code such as USR-2026-0001."""
    year = timezone.now().year
    with transaction.atomic():
        sequence, _ = IdentityCodeSequence.objects.select_for_update().get_or_create(
            code_type=code_type,
            year=year,
        )
        sequence.last_value += 1
        sequence.save(update_fields=['last_value'])
        return f'{code_type}-{year}-{sequence.last_value:03d}'


def generate_user_identity_code(first_name, last_name):
    """Create an immutable human-readable user ID from names and registration date."""
    date_value = timezone.localdate()
    initials = re.sub(r'[^A-Z0-9]', '', f'{first_name[:3]}{last_name[:3]}'.upper())
    initials = (initials or 'USR')[:6]
    with transaction.atomic():
        sequence, _ = IdentityCodeSequence.objects.select_for_update().get_or_create(
            code_type='UID',
            year=date_value.year,
        )
        sequence.last_value += 1
        sequence.save(update_fields=['last_value'])
        return f'{initials}-{date_value:%d%m%y}-{date_value.year}-{sequence.last_value:03d}'


class UserProfile(models.Model):
    """Extended user profile with account type and preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    secure_user_id = models.CharField(max_length=10, unique=True, editable=False, db_index=True, blank=True)
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default=ACCOUNT_TYPE_ENTERPRISE
    )
    country = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    identity_code = models.CharField(max_length=20, unique=True, editable=False, db_index=True, blank=True)
    public_user_id = models.CharField(max_length=40, unique=True, editable=False, db_index=True, blank=True)
    PLATFORM_ROLE_SUPER_USER = 'super_user'
    PLATFORM_ROLE_ADMIN = 'admin'
    PLATFORM_ROLE_MEMBER = 'member'
    PLATFORM_ROLE_EMPLOYEE = 'employee'
    PLATFORM_ROLE_CHOICES = [
        (PLATFORM_ROLE_SUPER_USER, 'Super User'),
        (PLATFORM_ROLE_ADMIN, 'Admin'),
        (PLATFORM_ROLE_MEMBER, 'Member'),
        (PLATFORM_ROLE_EMPLOYEE, 'Employee'),
    ]
    platform_role = models.CharField(max_length=20, choices=PLATFORM_ROLE_CHOICES, default=PLATFORM_ROLE_MEMBER)

    TAX_TYPE_CORPORATE = 'corporate'
    TAX_TYPE_PERSONAL = 'personal'
    TAX_TYPE_VAT = 'vat'
    TAX_TYPE_CHOICES = [
        (TAX_TYPE_CORPORATE, 'Corporate Tax'),
        (TAX_TYPE_PERSONAL, 'Personal Income Tax'),
        (TAX_TYPE_VAT, 'VAT/Sales Tax'),
    ]

    tax_type = models.CharField(max_length=20, choices=TAX_TYPE_CHOICES, default=TAX_TYPE_CORPORATE)
    tax_rate = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    avatar_color = models.CharField(max_length=7, default='#667eea')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @staticmethod
    def generate_secure_user_id():
        while True:
            candidate = str(secrets.randbelow(9_000_000_000) + 1_000_000_000)
            if not UserProfile.objects.filter(secure_user_id=candidate).exists():
                return candidate

    def save(self, *args, **kwargs):
        if self.pk:
            stored_codes = UserProfile.objects.filter(pk=self.pk).values('identity_code', 'public_user_id').first()
            if stored_codes:
                self.identity_code = stored_codes['identity_code']
                self.public_user_id = stored_codes['public_user_id']
        if not self.secure_user_id:
            self.secure_user_id = self.generate_secure_user_id()
        if not self.identity_code:
            self.identity_code = generate_identity_code('USR')
        if not self.public_user_id:
            self.public_user_id = generate_user_identity_code(self.user.first_name, self.user.last_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.email} ({self.get_account_type_display()})"


class EmailVerificationToken(models.Model):
    """Single-use, hashed email-verification token; plaintext is never persisted."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verification_tokens')
    token_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'expires_at'], name='finances_em_user_id_4eb519_idx')]


class IdentityVerification(models.Model):
    """User-provided ID and selfie evidence submitted after email verification."""

    STATUS_PENDING = 'pending'
    STATUS_SUBMITTED = 'submitted'
    STATUS_VERIFIED = 'verified'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_VERIFIED, 'Verified'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='identity_verification')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    id_document = models.FileField(upload_to='identity_verification/id_documents/', blank=True)
    selfie = models.FileField(upload_to='identity_verification/selfies/', blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Organization(models.Model):
    """Organization model for enterprise accounts"""
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_organizations')
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=64, unique=True, null=True, blank=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    logo_url = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    employee_count = models.IntegerField(default=1)
    primary_currency = models.CharField(max_length=3, default='USD')
    primary_country = models.CharField(max_length=100)
    enterprise_code = models.CharField(max_length=20, unique=True, editable=False, db_index=True, blank=True)
    enterprise_username = models.CharField(max_length=150, unique=True, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('owner', 'slug')
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(Lower('name'), name='unique_organization_name_case_insensitive'),
        ]

    def save(self, *args, **kwargs):
        if self.registration_number:
            self.registration_number = normalize_registration_number(self.registration_number)
        if self.pk:
            stored_code = Organization.objects.filter(pk=self.pk).values_list('enterprise_code', flat=True).first()
            if stored_code:
                self.enterprise_code = stored_code
        if not self.enterprise_code:
            self.enterprise_code = generate_identity_code('ENT')
        if not self.enterprise_username:
            base_username = re.sub(r'[^a-z0-9]', '', self.name.lower())[:140] or 'enterprise'
            candidate = f'{base_username}{timezone.now():%Y}'
            suffix = 1
            while Organization.objects.exclude(pk=self.pk).filter(enterprise_username__iexact=candidate).exists():
                suffix += 1
                candidate = f'{base_username}{suffix:03d}'
            self.enterprise_username = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class EnterpriseInvitationSequence(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='invitation_sequence')
    last_value = models.PositiveIntegerField(default=0)


class GovernanceConfiguration(models.Model):
    """Current portable governance configuration for an organization."""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        related_name='governance_configuration',
    )
    schema_version = models.CharField(max_length=20, default='v1')
    revision = models.PositiveIntegerField(default=0)
    configuration_file = models.FileField(upload_to='governance_configurations/')
    checksum = models.CharField(max_length=64, blank=True)
    generated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.organization.name} governance configuration ({self.schema_version})'


class GovernanceCloudExport(models.Model):
    """Audit record for a portable governance YAML delivery; credentials are never stored."""

    PROVIDER_CHOICES = [
        ('google_drive', 'Google Drive'),
        ('onedrive', 'Microsoft OneDrive'),
        ('aws_s3', 'AWS S3'),
        ('local_download', 'Local Download'),
    ]
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='governance_cloud_exports')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='governance_cloud_exports')
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    file_name = models.CharField(max_length=255)
    checksum = models.CharField(max_length=64)
    destination = models.CharField(max_length=500, blank=True)
    remote_reference = models.CharField(max_length=500, blank=True)
    overwrite_confirmed = models.BooleanField(default=False)
    error_message = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.organization.name} {self.provider} export ({self.status})'


class OrganizationEmailSubscription(models.Model):
    """Organization-level entitlement for AtonixCorp managed outbound email."""

    TIER_CHOICES = [
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('cancelled', 'Cancelled'),
    ]

    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='email_subscription')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='basic')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    billing_reference = models.CharField(max_length=120, blank=True)
    monthly_send_limit = models.PositiveIntegerField(default=250)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['organization__name']

    def __str__(self):
        return f'{self.organization.name} email subscription ({self.tier})'


class OrganizationEmailAccount(models.Model):
    """A provisioned sender identity; inbound mailbox hosting remains provider infrastructure."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='email_accounts')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='organization_email_accounts')
    local_part = models.CharField(max_length=64)
    address = models.EmailField(unique=True)
    display_name = models.CharField(max_length=160, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['address']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'local_part'], name='unique_organization_email_local_part'),
        ]

    def __str__(self):
        return self.address


class OrganizationEmailCampaign(models.Model):
    """Outbound governance, operational, or opted-in marketing email batch."""

    TYPE_CHOICES = [
        ('governance', 'Governance Notice'),
        ('operational', 'Operational Notice'),
        ('marketing', 'Marketing Campaign'),
    ]
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='email_campaigns')
    sender = models.ForeignKey(OrganizationEmailAccount, on_delete=models.PROTECT, related_name='campaigns')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='email_campaigns_created')
    campaign_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    subject = models.CharField(max_length=255)
    html_body = models.TextField()
    recipients = models.JSONField(default=list)
    consent_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.organization.name}: {self.subject}'


class OrganizationEmailDelivery(models.Model):
    """Immutable delivery audit record. Message bodies and SMTP credentials are never stored."""

    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('suppressed', 'Suppressed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='email_deliveries')
    campaign = models.ForeignKey(OrganizationEmailCampaign, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    sender = models.ForeignKey(OrganizationEmailAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='deliveries')
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    event_type = models.CharField(max_length=50, default='campaign')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    provider_message_id = models.CharField(max_length=255, blank=True)
    error_message = models.CharField(max_length=500, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'created_at']),
            models.Index(fields=['campaign', 'status']),
        ]

    def __str__(self):
        return f'{self.event_type} to {self.recipient} ({self.status})'


class OrganizationDirectoryEntry(models.Model):
    """LDAP-compatible directory projection for organization-scoped identities."""

    NODE_TYPE_CHOICES = [
        ('organization', 'Organization'),
        ('office', 'Office'),
        ('department', 'Department'),
        ('unit', 'Unit'),
        ('user', 'User'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='directory_entries')
    entity = models.ForeignKey('Entity', on_delete=models.CASCADE, null=True, blank=True, related_name='directory_entries')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='organization_directory_entries')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    node_type = models.CharField(max_length=20, choices=NODE_TYPE_CHOICES)
    uid = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    dn = models.CharField(max_length=500)
    cn = models.CharField(max_length=255)
    role_code = models.CharField(max_length=50, blank=True)
    permissions = models.JSONField(default=list, blank=True)
    source_type = models.CharField(max_length=50, blank=True)
    source_id = models.CharField(max_length=100, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['dn']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'dn'], name='unique_directory_dn_per_organization'),
            models.UniqueConstraint(fields=['organization', 'source_type', 'source_id'], name='unique_directory_source_per_organization'),
        ]

    def __str__(self):
        return self.dn


class Entity(models.Model):
    """Legal/business entity within an organization"""
    WORKSPACE_MODE_CHOICES = [
        ('accounting', 'Accounting'),
        ('equity', 'Equity'),
        ('combined', 'Combined'),
        ('standalone', 'Standalone'),
        ('workspace', 'Workspace'),
    ]

    ENTITY_TYPE_CHOICES = [
        ('sole_proprietor', 'Sole Proprietor'),
        ('llc', 'LLC'),
        ('partnership', 'Partnership'),
        ('corporation', 'Corporation'),
        ('holding_company', 'Holding Company'),
        ('nonprofit', 'Nonprofit'),
        ('subsidiary', 'Subsidiary'),
        ('branch', 'Branch'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('dormant', 'Dormant'),
        ('wind_down', 'In Wind-down'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='entities')
    name = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50, choices=ENTITY_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    registration_number = models.CharField(max_length=100, blank=True)
    local_currency = models.CharField(max_length=3, default='USD')
    main_bank = models.CharField(max_length=255, blank=True)
    tax_authority_url = models.URLField(blank=True)
    fiscal_year_end = models.DateField(null=True, blank=True)
    next_filing_date = models.DateField(null=True, blank=True)
    workspace_mode = models.CharField(max_length=20, choices=WORKSPACE_MODE_CHOICES, default='accounting')
    industry = models.CharField(max_length=100, blank=True)
    workspace_type = models.CharField(max_length=50, blank=True, default='')
    workspace_template_key = models.CharField(max_length=50, blank=True, default='')
    hierarchy_metadata = models.JSONField(default=dict, blank=True)
    dashboard_config = models.JSONField(default=dict, blank=True)
    rbac_config = models.JSONField(default=dict, blank=True)
    enabled_modules = models.JSONField(default=list, blank=True)
    parent_entity = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_entities'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['country', 'name']

    def __str__(self):
        return f"{self.name} ({self.country})"

    def create_default_structure(self):
        """Create default departments, roles, and categories for new entity"""
        from django.utils import timezone

        # Default departments
        default_departments = [
            {'name': 'Human Resources', 'code': f'HR_{self.id}', 'description': 'Human Resources and Personnel Management'},
            {'name': 'Finance', 'code': f'FIN_{self.id}', 'description': 'Financial Operations and Accounting'},
            {'name': 'Operations', 'code': f'OPS_{self.id}', 'description': 'Business Operations'},
            {'name': 'IT', 'code': f'IT_{self.id}', 'description': 'Information Technology'},
            {'name': 'Legal', 'code': f'LEGAL_{self.id}', 'description': 'Legal and Compliance'},
        ]

        departments = {}
        for dept_data in default_departments:
            dept, created = EntityDepartment.objects.get_or_create(
                entity=self,
                code=dept_data['code'],
                defaults=dept_data
            )
            departments[dept_data['name']] = dept

        # Default roles
        default_roles = [
            {'name': 'CEO', 'code': f'CEO_{self.id}', 'department': departments.get('Operations'), 'description': 'Chief Executive Officer'},
            {'name': 'CFO', 'code': f'CFO_{self.id}', 'department': departments.get('Finance'), 'description': 'Chief Financial Officer'},
            {'name': 'HR Manager', 'code': f'HRM_{self.id}', 'department': departments.get('Human Resources'), 'description': 'Human Resources Manager'},
            {'name': 'Finance Manager', 'code': f'FM_{self.id}', 'department': departments.get('Finance'), 'description': 'Finance Manager'},
            {'name': 'Operations Manager', 'code': f'OM_{self.id}', 'department': departments.get('Operations'), 'description': 'Operations Manager'},
            {'name': 'IT Manager', 'code': f'ITM_{self.id}', 'department': departments.get('IT'), 'description': 'IT Manager'},
            {'name': 'Accountant', 'code': f'ACC_{self.id}', 'department': departments.get('Finance'), 'description': 'Accountant'},
            {'name': 'HR Assistant', 'code': f'HRA_{self.id}', 'department': departments.get('Human Resources'), 'description': 'HR Assistant'},
        ]

        roles = {}
        for role_data in default_roles:
            role, created = EntityRole.objects.get_or_create(
                entity=self,
                code=role_data['code'],
                defaults=role_data
            )
            roles[role_data['name']] = role

        # Default expense categories
        default_expense_categories = [
            'Office Supplies', 'Travel', 'Marketing', 'Utilities', 'Rent', 'Insurance',
            'Professional Services', 'Equipment', 'Software', 'Training', 'Meals', 'Transportation'
        ]

        # Create empty budgets for each category
        for category in default_expense_categories:
            Budget.objects.get_or_create(
                entity=self,
                category=category,
                defaults={
                    'limit': 0,
                    'currency': self.local_currency,
                }
            )

        # Default income categories/sources
        default_income_sources = [
            'Product Sales', 'Service Revenue', 'Consulting', 'Investment Income', 'Grants', 'Other'
        ]

        # Create sample income records (empty)
        for source in default_income_sources:
            Income.objects.get_or_create(
                entity=self,
                source=source,
                date=timezone.now().date(),
                defaults={
                    'amount': 0,
                    'currency': self.local_currency,
                    'income_type': 'business'
                }
            )

        # Create default bookkeeping categories
        default_income_categories = [
            'Sales Revenue', 'Service Fees', 'Retainers', 'Investment Income',
            'Loan Repayments', 'Miscellaneous Income'
        ]
        
        default_expense_categories_bookkeeping = [
            'Staff Salaries', 'Contractor Payments', 'Rent', 'Utilities',
            'Car/Vehicle Expenses', 'Shipments & Logistics', 'Software Subscriptions',
            'Taxes', 'Insurance', 'Legal Fees', 'Marketing', 'Asset Purchases'
        ]
        
        for cat_name in default_income_categories:
            BookkeepingCategory.objects.get_or_create(
                entity=self,
                name=cat_name,
                type='income',
                defaults={'is_default': True}
            )
        
        for cat_name in default_expense_categories_bookkeeping:
            BookkeepingCategory.objects.get_or_create(
                entity=self,
                name=cat_name,
                type='expense',
                defaults={'is_default': True}
            )
        
        # Create default bookkeeping account
        BookkeepingAccount.objects.get_or_create(
            entity=self,
            name=f"{self.main_bank or 'Main Account'}",
            defaults={
                'type': 'bank',
                'balance': 0,
                'currency': self.local_currency,
                'is_active': True
            }
        )

        return {
            'departments': departments,
            'roles': roles,
            'expense_categories': default_expense_categories,
            'income_sources': default_income_sources,
            'bookkeeping_setup': True
        }


class EntityDepartment(models.Model):
    """Departments within an entity"""
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='departments')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    department_code = models.CharField(max_length=20, unique=True, editable=False, db_index=True, blank=True)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey('EntityStaff', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')
    budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'code')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.entity.name}"

    def save(self, *args, **kwargs):
        if self.pk:
            stored_code = EntityDepartment.objects.filter(pk=self.pk).values_list('department_code', flat=True).first()
            if stored_code:
                self.department_code = stored_code
        if not self.department_code:
            self.department_code = generate_identity_code('DEP')
        super().save(*args, **kwargs)


class DashboardAccessGrant(models.Model):
    """A revocable, optionally temporary grant for one isolated dashboard branch."""

    BRANCH_WORKSPACE = 'workspace'
    BRANCH_ENTITY = 'entity'
    BRANCH_EQUITY = 'equity'
    BRANCH_CHOICES = [
        (BRANCH_WORKSPACE, 'Workspace'),
        (BRANCH_ENTITY, 'Entity'),
        (BRANCH_EQUITY, 'Equity'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_access_grants')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='dashboard_access_grants')
    branch = models.CharField(max_length=20, choices=BRANCH_CHOICES)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True, related_name='dashboard_access_grants')
    workspace = models.ForeignKey('workspaces.Workspace', on_delete=models.CASCADE, null=True, blank=True, related_name='dashboard_access_grants')
    department = models.ForeignKey(EntityDepartment, on_delete=models.CASCADE, null=True, blank=True, related_name='dashboard_access_grants')
    invitation = models.ForeignKey('TeamMember', on_delete=models.SET_NULL, null=True, blank=True, related_name='dashboard_access_grants')
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='dashboard_access_grants_issued')
    expires_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'branch', 'revoked_at']),
            models.Index(fields=['organization', 'branch']),
        ]

    @property
    def is_active(self):
        invitation_is_active = (
            self.invitation_id is None
            or (self.invitation.is_active and self.invitation.accepted_at is not None)
        )
        return invitation_is_active and self.revoked_at is None and (
            self.expires_at is None or self.expires_at > timezone.now()
        )


class BankAccount(models.Model):
    """Bank accounts for entities"""
    VERIFICATION_STATUS_CHOICES = [
        ('unverified', 'Unverified'),
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    ]

    ACCOUNT_TYPE_CHOICES = [
        ('checking', 'Checking'),
        ('savings', 'Savings'),
        ('business', 'Business'),
        ('investment', 'Investment'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bank_accounts')
    provider = models.CharField(max_length=50, blank=True)
    provider_account_id = models.CharField(max_length=255, blank=True)
    account_name = models.CharField(max_length=255)
    account_number = models.CharField(max_length=100)  # Masked for security
    bank_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES, default='checking')
    currency = models.CharField(max_length=3, default='USD')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUS_CHOICES, default='unverified')
    iban = models.CharField(max_length=34, blank=True)
    swift_code = models.CharField(max_length=11, blank=True)
    routing_number = models.CharField(max_length=9, blank=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['bank_name', 'account_name']
        unique_together = ('entity', 'provider', 'provider_account_id')

    def __str__(self):
        return f"{self.account_name} - {self.bank_name} ({self.entity.name})"


class Wallet(models.Model):
    """Digital/cash wallets for entities"""
    WALLET_TYPE_CHOICES = [
        ('cash', 'Cash'),
        ('digital', 'Digital Wallet'),
        ('crypto', 'Cryptocurrency'),
        ('petty_cash', 'Petty Cash'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='wallets')
    name = models.CharField(max_length=255)
    wallet_type = models.CharField(max_length=20, choices=WALLET_TYPE_CHOICES, default='cash')
    currency = models.CharField(max_length=3, default='USD')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    provider = models.CharField(max_length=255, blank=True)  # e.g., PayPal, Venmo, Cash App
    account_id = models.CharField(max_length=255, blank=True)  # Masked account/wallet ID
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['wallet_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_wallet_type_display()}) - {self.entity.name}"


class ComplianceDocument(models.Model):
    """Legal and compliance documents with expiry tracking"""
    DOCUMENT_TYPE_CHOICES = [
        ('license', 'Business License'),
        ('registration', 'Company Registration'),
        ('tax_certificate', 'Tax Certificate'),
        ('insurance', 'Insurance Policy'),
        ('permit', 'Permit'),
        ('contract', 'Contract'),
        ('certificate', 'Certificate'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('expiring_soon', 'Expiring Soon'),
        ('renewed', 'Renewed'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='compliance_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    document_number = models.CharField(max_length=100, blank=True)
    issuing_authority = models.CharField(max_length=255)
    issue_date = models.DateField()
    expiry_date = models.DateField()
    renewal_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    file_path = models.FileField(upload_to='compliance_documents/', null=True, blank=True)
    notes = models.TextField(blank=True)
    reminder_days = models.IntegerField(default=30)  # Days before expiry to send reminder
    responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='compliance_documents')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expiry_date']

    def __str__(self):
        return f"{self.title} - {self.entity.name} ({self.expiry_date})"

    @property
    def days_until_expiry(self):
        from django.utils import timezone
        if self.expiry_date:
            return (self.expiry_date - timezone.now().date()).days
        return None

    @property
    def is_expiring_soon(self):
        days = self.days_until_expiry
        return days is not None and days <= self.reminder_days


class Permission(models.Model):
    """Define granular permissions for roles"""
    PERMISSION_CHOICES = [
        # Org-level permissions
        ('view_org_overview', 'View Organization Overview'),
        ('manage_org_settings', 'Manage Organization Settings'),
        ('manage_billing', 'Manage Billing'),
        
        # Entity permissions
        ('view_entities', 'View Entities'),
        ('create_entity', 'Create Entity'),
        ('edit_entity', 'Edit Entity'),
        ('delete_entity', 'Delete Entity'),
        
        # Tax & Compliance
        ('view_tax_compliance', 'View Tax Compliance'),
        ('edit_tax_compliance', 'Edit Tax Compliance'),
        ('manage_tax_regimes', 'Manage Tax Regimes'),
        ('view_tax_audit_logs', 'View Tax Audit Logs'),
        ('submit_tax_filings', 'Submit Tax Filings'),
        ('run_tax_calculations', 'Run Tax Calculations'),
        ('edit_tax_registrations', 'Edit Tax Registration Numbers'),
        ('export_tax_reports', 'Export Tax Reports'),
        
        # Cashflow & Treasury
        ('view_cashflow', 'View Cashflow'),
        ('edit_cashflow', 'Edit Cashflow'),
        
        # Risk & Exposure
        ('view_risk_exposure', 'View Risk Exposure'),
        ('edit_risk_exposure', 'Edit Risk Exposure'),
        
        # Reports
        ('view_reports', 'View Reports'),
        ('generate_reports', 'Generate Reports'),
        ('export_reports', 'Export Reports'),
        
        # Team
        ('view_team', 'View Team Members'),
        ('manage_team', 'Manage Team Members'),
        ('assign_roles', 'Assign Roles'),
    ]

    code = models.CharField(max_length=100, choices=PERMISSION_CHOICES, unique=True)

    def __str__(self):
        return self.get_code_display()


class EntityRole(models.Model):
    """Roles within an entity"""
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='roles')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    department = models.ForeignKey(EntityDepartment, on_delete=models.SET_NULL, null=True, blank=True, related_name='roles')
    description = models.TextField(blank=True)
    salary_range_min = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    salary_range_max = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    permissions = models.ManyToManyField(Permission, blank=True, related_name='entity_roles')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'code')
        ordering = ['department__name', 'name']

    def __str__(self):
        return f"{self.name} - {self.entity.name}"


class EntityStaff(models.Model):
    """Staff profiles within an entity"""
    EMPLOYMENT_TYPE_CHOICES = [
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('consultant', 'Consultant'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
        ('on_leave', 'On Leave'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='staff')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='entity_staff_profile')
    employee_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    department = models.ForeignKey(EntityDepartment, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='staff')
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE_CHOICES, default='full_time')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    hire_date = models.DateField()
    termination_date = models.DateField(null=True, blank=True)
    salary = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='direct_reports')
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.entity.name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class StaffPayrollProfile(models.Model):
    """Payroll settings and tax/bank metadata for a staff member."""

    PAY_FREQUENCY_CHOICES = [
        ('weekly', 'Weekly'),
        ('biweekly', 'Bi-Weekly'),
        ('semimonthly', 'Semi-Monthly'),
        ('monthly', 'Monthly'),
    ]

    SALARY_BASIS_CHOICES = [
        ('annual', 'Annual Salary'),
        ('monthly', 'Monthly Salary'),
    ]

    staff_member = models.OneToOneField(EntityStaff, on_delete=models.CASCADE, related_name='payroll_profile')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='staff_payroll_profiles')
    pay_frequency = models.CharField(max_length=20, choices=PAY_FREQUENCY_CHOICES, default='monthly')
    salary_basis = models.CharField(max_length=20, choices=SALARY_BASIS_CHOICES, default='annual')
    base_salary = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    standard_hours_per_period = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('160.00'))
    income_tax_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    employee_tax_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    employer_tax_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    default_bank_account_name = models.CharField(max_length=255, blank=True)
    default_bank_account_number = models.CharField(max_length=100, blank=True)
    default_bank_routing_number = models.CharField(max_length=50, blank=True)
    default_bank_iban = models.CharField(max_length=34, blank=True)
    default_bank_swift_code = models.CharField(max_length=11, blank=True)
    default_bank_sort_code = models.CharField(max_length=20, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    tax_identifier = models.CharField(max_length=100, blank=True)
    statutory_jurisdiction = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['staff_member__last_name', 'staff_member__first_name']
        indexes = [
            models.Index(fields=['entity', 'is_active']),
        ]

    def __str__(self):
        return f"Payroll Profile - {self.staff_member.full_name}"


class PayrollComponent(models.Model):
    """Reusable earnings, benefit, and deduction rules for payroll calculations."""

    COMPONENT_TYPE_CHOICES = [
        ('earning', 'Earning'),
        ('benefit', 'Benefit'),
        ('deduction', 'Deduction'),
    ]

    CALCULATION_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount'),
        ('percent_of_base', 'Percent of Base Salary'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='payroll_components')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    component_type = models.CharField(max_length=20, choices=COMPONENT_TYPE_CHOICES)
    calculation_type = models.CharField(max_length=20, choices=CALCULATION_TYPE_CHOICES, default='fixed')
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    taxable = models.BooleanField(default=True)
    employer_contribution = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'code')
        ordering = ['component_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.component_type})"


class StaffPayrollComponentAssignment(models.Model):
    """Assign payroll earnings, benefits, and deductions to individual staff members."""

    staff_member = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='payroll_component_assignments')
    component = models.ForeignKey(PayrollComponent, on_delete=models.CASCADE, related_name='staff_assignments')
    amount_override = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    effective_start = models.DateField(null=True, blank=True)
    effective_end = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('staff_member', 'component')
        ordering = ['component__component_type', 'component__name']

    def __str__(self):
        return f"{self.staff_member.full_name} - {self.component.name}"


class LeaveType(models.Model):
    """Entity leave policy with accrual rules."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='leave_types')
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    accrual_hours_per_run = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    max_balance_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carryover_limit_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_paid_leave = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'code')
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.entity.name}"


class LeaveBalance(models.Model):
    """Running leave accrual and usage balance for a staff member."""

    staff_member = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    opening_balance_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    accrued_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    used_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('staff_member', 'leave_type')
        ordering = ['staff_member__last_name', 'leave_type__name']

    @property
    def current_balance_hours(self):
        return (self.opening_balance_hours or 0) + (self.accrued_hours or 0) - (self.used_hours or 0)

    def __str__(self):
        return f"{self.staff_member.full_name} - {self.leave_type.name}"


class PayrollBankOriginatorProfile(models.Model):
    """Entity-level originator metadata used for bank payment exports."""

    entity = models.OneToOneField(Entity, on_delete=models.CASCADE, related_name='payroll_bank_originator_profile')
    originator_name = models.CharField(max_length=255)
    originator_identifier = models.CharField(max_length=100, blank=True)
    originating_bank_name = models.CharField(max_length=255, blank=True)
    debit_account_name = models.CharField(max_length=255, blank=True)
    debit_account_number = models.CharField(max_length=100, blank=True)
    debit_routing_number = models.CharField(max_length=50, blank=True)
    debit_iban = models.CharField(max_length=34, blank=True)
    debit_swift_code = models.CharField(max_length=11, blank=True)
    debit_sort_code = models.CharField(max_length=20, blank=True)
    company_entry_description = models.CharField(max_length=20, blank=True)
    company_discretionary_data = models.CharField(max_length=20, blank=True)
    initiating_party_name = models.CharField(max_length=255, blank=True)
    initiating_party_identifier = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['entity__name']

    def __str__(self):
        return f"{self.entity.name} Payroll Originator"


class PayrollRun(models.Model):
    """A payroll processing cycle for an entity and period."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('processed', 'Processed'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('pending_approval', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    PAY_FREQUENCY_CHOICES = StaffPayrollProfile.PAY_FREQUENCY_CHOICES
    BANK_FILE_FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('sepa', 'SEPA'),
        ('aba', 'ABA'),
        ('bacs', 'BACS'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='payroll_runs')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='payroll_runs')
    name = models.CharField(max_length=255)
    pay_frequency = models.CharField(max_length=20, choices=PAY_FREQUENCY_CHOICES, default='monthly')
    period_start = models.DateField()
    period_end = models.DateField()
    payment_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='draft')
    employee_count = models.PositiveIntegerField(default=0)
    gross_pay_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employee_benefits_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_benefits_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    deductions_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_withholding_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_tax_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_pay_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    statutory_summary = models.JSONField(default=dict, blank=True)
    requested_bank_file_format = models.CharField(max_length=20, choices=BANK_FILE_FORMAT_CHOICES, default='csv')
    requested_bank_institution = models.CharField(max_length=100, blank=True)
    requested_bank_export_variant = models.CharField(max_length=100, blank=True)
    journal_entry = models.ForeignKey('JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_runs')
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_runs_processed')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payroll_runs_approved')
    processed_at = models.DateTimeField(null=True, blank=True)
    approval_submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-payment_date', '-created_at']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['organization', 'payment_date']),
        ]

    def __str__(self):
        return f"{self.name} - {self.entity.name}"


class Payslip(models.Model):
    """Employee-level payroll statement generated from a pay run."""

    STATUS_CHOICES = [
        ('generated', 'Generated'),
        ('paid', 'Paid'),
        ('void', 'Void'),
    ]

    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='payslips')
    staff_member = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='payslips')
    payroll_profile = models.ForeignKey(StaffPayrollProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='payslips')
    gross_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employee_benefits_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_benefits_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    deductions_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    taxable_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    tax_withholding = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    employer_tax = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    leave_accrued_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    leave_used_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    leave_balance_hours = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    bank_payment_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('payroll_run', 'staff_member')
        ordering = ['staff_member__last_name', 'staff_member__first_name']

    def __str__(self):
        return f"{self.staff_member.full_name} - {self.payroll_run.name}"


class PayslipLineItem(models.Model):
    """Detailed earnings, benefit, deduction, and tax lines for a payslip."""

    CATEGORY_CHOICES = [
        ('earning', 'Earning'),
        ('benefit', 'Benefit'),
        ('deduction', 'Deduction'),
        ('withholding', 'Withholding'),
        ('employer_tax', 'Employer Tax'),
        ('leave', 'Leave'),
    ]

    payslip = models.ForeignKey(Payslip, on_delete=models.CASCADE, related_name='line_items')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    code = models.CharField(max_length=50)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    taxable = models.BooleanField(default=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.description} - {self.payslip.staff_member.full_name}"


class PayrollStatutoryReport(models.Model):
    """Generated statutory payroll reporting package for a payroll run."""

    REPORT_TYPE_CHOICES = [
        ('withholding_return', 'Withholding Return'),
        ('social_contribution', 'Social Contribution Report'),
        ('payroll_register', 'Payroll Register'),
    ]

    STATUS_CHOICES = [
        ('generated', 'Generated'),
        ('filed', 'Filed'),
        ('submitted', 'Submitted'),
    ]

    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE, related_name='statutory_reports')
    report_type = models.CharField(max_length=30, choices=REPORT_TYPE_CHOICES)
    jurisdiction = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    due_date = models.DateField(null=True, blank=True)
    report_payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_report_type_display()} - {self.payroll_run.name}"


class PayrollBankPaymentFile(models.Model):
    """Exportable bank payment file generated from a payroll run."""

    FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('sepa', 'SEPA'),
        ('aba', 'ABA'),
        ('bacs', 'BACS'),
    ]

    STATUS_CHOICES = [
        ('generated', 'Generated'),
        ('exported', 'Exported'),
    ]

    payroll_run = models.OneToOneField(PayrollRun, on_delete=models.CASCADE, related_name='bank_payment_file')
    file_format = models.CharField(max_length=20, choices=FORMAT_CHOICES, default='csv')
    file_name = models.CharField(max_length=255)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='generated')
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return self.file_name


class LeaveRequest(models.Model):
    """Requested and approved leave that feeds payroll accrual and usage."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('processed', 'Processed In Payroll'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='leave_requests')
    staff_member = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    hours_requested = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leave_requests_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_leave_requests')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['staff_member', 'start_date']),
        ]

    def __str__(self):
        return f"{self.staff_member.full_name} - {self.leave_type.name}"


class Role(models.Model):
    """Define roles with bundled permissions"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=50, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, related_name='roles')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_code_display()

    @staticmethod
    def get_or_create_default_roles():
        """Create or fetch default roles with permissions"""
        permissions_dict = {p[0]: Permission.objects.get_or_create(code=p[0])[0] for p in Permission.PERMISSION_CHOICES}
        
        # ORG_OWNER: All permissions
        owner_role, _ = Role.objects.get_or_create(
            code=ROLE_ORG_OWNER,
            defaults={'name': 'Organization Owner', 'description': 'Full access to organization'}
        )
        owner_role.permissions.set(Permission.objects.all())
        
        # CFO: All except billing
        cfo_role, _ = Role.objects.get_or_create(
            code=ROLE_CFO,
            defaults={'name': 'Chief Financial Officer', 'description': 'Full financial and tax access'}
        )
        cfo_perms = [p for code, p in permissions_dict.items() if 'manage_billing' not in code]
        cfo_role.permissions.set(cfo_perms)
        
        # FINANCE_ANALYST: View and edit data, no org-level settings
        analyst_role, _ = Role.objects.get_or_create(
            code=ROLE_FINANCE_ANALYST,
            defaults={'name': 'Finance Analyst', 'description': 'View and edit financial data'}
        )
        analyst_perms = [
            permissions_dict.get('view_org_overview'),
            permissions_dict.get('view_entities'),
            permissions_dict.get('create_entity'),
            permissions_dict.get('edit_entity'),
            permissions_dict.get('view_tax_compliance'),
            permissions_dict.get('edit_tax_compliance'),
            permissions_dict.get('view_cashflow'),
            permissions_dict.get('edit_cashflow'),
            permissions_dict.get('view_risk_exposure'),
            permissions_dict.get('view_reports'),
            permissions_dict.get('generate_reports'),
        ]
        analyst_role.permissions.set([p for p in analyst_perms if p])
        
        # VIEWER: Read-only access
        viewer_role, _ = Role.objects.get_or_create(
            code=ROLE_VIEWER,
            defaults={'name': 'Viewer', 'description': 'Read-only access to reports and dashboards'}
        )
        viewer_perms = [
            permissions_dict.get('view_org_overview'),
            permissions_dict.get('view_entities'),
            permissions_dict.get('view_tax_compliance'),
            permissions_dict.get('view_cashflow'),
            permissions_dict.get('view_risk_exposure'),
            permissions_dict.get('view_reports'),
        ]
        viewer_role.permissions.set([p for p in viewer_perms if p])
        
        # EXTERNAL_ADVISOR: Scoped access
        advisor_role, _ = Role.objects.get_or_create(
            code=ROLE_EXTERNAL_ADVISOR,
            defaults={'name': 'External Advisor', 'description': 'Limited scoped access'}
        )
        advisor_perms = [
            permissions_dict.get('view_tax_compliance'),
            permissions_dict.get('view_reports'),
        ]
        advisor_role.permissions.set([p for p in advisor_perms if p])

        compliance_role, _ = Role.objects.get_or_create(
            code=ROLE_COMPLIANCE_OFFICER,
            defaults={'name': 'Compliance Officer', 'description': 'Governance and audit oversight'}
        )
        compliance_perms = [
            permissions_dict.get('view_org_overview'),
            permissions_dict.get('view_entities'),
            permissions_dict.get('view_tax_compliance'),
            permissions_dict.get('edit_tax_compliance'),
            permissions_dict.get('manage_tax_regimes'),
            permissions_dict.get('view_tax_audit_logs'),
            permissions_dict.get('submit_tax_filings'),
            permissions_dict.get('run_tax_calculations'),
            permissions_dict.get('edit_tax_registrations'),
            permissions_dict.get('export_tax_reports'),
            permissions_dict.get('view_reports'),
            permissions_dict.get('generate_reports'),
        ]
        compliance_role.permissions.set([p for p in compliance_perms if p])
        
        return {
            ROLE_ORG_OWNER: owner_role,
            ROLE_CFO: cfo_role,
            ROLE_FINANCE_ANALYST: analyst_role,
            ROLE_VIEWER: viewer_role,
            ROLE_EXTERNAL_ADVISOR: advisor_role,
            ROLE_COMPLIANCE_OFFICER: compliance_role,
        }


class TeamMember(models.Model):
    """Team members in an organization"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='team_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_roles')
    role = models.ForeignKey(Role, on_delete=models.PROTECT)
    # Scope: if external advisor, can limit to specific entities
    scoped_entities = models.ManyToManyField(Entity, blank=True, help_text="Leave empty for full access")
    is_active = models.BooleanField(default=True)
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    invite_code_hash = models.CharField(max_length=128, blank=True)
    invite_code_issued_at = models.DateTimeField(null=True, blank=True)
    invitation_reference = models.CharField(max_length=40, unique=True, editable=False, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.role.name} @ {self.organization.name}"

    def issue_invite_code(self):
        raw_code = secrets.token_hex(4).upper()
        self.invite_code_hash = make_password(raw_code)
        self.invite_code_issued_at = timezone.now()
        if not self.invitation_reference:
            with transaction.atomic():
                sequence, _ = EnterpriseInvitationSequence.objects.select_for_update().get_or_create(
                    organization=self.organization,
                )
                sequence.last_value += 1
                sequence.save(update_fields=['last_value'])
                self.invitation_reference = f'INV-{self.organization.enterprise_code}-{sequence.last_value:02d}'
        return raw_code

    def check_invite_code(self, raw_code):
        if not self.invite_code_hash or not raw_code:
            return False
        return check_password(str(raw_code).strip(), self.invite_code_hash)


class Expense(models.Model):
    """Model for tracking expenses (personal or entity-specific)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_expenses', null=True, blank=True)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='expenses', null=True, blank=True)
    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    category = models.CharField(max_length=100)
    date = models.DateField()
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        scope = f"Entity: {self.entity}" if self.entity else f"User: {self.user}"
        return f"{self.description} - ${self.amount} ({self.category}) [{scope}]"


class Income(models.Model):
    """Model for tracking income (personal or entity-specific)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_income', null=True, blank=True)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='income', null=True, blank=True)
    source = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    date = models.DateField()
    income_type = models.CharField(max_length=50, default='salary')  # salary, investment, business, etc.
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-created_at']

    def __str__(self):
        scope = f"Entity: {self.entity}" if self.entity else f"User: {self.user}"
        return f"{self.source} - ${self.amount} [{scope}]"


class Budget(models.Model):
    """Model for tracking budgets by category"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_budgets', null=True, blank=True)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='budgets', null=True, blank=True)
    category = models.CharField(max_length=100)
    limit = models.DecimalField(max_digits=15, decimal_places=2)
    spent = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    color = models.CharField(max_length=7, default='#3498db')  # Hex color code
    currency = models.CharField(max_length=3, default='USD')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-category']

    def __str__(self):
        scope = f"Entity: {self.entity}" if self.entity else f"User: {self.user}"
        return f"{self.category} - ${self.spent}/${self.limit} [{scope}]"

    @property
    def percentage_used(self):
        """Calculate percentage of budget used"""
        if self.limit > 0:
            return (self.spent / self.limit) * 100
        return 0

    @property
    def remaining(self):
        """Calculate remaining budget"""
        return self.limit - self.spent


class TaxExposure(models.Model):
    """Track tax obligations per entity, country, period"""
    PERIOD_CHOICES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]

    STATUS_CHOICES = [
        ('estimated', 'Estimated'),
        ('ready', 'Ready to File'),
        ('filed', 'Filed'),
        ('paid', 'Paid'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='tax_exposures')
    country = models.CharField(max_length=100)
    tax_type = models.CharField(max_length=100)  # e.g., "Corporate Income Tax", "VAT"
    period = models.CharField(max_length=20, choices=PERIOD_CHOICES)
    tax_year = models.IntegerField()
    period_start = models.DateField()
    period_end = models.DateField()
    estimated_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='estimated')
    filing_deadline = models.DateField()
    payment_deadline = models.DateField()
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'country', 'tax_type', 'tax_year', 'period')
        ordering = ['filing_deadline']

    def __str__(self):
        return f"{self.tax_type} - {self.country} ({self.period_start} to {self.period_end})"


class TaxRegimeRegistry(models.Model):
    """Canonical registry of tax regimes by jurisdiction.

    This lets the platform describe tax logic for any country or territory without
    hard-coding regime behavior into entity or calculation flows.
    """

    REGIME_CATEGORY_CHOICES = [
        ('income_tax', 'Income Tax'),
        ('vat', 'VAT / GST / Sales Tax'),
        ('withholding', 'Withholding Tax'),
        ('payroll', 'Payroll Tax'),
        ('property', 'Property Tax'),
        ('customs', 'Customs / Duties'),
        ('other', 'Other'),
    ]

    FILING_FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'),
        ('bi_monthly', 'Bi-Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
        ('ad_hoc', 'Ad Hoc'),
        ('event_based', 'Event-Based'),
    ]

    jurisdiction_code = models.CharField(max_length=50)
    country = models.CharField(max_length=100)
    regime_code = models.CharField(max_length=80)
    regime_name = models.CharField(max_length=255)
    tax_type = models.CharField(max_length=120, blank=True)
    regime_category = models.CharField(max_length=30, choices=REGIME_CATEGORY_CHOICES, default='other')
    filing_frequency = models.CharField(max_length=20, choices=FILING_FREQUENCY_CHOICES, default='annual')
    filing_form = models.CharField(max_length=100, blank=True)
    required_forms = models.JSONField(default=list, blank=True)
    calculation_method = models.CharField(max_length=120, blank=True)
    penalty_rules = models.JSONField(default=dict, blank=True)
    rules_json = models.JSONField(default=dict, blank=True)
    forms_json = models.JSONField(default=list, blank=True)
    penalty_rules_json = models.JSONField(default=dict, blank=True)
    compliance_rules_json = models.JSONField(default=dict, blank=True)
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    rule_set = models.JSONField(default=dict, blank=True)
    reference_links = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('jurisdiction_code', 'regime_code')
        ordering = ['jurisdiction_code', 'regime_name']

    def __str__(self):
        return f"{self.jurisdiction_code} - {self.regime_name}"


class TaxProfile(models.Model):
    """Tax profile per entity and country/jurisdiction.

    Stores the tax rule configuration and compliance state used by the Tax & Compliance UI.
    """

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('inactive', 'Inactive'),
    ]

    RESIDENCY_STATUS_CHOICES = [
        ('detected', 'Detected'),
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='tax_profiles')
    country = models.CharField(max_length=100)
    jurisdiction_code = models.CharField(max_length=50, blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    tax_rules = models.JSONField(default=dict, blank=True)
    registered_regimes = models.JSONField(default=list, blank=True)
    registration_numbers = models.JSONField(default=dict, blank=True)
    filing_preferences = models.JSONField(default=dict, blank=True)
    auto_update = models.BooleanField(default=True)
    residency_status = models.CharField(max_length=20, choices=RESIDENCY_STATUS_CHOICES, default='detected')
    compliance_score = models.IntegerField(default=0)
    last_rule_update = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'country')
        ordering = ['country', '-updated_at']

    def __str__(self):
        return f"TaxProfile {self.country} - {self.entity.name}"

    @property
    def resolved_jurisdiction_code(self):
        return self.jurisdiction_code or self.country

    @property
    def active_regime_codes(self):
        if isinstance(self.registered_regimes, list):
            return [str(code) for code in self.registered_regimes if code]
        return []


class ComplianceDeadline(models.Model):
    """Track compliance deadlines for entities"""
    DEADLINE_TYPE_CHOICES = [
        ('tax_filing', 'Tax Filing'),
        ('vat_filing', 'VAT Filing'),
        ('payroll', 'Payroll Filing'),
        ('audit', 'Audit'),
        ('renewal', 'License/Registration Renewal'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('due_soon', 'Due Soon'),
        ('overdue', 'Overdue'),
        ('completed', 'Completed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='compliance_deadlines')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='compliance_deadlines')
    title = models.CharField(max_length=255)
    deadline_type = models.CharField(max_length=50, choices=DEADLINE_TYPE_CHOICES)
    deadline_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    description = models.TextField(blank=True)
    responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    completed_at = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['deadline_date']

    def __str__(self):
        return f"{self.title} - {self.entity.name} ({self.deadline_date})"


class CashflowForecast(models.Model):
    """Cashflow forecasting and tracking"""
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='cashflow_forecasts')
    month = models.DateField()  # First day of month
    category = models.CharField(max_length=100)  # e.g., "Income", "Expenses", "Tax Payments", "Payroll"
    forecasted_amount = models.DecimalField(max_digits=15, decimal_places=2)
    actual_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'month', 'category')
        ordering = ['-month']

    def __str__(self):
        return f"{self.entity.name} - {self.category} ({self.month})"


class AuditLog(models.Model):
    """Track all changes for compliance and audit purposes"""
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
        ('reconcile', 'Reconcile'),
        ('bulk_import', 'Bulk Import'),
        ('replay', 'Replay'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='audit_logs')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True, related_name='audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)  # Model that was changed
    object_id = models.CharField(max_length=100)
    changes = models.JSONField(default=dict)  # Track what changed
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        scope = f"Entity: {self.entity.name}" if self.entity else f"Organization: {self.organization.name}"
        return f"{self.action} {self.model_name} by {self.user} on {self.created_at} [{scope}]"


class PlatformAuditEvent(models.Model):
    """Cross-domain audit stream for finance, workspace, and future product areas."""

    ACTOR_TYPE_CHOICES = [
        ('user', 'User'),
        ('system', 'System'),
        ('external', 'External'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='platform_audit_events')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True, related_name='platform_audit_events')
    workspace_id = models.UUIDField(null=True, blank=True)
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='platform_audit_events')
    actor_type = models.CharField(max_length=20, choices=ACTOR_TYPE_CHOICES, default='user')
    actor_identifier = models.CharField(max_length=100, blank=True)
    subject_type = models.CharField(max_length=100, blank=True)
    subject_id = models.CharField(max_length=100, blank=True)
    action = models.CharField(max_length=100, blank=True)
    correlation_id = models.CharField(max_length=100, blank=True)

    domain = models.CharField(max_length=50)
    event_type = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=100)
    resource_name = models.CharField(max_length=255, blank=True)
    summary = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    context = models.JSONField(default=dict, blank=True)
    diff = models.JSONField(default=dict, blank=True)
    search_text = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['domain', 'event_type']),
            models.Index(fields=['organization', 'occurred_at']),
            models.Index(fields=['workspace_id', 'occurred_at']),
            models.Index(fields=['resource_type', 'resource_id']),
            models.Index(fields=['subject_type', 'subject_id']),
            models.Index(fields=['actor_identifier', 'occurred_at']),
            models.Index(fields=['action', 'occurred_at']),
            models.Index(fields=['correlation_id']),
        ]

    def __str__(self):
        return f"{self.domain}:{self.event_type} {self.resource_type}#{self.resource_id}"


GOVERNANCE_POLICY_STATUS_CHOICES = [
    ('draft', 'Draft'), ('active', 'Active'), ('superseded', 'Superseded'), ('archived', 'Archived'),
]
GOVERNANCE_AMENDMENT_TYPE_CHOICES = [
    ('standard', 'Standard'), ('operational', 'Operational'), ('ethical_security', 'Ethical / Security'),
    ('constitutional', 'Constitutional'), ('sovereignty', 'Sovereignty'), ('emergency', 'Emergency'),
]
GOVERNANCE_AMENDMENT_STATUS_CHOICES = [
    ('draft', 'Draft'), ('internal_review', 'Internal Review'), ('council_review', 'Council Review'),
    ('voting', 'Voting'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('published', 'Published'),
]
GOVERNANCE_VOTE_CHOICES = [('approve', 'Approve'), ('reject', 'Reject'), ('abstain', 'Abstain')]


class GovernancePolicy(models.Model):
    """Versioned governance policy owned by an organization."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='governance_policies')
    policy_code = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    edition = models.CharField(max_length=50, default='1.0')
    status = models.CharField(max_length=20, choices=GOVERNANCE_POLICY_STATUS_CHOICES, default='draft')
    summary = models.TextField(blank=True)
    source_document = models.CharField(max_length=500, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    next_review_date = models.DateField(null=True, blank=True)
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='governance_policies_owned')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['policy_code', '-created_at']
        constraints = [models.UniqueConstraint(fields=['organization', 'policy_code', 'edition'], name='unique_governance_policy_edition')]

    def __str__(self):
        return f"{self.policy_code} - {self.title} (Edition {self.edition})"


class GovernanceAmendment(models.Model):
    """Controlled amendment with the reviews required by the governance policy."""

    policy = models.ForeignKey(GovernancePolicy, on_delete=models.CASCADE, related_name='amendments')
    amendment_number = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    amendment_type = models.CharField(max_length=20, choices=GOVERNANCE_AMENDMENT_TYPE_CHOICES, default='standard')
    status = models.CharField(max_length=20, choices=GOVERNANCE_AMENDMENT_STATUS_CHOICES, default='draft')
    rationale = models.TextField()
    impact_analysis = models.TextField(blank=True)
    ethical_review = models.TextField(blank=True)
    sovereignty_check = models.TextField(blank=True)
    operational_feasibility = models.TextField(blank=True)
    security_implications = models.TextField(blank=True)
    implementation_timeline = models.CharField(max_length=255, blank=True)
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='governance_amendments_submitted')
    submitted_at = models.DateTimeField(null=True, blank=True)
    voting_opens_at = models.DateTimeField(null=True, blank=True)
    voting_closes_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [models.UniqueConstraint(fields=['policy', 'amendment_number'], name='unique_governance_amendment_number')]

    @property
    def required_approval_percent(self):
        return {'standard': 60, 'operational': 70, 'ethical_security': 75, 'constitutional': 80, 'sovereignty': 90, 'emergency': 75}[self.amendment_type]

    def __str__(self):
        return f"{self.amendment_number} - {self.title}"


class GovernanceVote(models.Model):
    """One verified vote per member for a governance amendment."""

    amendment = models.ForeignKey(GovernanceAmendment, on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='governance_votes')
    decision = models.CharField(max_length=10, choices=GOVERNANCE_VOTE_CHOICES)
    verified_at = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True)

    class Meta:
        ordering = ['-verified_at']
        constraints = [models.UniqueConstraint(fields=['amendment', 'voter'], name='unique_governance_vote_per_member')]

    def __str__(self):
        return f"{self.amendment.amendment_number} - {self.voter} ({self.decision})"


GOVERNANCE_COMMISSION_TRIGGER_CHOICES = [
    ('organization_activity', 'Organization Activity'),
    ('financial_transaction', 'Financial Transaction'),
    ('infrastructure_deployment', 'Infrastructure Deployment'),
    ('compliance_enforcement', 'Compliance Enforcement'),
    ('governance_approval', 'Governance Approval'),
]
GOVERNANCE_COMMISSION_STATUS_CHOICES = [
    ('accrued', 'Accrued'), ('approved', 'Approved'), ('paid', 'Paid'), ('void', 'Void'),
]


class GovernanceCommissionPlan(models.Model):
    """Role-based commission policy for an organization's governance model."""

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='governance_commission_plans')
    role_code = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    trigger_type = models.CharField(max_length=40, choices=GOVERNANCE_COMMISSION_TRIGGER_CHOICES)
    rate_percent = models.DecimalField(max_digits=7, decimal_places=4)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='governance_commission_plans_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['role_code', 'trigger_type', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['organization', 'role_code', 'trigger_type', 'name'],
                name='unique_governance_commission_plan',
            ),
        ]

    def __str__(self):
        return f"{self.organization.name}: {self.role_code} / {self.name}"


class GovernanceCommissionEntry(models.Model):
    """Auditable calculated commission entry. Calculation inputs cannot change after creation."""

    plan = models.ForeignKey(GovernanceCommissionPlan, on_delete=models.PROTECT, related_name='entries')
    recipient = models.ForeignKey(User, on_delete=models.PROTECT, related_name='governance_commission_entries')
    source_reference = models.CharField(max_length=100)
    source_description = models.CharField(max_length=255, blank=True)
    base_amount = models.DecimalField(max_digits=18, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=GOVERNANCE_COMMISSION_STATUS_CHOICES, default='accrued')
    calculated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='governance_commission_entries_calculated')
    calculated_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-calculated_at']
        constraints = [
            models.UniqueConstraint(fields=['plan', 'source_reference', 'recipient'], name='unique_governance_commission_source'),
        ]

    def __str__(self):
        return f"{self.plan.name}: {self.commission_amount} {self.currency}"


class PlatformTask(models.Model):
    """Unified task layer that can aggregate work across product domains."""

    ASSIGNEE_TYPE_CHOICES = [
        ('user', 'User'),
        ('role', 'Role'),
        ('group', 'Group'),
    ]

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('blocked', 'Blocked'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='platform_tasks')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True, related_name='platform_tasks')
    workspace_id = models.UUIDField(null=True, blank=True)
    domain = models.CharField(max_length=50, default='platform')
    task_type = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    assignee_type = models.CharField(max_length=20, choices=ASSIGNEE_TYPE_CHOICES, default='user')
    assignee_id = models.CharField(max_length=100, blank=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_platform_tasks')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_platform_tasks')
    origin_type = models.CharField(max_length=100, blank=True)
    origin_id = models.CharField(max_length=100, blank=True)
    source_object_type = models.CharField(max_length=100, blank=True)
    source_object_id = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['status', '-created_at']
        indexes = [
            models.Index(fields=['domain', 'status']),
            models.Index(fields=['organization', 'status']),
            models.Index(fields=['workspace_id', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['source_object_type', 'source_object_id']),
            models.Index(fields=['origin_type', 'origin_id']),
            models.Index(fields=['assignee_type', 'assignee_id']),
        ]

    def __str__(self):
        return f"{self.title} [{self.status}]"


# ===== FINANCIAL MODELING MODELS =====

class ModelTemplate(models.Model):
    """Pre-defined financial model templates"""
    TEMPLATE_TYPES = [
        ('dcf', 'Discounted Cash Flow'),
        ('comparable', 'Comparable Companies'),
        ('merger', 'Merger & Acquisition'),
        ('lbo', 'Leveraged Buyout'),
        ('real_estate', 'Real Estate'),
        ('venture', 'Venture Capital'),
        ('distressed', 'Distressed Assets'),
    ]

    name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=50, choices=TEMPLATE_TYPES)
    description = models.TextField()
    industry = models.CharField(max_length=100, blank=True)
    version = models.CharField(max_length=20, default='1.0')
    is_active = models.BooleanField(default=True)
    default_assumptions = models.JSONField(default=dict)
    calculation_logic = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"


class FinancialModel(models.Model):
    """Core financial model instance"""
    MODEL_TYPES = [
        ('dcf', 'DCF'),
        ('comparable', 'Comparable'),
        ('merger', 'Merger'),
        ('lbo', 'LBO'),
        ('real_estate', 'Real Estate'),
        ('venture', 'Venture'),
        ('distressed', 'Distressed'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('calculating', 'Calculating'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]

    # Basic info
    name = models.CharField(max_length=255)
    model_type = models.CharField(max_length=50, choices=MODEL_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Relationships
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='financial_models')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True)
    template = models.ForeignKey(ModelTemplate, on_delete=models.SET_NULL, null=True, blank=True)

    # Model data
    input_data = models.JSONField(default=dict)
    assumptions = models.JSONField(default=dict)
    results = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)

    # Financial metrics
    enterprise_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    equity_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    irr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    moic = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    calculated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.name} ({self.get_model_type_display()})"


class Scenario(models.Model):
    """Scenario analysis for financial models"""
    SCENARIO_TYPES = [
        ('best', 'Best Case'),
        ('base', 'Base Case'),
        ('worst', 'Worst Case'),
        ('custom', 'Custom'),
    ]

    name = models.CharField(max_length=255)
    scenario_type = models.CharField(max_length=20, choices=SCENARIO_TYPES)
    financial_model = models.ForeignKey(FinancialModel, on_delete=models.CASCADE, related_name='scenarios')

    # Scenario parameters
    assumptions_override = models.JSONField(default=dict)
    results = models.JSONField(default=dict)

    # Key metrics
    enterprise_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    irr = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    probability = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.financial_model.name}"


class SensitivityAnalysis(models.Model):
    """Sensitivity analysis for key variables"""
    financial_model = models.ForeignKey(FinancialModel, on_delete=models.CASCADE, related_name='sensitivity_analyses')

    variable_name = models.CharField(max_length=100)
    base_value = models.DecimalField(max_digits=15, decimal_places=4)
    range_min = models.DecimalField(max_digits=15, decimal_places=4)
    range_max = models.DecimalField(max_digits=15, decimal_places=4)
    steps = models.IntegerField(default=10)

    results = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sensitivity: {self.variable_name} - {self.financial_model.name}"


class AIInsight(models.Model):
    """AI-generated insights and recommendations"""
    INSIGHT_TYPES = [
        ('pattern', 'Pattern Recognition'),
        ('anomaly', 'Anomaly Detection'),
        ('trend', 'Trend Analysis'),
        ('benchmark', 'Benchmarking'),
        ('recommendation', 'Recommendation'),
        ('risk', 'Risk Assessment'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    financial_model = models.ForeignKey(FinancialModel, on_delete=models.CASCADE, related_name='ai_insights')
    insight_type = models.CharField(max_length=50, choices=INSIGHT_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')

    title = models.CharField(max_length=255)
    description = models.TextField()
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    supporting_data = models.JSONField(default=dict)
    recommendations = models.JSONField(default=dict)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_insight_type_display()}: {self.title}"


class CustomKPI(models.Model):
    """Custom Key Performance Indicators"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='custom_kpis')
    name = models.CharField(max_length=255)
    formula = models.TextField()  # Formula expression
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=50, blank=True)
    target_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.organization.name})"


class KPICalculation(models.Model):
    """Calculated KPI values over time"""
    kpi = models.ForeignKey(CustomKPI, on_delete=models.CASCADE, related_name='calculations')
    financial_model = models.ForeignKey(FinancialModel, on_delete=models.CASCADE, related_name='kpi_calculations')

    value = models.DecimalField(max_digits=15, decimal_places=4)
    status = models.CharField(max_length=20, choices=[
        ('on_target', 'On Target'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
        ('normal', 'Normal'),
    ], default='normal')

    calculated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-calculated_at']

    def __str__(self):
        return f"{self.kpi.name}: {self.value}"


class Report(models.Model):
    """Generated financial reports"""
    REPORT_TYPES = [
        ('executive', 'Executive Summary'),
        ('detailed', 'Detailed Analysis'),
        ('scenario', 'Scenario Analysis'),
        ('compliance', 'Compliance Report'),
        ('valuation', 'Valuation Report'),
        ('custom', 'Custom Report'),
    ]

    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('html', 'HTML'),
        ('json', 'JSON'),
        ('csv', 'CSV'),
        ('xlsx', 'Excel'),
    ]

    title = models.CharField(max_length=255)
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    financial_model = models.ForeignKey(FinancialModel, on_delete=models.CASCADE, related_name='reports')

    # Report content
    content = models.JSONField(default=dict)
    summary = models.TextField(blank=True)
    recommendations = models.JSONField(default=dict)

    # Export options
    export_format = models.CharField(max_length=10, choices=EXPORT_FORMATS, default='pdf')
    file_path = models.FileField(upload_to='reports/', null=True, blank=True)

    # Metadata
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=False)
    version = models.CharField(max_length=20, default='1.0')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_report_type_display()})"


class Consolidation(models.Model):
    """Multi-entity financial consolidation"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('error', 'Error'),
    ]

    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='consolidations')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Consolidation parameters
    consolidation_date = models.DateField()
    reporting_currency = models.CharField(max_length=3, default='USD')
    include_minority_interest = models.BooleanField(default=True)
    eliminate_intercompany = models.BooleanField(default=True)

    # Results
    consolidated_pnl = models.JSONField(default=dict)
    consolidated_balance_sheet = models.JSONField(default=dict)
    consolidated_cashflow = models.JSONField(default=dict)
    adjustments = models.JSONField(default=dict)

    # Key metrics
    total_assets = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    total_liabilities = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    shareholders_equity = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Consolidation: {self.name} ({self.consolidation_date})"


class ConsolidationEntity(models.Model):
    """Entity included in consolidation"""
    consolidation = models.ForeignKey(Consolidation, on_delete=models.CASCADE, related_name='entities')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE)
    ownership_percentage = models.DecimalField(max_digits=7, decimal_places=4, default=100.0000)
    acquisition_date = models.DateField(null=True, blank=True)
    goodwill = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    # Financial data for consolidation
    pnl_data = models.JSONField(default=dict)
    balance_sheet_data = models.JSONField(default=dict)
    cashflow_data = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.entity.name} ({self.ownership_percentage}%)"


class IntercompanyTransaction(models.Model):
    """Cross-entity accounting transaction with mirrored subledger and journal propagation."""

    TRANSACTION_TYPE_CHOICES = [
        ('invoice', 'Intercompany Invoice'),
        ('loan', 'Intercompany Loan'),
        ('transfer_pricing', 'Transfer Pricing Charge'),
        ('adjustment', 'Intercompany Adjustment'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('eliminated', 'Eliminated'),
        ('cancelled', 'Cancelled'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='intercompany_transactions')
    source_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='intercompany_source_transactions')
    destination_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='intercompany_destination_transactions')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPE_CHOICES)
    reference_number = models.CharField(max_length=100, unique=True)
    transaction_date = models.DateField()
    due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transfer_pricing_markup_percent = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    source_invoice = models.OneToOneField('Invoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='originating_intercompany_transaction')
    destination_bill = models.OneToOneField('Bill', on_delete=models.SET_NULL, null=True, blank=True, related_name='originating_intercompany_transaction')
    destination_loan = models.OneToOneField('Loan', on_delete=models.SET_NULL, null=True, blank=True, related_name='originating_intercompany_transaction')
    source_journal_entry = models.OneToOneField('JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='intercompany_source_transaction')
    destination_journal_entry = models.OneToOneField('JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='intercompany_destination_transaction')
    posted_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='intercompany_transactions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date', '-created_at']
        indexes = [
            models.Index(fields=['organization', 'transaction_type', 'status']),
            models.Index(fields=['source_entity', 'transaction_date']),
            models.Index(fields=['destination_entity', 'transaction_date']),
        ]

    def __str__(self):
        return f"{self.reference_number} - {self.source_entity.name} -> {self.destination_entity.name}"


class IntercompanyEliminationEntry(models.Model):
    """Elimination and consolidation adjustment output generated from intercompany transactions."""

    ELIMINATION_TYPE_CHOICES = [
        ('revenue_expense', 'Revenue and Expense Elimination'),
        ('receivable_payable', 'Receivable and Payable Elimination'),
        ('loan_balance', 'Loan Balance Elimination'),
        ('manual_adjustment', 'Manual Adjustment'),
    ]

    consolidation = models.ForeignKey(Consolidation, on_delete=models.CASCADE, related_name='intercompany_eliminations')
    transaction = models.ForeignKey(IntercompanyTransaction, on_delete=models.CASCADE, related_name='elimination_entries')
    elimination_type = models.CharField(max_length=30, choices=ELIMINATION_TYPE_CHOICES)
    source_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='intercompany_eliminations_out')
    destination_entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='intercompany_eliminations_in')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    adjustment_payload = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consolidation', 'elimination_type']),
            models.Index(fields=['transaction', 'created_at']),
        ]

    def __str__(self):
        return f"{self.consolidation.name} - {self.transaction.reference_number} ({self.elimination_type})"


class TaxCalculation(models.Model):
    """Tax calculations for different jurisdictions"""
    CALCULATION_TYPES = [
        ('corporate', 'Corporate Tax'),
        ('personal', 'Personal Income Tax'),
        ('vat', 'Value Added Tax'),
        ('withholding', 'Withholding Tax'),
        ('property', 'Property Tax'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='tax_calculations')
    tax_year = models.IntegerField()
    calculation_type = models.CharField(max_length=50, choices=CALCULATION_TYPES)
    jurisdiction = models.CharField(max_length=100)
    regime_code = models.CharField(max_length=80, blank=True, default='')
    regime_name = models.CharField(max_length=255, blank=True, default='')
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    calculation_json = models.JSONField(default=dict, blank=True)
    liability_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default='draft')

    # Tax calculation inputs
    taxable_income = models.DecimalField(max_digits=15, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=7, decimal_places=4)
    deductions = models.JSONField(default=dict)
    credits = models.JSONField(default=dict)

    # Results
    calculated_tax = models.DecimalField(max_digits=15, decimal_places=2)
    effective_rate = models.DecimalField(max_digits=7, decimal_places=4)
    breakdown = models.JSONField(default=dict)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entity', 'tax_year', 'calculation_type', 'jurisdiction')

    def __str__(self):
        return f"{self.calculation_type} - {self.entity.name} ({self.tax_year})"


class TaxFiling(models.Model):
    """Tax filing submission record."""

    SUBMISSION_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('ready', 'Ready'),
        ('submitted', 'Submitted'),
        ('due_soon', 'Due Soon'),
        ('late', 'Late'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='tax_filings')
    tax_regime_code = models.CharField(max_length=80)
    period_start = models.DateField()
    period_end = models.DateField()
    form_type = models.CharField(max_length=100)
    form_json = models.JSONField(default=dict, blank=True)
    calculation = models.ForeignKey(TaxCalculation, on_delete=models.SET_NULL, null=True, blank=True, related_name='filings')
    submission_status = models.CharField(max_length=20, choices=SUBMISSION_STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    reference_number = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('entity', 'tax_regime_code', 'period_start', 'period_end')

    def __str__(self):
        return f"{self.tax_regime_code} - {self.entity.name} ({self.period_start} to {self.period_end})"


class TaxAuditLog(models.Model):
    """Immutable audit trail for tax actions."""

    ACTION_TYPE_CHOICES = [
        ('create_profile', 'Create Profile'),
        ('update_profile', 'Update Profile'),
        ('calculate', 'Calculate'),
        ('file', 'File'),
        ('submit', 'Submit'),
        ('reconcile', 'Reconcile'),
        ('rule_change', 'Rule Change'),
        ('status_change', 'Status Change'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='tax_audit_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tax_audit_logs')
    action_type = models.CharField(max_length=50, choices=ACTION_TYPE_CHOICES)
    old_value_json = models.JSONField(default=dict, blank=True)
    new_value_json = models.JSONField(default=dict, blank=True)
    reason = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    device_metadata = models.JSONField(default=dict, blank=True)
    previous_hash = models.CharField(max_length=64, blank=True)
    event_hash = models.CharField(max_length=64, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ['-timestamp']

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('TaxAuditLog entries are immutable.')
        if not self.country and self.entity_id:
            self.country = self.entity.country
        if not self.previous_hash and self.entity_id:
            previous = TaxAuditLog.objects.filter(entity=self.entity).exclude(pk=self.pk).order_by('-timestamp').first()
            self.previous_hash = previous.event_hash if previous else ''
        if not getattr(self, 'timestamp', None):
            self.timestamp = timezone.now()
        if not self.event_hash:
            import hashlib
            import json

            payload = {
                'entity_id': str(self.entity_id or ''),
                'user_id': str(self.user_id or ''),
                'action_type': self.action_type,
                'old_value_json': self.old_value_json,
                'new_value_json': self.new_value_json,
                'reason': self.reason,
                'country': self.country,
                'device_metadata': self.device_metadata,
                'ip_address': self.ip_address,
                'previous_hash': self.previous_hash,
                'timestamp': self.timestamp.isoformat() if self.timestamp else '',
            }
            self.event_hash = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode('utf-8')).hexdigest()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.action_type} - {self.entity.name} ({self.timestamp})"


class TaxRuleSetVersion(models.Model):
    """Versioned tax rule-set governance record."""

    APPROVAL_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('in_review', 'In Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('deployed', 'Deployed'),
        ('expired', 'Expired'),
    ]

    registry = models.ForeignKey(TaxRegimeRegistry, on_delete=models.CASCADE, related_name='rule_versions')
    version_number = models.CharField(max_length=40)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    change_log = models.JSONField(default=list, blank=True)
    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_tax_rule_versions')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_tax_rule_versions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('registry', 'version_number')
        ordering = ['-effective_from', '-created_at']

    def __str__(self):
        return f"{self.registry.regime_code} v{self.version_number}"


class TaxRiskAlert(models.Model):
    """Automated fraud and manipulation alert record."""

    ALERT_TYPE_CHOICES = [
        ('backdated_filing', 'Backdated Filing'),
        ('manipulated_tax_base', 'Manipulated Tax Base'),
        ('duplicate_filing', 'Duplicate Filing'),
        ('suspicious_rule_change', 'Suspicious Rule Change'),
        ('unauthorized_access', 'Unauthorized Access'),
    ]

    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='tax_risk_alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPE_CHOICES)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    title = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    source_model = models.CharField(max_length=120, blank=True)
    source_id = models.CharField(max_length=120, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_tax_risk_alerts')

    class Meta:
        ordering = ['-detected_at']

    def __str__(self):
        return f"{self.alert_type} - {self.entity.name}"


# ============================================================================
# WORKFLOW & AUTOMATION MODELS
# ============================================================================


class RecurringTransaction(models.Model):
    """Template for automatically created recurring bookkeeping transactions.

    Used for items like payroll, rent, subscriptions, depreciation journals, etc.
    """

    FREQUENCY_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
        ("yearly", "Yearly"),
    ]

    # Local copy of transaction type/payment method choices to avoid referencing
    # the Transaction class before it is defined.
    TRANSACTION_TYPE_CHOICES = [
        ("income", "Income"),
        ("expense", "Expense"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("bank", "Bank Transfer"),
        ("wallet", "Wallet"),
        ("cash", "Cash"),
        ("card", "Card Payment"),
        ("cheque", "Cheque"),
        ("other", "Other"),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name="recurring_transactions")
    account = models.ForeignKey('BookkeepingAccount', on_delete=models.PROTECT, related_name="recurring_transactions")
    category = models.ForeignKey('BookkeepingCategory', on_delete=models.PROTECT, related_name="recurring_transactions")

    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="bank")
    description = models.TextField()

    staff_member = models.ForeignKey(EntityStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="recurring_transactions_created")

    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default="monthly")
    next_run_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    max_occurrences = models.IntegerField(null=True, blank=True)
    occurrences_executed = models.IntegerField(default=0)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_active", "next_run_date"]

    def __str__(self):
        return f"{self.get_frequency_display()} {self.get_type_display()} - {self.entity.name}"

    def _frequency_delta_days(self):
        """Approximate frequency in days (used for simple scheduling)."""
        if self.frequency == "daily":
            return 1
        if self.frequency == "weekly":
            return 7
        if self.frequency == "monthly":
            return 30
        if self.frequency == "quarterly":
            return 90
        if self.frequency == "yearly":
            return 365
        return 30

    def is_due(self, as_of_date=None):
        from datetime import date

        if not self.is_active:
            return False

        today = as_of_date or date.today()
        if self.next_run_date and self.next_run_date > today:
            return False

        if self.end_date and today > self.end_date:
            return False

        if self.max_occurrences is not None and self.occurrences_executed >= self.max_occurrences:
            return False

        return True

    def schedule_next(self):
        from datetime import timedelta, date

        base_date = self.next_run_date or date.today()
        delta_days = self._frequency_delta_days()
        self.next_run_date = base_date + timedelta(days=delta_days)
        self.save(update_fields=["next_run_date"])

    def create_transaction(self, run_date=None):
        """Create a concrete Transaction instance from this template."""
        from datetime import date

        if not self.is_due(run_date):
            return None

        transaction_date = run_date or self.next_run_date or date.today()

        transaction = Transaction.objects.create(
            entity=self.entity,
            type=self.type,
            category=self.category,
            account=self.account,
            amount=self.amount,
            currency=self.currency,
            payment_method=self.payment_method,
            description=self.description,
            reference_number=f"AUTO-{self.id}-{self.occurrences_executed + 1}",
            date=transaction_date,
            staff_member=self.staff_member,
            created_by=self.created_by,
        )

        self.occurrences_executed += 1
        self.save(update_fields=["occurrences_executed"])
        self.schedule_next()
        return transaction


class TaskRequest(models.Model):
    """Queue-based task management for digital office workflows.

    Allows users to submit tasks (e.g. generate statements, run tax calcs,
    import bank feeds) and poll for status instead of waiting in a physical
    queue.
    """

    TASK_TYPE_CHOICES = [
        ("generate_statement", "Generate Financial Statement"),
        ("run_tax_calculation", "Run Tax Calculation"),
        ("import_bank_feed", "Import Bank Feed"),
        ("process_payroll", "Process Payroll"),
        ("custom", "Custom Task"),
    ]

    STATUS_CHOICES = [
        ("queued", "Queued"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
        ("cancelled", "Cancelled"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="task_requests")
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, null=True, blank=True, related_name="task_requests")
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="task_requests")

    task_type = models.CharField(max_length=50, choices=TASK_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="normal")

    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "status"]),
            models.Index(fields=["entity", "status"]),
        ]

    def __str__(self):
        return f"{self.get_task_type_display()} [{self.get_status_display()}]"

    def mark_processing(self):
        from django.utils import timezone

        self.status = "processing"
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_completed(self, result=None):
        from django.utils import timezone

        self.status = "completed"
        if result is not None:
            self.result = result
        self.completed_at = timezone.now()
        self.error_message = ""
        self.save(update_fields=["status", "result", "completed_at", "error_message"])

    def mark_failed(self, error_message):
        from django.utils import timezone

        self.status = "failed"
        self.error_message = str(error_message)
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])


# ============================================================================
# BOOKKEEPING MODULE MODELS
# ============================================================================

class BookkeepingCategory(models.Model):
    """Transaction categories for income and expenses"""
    CATEGORY_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bookkeeping_categories')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=CATEGORY_TYPE_CHOICES)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['type', 'name']
        unique_together = ('entity', 'name', 'type')
        verbose_name_plural = 'Bookkeeping Categories'
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class BookkeepingAccount(models.Model):
    """Financial accounts for tracking balances"""
    ACCOUNT_TYPE_CHOICES = [
        ('bank', 'Bank Account'),
        ('wallet', 'Wallet'),
        ('cash', 'Cash'),
    ]
    
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bookkeeping_accounts')
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    account_number = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_active', 'type', 'name']
        unique_together = ('entity', 'name')
    
    def __str__(self):
        return f"{self.name} - {self.currency} {self.balance:,.2f}"


class Transaction(models.Model):
    """Core transaction model for bookkeeping"""
    TRANSACTION_TYPE_CHOICES = [
        ('income', 'Income'),
        ('expense', 'Expense'),
    ]
    
    PAYMENT_METHOD_CHOICES = [
        ('bank', 'Bank Transfer'),
        ('wallet', 'Wallet'),
        ('cash', 'Cash'),
        ('card', 'Card Payment'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]
    
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='transactions')
    type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    category = models.ForeignKey(BookkeepingCategory, on_delete=models.PROTECT, related_name='transactions')
    account = models.ForeignKey(BookkeepingAccount, on_delete=models.PROTECT, related_name='transactions')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    description = models.TextField()
    reference_number = models.CharField(max_length=100, blank=True)
    date = models.DateField()
    attachment_url = models.URLField(blank=True)
    
    # Staff payroll tracking
    staff_member = models.ForeignKey(EntityStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='transactions_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['entity', 'date']),
            models.Index(fields=['entity', 'type']),
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.currency} {self.amount:,.2f} - {self.description[:50]}"
    
    def save(self, *args, **kwargs):
        """Update account balance on transaction save"""
        is_new = self.pk is None
        old_transaction = None
        
        if not is_new:
            old_transaction = Transaction.objects.get(pk=self.pk)
        
        super().save(*args, **kwargs)
        
        # Update account balance
        if is_new:
            if self.type == 'income':
                self.account.balance += self.amount
            else:  # expense
                self.account.balance -= self.amount
            self.account.save()
        elif old_transaction:
            # Reverse old transaction
            if old_transaction.type == 'income':
                old_transaction.account.balance -= old_transaction.amount
            else:
                old_transaction.account.balance += old_transaction.amount
            old_transaction.account.save()
            
            # Apply new transaction
            if self.type == 'income':
                self.account.balance += self.amount
            else:
                self.account.balance -= self.amount
            self.account.save()
    
    def delete(self, *args, **kwargs):
        """Reverse account balance on transaction delete"""
        if self.type == 'income':
            self.account.balance -= self.amount
        else:
            self.account.balance += self.amount
        self.account.save()
        super().delete(*args, **kwargs)


class BookkeepingAuditLog(models.Model):
    """Audit log for all bookkeeping actions"""
    ACTION_CHOICES = [
        ('create_transaction', 'Created Transaction'),
        ('edit_transaction', 'Edited Transaction'),
        ('delete_transaction', 'Deleted Transaction'),
        ('create_category', 'Created Category'),
        ('edit_category', 'Edited Category'),
        ('delete_category', 'Deleted Category'),
        ('create_account', 'Created Account'),
        ('edit_account', 'Edited Account'),
        ('delete_account', 'Deleted Account'),
    ]
    
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bookkeeping_audit_logs')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['entity', 'timestamp']),
            models.Index(fields=['action']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user} - {self.timestamp}"


class FixedAsset(models.Model):
    """Fixed assets with depreciation tracking"""
    DEPRECIATION_METHODS = [
        ('straight_line', 'Straight-Line'),
        ('declining_balance', 'Declining Balance'),
        ('units_of_production', 'Units of Production'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='fixed_assets')
    name = models.CharField(max_length=255)
    asset_type = models.CharField(max_length=100)  # e.g. "Equipment", "Building"
    purchase_date = models.DateField()
    cost = models.DecimalField(max_digits=15, decimal_places=2)
    salvage_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    useful_life_years = models.IntegerField()  # Useful life in years
    depreciation_method = models.CharField(max_length=20, choices=DEPRECIATION_METHODS, default='straight_line')
    accumulated_depreciation = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    book_value = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.asset_type}"

    def calculate_depreciation(self):
        """Calculate annual depreciation amount"""
        if self.depreciation_method == 'straight_line':
            return (self.cost - self.salvage_value) / self.useful_life_years
        return 0


class AccrualEntry(models.Model):
    """Accrual entries for expenses/revenues recognized but not yet paid"""
    ACCRUAL_TYPES = [
        ('revenue', 'Revenue Accrual'),
        ('expense', 'Expense Accrual'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='accrual_entries')
    accrual_type = models.CharField(max_length=20, choices=ACCRUAL_TYPES)
    description = models.CharField(max_length=255)
    category = models.ForeignKey(BookkeepingCategory, on_delete=models.PROTECT, related_name='accruals')
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    accrual_date = models.DateField()
    settlement_date = models.DateField(null=True, blank=True)
    is_settled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-accrual_date']

    def __str__(self):
        return f"{self.get_accrual_type_display()}: {self.description}"


# ============================================================================
# CHART OF ACCOUNTS (COA) & GENERAL LEDGER (GL) MODELS
# ============================================================================

class ChartOfAccounts(models.Model):
    """Chart of Accounts - the backbone of the accounting system"""
    ACCOUNT_TYPE_CHOICES = [
        ('asset', 'Asset'),
        ('liability', 'Liability'),
        ('equity', 'Equity'),
        ('revenue', 'Revenue'),
        ('expense', 'Expense'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='chart_of_accounts')
    account_code = models.CharField(max_length=20)  # e.g., "1000", "2100"
    account_name = models.CharField(max_length=255)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE_CHOICES)
    parent_account = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='sub_accounts')
    currency = models.CharField(max_length=3, default='USD')
    description = models.TextField(blank=True)
    cost_center = models.CharField(max_length=100, blank=True)  # For departmental/cost center tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    current_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'account_code')
        ordering = ['account_code']
        verbose_name_plural = 'Chart of Accounts'

    def __str__(self):
        return f"{self.account_code} - {self.account_name}"


class GeneralLedger(models.Model):
    """General Ledger - master record of all financial activity with double-entry bookkeeping"""
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='general_ledger')
    debit_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='debit_entries')
    credit_account = models.ForeignKey(ChartOfAccounts, on_delete=models.PROTECT, related_name='credit_entries')
    debit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.TextField()
    reference_number = models.CharField(max_length=100)
    posting_date = models.DateField()
    journal_entry = models.ForeignKey('JournalEntry', on_delete=models.CASCADE, related_name='ledger_entries')
    posting_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('posted', 'Posted'), ('reversed', 'Reversed')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['posting_date', 'created_at']
        indexes = [
            models.Index(fields=['entity', 'posting_date']),
            models.Index(fields=['posting_status']),
        ]

    def __str__(self):
        return f"GL: {self.debit_account.account_code} DR {self.debit_amount} / {self.credit_account.account_code} CR {self.credit_amount}"


class JournalEntry(models.Model):
    """Journal Entries - all financial transactions recorded as double-entry journal entries"""
    ENTRY_TYPE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('automated', 'Automated Entry'),
        ('reversal', 'Reversal Entry'),
        ('adjusting', 'Adjusting Entry'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending_review', 'Pending Review'),
        ('pending_approval', 'Pending Approval'),
        ('posted', 'Posted'),
        ('rejected', 'Rejected'),
        ('reversed', 'Reversed'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='journal_entries')
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPE_CHOICES, default='manual')
    reference_number = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    posting_date = models.DateField()
    memo = models.TextField(blank=True)
    amount_total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Approval workflow
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='journal_entries_created')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    # Recurring journal template
    is_recurring = models.BooleanField(default=False)
    recurring_template = models.ForeignKey('RecurringJournalTemplate', on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_entries')

    # Reversal tracking
    reversing_entry = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversed_by')
    original_entry = models.OneToOneField('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='reversal_entry')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['posting_date', '-created_at']
        indexes = [
            models.Index(fields=['entity', 'posting_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.reference_number} - {self.description[:50]}"


class JournalApprovalMatrix(models.Model):
    """Role-based approval matrix for journal entries."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='journal_approval_matrices')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    entry_type = models.CharField(max_length=20, choices=JournalEntry.ENTRY_TYPE_CHOICES, blank=True)
    minimum_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    preparer_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='prepared_journal_matrices')
    reviewer_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='review_journal_matrices')
    approver_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='approve_journal_matrices')
    require_reviewer = models.BooleanField(default=True)
    require_approver = models.BooleanField(default=True)
    allow_self_review = models.BooleanField(default=False)
    allow_self_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['entity', 'minimum_amount', 'name']
        indexes = [
            models.Index(fields=['entity', 'is_active']),
            models.Index(fields=['entity', 'entry_type']),
        ]

    def __str__(self):
        return f"{self.entity.name} - {self.name}"


class JournalApprovalDelegation(models.Model):
    """Delegation of journal approval authority for a bounded window and amount."""

    STAGE_CHOICES = [
        ('reviewer', 'Reviewer'),
        ('approver', 'Approver'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='journal_approval_delegations')
    delegator = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='journal_authority_delegated')
    delegate = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='journal_authority_received')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    minimum_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_delegations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'delegator__last_name']
        indexes = [
            models.Index(fields=['entity', 'stage', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.delegator.full_name} -> {self.delegate.full_name} ({self.stage})"


class JournalEntryApprovalStep(models.Model):
    """Each control step that a journal entry must pass before posting."""

    STAGE_CHOICES = [
        ('preparer', 'Preparer'),
        ('reviewer', 'Reviewer'),
        ('approver', 'Approver'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('skipped', 'Skipped'),
    ]

    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='approval_steps')
    step_order = models.PositiveIntegerField()
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    assigned_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_approval_steps')
    assigned_staff = models.ForeignKey(EntityStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_journal_approval_steps')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    acted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_approval_actions')
    acted_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    delegated_from = models.ForeignKey(JournalApprovalDelegation, on_delete=models.SET_NULL, null=True, blank=True, related_name='acted_steps')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['journal_entry', 'step_order']
        unique_together = ('journal_entry', 'step_order')
        indexes = [
            models.Index(fields=['journal_entry', 'status']),
            models.Index(fields=['assigned_role', 'status']),
        ]

    def __str__(self):
        return f"{self.journal_entry.reference_number} - {self.stage} ({self.status})"


class JournalEntryChangeLog(models.Model):
    """Immutable journal workflow and change-management log."""

    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('reversed', 'Reversed'),
        ('period_locked', 'Blocked By Period Lock'),
        ('matrix_applied', 'Approval Matrix Applied'),
    ]

    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='change_logs')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='journal_change_logs')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='journal_change_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    stage = models.CharField(max_length=20, blank=True)
    details = models.TextField(blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['journal_entry', 'created_at']),
            models.Index(fields=['entity', 'action']),
        ]

    def __str__(self):
        return f"{self.journal_entry.reference_number} - {self.action}"


ACCOUNTING_APPROVAL_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('pending_review', 'Pending Review'),
    ('pending_approval', 'Pending Approval'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
]

ACCOUNTING_APPROVAL_STAGE_CHOICES = [
    ('preparer', 'Preparer'),
    ('reviewer', 'Reviewer'),
    ('approver', 'Approver'),
]

ACCOUNTING_APPROVAL_STEP_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('skipped', 'Skipped'),
]

ACCOUNTING_APPROVAL_OBJECT_CHOICES = [
    ('purchase_order', 'Purchase Order'),
    ('bill', 'Bill'),
    ('bill_payment', 'Bill Payment'),
    ('payment', 'Customer Payment'),
    ('payroll_run', 'Payroll Run'),
]


class AccountingApprovalMatrix(models.Model):
    """Role-based approval matrix for non-journal accounting objects."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='accounting_approval_matrices')
    name = models.CharField(max_length=255)
    object_type = models.CharField(max_length=30, choices=ACCOUNTING_APPROVAL_OBJECT_CHOICES)
    description = models.TextField(blank=True)
    minimum_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    preparer_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='prepared_accounting_matrices')
    reviewer_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='review_accounting_matrices')
    approver_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='approve_accounting_matrices')
    require_reviewer = models.BooleanField(default=True)
    require_approver = models.BooleanField(default=True)
    allow_self_review = models.BooleanField(default=False)
    allow_self_approval = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['entity', 'object_type', 'minimum_amount', 'name']
        indexes = [
            models.Index(fields=['entity', 'object_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.entity.name} - {self.name} ({self.object_type})"


class AccountingApprovalDelegation(models.Model):
    """Delegation of approval authority for supported accounting objects."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='accounting_approval_delegations')
    object_type = models.CharField(max_length=30, choices=ACCOUNTING_APPROVAL_OBJECT_CHOICES, blank=True)
    delegator = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='accounting_authority_delegated')
    delegate = models.ForeignKey(EntityStaff, on_delete=models.CASCADE, related_name='accounting_authority_received')
    stage = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STAGE_CHOICES)
    minimum_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    maximum_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_delegations_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', 'delegator__last_name']
        indexes = [
            models.Index(fields=['entity', 'object_type', 'stage', 'is_active']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.delegator.full_name} -> {self.delegate.full_name} ({self.stage})"


class AccountingApprovalRecord(models.Model):
    """Approval workflow state for supported accounting objects."""

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='accounting_approval_records')
    object_type = models.CharField(max_length=30, choices=ACCOUNTING_APPROVAL_OBJECT_CHOICES)
    object_id = models.PositiveIntegerField()
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STATUS_CHOICES, default='draft')
    requested_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_approvals_requested')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_approvals_approved')
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ('object_type', 'object_id')
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['object_type', 'object_id']),
        ]

    def __str__(self):
        return f"{self.get_object_type_display()} - {self.title}"


class AccountingApprovalStep(models.Model):
    """Approval steps for supported accounting objects."""

    approval = models.ForeignKey(AccountingApprovalRecord, on_delete=models.CASCADE, related_name='steps')
    step_order = models.PositiveIntegerField()
    stage = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STAGE_CHOICES)
    assigned_role = models.ForeignKey(EntityRole, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_approval_steps')
    assigned_staff = models.ForeignKey(EntityStaff, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_accounting_approval_steps')
    status = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STEP_STATUS_CHOICES, default='pending')
    acted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_approval_actions')
    acted_at = models.DateTimeField(null=True, blank=True)
    comments = models.TextField(blank=True)
    delegated_from = models.ForeignKey(AccountingApprovalDelegation, on_delete=models.SET_NULL, null=True, blank=True, related_name='acted_steps')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['approval', 'step_order']
        unique_together = ('approval', 'step_order')
        indexes = [
            models.Index(fields=['approval', 'status']),
            models.Index(fields=['assigned_role', 'status']),
        ]

    def __str__(self):
        return f"{self.approval.title} - {self.stage} ({self.status})"


class AccountingApprovalChangeLog(models.Model):
    """Immutable approval and change-management log for supported accounting objects."""

    ACTION_CHOICES = [
        ('created', 'Created'),
        ('updated', 'Updated'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('executed', 'Executed'),
        ('period_locked', 'Blocked By Period Lock'),
        ('matrix_applied', 'Approval Matrix Applied'),
    ]

    approval = models.ForeignKey(AccountingApprovalRecord, on_delete=models.CASCADE, related_name='change_logs')
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='accounting_change_logs')
    actor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_change_logs')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    stage = models.CharField(max_length=20, blank=True)
    details = models.TextField(blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['approval', 'created_at']),
            models.Index(fields=['entity', 'action']),
        ]

    def __str__(self):
        return f"{self.approval.title} - {self.action}"


class RecurringJournalTemplate(models.Model):
    """Recurring Journal Entry Templates - for automated periodic entries"""
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('yearly', 'Yearly'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='recurring_journal_templates')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    next_posting_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Template line items stored as JSON
    journal_lines = models.JSONField(default=dict)  # [{debit_account_id, credit_account_id, amount}, ...]

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recurring_journal_templates_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['next_posting_date']

    def __str__(self):
        return f"{self.name} ({self.get_frequency_display()})"


class LedgerPeriod(models.Model):
    """Accounting periods - for period-based operations (opening, closing)"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('pending_close', 'Pending Close'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='ledger_periods')
    period_name = models.CharField(max_length=100)  # e.g., "January 2025", "Q1 2025"
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    no_posting_after = models.DateField(null=True, blank=True)  # Lock period after this date
    
    created_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ledger_periods_closed')

    class Meta:
        unique_together = ('entity', 'start_date', 'end_date')
        ordering = ['start_date']

    def __str__(self):
        return f"{self.entity.name} - {self.period_name}"


# ============================================================================
# SALES & RECEIVABLES (AR) MODELS
# ============================================================================

class Customer(models.Model):
    """Customer records for Accounts Receivable"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('dormant', 'Dormant'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='customers')
    customer_code = models.CharField(max_length=50, unique=True)
    customer_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    contact_person = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)  # Customer's tax ID
    
    payment_terms = models.IntegerField(default=30)  # Days
    currency = models.CharField(max_length=3, default='USD')
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['customer_name']
        unique_together = ('entity', 'customer_code')

    def __str__(self):
        return f"{self.customer_code} - {self.customer_name}"


class Invoice(models.Model):
    """Sales invoices for Accounts Receivable"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='invoices')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='invoices')
    
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    outstanding_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='invoices_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'invoice_number')
        ordering = ['-invoice_date']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number}"


class InvoiceLineItem(models.Model):
    """Line items on an invoice"""
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=7, decimal_places=4, default=0)
    line_amount = models.DecimalField(max_digits=15, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.description} x {self.quantity}"


class CreditNote(models.Model):
    """Credit notes for reducing AR"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('applied', 'Applied'),
        ('cancelled', 'Cancelled'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='credit_notes')
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_notes')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='credit_notes')
    
    credit_note_number = models.CharField(max_length=50, unique=True)
    credit_date = models.DateField()
    
    reason = models.TextField()
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='credit_notes_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entity', 'credit_note_number')
        ordering = ['-credit_date']

    def __str__(self):
        return f"Credit Note {self.credit_note_number}"


class Payment(models.Model):
    """Customer payments for invoices"""
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
        ('cheque', 'Cheque'),
        ('other', 'Other'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='payments')
    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='payments')
    
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    approval_status = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STATUS_CHOICES, default='draft')
    approval_submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments_created')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Payment - {self.amount} on {self.payment_date}"


# ============================================================================
# PURCHASES & PAYABLES (AP) MODELS
# ============================================================================

class Vendor(models.Model):
    """Vendor records for Accounts Payable"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_hold', 'On Hold'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='vendors')
    vendor_code = models.CharField(max_length=50, unique=True)
    vendor_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    
    contact_person = models.CharField(max_length=255, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    service_description = models.TextField(blank=True)
    
    payment_terms = models.IntegerField(default=30)  # Days
    currency = models.CharField(max_length=3, default='USD')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['vendor_name']
        unique_together = ('entity', 'vendor_code')

    def _generate_vendor_code(self):
        base = f"VEN-{self.entity_id or 0}"
        sequence = Vendor.objects.filter(entity_id=self.entity_id).count() + 1

        while True:
            candidate = f"{base}-{sequence:04d}"
            if not Vendor.objects.filter(vendor_code=candidate).exclude(pk=self.pk).exists():
                return candidate
            sequence += 1

    def save(self, *args, **kwargs):
        if not self.vendor_code:
            self.vendor_code = self._generate_vendor_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.vendor_code} - {self.vendor_name}"


class PurchaseOrder(models.Model):
    """Purchase orders for vendor management"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('partially_received', 'Partially Received'),
        ('received', 'Received'),
        ('cancelled', 'Cancelled'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='purchase_orders')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='purchase_orders')
    
    po_number = models.CharField(max_length=50, unique=True)
    po_date = models.DateField()
    expected_delivery_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approval_status = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STATUS_CHOICES, default='draft')
    approval_submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchase_orders_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='purchase_orders_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'po_number')
        ordering = ['-po_date']

    def __str__(self):
        return f"PO {self.po_number}"


class Bill(models.Model):
    """Supplier bills/invoices for Accounts Payable"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bills')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='bills')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills')
    
    bill_number = models.CharField(max_length=50, unique=True)
    bill_date = models.DateField()
    due_date = models.DateField()
    
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    paid_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    outstanding_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    currency = models.CharField(max_length=3, default='USD')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approval_status = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STATUS_CHOICES, default='draft')
    approval_submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bills_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='bills_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('entity', 'bill_number')
        ordering = ['-bill_date']
        indexes = [
            models.Index(fields=['entity', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"Bill {self.bill_number}"


class BillPayment(models.Model):
    """Payments made to vendors for bills"""
    PAYMENT_METHOD_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
        ('credit_card', 'Credit Card'),
        ('other', 'Other'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bill_payments')
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT, related_name='payments')
    vendor = models.ForeignKey(Vendor, on_delete=models.PROTECT, related_name='bill_payments')
    
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_number = models.CharField(max_length=100, blank=True)
    approval_status = models.CharField(max_length=20, choices=ACCOUNTING_APPROVAL_STATUS_CHOICES, default='draft')
    approval_submitted_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bill_payments_approved')
    approved_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bill_payments_created')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-payment_date']

    def __str__(self):
        return f"Bill Payment - {self.amount} on {self.payment_date}"


# ============================================================================
# INVENTORY ACCOUNTING MODELS
# ============================================================================

class InventoryItem(models.Model):
    """Inventory SKU definitions"""
    VALUATION_METHODS = [
        ('fifo', 'FIFO'),
        ('lifo', 'LIFO'),
        ('weighted_avg', 'Weighted Average'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='inventory_items')
    sku = models.CharField(max_length=100, unique=True)
    item_name = models.CharField(max_length=255)
    item_code = models.CharField(max_length=50, unique=True)
    
    description = models.TextField(blank=True)
    category = models.CharField(max_length=100)
    unit_of_measure = models.CharField(max_length=20)  # e.g., "pc", "kg", "L"
    
    quantity_on_hand = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=15, decimal_places=2)
    reorder_quantity = models.DecimalField(max_digits=15, decimal_places=2)
    
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2)
    valuation_method = models.CharField(max_length=20, choices=VALUATION_METHODS, default='fifo')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['item_name']
        unique_together = ('entity', 'sku')

    def __str__(self):
        return f"{self.sku} - {self.item_name}"


class InventoryTransaction(models.Model):
    """All inventory movements"""
    TRANSACTION_TYPE_CHOICES = [
        ('purchase', 'Purchase'),
        ('sale', 'Sale'),
        ('adjustment', 'Adjustment'),
        ('return', 'Return'),
        ('transfer', 'Transfer'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='inventory_transactions')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='transactions')
    
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    transaction_date = models.DateField()
    
    quantity_before = models.DecimalField(max_digits=15, decimal_places=2)
    quantity = models.DecimalField(max_digits=15, decimal_places=2)  # Positive for IN, Negative for OUT
    quantity_after = models.DecimalField(max_digits=15, decimal_places=2)
    
    unit_cost = models.DecimalField(max_digits=15, decimal_places=2)
    total_cost = models.DecimalField(max_digits=15, decimal_places=2)
    
    reference_number = models.CharField(max_length=100, blank=True)  # Invoice, PO, etc.
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='inventory_transactions_created')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date']
        indexes = [
            models.Index(fields=['entity', 'transaction_date']),
            models.Index(fields=['inventory_item']),
        ]

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.inventory_item.sku} x {self.quantity}"


class InventoryCostOfGoodsSold(models.Model):
    """COGS calculation for inventory"""
    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='inventory_cogs')
    period_start = models.DateField()
    period_end = models.DateField()
    
    opening_inventory = models.DecimalField(max_digits=15, decimal_places=2)
    purchases = models.DecimalField(max_digits=15, decimal_places=2)
    closing_inventory = models.DecimalField(max_digits=15, decimal_places=2)
    cogs = models.DecimalField(max_digits=15, decimal_places=2)  # Opening + Purchases - Closing
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('entity', 'period_start', 'period_end')
        ordering = ['-period_end']

    def __str__(self):
        return f"COGS {self.entity.name} - {self.period_start} to {self.period_end}"


# ============================================================================
# RECONCILIATION MODELS
# ============================================================================

class BankReconciliation(models.Model):
    """Bank reconciliation"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('reconciled', 'Reconciled'),
        ('unreconciled', 'Unreconciled'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='bank_reconciliations')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, related_name='reconciliations')
    
    reconciliation_date = models.DateField()
    bank_statement_balance = models.DecimalField(max_digits=15, decimal_places=2)
    book_balance = models.DecimalField(max_digits=15, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    variance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    reconciled_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='bank_reconciliations')
    reconciled_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-reconciliation_date']
        unique_together = ('entity', 'bank_account', 'reconciliation_date')

    def __str__(self):
        return f"Bank Reconciliation - {self.bank_account.account_name} ({self.reconciliation_date})"


# ============================================================================
# REVENUE RECOGNITION & DEFERRED REVENUE MODELS
# ============================================================================

class DeferredRevenue(models.Model):
    """Deferred revenue for accrual accounting"""
    STATUS_CHOICES = [
        ('deferred', 'Deferred'),
        ('recognizing', 'Recognizing'),
        ('recognized', 'Fully Recognized'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='deferred_revenues')
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='deferred_revenues')
    
    contract_number = models.CharField(max_length=100)
    contract_start_date = models.DateField()
    contract_end_date = models.DateField()
    
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    recognized_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    remaining_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='deferred')
    
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-contract_start_date']

    def __str__(self):
        return f"Deferred Revenue - {self.contract_number}"


class RevenueRecognitionSchedule(models.Model):
    """Schedule for recognizing deferred revenue"""
    deferred_revenue = models.ForeignKey(DeferredRevenue, on_delete=models.CASCADE, related_name='recognition_schedule')
    
    recognition_period_start = models.DateField()
    recognition_period_end = models.DateField()
    recognition_date = models.DateField()
    
    amount_to_recognize = models.DecimalField(max_digits=15, decimal_places=2)
    
    is_recognized = models.BooleanField(default=False)
    recognized_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('deferred_revenue', 'recognition_period_start')
        ordering = ['recognition_date']

    def __str__(self):
        return f"Revenue Recognition - {self.deferred_revenue.contract_number} ({self.recognition_period_start})"


# ============================================================================
# PERIOD CLOSE & ADJUSTMENT MODELS
# ============================================================================

class PeriodCloseChecklist(models.Model):
    """Checklist for period-end closing"""
    STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='close_checklists')
    period = models.ForeignKey(LedgerPeriod, on_delete=models.CASCADE, related_name='close_checklist')
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='not_started')
    
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('entity', 'period')

    def __str__(self):
        return f"Close Checklist - {self.entity.name} ({self.period.period_name})"


class PeriodCloseItem(models.Model):
    """Individual items in the close checklist"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    checklist = models.ForeignKey(PeriodCloseChecklist, on_delete=models.CASCADE, related_name='items')
    
    task_name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sequence = models.IntegerField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    responsible_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['sequence']

    def __str__(self):
        return f"{self.task_name}"


# ============================================================================
# MULTI-CURRENCY & FX MODELS
# ============================================================================

class ExchangeRate(models.Model):
    """Historical and current exchange rates"""
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    rate = models.DecimalField(max_digits=15, decimal_places=6)
    rate_date = models.DateField()
    source = models.CharField(max_length=100, blank=True)  # e.g., "ECB", "Fed", "Manual"
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('from_currency', 'to_currency', 'rate_date')
        ordering = ['-rate_date']

    def __str__(self):
        return f"{self.from_currency}/{self.to_currency} @ {self.rate} on {self.rate_date}"


class FXGainLoss(models.Model):
    """Realized and unrealized FX gains/losses"""
    GAIN_TYPE_CHOICES = [
        ('realized', 'Realized'),
        ('unrealized', 'Unrealized'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='fx_gainloss')
    
    transaction = models.ForeignKey(Transaction, on_delete=models.PROTECT, null=True, blank=True, related_name='fx_gainloss')
    
    from_currency = models.CharField(max_length=3)
    to_currency = models.CharField(max_length=3)
    
    original_amount = models.DecimalField(max_digits=15, decimal_places=2)
    original_rate = models.DecimalField(max_digits=15, decimal_places=6)
    original_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    current_rate = models.DecimalField(max_digits=15, decimal_places=6)
    current_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    gain_loss_amount = models.DecimalField(max_digits=15, decimal_places=2)
    gain_type = models.CharField(max_length=20, choices=GAIN_TYPE_CHOICES)
    
    transaction_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"FX {self.gain_type.title()} - {self.from_currency}/{self.to_currency}: {self.gain_loss_amount}"


# ============================================================================
# NOTIFICATION & ALERT MODELS
# ============================================================================

class Notification(models.Model):
    """System notifications and alerts"""
    NOTIFICATION_TYPE_CHOICES = [
        ('budget_alert', 'Budget Alert'),
        ('deadline_reminder', 'Deadline Reminder'),
        ('payment_due', 'Payment Due'),
        ('approval_request', 'Approval Request'),
        ('error', 'Error Alert'),
        ('system', 'System Message'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    STATUS_CHOICES = [
        ('unread', 'Unread'),
        ('read', 'Read'),
        ('archived', 'Archived'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='notifications')
    
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='unread')
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    related_entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)
    related_content_type = models.CharField(max_length=100, blank=True)  # e.g., "Invoice", "Bill"
    related_object_id = models.CharField(max_length=100, blank=True)
    
    action_url = models.URLField(blank=True)
    
    read_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['organization', 'sent_at']),
        ]

    def __str__(self):
        return f"{self.get_notification_type_display()}: {self.title}"


class NotificationPreference(models.Model):
    """User notification preferences"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    email_budget_alerts = models.BooleanField(default=True)
    email_deadline_reminders = models.BooleanField(default=True)
    email_payment_due = models.BooleanField(default=True)
    email_approval_requests = models.BooleanField(default=True)
    
    sms_budget_alerts = models.BooleanField(default=False)
    sms_deadline_reminders = models.BooleanField(default=True)
    sms_payment_due = models.BooleanField(default=True)
    
    in_app_all = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Notification preferences for {self.user.email}"


# ============ CLIENT MANAGEMENT FEATURES ============

class Client(models.Model):
    """Client profile for accounting firms"""
    STATUS_CHOICES = [
        ('prospect', 'Prospect'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('terminated', 'Terminated'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='clients')
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=100)
    industry = models.CharField(max_length=100, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_id = models.CharField(max_length=100, blank=True)
    contact_person = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    website = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='prospect')
    assigned_accountant = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_clients')
    monthly_fee = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, default='USD')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('organization', 'email')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class ClientPortal(models.Model):
    """Portal access for clients"""
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='portal')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_portal')
    portal_slug = models.SlugField(unique=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Portal: {self.client.name}"


class ClientMessage(models.Model):
    """Secure messaging between accountants and clients"""
    MESSAGE_TYPE_CHOICES = [
        ('message', 'Message'),
        ('document_request', 'Document Request'),
        ('approval_request', 'Approval Request'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='messages')
    from_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='sent_client_messages')
    to_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='received_client_messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPE_CHOICES, default='message')
    subject = models.CharField(max_length=255)
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    is_urgent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject}"


class ClientDocument(models.Model):
    """Document management for clients"""
    DOCUMENT_TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('receipt', 'Receipt'),
        ('statement', 'Statement'),
        ('tax_document', 'Tax Document'),
        ('form', 'Form'),
        ('proof', 'Proof'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('archived', 'Archived'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='documents')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='client_documents')
    document_type = models.CharField(max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    file_url = models.FileField(upload_to='client_documents/%Y/%m/%d/')
    file_size = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_documents')
    review_notes = models.TextField(blank=True)
    tags = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.client.name}"


class DocumentRequest(models.Model):
    """Request for documents from clients"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='document_requests')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT)
    document_type = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField()
    reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-due_date', '-created_at']

    def __str__(self):
        return f"{self.document_type} - {self.client.name}"


class ApprovalRequest(models.Model):
    """Approval workflow for client data/transactions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    TYPE_CHOICES = [
        ('invoice', 'Invoice'),
        ('payment', 'Payment'),
        ('adjustment', 'Adjustment'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='approval_requests')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    request_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    request_data = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    requested_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='+')
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_requests')
    rejection_reason = models.TextField(blank=True)
    due_date = models.DateField()
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.request_type}: {self.client.name}"


# ============ DOCUMENT MANAGEMENT ============

class DocumentTemplate(models.Model):
    """Reusable document templates"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='document_templates')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    template_content = models.TextField()
    category = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ============ LOAN MANAGEMENT ============

class Loan(models.Model):
    """Loan tracking for entities"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paid_off', 'Paid Off'),
        ('defaulted', 'Defaulted'),
        ('refinanced', 'Refinanced'),
    ]

    LOAN_TYPE_CHOICES = [
        ('term_loan', 'Term Loan'),
        ('line_of_credit', 'Line of Credit'),
        ('equipment', 'Equipment Financing'),
        ('real_estate', 'Real Estate'),
        ('other', 'Other'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='loans')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    lender_name = models.CharField(max_length=255)
    loan_type = models.CharField(max_length=50, choices=LOAN_TYPE_CHOICES)
    loan_amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    interest_rate = models.DecimalField(max_digits=6, decimal_places=3)
    start_date = models.DateField()
    maturity_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    principal_remaining = models.DecimalField(max_digits=15, decimal_places=2)
    monthly_payment = models.DecimalField(max_digits=15, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.loan_type}: {self.lender_name}"


class LoanPayment(models.Model):
    """Loan repayment schedule and payments"""
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='payments')
    payment_number = models.IntegerField()
    payment_date = models.DateField()
    principal_paid = models.DecimalField(max_digits=15, decimal_places=2)
    interest_paid = models.DecimalField(max_digits=15, decimal_places=2)
    total_paid = models.DecimalField(max_digits=15, decimal_places=2)
    principal_remaining = models.DecimalField(max_digits=15, decimal_places=2)
    status = models.CharField(max_length=20, default='scheduled')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['payment_number']
        unique_together = ('loan', 'payment_number')

    def __str__(self):
        return f"Payment {self.payment_number}: {self.loan.lender_name}"


# ============ COMPLIANCE & KYC/AML ============

class KYCProfile(models.Model):
    """KYC (Know Your Customer) profile for clients/entities"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]

    entity = models.OneToOneField(Entity, on_delete=models.CASCADE, related_name='kyc_profile', null=True, blank=True)
    client = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='kyc_profile', null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    # Basic KYC Data
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    beneficial_owners = models.JSONField(default=list, blank=True)
    verification_date = models.DateField(null=True, blank=True)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    
    # Documents
    id_document_url = models.FileField(upload_to='kyc/id_documents/', blank=True)
    proof_of_address_url = models.FileField(upload_to='kyc/proof_of_address/', blank=True)
    business_registration_url = models.FileField(upload_to='kyc/business_registration/', blank=True)
    
    rejection_reason = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.entity:
            return f"KYC: {self.entity.name}"
        return f"KYC: {self.client.name}"


class AMLTransaction(models.Model):
    """AML (Anti-Money Laundering) monitoring"""
    RISK_LEVEL_CHOICES = [
        ('low', 'Low Risk'),
        ('medium', 'Medium Risk'),
        ('high', 'High Risk'),
        ('critical', 'Critical Risk'),
    ]

    STATUS_CHOICES = [
        ('flagged', 'Flagged'),
        ('investigating', 'Under Investigation'),
        ('cleared', 'Cleared'),
        ('reported', 'Reported'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='aml_transactions', null=True, blank=True)
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='aml_flags', null=True, blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    transaction_date = models.DateTimeField()
    transaction_type = models.CharField(max_length=50)
    
    risk_level = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='flagged')
    
    reason = models.TextField()
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"AML Flag: {self.amount} {self.currency}"


# ============ BILLING & FIRM MANAGEMENT ============

class FirmService(models.Model):
    """Services offered by accounting firm"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    billing_frequency = models.CharField(max_length=50, choices=[
        ('one_time', 'One Time'),
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class ClientInvoice(models.Model):
    """Invoices sent to clients by accounting firm"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('viewed', 'Viewed'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='invoices')
    invoice_number = models.CharField(max_length=100, unique=True)
    currency = models.CharField(max_length=3, default='USD')
    
    issue_date = models.DateField()
    due_date = models.DateField()
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    payment_received = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    payment_date = models.DateField(null=True, blank=True)
    
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    sent_at = models.DateTimeField(null=True, blank=True)
    viewed_at = models.DateTimeField(null=True, blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-issue_date']
        unique_together = ('organization', 'invoice_number')

    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.client.name}"


class ClientInvoiceLineItem(models.Model):
    """Line items in client invoices"""
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.CASCADE, related_name='line_items')
    service = models.ForeignKey(FirmService, on_delete=models.SET_NULL, null=True, blank=True)
    description = models.CharField(max_length=500)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=15, decimal_places=2)
    total_price = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return f"{self.description} - {self.invoice.invoice_number}"


class ClientSubscription(models.Model):
    """Recurring subscription for clients"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='subscriptions')
    service = models.ForeignKey(FirmService, on_delete=models.PROTECT)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    next_billing_date = models.DateField()
    
    auto_renew = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.service.name} - {self.client.name}"


# ============ WHITE-LABELING ============

class WhiteLabelBranding(models.Model):
    """White-label branding for accounting firms"""
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name='white_label_branding')
    
    primary_color = models.CharField(max_length=7, default='#667eea')
    secondary_color = models.CharField(max_length=7, default='#764ba2')
    accent_color = models.CharField(max_length=7, default='#f093fb')
    
    logo_url = models.FileField(upload_to='white_label/logos/', blank=True)
    logo_light_url = models.FileField(upload_to='white_label/logos/', blank=True)
    logo_dark_url = models.FileField(upload_to='white_label/logos/', blank=True)
    
    favicon_url = models.FileField(upload_to='white_label/favicons/', blank=True)
    
    custom_domain = models.CharField(max_length=255, blank=True, null=True, unique=True)
    
    portal_name = models.CharField(max_length=255)
    portal_description = models.TextField(blank=True)
    
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=20, blank=True)
    
    font_family = models.CharField(max_length=100, default='Inter')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"White Label: {self.organization.name}"


# ============ EMBEDDED BANKING & PAYMENTS ============

class BankingIntegration(models.Model):
    """Banking API integrations"""
    INTEGRATION_TYPE_CHOICES = [
        ('open_banking', 'Open Banking'),
        ('payment_processor', 'Payment Processor'),
        ('financial_data', 'Financial Data Aggregator'),
        ('loan_provider', 'Loan Provider'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('pending', 'Pending Activation'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='banking_integrations')
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_integrations')
    integration_type = models.CharField(max_length=50, choices=INTEGRATION_TYPE_CHOICES)
    provider_code = models.CharField(max_length=50, default='custom')
    provider_name = models.CharField(max_length=255)
    
    api_key = models.CharField(max_length=500, blank=True)
    api_secret = models.CharField(max_length=500, blank=True)
    access_token_encrypted = models.TextField(blank=True)
    refresh_token_encrypted = models.TextField(blank=True)
    webhook_signing_secret_encrypted = models.TextField(blank=True)
    webhook_url = models.URLField(blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_active = models.BooleanField(default=True)
    
    last_sync = models.DateTimeField(null=True, blank=True)
    last_webhook_at = models.DateTimeField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    token_last_rotated_at = models.DateTimeField(null=True, blank=True)
    consent_reference = models.CharField(max_length=100, blank=True)
    consent_scopes = models.JSONField(default=list, blank=True)
    consent_granted_at = models.DateTimeField(null=True, blank=True)
    consent_revoked_at = models.DateTimeField(null=True, blank=True)
    consent_metadata = models.JSONField(default=dict, blank=True)
    failure_count = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.provider_name} - {self.organization.name}"

    @property
    def has_access_token(self):
        return bool(self.access_token_encrypted)

    def set_api_key(self, value):
        from .banking_security import encrypt_secret
        self.api_key = encrypt_secret(value) if value else ''

    def get_api_key(self):
        from .banking_security import decrypt_secret
        return decrypt_secret(self.api_key)

    def set_api_secret(self, value):
        from .banking_security import encrypt_secret
        self.api_secret = encrypt_secret(value) if value else ''

    def get_api_secret(self):
        from .banking_security import decrypt_secret
        return decrypt_secret(self.api_secret)

    def set_access_token(self, value):
        from .banking_security import encrypt_secret
        self.access_token_encrypted = encrypt_secret(value) if value else ''

    def get_access_token(self):
        from .banking_security import decrypt_secret
        return decrypt_secret(self.access_token_encrypted)

    def set_refresh_token(self, value):
        from .banking_security import encrypt_secret
        self.refresh_token_encrypted = encrypt_secret(value) if value else ''

    def get_refresh_token(self):
        from .banking_security import decrypt_secret
        return decrypt_secret(self.refresh_token_encrypted)

    def set_webhook_signing_secret(self, value):
        from .banking_security import encrypt_secret
        self.webhook_signing_secret_encrypted = encrypt_secret(value) if value else ''

    def get_webhook_signing_secret(self):
        from .banking_security import decrypt_secret
        return decrypt_secret(self.webhook_signing_secret_encrypted)


class BankingConsentLog(models.Model):
    """Auditable record of explicit user consent for bank data access."""

    STATUS_CHOICES = [
        ('requested', 'Requested'),
        ('granted', 'Granted'),
        ('revoked', 'Revoked'),
        ('failed', 'Failed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='banking_consent_logs')
    integration = models.ForeignKey(BankingIntegration, on_delete=models.CASCADE, related_name='consent_logs')
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_consent_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_consent_logs')
    provider_code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')
    redirect_uri = models.URLField(blank=True)
    state = models.CharField(max_length=100, db_index=True)
    scopes = models.JSONField(default=list, blank=True)
    consent_reference = models.CharField(max_length=100, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['integration', 'requested_at']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        return f"Consent {self.status} for {self.integration.provider_name} ({self.organization.name})"


class BankingSyncRun(models.Model):
    """Execution log for manual, webhook, and scheduled bank synchronizations."""

    TRIGGER_TYPE_CHOICES = [
        ('manual', 'Manual'),
        ('scheduled', 'Scheduled'),
        ('webhook', 'Webhook'),
    ]

    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]

    integration = models.ForeignKey(BankingIntegration, on_delete=models.CASCADE, related_name='sync_runs')
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_sync_runs')
    initiated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_sync_runs')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_TYPE_CHOICES, default='manual')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    request_payload = models.JSONField(default=dict, blank=True)
    response_payload = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    accounts_processed = models.PositiveIntegerField(default=0)
    transactions_processed = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['integration', 'started_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Sync {self.trigger_type} {self.status} for {self.integration.provider_name}"


class BankingCategorizationRule(models.Model):
    """Rules that classify imported bank transactions into expense buckets."""

    MATCH_TYPE_CHOICES = [
        ('exact', 'Exact'),
        ('contains', 'Contains'),
        ('regex', 'Regex'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='banking_categorization_rules')
    merchant_pattern = models.CharField(max_length=255, blank=True)
    description_pattern = models.CharField(max_length=255, blank=True)
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default='contains')
    category_name = models.CharField(max_length=255)
    dashboard_bucket = models.CharField(max_length=255, blank=True)
    priority = models.PositiveIntegerField(default=100)
    is_active = models.BooleanField(default=True)
    learned_from_user = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_rules_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_rules_updated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-priority', 'merchant_pattern', 'description_pattern']
        indexes = [
            models.Index(fields=['entity', 'is_active']),
            models.Index(fields=['entity', 'category_name']),
        ]

    def __str__(self):
        pattern = self.merchant_pattern or self.description_pattern or 'rule'
        return f"{pattern} -> {self.category_name}"


class BankingTransaction(models.Model):
    """Real-time banking transactions from integrated banks"""
    TRANSACTION_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='banking_transactions')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.CASCADE)
    integration = models.ForeignKey(BankingIntegration, on_delete=models.CASCADE, null=True, blank=True, related_name='transactions')
    sync_run = models.ForeignKey(BankingSyncRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    
    transaction_id = models.CharField(max_length=255, unique=True)
    transaction_date = models.DateTimeField()
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3)
    
    description = models.CharField(max_length=500)
    merchant_name = models.CharField(max_length=255, blank=True)
    raw_category = models.CharField(max_length=255, blank=True)
    normalized_category = models.CharField(max_length=255, blank=True)
    dashboard_bucket = models.CharField(max_length=255, blank=True)
    categorization_source = models.CharField(max_length=50, blank=True)
    categorization_confidence = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    counterparty_name = models.CharField(max_length=255)
    counterparty_account = models.CharField(max_length=100, blank=True)
    
    transaction_type = models.CharField(max_length=50)  # debit, credit, transfer, etc.
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS_CHOICES)
    
    is_matched = models.BooleanField(default=False)
    matched_transaction = models.ForeignKey(Transaction, on_delete=models.SET_NULL, null=True, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-transaction_date']

    def __str__(self):
        return f"{self.transaction_id}: {self.amount} {self.currency}"


class BankingCategorizationDecision(models.Model):
    """History of categorization decisions, including user overrides and learned rules."""

    DECISION_SOURCE_CHOICES = [
        ('rule_engine', 'Rule Engine'),
        ('provider_hint', 'Provider Hint'),
        ('keyword', 'Keyword'),
        ('user_override', 'User Override'),
        ('ml_feedback', 'ML Feedback'),
        ('fallback', 'Fallback'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='banking_categorization_decisions')
    banking_transaction = models.ForeignKey(BankingTransaction, on_delete=models.CASCADE, related_name='categorization_decisions')
    matched_rule = models.ForeignKey(BankingCategorizationRule, on_delete=models.SET_NULL, null=True, blank=True, related_name='decisions')
    source = models.CharField(max_length=30, choices=DECISION_SOURCE_CHOICES)
    raw_category = models.CharField(max_length=255, blank=True)
    assigned_category = models.CharField(max_length=255)
    dashboard_bucket = models.CharField(max_length=255, blank=True)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    explanation = models.TextField(blank=True)
    is_current = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='banking_categorization_decisions')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['banking_transaction', 'is_current']),
            models.Index(fields=['entity', 'assigned_category']),
        ]

    def __str__(self):
        return f"{self.assigned_category} ({self.source})"


class ReconciliationMatch(models.Model):
    """Links imported bank transactions to posted ledger activity"""
    MATCH_TYPE_CHOICES = [
        ('exact', 'Exact'),
        ('manual', 'Manual'),
        ('partial', 'Partial'),
    ]

    entity = models.ForeignKey(Entity, on_delete=models.CASCADE, related_name='reconciliation_matches')
    bank_transaction = models.OneToOneField(
        BankingTransaction, on_delete=models.CASCADE, related_name='reconciliation_match'
    )
    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name='reconciliation_matches'
    )
    match_type = models.CharField(max_length=20, choices=MATCH_TYPE_CHOICES, default='manual')
    matched_amount = models.DecimalField(max_digits=15, decimal_places=2)
    notes = models.TextField(blank=True)
    matched_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='reconciliation_matches_created'
    )
    matched_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-matched_at']

    def __str__(self):
        return f"Reconciliation {self.bank_transaction.transaction_id} -> {self.journal_entry.reference_number}"


class EmbeddedPayment(models.Model):
    """Embedded payment request for clients"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('captured', 'Captured'),
        ('refunded', 'Refunded'),
        ('failed', 'Failed'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='embedded_payments')
    invoice = models.ForeignKey(ClientInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    currency = models.CharField(max_length=3, default='USD')
    
    payment_method = models.CharField(max_length=50)  # card, bank_transfer, etc.
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    payment_link = models.URLField(blank=True)
    payment_ref = models.CharField(max_length=255, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.payment_ref}: {self.amount} {self.currency}"


# ============ WORKFLOW AUTOMATION ============

class AutomationWorkflow(models.Model):
    """Automation workflow definitions"""
    TRIGGER_TYPE_CHOICES = [
        ('schedule', 'Schedule'),
        ('event', 'Event'),
        ('manual', 'Manual'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='automation_workflows')
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True)
    
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPE_CHOICES)
    trigger_config = models.JSONField()  # Stores trigger details
    
    actions = models.JSONField()  # Stores list of actions
    
    is_active = models.BooleanField(default=True)
    
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.organization.name}"


class AutomationExecution(models.Model):
    """Log of automation workflow executions"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    workflow = models.ForeignKey(AutomationWorkflow, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    triggered_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    execution_result = models.JSONField(blank=True, null=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-triggered_at']

    def __str__(self):
        return f"{self.workflow.name}: {self.status}"


class AutomationArtifact(models.Model):
    """Persisted automation outputs such as board packs generated by workflow executions."""

    ARTIFACT_TYPE_CHOICES = [
        ('enterprise_board_pack', 'Enterprise Board Pack'),
        ('compliance_board_pack', 'Compliance Board Pack'),
    ]

    workflow = models.ForeignKey(AutomationWorkflow, on_delete=models.CASCADE, related_name='artifacts')
    execution = models.ForeignKey(AutomationExecution, on_delete=models.CASCADE, related_name='artifacts')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='automation_artifacts')
    entity = models.ForeignKey(Entity, on_delete=models.SET_NULL, null=True, blank=True, related_name='automation_artifacts')

    artifact_type = models.CharField(max_length=50, choices=ARTIFACT_TYPE_CHOICES, default='enterprise_board_pack')
    export_format = models.CharField(max_length=10, default='pdf')
    file_name = models.CharField(max_length=255)
    file_path = models.FileField(upload_to='automation_artifacts/%Y/%m/%d/')
    metadata = models.JSONField(default=dict, blank=True)

    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} ({self.export_format})"


# ============ FIRM DASHBOARD & BUSINESS INTELLIGENCE ============

class FirmMetric(models.Model):
    """Key metrics for firm dashboard"""
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='firm_metrics')
    
    metric_name = models.CharField(max_length=255)
    metric_key = models.SlugField()
    
    value = models.DecimalField(max_digits=20, decimal_places=2, null=True)
    value_type = models.CharField(max_length=50)  # currency, percentage, count, etc.
    
    period = models.CharField(max_length=20)  # day, week, month, quarter, year
    period_date = models.DateField()
    
    previous_value = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    change_percentage = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-period_date']
        unique_together = ('organization', 'metric_key', 'period_date')

    def __str__(self):
        return f"{self.metric_name}: {self.value}"


class ClientMarketplaceIntegration(models.Model):
    """Third-party integrations/add-ons for clients"""
    CATEGORY_CHOICES = [
        ('integration', 'Integration'),
        ('addon', 'Add-on'),
        ('partner_service', 'Partner Service'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='integrations')
    
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    provider = models.CharField(max_length=255)
    
    description = models.TextField(blank=True)
    icon_url = models.URLField(blank=True)
    
    api_key = models.CharField(max_length=500, blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('client', 'provider')

    def __str__(self):
        return f"{self.name} - {self.client.name}"


class DeveloperModuleInstallation(models.Model):
    """Organization-scoped deployment record for AtonixCorp marketplace modules."""

    TIER_CHOICES = [
        ('basic', 'Basic'),
        ('professional', 'Professional'),
        ('enterprise', 'Enterprise'),
        ('institutional', 'Institutional'),
    ]

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='developer_module_installations')
    module_key = models.SlugField(max_length=80)
    module_name = models.CharField(max_length=255)
    category = models.CharField(max_length=40)
    version = models.CharField(max_length=40, default='1.0.0')
    required_tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='basic')
    status = models.CharField(max_length=20, choices=[('active', 'Active'), ('disabled', 'Disabled')], default='active')
    configuration = models.JSONField(default=dict, blank=True)
    installed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_modules_installed')
    installed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['module_name']
        constraints = [
            models.UniqueConstraint(fields=['organization', 'module_key'], name='unique_developer_module_installation'),
        ]

    def __str__(self):
        return f"{self.module_name} - {self.organization.name}"


# ============================================================================
# V1 PUBLIC API – OAUTH, API KEYS, IDEMPOTENCY, MIGRATION, WEBHOOKS
# ============================================================================

class OAuthApplication(models.Model):
    """OAuth 2.0 application for client_credentials grant"""
    ENVIRONMENT_CHOICES = [
        ('sandbox', 'Sandbox'),
        ('production', 'Production'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='oauth_applications'
    )
    name = models.CharField(max_length=255)
    client_id = models.CharField(max_length=100, unique=True)
    # Stored as SHA-256 hex digest – never store plaintext
    client_secret_hash = models.CharField(max_length=64)
    scopes = models.JSONField(default=list, blank=True)
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES, default='sandbox')
    source_metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='oauth_applications_created'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='oauth_applications_updated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.client_id})"


class APIKey(models.Model):
    """Access token issued via OAuth client_credentials grant"""
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='api_keys'
    )
    application = models.ForeignKey(
        OAuthApplication, on_delete=models.CASCADE, related_name='api_keys'
    )
    # Stored as SHA-256 hex digest of the raw bearer token
    token_hash = models.CharField(max_length=64, unique=True)
    # First 8 chars of the raw token for display/lookup hints
    token_prefix = models.CharField(max_length=8, db_index=True)
    scopes = models.JSONField(default=list, blank=True)
    environment = models.CharField(max_length=20, choices=OAuthApplication.ENVIRONMENT_CHOICES, default='sandbox')
    source_metadata = models.JSONField(default=dict, blank=True)
    expires_at = models.DateTimeField()
    is_revoked = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='api_keys_created'
    )
    revoked_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='api_keys_revoked'
    )
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        from django.utils import timezone
        return not self.is_revoked and self.expires_at > timezone.now()

    def __str__(self):
        return f"APIKey {self.token_prefix}... (org: {self.organization.name})"


class IdempotencyKey(models.Model):
    """Deduplication record for financial POST operations"""
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='idempotency_keys'
    )
    key = models.CharField(max_length=255)
    endpoint = models.CharField(max_length=255)
    response_body = models.JSONField(default=dict)
    response_status = models.IntegerField(default=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'key', 'endpoint')
        ordering = ['-created_at']

    def __str__(self):
        return f"IdempotencyKey {self.key} @ {self.endpoint}"


class MigrationJob(models.Model):
    """Bulk data migration / import job"""
    JOB_TYPE_CHOICES = [
        ('chart_of_accounts', 'Chart of Accounts'),
        ('customers', 'Customers'),
        ('vendors', 'Vendors'),
        ('invoices', 'Invoices'),
        ('bills', 'Bills'),
        ('transactions', 'Transactions'),
        ('opening_balances', 'Opening Balances'),
        ('historical_financials', 'Historical Financials'),
        ('bank_statements', 'Bank Statements'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    SOURCE_SYSTEM_CHOICES = [
        ('quickbooks_online', 'QuickBooks Online'),
        ('xero', 'Xero'),
        ('sage', 'Sage'),
        ('freshbooks', 'FreshBooks'),
        ('wave', 'Wave'),
        ('manual', 'Manual/CSV'),
        ('other', 'Other'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='migration_jobs'
    )
    entity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name='migration_jobs',
        null=True, blank=True
    )
    type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES)
    source_system = models.CharField(
        max_length=50, choices=SOURCE_SYSTEM_CHOICES, blank=True, default='other'
    )
    file_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_records = models.IntegerField(default=0)
    failed_records = models.IntegerField(default=0)
    total_records = models.IntegerField(default=0)
    error_report = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='migration_jobs_created'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='migration_jobs_updated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"MigrationJob {self.id}: {self.type} ({self.status})"


class SystemEvent(models.Model):
    """Persisted financial system events available for delivery and replay"""
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='system_events'
    )
    event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', 'event_type']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"


class WebhookEndpoint(models.Model):
    """Registered webhook endpoint for event delivery"""
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name='webhook_endpoints'
    )
    url = models.URLField()
    # JSON list of event type strings e.g. ["invoice.created", "invoice.paid"]
    events = models.JSONField(default=list)
    # HMAC-SHA256 signing secret – stored plaintext (short-lived, org-scoped)
    secret = models.CharField(max_length=255, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_endpoints_created'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='webhook_endpoints_updated'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Webhook {self.url} (org: {self.organization.name})"


class WebhookDelivery(models.Model):
    """Log of individual webhook delivery attempts"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    endpoint = models.ForeignKey(
        WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries'
    )
    event_type = models.CharField(max_length=100)
    event_id = models.CharField(max_length=100)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_status = models.IntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempt_count = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Delivery {self.event_type} → {self.endpoint.url} ({self.status})"


# ============================================================================
# DEVELOPER PORTAL – API CATALOG, SEARCH, AND KEY REQUESTS
# ============================================================================

class RateLimitProfile(models.Model):
    """Named quota profile for developer portal APIs and issued credentials"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    requests_per_minute = models.PositiveIntegerField(default=60)
    requests_per_day = models.PositiveIntegerField(default=10000)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Rate Limit Profile'
        verbose_name_plural = 'Rate Limit Profiles'

    def __str__(self):
        return f"{self.name} ({self.requests_per_minute}/min, {self.requests_per_day}/day)"

class DeveloperAPICategory(models.Model):
    """Top-level grouping for developer-facing APIs"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = 'Developer API Category'
        verbose_name_plural = 'Developer API Categories'

    def __str__(self):
        return self.name


class DeveloperAPITag(models.Model):
    """Searchable labels applied to developer-facing APIs"""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Developer API Tag'
        verbose_name_plural = 'Developer API Tags'

    def __str__(self):
        return self.name


class DeveloperAPI(models.Model):
    """Catalog record shown in the developer portal"""
    STATUS_CHOICES = [
        ('stable', 'Stable'),
        ('beta', 'Beta'),
        ('deprecated', 'Deprecated'),
    ]
    ACCESS_LEVEL_CHOICES = [
        ('public', 'Public'),
        ('partner', 'Partner'),
        ('internal', 'Internal'),
    ]
    AUTH_TYPE_CHOICES = [
        ('api_key', 'API Key'),
        ('oauth2', 'OAuth 2.0'),
        ('both', 'API Key and OAuth 2.0'),
    ]

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.CharField(max_length=500)
    overview = models.TextField()
    use_cases = models.JSONField(default=list, blank=True)
    data_domains = models.JSONField(default=list, blank=True)
    data_types = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='stable')
    access_level = models.CharField(max_length=20, choices=ACCESS_LEVEL_CHOICES, default='public')
    auth_type = models.CharField(max_length=20, choices=AUTH_TYPE_CHOICES, default='api_key')
    compliance_notes = models.TextField(blank=True)
    rate_limits = models.JSONField(default=dict, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    is_featured = models.BooleanField(default=False)
    featured_rank = models.PositiveIntegerField(default=0)
    rate_limit_profile = models.ForeignKey(
        RateLimitProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_apis'
    )
    categories = models.ManyToManyField(DeveloperAPICategory, related_name='apis', blank=True)
    tags = models.ManyToManyField(DeveloperAPITag, related_name='apis', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['featured_rank', 'name']
        verbose_name = 'Developer API'
        verbose_name_plural = 'Developer APIs'

    def __str__(self):
        return self.name


class DeveloperAPIVersion(models.Model):
    """Version-specific metadata for an API catalog entry"""
    api = models.ForeignKey(DeveloperAPI, on_delete=models.CASCADE, related_name='versions')
    version = models.CharField(max_length=20)
    base_path = models.CharField(max_length=255)
    summary = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=DeveloperAPI.STATUS_CHOICES, default='stable')
    is_default = models.BooleanField(default=False)
    release_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['api__name', 'version']
        unique_together = ('api', 'version')
        verbose_name = 'Developer API Version'
        verbose_name_plural = 'Developer API Versions'

    def __str__(self):
        return f"{self.api.name} {self.version}"


class DeveloperAPIEndpoint(models.Model):
    """Endpoint documentation record for a versioned developer API"""
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]

    version = models.ForeignKey(DeveloperAPIVersion, on_delete=models.CASCADE, related_name='endpoints')
    name = models.CharField(max_length=255)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    path = models.CharField(max_length=255)
    summary = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    path_params = models.JSONField(default=list, blank=True)
    query_params = models.JSONField(default=list, blank=True)
    headers = models.JSONField(default=list, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    request_example = models.TextField(blank=True)
    response_example = models.TextField(blank=True)
    error_responses = models.JSONField(default=list, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'method', 'path']
        verbose_name = 'Developer API Endpoint'
        verbose_name_plural = 'Developer API Endpoints'

    def __str__(self):
        return f"{self.method} {self.path}"


class DeveloperPortalKeyRequest(models.Model):
    """Tracks developer key requests initiated from the public portal"""
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('generated', 'Generated'),
        ('revoked', 'Revoked'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(db_index=True)
    organization_name = models.CharField(max_length=255, blank=True)
    intended_use = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='submitted')
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_portal_key_requests'
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_portal_key_requests'
    )
    application = models.ForeignKey(
        OAuthApplication, on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_portal_key_requests'
    )
    rate_limit_profile = models.ForeignKey(
        RateLimitProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='developer_portal_key_requests'
    )
    source_metadata = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Developer Portal Key Request'
        verbose_name_plural = 'Developer Portal Key Requests'

    def __str__(self):
        return f"{self.email} ({self.status})"


class DeveloperPortalAPILog(models.Model):
    """Audit trail for developer portal catalog, docs, search, status, and key-registration access"""
    api_service = models.ForeignKey(
        DeveloperAPI, on_delete=models.SET_NULL, null=True, blank=True, related_name='portal_logs'
    )
    endpoint = models.ForeignKey(
        DeveloperAPIEndpoint, on_delete=models.SET_NULL, null=True, blank=True, related_name='portal_logs'
    )
    key_request = models.ForeignKey(
        DeveloperPortalKeyRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='api_logs'
    )
    rate_limit_profile = models.ForeignKey(
        RateLimitProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name='portal_logs'
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    status_code = models.PositiveIntegerField()
    request_timestamp = models.DateTimeField()
    response_time_ms = models.PositiveIntegerField(default=0)
    client_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-request_timestamp']
        verbose_name = 'Developer Portal API Log'
        verbose_name_plural = 'Developer Portal API Logs'
        indexes = [
            models.Index(fields=['path', 'method']),
            models.Index(fields=['request_timestamp']),
            models.Index(fields=['status_code']),
        ]

    def __str__(self):
        return f"{self.method} {self.path} ({self.status_code})"
