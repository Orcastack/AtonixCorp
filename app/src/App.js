import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { FinanceProvider } from './context/FinanceContext';
import { EnterpriseProvider } from './context/EnterpriseContext';
import { EquityProvider } from './context/EquityContext';
import { FilterProvider } from './context/FilterContext';
import { LanguageProvider } from './context/LanguageContext';
import { AccessibilityProvider } from './context/AccessibilityContext';
import ProtectedRoute from './components/ProtectedRoute';
import GlobalConsoleRoute from './components/GlobalConsoleRoute';
import Layout from './components/Layout/Layout';
import EntityLayout from './components/EntityLayout/EntityLayout';
import Landing from './pages/Landing/Landing';
import Login from './pages/Login/Login';
import Register from './pages/Register/Register';
import GlobalTax from './pages/GlobalTax/GlobalTax';
import EnterpriseOrgOverview from './pages/Enterprise/EnterpriseOrgOverview';
import EnterpriseEntities from './pages/Enterprise/EnterpriseEntities';
import EntityDashboard from './pages/Enterprise/EntityDashboard';
import BookkeepingDashboard from './pages/Enterprise/Bookkeeping/BookkeepingDashboard';
import TransactionList from './pages/Enterprise/Bookkeeping/TransactionList';
import CategoryManager from './pages/Enterprise/Bookkeeping/CategoryManager';
import AccountManager from './pages/Enterprise/Bookkeeping/AccountManager';
import BookkeepingReports from './pages/Enterprise/Bookkeeping/BookkeepingReports';
import StaffHR from './pages/Enterprise/Bookkeeping/StaffHR';
import CashflowTreasuryDashboard from './pages/Enterprise/CashflowTreasuryDashboard';
import ExpensesManager from './pages/Enterprise/Management/ExpensesManager';
import IncomeManager from './pages/Enterprise/Management/IncomeManager';
import BudgetsManager from './pages/Enterprise/Management/BudgetsManager';
import EnterpriseTaxCompliance from './pages/Enterprise/EnterpriseTaxCompliance';
import EnterpriseCashflow from './pages/Enterprise/EnterpriseCashflow';
import EnterpriseRiskExposure from './pages/Enterprise/EnterpriseRiskExposure';
import EnterpriseReports from './pages/Enterprise/EnterpriseReports';
import EnterpriseAuditExplorer from './pages/Enterprise/EnterpriseAuditExplorer';
import EnterpriseTeam from './pages/Enterprise/EnterpriseTeam';
import EnterpriseSettings from './pages/EnterpriseSettings/EnterpriseSettings';
import FirmDashboard from './pages/Firm/FirmDashboard';
import WhiteLabel from './pages/Firm/WhiteLabel';
import Marketplace from './pages/Firm/Marketplace';
import APIIntegrations from './pages/Firm/APIIntegrations';
import ChartOfAccounts from './pages/Enterprise/Accounting/ChartOfAccounts';
import GeneralLedger from './pages/Enterprise/Accounting/GeneralLedger';
import JournalEntries from './pages/Enterprise/Accounting/JournalEntries';
import IntercompanyConsole from './pages/Enterprise/Accounting/IntercompanyConsole';
import ARModule from './pages/Enterprise/Accounting/ARModule';
import APModule from './pages/Enterprise/Accounting/APModule';
import Inventory from './pages/Enterprise/Accounting/Inventory';
import BankReconciliation from './pages/Enterprise/Accounting/BankReconciliation';
import RevenueRecognition from './pages/Enterprise/Accounting/RevenueRecognition';
import LegacyPeriodClose from './pages/Enterprise/Accounting/PeriodClose';
import FXModule from './pages/Enterprise/Accounting/FXModule';
import NotificationsCenter from './pages/Enterprise/Accounting/NotificationsCenter';

