from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExpenseViewSet, IncomeViewSet, BudgetViewSet,
    ModelTemplateViewSet, FinancialModelViewSet, ScenarioViewSet,
    SensitivityAnalysisViewSet, AIInsightViewSet, CustomKPIViewSet,
    KPICalculationViewSet, ReportViewSet, ConsolidationViewSet,
    ConsolidationEntityViewSet, TaxCalculationViewSet
)
from .platform_views import health_check, ingest_platform_event, internal_audit_events
from .views import list_countries, get_country
from .enterprise_views import (
    OrganizationViewSet, EntityViewSet, TeamMemberViewSet,
    TaxExposureViewSet, TaxProfileViewSet, TaxRegimeRegistryViewSet, TaxCalculationHistoryViewSet, TaxFilingViewSet, TaxAuditLogViewSet, ComplianceDeadlineViewSet, CashflowForecastViewSet,
    TaxRuleSetVersionViewSet, TaxRiskAlertViewSet, GovernancePolicyViewSet,
    GovernanceAmendmentViewSet, GovernanceVoteViewSet, GovernanceCommissionPlanViewSet, GovernanceCommissionEntryViewSet,
    RoleViewSet, PermissionViewSet, AuditLogViewSet, PlatformAuditEventViewSet,
    EntityDepartmentViewSet, EntityRoleViewSet, EntityStaffViewSet,
    StaffPayrollProfileViewSet, PayrollComponentViewSet, StaffPayrollComponentAssignmentViewSet,
    LeaveTypeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet, PayrollBankOriginatorProfileViewSet, PayrollRunViewSet,
    PayslipViewSet, PayrollStatutoryReportViewSet, PayrollBankPaymentFileViewSet,
    BankAccountViewSet, WalletViewSet, ComplianceDocumentViewSet,
    BookkeepingCategoryViewSet, BookkeepingAccountViewSet, TransactionViewSet, BookkeepingAuditLogViewSet,
    CashflowTreasuryViewSet, RecurringTransactionViewSet, TaskRequestViewSet, PlatformTaskViewSet, FinancialStatementsViewSet,
    EnterpriseReportingViewSet,
    # New viewsets for Accounting module
    ChartOfAccountsViewSet, GeneralLedgerViewSet, JournalApprovalMatrixViewSet,
    JournalApprovalDelegationViewSet, JournalEntryApprovalStepViewSet, JournalEntryChangeLogViewSet,
    AccountingApprovalMatrixViewSet, AccountingApprovalDelegationViewSet,
    AccountingApprovalRecordViewSet, AccountingApprovalStepViewSet,
    AccountingApprovalChangeLogViewSet, AccountingApprovalInboxViewSet,
    JournalEntryViewSet,
    RecurringJournalTemplateViewSet, LedgerPeriodViewSet,
    CustomerViewSet, InvoiceViewSet, CreditNoteViewSet, PaymentViewSet,
    VendorViewSet, PurchaseOrderViewSet, BillViewSet, BillPaymentViewSet,
    InventoryItemViewSet, InventoryTransactionViewSet, InventoryCOGSViewSet,
    BankReconciliationViewSet,
    DeferredRevenueViewSet, RevenueRecognitionScheduleViewSet,
    PeriodCloseChecklistViewSet, PeriodCloseItemViewSet,
    ExchangeRateViewSet, FXGainLossViewSet,
    NotificationViewSet, NotificationPreferenceViewSet,
    IntercompanyTransactionViewSet, IntercompanyEliminationEntryViewSet,
    # NEW VIEWSETS
    ClientViewSet, ClientPortalViewSet, ClientMessageViewSet, ClientDocumentViewSet,
    DocumentRequestViewSet, ApprovalRequestViewSet, DocumentTemplateViewSet, LoanViewSet,
    LoanPaymentViewSet, KYCProfileViewSet, AMLTransactionViewSet, FirmServiceViewSet,
    ClientInvoiceViewSet, ClientInvoiceLineItemViewSet, ClientSubscriptionViewSet,
    WhiteLabelBrandingViewSet, BankingIntegrationViewSet, BankingTransactionViewSet,
    EmbeddedPaymentViewSet, AutomationWorkflowViewSet, AutomationExecutionViewSet, AutomationArtifactViewSet,
    FirmMetricViewSet, ClientMarketplaceIntegrationViewSet, DeveloperModuleInstallationViewSet
)
from .tax_api_views import (
    CompanyTaxProfileAPIView,
    TaxAuditAPIView,
    TaxCalculateAPIView,
    TaxComplianceAlertsAPIView,
    TaxComplianceCalendarAPIView,
    TaxFilingCreateAPIView,
    TaxFilingSubmitAPIView,
    TaxRegimeCollectionAPIView,
    TaxRegimeCountryAPIView,
)