//  New module pages
import AppNotifications from './modules/overview/Notifications';
import AppTasks from './modules/overview/Tasks';
import AppChartOfAccounts from './modules/accounting/coa/ChartOfAccounts';
import AppGeneralLedger from './modules/accounting/general-ledger/GeneralLedger';
import AppJournalEntries from './modules/accounting/journals/JournalEntries';
import AppAccountingApprovalInbox from './modules/accounting/ApprovalInbox';
import AppIntercompanyConsole from './modules/accounting/IntercompanyConsole';
import AppReconciliation from './modules/accounting/reconciliation/Reconciliation';
import AppAccountsReceivable from './modules/subledgers/ar/AccountsReceivable';
import AppAccountsPayable from './modules/subledgers/ap/AccountsPayable';
import AppCashBank from './modules/subledgers/cash-bank/CashBank';
import AppFixedAssets from './modules/subledgers/fixed-assets/FixedAssets';
import AppInventoryModule from './modules/subledgers/inventory/InventoryModule';
import AppPayroll from './modules/subledgers/payroll/Payroll';
import AppTaxSubledger from './modules/subledgers/tax/TaxSubledger';
import AppInvoices from './modules/billing/Invoices';
import AppBills from './modules/billing/Bills';
import AppCustomers from './modules/billing/Customers';
import AppVendors from './modules/billing/Vendors';
import AppPaymentScheduling from './modules/billing/PaymentScheduling';
import AppCollections from './modules/billing/Collections';
import AppStatements from './modules/reporting/Statements';
import AppTrialBalance from './modules/reporting/TrialBalance';
import AppAnalytics from './modules/reporting/Analytics';
import AppRiskExposure from './modules/reporting/RiskExposure';
import AppBudgets from './modules/budgeting/Budgets';
import AppForecasts from './modules/budgeting/Forecasts';
import AppVarianceAnalysis from './modules/budgeting/VarianceAnalysis';
import AppTaxCenter from './modules/compliance/TaxCenter';
import AppAuditTrail from './modules/compliance/AuditTrail';
import AppPeriodClose from './modules/compliance/PeriodClose';
import AppTaxCalculator from './modules/compliance/TaxCalculator';
import AppTaxMonitoring from './modules/compliance/TaxMonitoring';
import AppFilingAssistant from './modules/compliance/FilingAssistant';
import AppDocumentVault from './modules/documents/DocumentVault';
import AppReceipts from './modules/documents/Receipts';
import AppClientDirectory from './modules/clients/ClientDirectory';
import AppClientPortal from './modules/clients/ClientPortal';
import AppAutomationRules from './modules/automation/AutomationRules';
import AppRecurringEntries from './modules/automation/RecurringEntries';
import AppAIInsights from './modules/automation/AIInsights';
import AppAIAdvisor from './modules/automation/AIAdvisor';
import AppAPIKeys from './modules/integrations/APIKeys';
import AppIntegrationsList from './modules/integrations/IntegrationsList';
import AppFirmSettings from './modules/settings/FirmSettings';
import AppTeamPermissions from './modules/settings/TeamPermissions';
import AppSecurity from './modules/settings/Security';
import AppBranding from './modules/settings/Branding';
import AppSubscription from './modules/settings/Subscription';
import AppHelpCenter from './modules/support/HelpCenter';
import AppSupportTickets from './modules/support/SupportTickets';
import Product from './pages/Product/Product';
import Deployment from './pages/Deployment/Deployment';
import Features from './pages/Features/Features';
import Pricing from './pages/Pricing/Pricing';
import About from './pages/About/About';
import Support from './pages/Support/Support';
import HelpCenter from './pages/HelpCenter/HelpCenter';
import Contact from './pages/Contact/Contact';
import Privacy from './pages/Privacy/Privacy';
import CLIDocs from './pages/CLIDocs/CLIDocs';
import Governance from './pages/Governance/Governance';
import GovernanceCenter from './pages/Governance/GovernanceCenter';
import DeveloperPortal from './pages/Developer/DeveloperPortal';
import ModuleMarketplace from './pages/Developer/ModuleMarketplace';
import GlobalErrorCenter from './components/GlobalErrorCenter';
import Dashboard from './pages/Dashboard/Dashboard';
import GlobalConsole from './pages/GlobalConsole/GlobalConsole';
import WorkspaceSelector from './pages/WorkspaceSelector/WorkspaceSelector';
import CreateWorkspace from './pages/Workspace/CreateWorkspace';
import CreateWorkspaceFlow from './pages/Workspace/CreateWorkspaceFlow';
import CreateEntityFlow from './pages/Enterprise/CreateEntityFlow';
import CreateEquityFlow from './pages/Equity/CreateEquityFlow';
import WorkspaceRoute from './components/WorkspaceRoute';
import WorkspaceLayout from './components/WorkspaceLayout/WorkspaceLayout';
import WorkspaceOverview     from './pages/Workspace/modules/WorkspaceOverview';
import WorkspaceMembers      from './pages/Workspace/modules/WorkspaceMembers';
import WorkspaceDepartments  from './pages/Workspace/modules/WorkspaceDepartments';
import WorkspaceMeetings     from './pages/Workspace/modules/WorkspaceMeetings';
import WorkspaceCalendar     from './pages/Workspace/modules/WorkspaceCalendar';
import WorkspaceFiles        from './pages/Workspace/modules/WorkspaceFiles';
import WorkspacePermissions  from './pages/Workspace/modules/WorkspacePermissions';
import WorkspaceSettings     from './pages/Workspace/modules/WorkspaceSettings';
import WorkspaceEmail        from './pages/Workspace/modules/WorkspaceEmail';
import WorkspaceMarketing    from './pages/Workspace/modules/WorkspaceMarketing';
import EquityLayout from './components/EquityLayout/EquityLayout';
import MyEquity from './pages/Equity/modules/MyEquity';
import OwnershipRegistry from './pages/Equity/modules/OwnershipRegistry';
import CapTable from './pages/Equity/modules/CapTable';
import VestingGrants from './pages/Equity/modules/VestingGrants';
import ExerciseCenter from './pages/Equity/modules/ExerciseCenter';
import AutomationCenter from './pages/Equity/modules/AutomationCenter';
import Valuation from './pages/Equity/modules/Valuation';
import ApprovalInbox from './pages/Equity/modules/ApprovalInbox';
import ScenarioModeling from './pages/Equity/modules/ScenarioModeling';
import EquityTransactions from './pages/Equity/modules/EquityTransactions';
import GovernanceReporting from './pages/Equity/modules/GovernanceReporting';