router = DefaultRouter()

# Personal finance endpoints
router.register(r'expenses', ExpenseViewSet, basename='expense')
router.register(r'income', IncomeViewSet, basename='income')
router.register(r'budgets', BudgetViewSet, basename='budget')

# Enterprise endpoints
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'entities', EntityViewSet, basename='entity')
router.register(r'team-members', TeamMemberViewSet, basename='team-member')
router.register(r'tax-exposures', TaxExposureViewSet, basename='tax-exposure')
router.register(r'tax-profiles', TaxProfileViewSet, basename='tax-profile')
router.register(r'tax-regime-registry', TaxRegimeRegistryViewSet, basename='tax-regime-registry')
router.register(r'tax-calculations-history', TaxCalculationHistoryViewSet, basename='tax-calculation-history')
router.register(r'tax-filings', TaxFilingViewSet, basename='tax-filing')
router.register(r'tax-audit-logs', TaxAuditLogViewSet, basename='tax-audit-log')
router.register(r'tax-rule-set-versions', TaxRuleSetVersionViewSet, basename='tax-rule-set-version')
router.register(r'tax-risk-alerts', TaxRiskAlertViewSet, basename='tax-risk-alert')
router.register(r'compliance-deadlines', ComplianceDeadlineViewSet, basename='compliance-deadline')
router.register(r'cashflow-forecasts', CashflowForecastViewSet, basename='cashflow-forecast')
router.register(r'roles', RoleViewSet, basename='role')
router.register(r'permissions', PermissionViewSet, basename='permission')
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'platform-audit-events', PlatformAuditEventViewSet, basename='platform-audit-event')
router.register(r'governance-policies', GovernancePolicyViewSet, basename='governance-policy')
router.register(r'governance-amendments', GovernanceAmendmentViewSet, basename='governance-amendment')
router.register(r'governance-votes', GovernanceVoteViewSet, basename='governance-vote')
router.register(r'governance-commission-plans', GovernanceCommissionPlanViewSet, basename='governance-commission-plan')
router.register(r'governance-commission-entries', GovernanceCommissionEntryViewSet, basename='governance-commission-entry')

# Entity-specific endpoints
router.register(r'entity-departments', EntityDepartmentViewSet, basename='entity-department')
router.register(r'entity-roles', EntityRoleViewSet, basename='entity-role')
router.register(r'entity-staff', EntityStaffViewSet, basename='entity-staff')
router.register(r'staff-payroll-profiles', StaffPayrollProfileViewSet, basename='staff-payroll-profile')
router.register(r'payroll-components', PayrollComponentViewSet, basename='payroll-component')
router.register(r'staff-payroll-component-assignments', StaffPayrollComponentAssignmentViewSet, basename='staff-payroll-component-assignment')
router.register(r'leave-types', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave-balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'leave-requests', LeaveRequestViewSet, basename='leave-request')
router.register(r'payroll-bank-originators', PayrollBankOriginatorProfileViewSet, basename='payroll-bank-originator')
router.register(r'payroll-runs', PayrollRunViewSet, basename='payroll-run')
router.register(r'payslips', PayslipViewSet, basename='payslip')
router.register(r'payroll-statutory-reports', PayrollStatutoryReportViewSet, basename='payroll-statutory-report')
router.register(r'payroll-bank-files', PayrollBankPaymentFileViewSet, basename='payroll-bank-file')
router.register(r'bank-accounts', BankAccountViewSet, basename='bank-account')
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'compliance-documents', ComplianceDocumentViewSet, basename='compliance-document')