function App() {
  const configuredBasename = process.env.PUBLIC_URL
    ? new URL(process.env.PUBLIC_URL, window.location.origin).pathname.replace(/\/$/, '')
    : '';
  const isPrefixedLocalRoute = typeof window !== 'undefined'
    && configuredBasename
    && window.location.pathname.startsWith(`${configuredBasename}/`);
  const routerBasename = process.env.NODE_ENV === 'production' || isPrefixedLocalRoute
    ? configuredBasename
    : '/';

  // Console module routes — open inside the AtonixCorp Console (Layout with sidebar).
  // WorkspaceRoute / WorkspaceLayout is reserved for workspace-scoped routes only.
  const renderModuleCrudRoutes = (basePath, Component, requiredPermission) => [
    <Route key={`${basePath}-index`}  path={basePath}               element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
    <Route key={`${basePath}-list`}   path={`${basePath}/list`}     element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
    <Route key={`${basePath}-create`} path={`${basePath}/create`}   element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
    <Route key={`${basePath}-edit`}   path={`${basePath}/edit/:id`} element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
    <Route key={`${basePath}-view`}   path={`${basePath}/view/:id`} element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
  ];

  const renderModulePageRoutes = (basePath, Component, requiredPermission) => [
    <Route key={`${basePath}-index`} path={basePath}           element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
    <Route key={`${basePath}-list`}  path={`${basePath}/list`} element={<ProtectedRoute requiredPermission={requiredPermission}><Layout><Component /></Layout></ProtectedRoute>} />,
  ];

  const renderStandalonePageRoutes = (basePath, Component, requiredPermission) => [
    <Route key={`${basePath}-index`} path={basePath}           element={<ProtectedRoute requiredPermission={requiredPermission}><Component /></ProtectedRoute>} />,
    <Route key={`${basePath}-list`}  path={`${basePath}/list`} element={<ProtectedRoute requiredPermission={requiredPermission}><Component /></ProtectedRoute>} />,
  ];

  return (
    <AccessibilityProvider>
      <LanguageProvider>
        <AuthProvider>
          <FinanceProvider>
            <EnterpriseProvider>
              <EquityProvider>
                <FilterProvider>
              <Router basename={routerBasename}>
            <GlobalErrorCenter />
            <Routes>
              {/* Public Routes */}
              <Route path="/" element={<Landing />} />
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Website Pages */}
              <Route path="/product" element={<Product />} />
              <Route path="/deployment" element={<Deployment />} />
              <Route path="/features" element={<Features />} />
              <Route path="/pricing" element={<Pricing />} />
              <Route path="/about" element={<About />} />
              <Route path="/support" element={<Support />} />
              <Route path="/help-center" element={<HelpCenter />} />
              <Route path="/contact" element={<Contact />} />
              <Route path="/privacy" element={<Privacy />} />
              <Route path="/global-tax" element={<GlobalTax />} />
              <Route path="/governance" element={<Governance />} />
              <Route path="/developers" element={<DeveloperPortal />} />
              <Route path="/v1/docs" element={<CLIDocs />} />

              {/* Legacy financial dashboard shell */}
              <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />

              {/* Standalone authenticated surfaces — no dashboard shell */}
              {renderStandalonePageRoutes('/security-center', AppSecurity, 'manage_org_settings')}
              {renderStandalonePageRoutes('/support-center', AppHelpCenter, 'view_org_overview')}
              {renderStandalonePageRoutes('/support-tickets', AppSupportTickets, 'view_org_overview')}
              {renderModulePageRoutes('/app/governance', GovernanceCenter, 'manage_org_settings')}
              {renderModulePageRoutes('/app/marketplace', ModuleMarketplace, 'manage_org_settings')}

              {/* Global Console — no sidebar */}
              <Route path="/app/console" element={<ProtectedRoute><GlobalConsoleRoute><GlobalConsole /></GlobalConsoleRoute></ProtectedRoute>} />
              <Route path="/app/organizations/select" element={<ProtectedRoute><WorkspaceSelector /></ProtectedRoute>} />
              <Route path="/app/workspaces/create" element={<ProtectedRoute><CreateWorkspace /></ProtectedRoute>} />
              <Route path="/app/organizations/create" element={<ProtectedRoute><CreateWorkspace /></ProtectedRoute>} />
              <Route path="/app/workspaces/new" element={<ProtectedRoute><CreateWorkspaceFlow /></ProtectedRoute>} />
              <Route path="/app/entities/create" element={<ProtectedRoute><CreateEntityFlow /></ProtectedRoute>} />
              <Route path="/app/equity/create" element={<ProtectedRoute><CreateEquityFlow /></ProtectedRoute>} />

              {/* Enterprise Routes */}
              <Route path="/app/enterprise/org-overview" element={
                <ProtectedRoute requiredPermission="view_org_overview">
                  <Layout><EnterpriseOrgOverview /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/entities" element={
                <ProtectedRoute requiredPermission="view_entities">
                  <Layout><EnterpriseEntities /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/entities/:entityId/dashboard" element={
                <ProtectedRoute requiredPermission="view_entities">
                  <EntityLayout><EntityDashboard /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bookkeeping" element={
                <ProtectedRoute>
                  <EntityLayout><BookkeepingDashboard /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bookkeeping/transactions" element={
                <ProtectedRoute>
                  <EntityLayout><TransactionList /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bookkeeping/categories" element={
                <ProtectedRoute>
                  <EntityLayout><CategoryManager /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bookkeeping/accounts" element={
                <ProtectedRoute>
                  <EntityLayout><AccountManager /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bookkeeping/reports" element={
                <ProtectedRoute>
                  <EntityLayout><BookkeepingReports /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bookkeeping/staff-hr" element={
                <ProtectedRoute>
                  <EntityLayout><StaffHR /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/cashflow-treasury" element={
                <ProtectedRoute>
                  <EntityLayout><CashflowTreasuryDashboard /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/expenses" element={
                <ProtectedRoute>
                  <EntityLayout><ExpensesManager /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/income" element={
                <ProtectedRoute>
                  <EntityLayout><IncomeManager /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/budgets" element={
                <ProtectedRoute>
                  <EntityLayout><BudgetsManager /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/chart-of-accounts" element={
                <ProtectedRoute>
                  <EntityLayout><ChartOfAccounts /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/general-ledger" element={
                <ProtectedRoute>
                  <EntityLayout><GeneralLedger /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/journal-entries" element={
                <ProtectedRoute>
                  <EntityLayout><JournalEntries /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/journal-entries/create" element={
                <ProtectedRoute>
                  <EntityLayout><JournalEntries /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/journal-entries/edit/:id" element={
                <ProtectedRoute>
                  <EntityLayout><JournalEntries /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/journal-entries/view/:id" element={
                <ProtectedRoute>
                  <EntityLayout><JournalEntries /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/intercompany" element={
                <ProtectedRoute>
                  <EntityLayout><IntercompanyConsole /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/accounts-receivable" element={
                <ProtectedRoute>
                  <EntityLayout><ARModule /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/accounts-payable" element={
                <ProtectedRoute>
                  <EntityLayout><APModule /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/inventory" element={
                <ProtectedRoute>
                  <EntityLayout><Inventory /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/bank-reconciliation" element={
                <ProtectedRoute>
                  <EntityLayout><BankReconciliation /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/revenue-recognition" element={
                <ProtectedRoute>
                  <EntityLayout><RevenueRecognition /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/period-close" element={
                <ProtectedRoute>
                  <EntityLayout><LegacyPeriodClose /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/fx-accounting" element={
                <ProtectedRoute>
                  <EntityLayout><FXModule /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/notifications" element={
                <ProtectedRoute>
                  <EntityLayout><NotificationsCenter /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/enterprise/entity/:entityId/approval-inbox" element={
                <ProtectedRoute>
                  <EntityLayout><AppAccountingApprovalInbox /></EntityLayout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/tax-compliance" element={
                <ProtectedRoute requiredPermission="view_tax_compliance">
                  <Layout><EnterpriseTaxCompliance /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/cashflow" element={
                <ProtectedRoute requiredPermission="view_cashflow">
                  <Layout><EnterpriseCashflow /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/risk-exposure" element={
                <ProtectedRoute requiredPermission="view_risk_exposure">
                  <Layout><EnterpriseRiskExposure /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/reports" element={
                <ProtectedRoute requiredPermission="view_reports">
                  <Layout><EnterpriseReports /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/audit-explorer" element={
                <ProtectedRoute requiredPermission="view_reports">
                  <Layout><EnterpriseAuditExplorer /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/team" element={
                <ProtectedRoute requiredPermission="view_team">
                  <Layout><EnterpriseTeam /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/enterprise/settings" element={
                <ProtectedRoute requiredPermission="manage_org_settings">
                  <Layout><EnterpriseSettings /></Layout>
                </ProtectedRoute>
              } />

              {/* Legacy Group Overview route */}
              <Route path="/app/firm/enterprise-branches" element={<Navigate to="/app/enterprise/org-overview" replace />} />

              {/* Firm Management Routes */}
              <Route path="/app/firm/dashboard" element={
                <ProtectedRoute>
                  <Layout><FirmDashboard /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/firm/white-label" element={
                <ProtectedRoute>
                  <Layout><WhiteLabel /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/firm/marketplace" element={
                <ProtectedRoute>
                  <Layout><Marketplace /></Layout>
                </ProtectedRoute>
              } />
              <Route path="/app/firm/integrations" element={
                <ProtectedRoute>
                  <Layout><APIIntegrations /></Layout>
                </ProtectedRoute>
              } />

              {/*  New Module Routes  */}
              {/* Overview */}
              {renderModulePageRoutes('/app/overview/notifications', AppNotifications, 'view_org_overview')}
              {renderModuleCrudRoutes('/app/overview/tasks', AppTasks, 'view_org_overview')}

              {/* Accounting */}
              {renderModuleCrudRoutes('/app/accounting/chart-of-accounts', AppChartOfAccounts, 'view_entities')}
              {renderModulePageRoutes('/app/accounting/general-ledger', AppGeneralLedger, 'view_entities')}
              {renderModuleCrudRoutes('/app/accounting/journal-entries', AppJournalEntries, 'view_entities')}
              {renderModulePageRoutes('/app/accounting/approval-inbox', AppAccountingApprovalInbox, 'view_entities')}
              {renderModulePageRoutes('/app/accounting/intercompany', AppIntercompanyConsole, 'view_entities')}
              {renderModuleCrudRoutes('/app/accounting/reconciliation', AppReconciliation, 'view_entities')}

              {/* Sub-Ledgers */}
              {renderModuleCrudRoutes('/app/subledgers/accounts-receivable', AppAccountsReceivable, 'view_entities')}
              {renderModuleCrudRoutes('/app/subledgers/accounts-payable', AppAccountsPayable, 'view_entities')}
              {renderModuleCrudRoutes('/app/subledgers/cash-bank', AppCashBank, 'view_cashflow')}
              {renderModuleCrudRoutes('/app/subledgers/fixed-assets', AppFixedAssets, 'view_entities')}
              {renderModuleCrudRoutes('/app/subledgers/inventory', AppInventoryModule, 'view_entities')}
              {renderModuleCrudRoutes('/app/subledgers/payroll', AppPayroll, 'view_entities')}
              {renderModuleCrudRoutes('/app/subledgers/tax', AppTaxSubledger, 'view_tax_compliance')}

              {/* Billing */}
              {renderModuleCrudRoutes('/app/billing/invoices', AppInvoices, 'view_entities')}
              {renderModuleCrudRoutes('/app/billing/bills', AppBills, 'view_entities')}
              {renderModuleCrudRoutes('/app/billing/customers', AppCustomers, 'view_entities')}
              {renderModuleCrudRoutes('/app/billing/vendors', AppVendors, 'view_entities')}
              {renderModulePageRoutes('/app/billing/payment-scheduling', AppPaymentScheduling, 'view_entities')}
              {renderModulePageRoutes('/app/billing/collections', AppCollections, 'view_entities')}

              {/* Reporting */}
              {renderModulePageRoutes('/app/reporting/statements', AppStatements, 'view_reports')}
              {renderModulePageRoutes('/app/reporting/trial-balance', AppTrialBalance, 'view_reports')}
              {renderModulePageRoutes('/app/reporting/analytics', AppAnalytics, 'view_reports')}
              {renderModulePageRoutes('/app/reporting/risk-exposure', AppRiskExposure, 'view_risk_exposure')}

              {/* Budgeting */}
              {renderModulePageRoutes('/app/budgeting/budgets', AppBudgets, 'view_cashflow')}
              {renderModulePageRoutes('/app/budgeting/forecasts', AppForecasts, 'view_cashflow')}
              {renderModulePageRoutes('/app/budgeting/variance-analysis', AppVarianceAnalysis, 'view_cashflow')}

              {/* Compliance */}
              {renderModuleCrudRoutes('/app/compliance/tax-center', AppTaxCenter, 'view_tax_compliance')}
              {renderModuleCrudRoutes('/app/compliance/audit-trail', AppAuditTrail, 'view_reports')}
              {renderModuleCrudRoutes('/app/compliance/period-close', AppPeriodClose, 'view_tax_compliance')}
              {renderModulePageRoutes('/app/compliance/tax-calculator', AppTaxCalculator, 'view_tax_compliance')}
              {renderModulePageRoutes('/app/compliance/monitoring', AppTaxMonitoring, 'view_tax_compliance')}
              {renderModulePageRoutes('/app/compliance/filing', AppFilingAssistant, 'view_tax_compliance')}

              {/* Documents */}
              {renderModulePageRoutes('/app/documents/vault', AppDocumentVault, 'view_entities')}
              {renderModulePageRoutes('/app/documents/receipts', AppReceipts, 'view_entities')}

              {/* Clients */}
              {renderModulePageRoutes('/app/clients/directory', AppClientDirectory, 'view_entities')}
              {renderModulePageRoutes('/app/clients/portal', AppClientPortal, 'view_entities')}

              {/* Automation */}
              {renderModulePageRoutes('/app/automation/rules', AppAutomationRules, 'view_reports')}
              {renderModulePageRoutes('/app/automation/recurring', AppRecurringEntries, 'view_entities')}
              {renderModulePageRoutes('/app/automation/ai-insights', AppAIInsights, 'view_reports')}
              {renderModulePageRoutes('/app/automation/ai-advisor', AppAIAdvisor, 'view_reports')}

              {/* Integrations */}
              {renderModulePageRoutes('/app/integrations/api-keys', AppAPIKeys, 'manage_org_settings')}
              {renderModulePageRoutes('/app/integrations/list', AppIntegrationsList, 'manage_org_settings')}

              {/* Settings */}
              {renderModulePageRoutes('/app/settings/firm', AppFirmSettings, 'manage_org_settings')}
              {renderModulePageRoutes('/app/settings/team', AppTeamPermissions, 'view_team')}
              <Route path="/app/settings/security" element={<Navigate to="/security-center" replace />} />
              <Route path="/app/settings/security/list" element={<Navigate to="/security-center" replace />} />
              <Route path="/app/settings/entities" element={<Navigate to="/app/enterprise/entities" replace />} />
              {renderModulePageRoutes('/app/settings/branding', AppBranding, 'manage_org_settings')}
              {renderModulePageRoutes('/app/settings/subscription', AppSubscription, 'manage_billing')}
              {/* Support */}
              <Route path="/app/support/help" element={<Navigate to="/support-center" replace />} />
              <Route path="/app/support/help/list" element={<Navigate to="/support-center" replace />} />
              <Route path="/app/support/tickets" element={<Navigate to="/support-tickets" replace />} />
              <Route path="/app/support/tickets/list" element={<Navigate to="/support-tickets" replace />} />

              {/* ── Workspace Module Routes ──────────────────────────────────────────── */}
              {/* Each workspace route is guarded by WorkspaceRoute and rendered inside   */}
              {/* WorkspaceLayout — completely isolated from the AtonixCorp Console.   */}
              <Route path="/app/workspace/:workspaceId/overview"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceOverview /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/members"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceMembers /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/departments"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceDepartments /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/groups"
                element={<Navigate to="../departments" replace />} />
              <Route path="/app/workspace/:workspaceId/meetings"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceMeetings /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/calendar"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceCalendar /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/files"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceFiles /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/permissions"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspacePermissions /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/settings"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceSettings /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/email"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceEmail /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/workspace/:workspaceId/marketing"
                element={<WorkspaceRoute><WorkspaceLayout><WorkspaceMarketing /></WorkspaceLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/registry"
                element={<WorkspaceRoute><EquityLayout><OwnershipRegistry /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/me"
                element={<WorkspaceRoute><EquityLayout><MyEquity /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/cap-table"
                element={<WorkspaceRoute><EquityLayout><CapTable /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/grants"
                element={<WorkspaceRoute><EquityLayout><VestingGrants /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/exercises"
                element={<WorkspaceRoute><EquityLayout><ExerciseCenter /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/automation"
                element={<WorkspaceRoute><EquityLayout><AutomationCenter /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/valuation"
                element={<WorkspaceRoute><EquityLayout><Valuation /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/approvals"
                element={<WorkspaceRoute><EquityLayout><ApprovalInbox /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/scenarios"
                element={<WorkspaceRoute><EquityLayout><ScenarioModeling /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/transactions"
                element={<WorkspaceRoute><EquityLayout><EquityTransactions /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId/governance"
                element={<WorkspaceRoute><EquityLayout><GovernanceReporting /></EquityLayout></WorkspaceRoute>} />
              <Route path="/app/equity/:workspaceId"
                element={<Navigate to="registry" replace />} />
              {/* Redirect bare workspace path → overview */}
              <Route path="/app/workspace/:workspaceId"
                element={<Navigate to="overview" replace />} />
            </Routes>
              </Router>
              </FilterProvider>
              </EquityProvider>
          </EnterpriseProvider>
        </FinanceProvider>
      </AuthProvider>
    </LanguageProvider>
    </AccessibilityProvider>
  );
}

export default App;