# Bookkeeping endpoints
router.register(r'bookkeeping-categories', BookkeepingCategoryViewSet, basename='bookkeeping-category')
router.register(r'bookkeeping-accounts', BookkeepingAccountViewSet, basename='bookkeeping-account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'bookkeeping-audit-logs', BookkeepingAuditLogViewSet, basename='bookkeeping-audit-log')

# Workflow & task queue endpoints
router.register(r'recurring-transactions', RecurringTransactionViewSet, basename='recurring-transaction')
router.register(r'task-requests', TaskRequestViewSet, basename='task-request')
router.register(r'platform-tasks', PlatformTaskViewSet, basename='platform-task')

# Financial statements endpoints (no model viewset, just actions)
router.register(r'financial-statements', FinancialStatementsViewSet, basename='financial-statements')
router.register(r'enterprise-reporting', EnterpriseReportingViewSet, basename='enterprise-reporting')

# Cashflow & Treasury endpoints
router.register(r'cashflow-treasury', CashflowTreasuryViewSet, basename='cashflow-treasury')

# Financial modeling endpoints
router.register(r'model-templates', ModelTemplateViewSet, basename='model-template')
router.register(r'financial-models', FinancialModelViewSet, basename='financial-model')
router.register(r'scenarios', ScenarioViewSet, basename='scenario')
router.register(r'sensitivity-analyses', SensitivityAnalysisViewSet, basename='sensitivity-analysis')
router.register(r'ai-insights', AIInsightViewSet, basename='ai-insight')
router.register(r'custom-kpis', CustomKPIViewSet, basename='custom-kpi')
router.register(r'kpi-calculations', KPICalculationViewSet, basename='kpi-calculation')
router.register(r'reports', ReportViewSet, basename='report')
router.register(r'consolidations', ConsolidationViewSet, basename='consolidation')
router.register(r'consolidation-entities', ConsolidationEntityViewSet, basename='consolidation-entity')
router.register(r'tax-calculations', TaxCalculationViewSet, basename='tax-calculation')

# NEW: Chart of Accounts & General Ledger
router.register(r'chart-of-accounts', ChartOfAccountsViewSet, basename='chart-of-accounts')
router.register(r'general-ledger', GeneralLedgerViewSet, basename='general-ledger')
router.register(r'journal-approval-matrices', JournalApprovalMatrixViewSet, basename='journal-approval-matrix')
router.register(r'journal-approval-delegations', JournalApprovalDelegationViewSet, basename='journal-approval-delegation')
router.register(r'journal-approval-steps', JournalEntryApprovalStepViewSet, basename='journal-approval-step')
router.register(r'journal-change-logs', JournalEntryChangeLogViewSet, basename='journal-change-log')
router.register(r'accounting-approval-matrices', AccountingApprovalMatrixViewSet, basename='accounting-approval-matrix')
router.register(r'accounting-approval-delegations', AccountingApprovalDelegationViewSet, basename='accounting-approval-delegation')
router.register(r'accounting-approval-records', AccountingApprovalRecordViewSet, basename='accounting-approval-record')
router.register(r'accounting-approval-steps', AccountingApprovalStepViewSet, basename='accounting-approval-step')
router.register(r'accounting-approval-change-logs', AccountingApprovalChangeLogViewSet, basename='accounting-approval-change-log')
router.register(r'accounting-approval-inbox', AccountingApprovalInboxViewSet, basename='accounting-approval-inbox')
router.register(r'journal-entries', JournalEntryViewSet, basename='journal-entry')
router.register(r'recurring-journal-templates', RecurringJournalTemplateViewSet, basename='recurring-journal-template')
router.register(r'ledger-periods', LedgerPeriodViewSet, basename='ledger-period')

# NEW: Accounts Receivable (AR)
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'credit-notes', CreditNoteViewSet, basename='credit-note')
router.register(r'payments', PaymentViewSet, basename='payment')

from .v1_views import GlobalWorkspaceInviteView
# NEW: Accounts Payable (AP)
router.register(r'vendors', VendorViewSet, basename='vendor')
router.register(r'purchase-orders', PurchaseOrderViewSet, basename='purchase-order')
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'bill-payments', BillPaymentViewSet, basename='bill-payment')

# NEW: Inventory
router.register(r'inventory-items', InventoryItemViewSet, basename='inventory-item')
router.register(r'inventory-transactions', InventoryTransactionViewSet, basename='inventory-transaction')
router.register(r'inventory-cogs', InventoryCOGSViewSet, basename='inventory-cogs')

# NEW: Reconciliation
router.register(r'bank-reconciliations', BankReconciliationViewSet, basename='bank-reconciliation')

# NEW: Revenue Recognition & Deferred Revenue
router.register(r'deferred-revenues', DeferredRevenueViewSet, basename='deferred-revenue')
router.register(r'revenue-recognition-schedules', RevenueRecognitionScheduleViewSet, basename='revenue-recognition-schedule')

# NEW: Period Close
router.register(r'period-close-checklists', PeriodCloseChecklistViewSet, basename='period-close-checklist')
router.register(r'period-close-items', PeriodCloseItemViewSet, basename='period-close-item')

# NEW: FX & Multi-Currency
router.register(r'exchange-rates', ExchangeRateViewSet, basename='exchange-rate')
router.register(r'fx-gainloss', FXGainLossViewSet, basename='fx-gainloss')

# NEW: Notifications
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'notification-preferences', NotificationPreferenceViewSet, basename='notification-preference')

# NEW: Intercompany accounting and eliminations
router.register(r'intercompany-transactions', IntercompanyTransactionViewSet, basename='intercompany-transaction')
router.register(r'intercompany-eliminations', IntercompanyEliminationEntryViewSet, basename='intercompany-elimination')

# NEW: Client Management
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'client-portals', ClientPortalViewSet, basename='client-portal')
router.register(r'client-messages', ClientMessageViewSet, basename='client-message')
router.register(r'client-documents', ClientDocumentViewSet, basename='client-document')
router.register(r'document-requests', DocumentRequestViewSet, basename='document-request')
router.register(r'approval-requests', ApprovalRequestViewSet, basename='approval-request')
router.register(r'document-templates', DocumentTemplateViewSet, basename='document-template')

# NEW: Loan Management
router.register(r'loans', LoanViewSet, basename='loan')
router.register(r'loan-payments', LoanPaymentViewSet, basename='loan-payment')

# NEW: Compliance & KYC/AML
router.register(r'kyc-profiles', KYCProfileViewSet, basename='kyc-profile')
router.register(r'aml-transactions', AMLTransactionViewSet, basename='aml-transaction')

# NEW: Billing & Firm Management
router.register(r'firm-services', FirmServiceViewSet, basename='firm-service')
router.register(r'client-invoices', ClientInvoiceViewSet, basename='client-invoice')
router.register(r'client-invoice-line-items', ClientInvoiceLineItemViewSet, basename='client-invoice-line-item')
router.register(r'client-subscriptions', ClientSubscriptionViewSet, basename='client-subscription')

# NEW: White-Labeling
router.register(r'white-label-branding', WhiteLabelBrandingViewSet, basename='white-label-branding')

# NEW: Embedded Banking & Payments
router.register(r'banking-integrations', BankingIntegrationViewSet, basename='banking-integration')
router.register(r'banking-transactions', BankingTransactionViewSet, basename='banking-transaction')
router.register(r'embedded-payments', EmbeddedPaymentViewSet, basename='embedded-payment')

# NEW: Workflow Automation
router.register(r'automation-workflows', AutomationWorkflowViewSet, basename='automation-workflow')
router.register(r'automation-executions', AutomationExecutionViewSet, basename='automation-execution')
router.register(r'automation-artifacts', AutomationArtifactViewSet, basename='automation-artifact')

# NEW: Firm Dashboard
router.register(r'firm-metrics', FirmMetricViewSet, basename='firm-metric')
router.register(r'client-marketplace-integrations', ClientMarketplaceIntegrationViewSet, basename='client-marketplace-integration')
router.register(r'developer-module-installations', DeveloperModuleInstallationViewSet, basename='developer-module-installation')

urlpatterns = [
    path('', include(router.urls)),
    path('global/invite', GlobalWorkspaceInviteView.as_view(), name='global-invite'),
    path('tax/regimes', TaxRegimeCollectionAPIView.as_view(), name='tax-regime-collection'),
    path('tax/regimes/<str:country>', TaxRegimeCountryAPIView.as_view(), name='tax-regime-country'),
    path('companies/<int:entity_id>/tax', CompanyTaxProfileAPIView.as_view(), name='company-tax-profile'),
    path('tax/calculate', TaxCalculateAPIView.as_view(), name='tax-calculate'),
    path('tax/filings/create', TaxFilingCreateAPIView.as_view(), name='tax-filing-create'),
    path('tax/filings/submit', TaxFilingSubmitAPIView.as_view(), name='tax-filing-submit'),
    path('tax/filings/<int:pk>', TaxFilingViewSet.as_view({'get': 'retrieve'}), name='tax-filing-detail'),
    path('tax/compliance/calendar', TaxComplianceCalendarAPIView.as_view(), name='tax-compliance-calendar'),
    path('tax/compliance/alerts', TaxComplianceAlertsAPIView.as_view(), name='tax-compliance-alerts'),
    path('tax/audit', TaxAuditAPIView.as_view(), name='tax-audit'),
    path('health/', health_check, name='health-check'),
    path('platform/events/', ingest_platform_event, name='platform-event-ingest'),
    path('internal/audit-events', internal_audit_events, name='internal-audit-events'),
    path('tax/countries/', list_countries, name='tax_countries_list'),
    path('tax/countries/<str:code>/', get_country, name='tax_country_detail'),
]
