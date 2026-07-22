import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import { LogoMark } from '../Brand/LogoMark';
import ModuleIcon from '../branding/ModuleIcon';
import './Layout.css';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const { currentOrganization, hasPermission, PERMISSIONS } = useEnterprise();
  const location = useLocation();
  const navigate = useNavigate();

  const [sidebarMinimized, setSidebarMinimized] = React.useState(false);
  const [expandedMenus, setExpandedMenus] = React.useState({});
  const [collapsedSections, setCollapsedSections] = React.useState({});
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const toggleSidebar = () => setSidebarMinimized(!sidebarMinimized);

  const toggleSection = (label) => {
    setCollapsedSections(prev => ({ ...prev, [label]: !prev[label] }));
  };

  const userInitial = (user?.name || user?.email || 'U').charAt(0).toUpperCase();
  const enterpriseRoutePrefixes = ['/app/enterprise', '/app/governance', '/app/accounting', '/app/equity', '/app/subledgers'];
  const isEnterpriseRoute = enterpriseRoutePrefixes.some((prefix) => location.pathname.startsWith(prefix));

  //  Navigation definitions

  const overviewNav = [
    { to: '/app/enterprise/org-overview',    label: 'Overview', icon: <ModuleIcon name="compute" /> },
    { to: '/app/overview/notifications',     label: 'Notifications' },
    { to: '/app/overview/tasks',             label: 'Tasks' },
  ];

  const workspaceNav = [
    { to: '/app/enterprise/team',            label: 'Team & Permissions', icon: <ModuleIcon name="workspace" /> },
    { to: '/app/enterprise/reports',         label: 'Reports' },
    { to: '/app/enterprise/audit-explorer',  label: 'Platform Audit' },
    { to: '/app/governance',                 label: 'Governance Center', icon: <ModuleIcon name="governance" /> },
    { to: '/app/enterprise/tax-compliance',  label: 'Tax Compliance' },
    { to: '/app/settings/branding',          label: 'Branding' },
  ];

  const accountingNav = [
    { to: '/app/accounting/chart-of-accounts', label: 'Chart of Accounts' },
    { to: '/app/accounting/general-ledger',    label: 'General Ledger' },
    { to: '/app/accounting/journal-entries',   label: 'Journal Entries' },
    { to: '/app/accounting/intercompany',      label: 'Intercompany Console' },
    {
      label: 'Sub-Ledgers',
      submenu: [
        { to: '/app/subledgers/accounts-receivable', label: 'Accounts Receivable' },
        { to: '/app/subledgers/accounts-payable',    label: 'Accounts Payable' },
        { to: '/app/subledgers/cash-bank',           label: 'Cash & Bank' },
        { to: '/app/subledgers/fixed-assets',        label: 'Fixed Assets' },
        { to: '/app/subledgers/inventory',           label: 'Inventory' },
        { to: '/app/subledgers/payroll',             label: 'Payroll' },
        { to: '/app/subledgers/tax',                 label: 'Tax' },
      ]
    },
    { to: '/app/accounting/reconciliation', label: 'Reconciliation' },
  ];

  const billingNav = [
    { to: '/app/billing/invoices',           label: 'Invoices' },
    { to: '/app/billing/bills',              label: 'Bills' },
    { to: '/app/billing/customers',          label: 'Customers' },
    { to: '/app/billing/vendors',            label: 'Vendors' },
    { to: '/app/billing/payment-scheduling', label: 'Payment Scheduling' },
    { to: '/app/billing/collections',        label: 'Collections' },
  ];

  const reportingNav = [
    { to: '/app/reporting/statements',    label: 'Financial Statements' },
    { to: '/app/reporting/trial-balance', label: 'Trial Balance' },
    { to: '/app/reporting/analytics',     label: 'Reports & Analytics' },
    { to: '/app/reporting/risk-exposure', label: 'Risk & Exposure' },
  ];

  const budgetingNav = [
    { to: '/app/budgeting/budgets',           label: 'Budgets' },
    { to: '/app/budgeting/forecasts',         label: 'Forecasts' },
    { to: '/app/budgeting/variance-analysis', label: 'Variance Analysis' },
  ];

  const complianceNav = [
    { to: '/app/compliance/tax-center',    label: 'Tax Center' },
    { to: '/app/compliance/tax-calculator',label: 'Tax Calculator' },
    { to: '/app/compliance/monitoring',    label: 'Monitoring' },
    { to: '/app/compliance/audit-trail',   label: 'Audit Trail' },
    { to: '/app/compliance/period-close',  label: 'Period Close' },
    { to: '/app/compliance/filing',        label: 'Filing Assistant' },
  ];

  const documentsNav = [
    { to: '/app/documents/vault',    label: 'Document Vault' },
    { to: '/app/documents/receipts', label: 'Receipts' },
  ];

  const clientsNav = [
    { to: '/app/clients/directory', label: 'Clients' },
    { to: '/app/clients/portal',    label: 'Client Portal' },
  ];

  const automationNav = [
    { to: '/app/automation/rules',      label: 'Automation Rules' },
    { to: '/app/automation/recurring',  label: 'Recurring Entries' },
    { to: '/app/automation/ai-insights',label: 'AI Insights' },
    { to: '/app/automation/ai-advisor', label: 'AI Advisor' },
  ];

  const integrationsNav = [
    { to: '/app/marketplace', label: 'Module Marketplace' },
    { to: '/app/integrations/api-keys', label: 'API Keys', icon: <ModuleIcon name="compute" /> },
    { to: '/app/integrations/list',     label: 'Connected Apps' },
  ];

  const supportNav = [
    { to: '/app/console/settings/support-center', label: 'Help Center', target: '_blank', rel: 'noreferrer noopener' },
    { to: '/support-tickets',     label: 'Support Tickets', target: '_blank', rel: 'noreferrer noopener' },
  ];

  const canSeeEnterprise = hasPermission(PERMISSIONS.VIEW_ORG_OVERVIEW);
  const canSeeDepartments = hasPermission(PERMISSIONS.VIEW_TEAM);
  const canSeeFinance = hasPermission(PERMISSIONS.VIEW_ENTITIES);
  const visibleSections = {
    overview: canSeeEnterprise,
    workspace: canSeeEnterprise || canSeeDepartments,
    accounting: canSeeFinance,
    billing: canSeeFinance,
    reporting: canSeeFinance,
    budgeting: canSeeFinance,
    compliance: canSeeEnterprise,
    documents: canSeeEnterprise,
    clients: canSeeEnterprise,
    automation: canSeeEnterprise,
    integrations: canSeeEnterprise,
    firm: canSeeEnterprise,
  };

  const firmNav = [
    { to: '/app/firm/dashboard',    label: 'Firm Dashboard' },
    { to: '/app/firm/white-label',  label: 'White Label' },
    { to: '/app/firm/marketplace',  label: 'Marketplace' },
    { to: '/app/firm/integrations', label: 'API Integrations' },
  ];

  const toggleSubMenu = (label) => {
    setExpandedMenus(prev => ({
      ...prev,
      [label]: !prev[label]
    }));
  };

  const renderNavGroup = (items) =>
    items.map((item) => {
      if (item.submenu) {
        const isExpanded = expandedMenus[item.label];
        return (
          <li key={item.label}>
            <button
              className="nav-link submenu-toggle"
              onClick={() => toggleSubMenu(item.label)}
              title={sidebarMinimized ? item.label : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              {!sidebarMinimized && (
                <>
                  <span className="nav-label">{item.label}</span>

                </>
              )}
            </button>
            {isExpanded && !sidebarMinimized && (
              <ul className="submenu">
                {item.submenu.map(subitem => (
                  <li key={subitem.to}>
                    <NavLink
                      to={subitem.to}
                      className={({ isActive }) => `nav-link submenu-item${isActive ? ' active' : ''}`}
                      target={subitem.target}
                      rel={subitem.rel}
                    >
                      <span className="nav-icon">{subitem.icon}</span>
                      <span className="nav-label">{subitem.label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            )}
          </li>
        );
      }

      const { to, icon, label, target, rel } = item;
      const fallbackIcon = (label || '•').slice(0, 1).toUpperCase();
      return (
        <li key={to}>
          <NavLink
            to={to}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            title={sidebarMinimized ? label : undefined}
            target={target}
            rel={rel}
          >
            <span className="nav-icon">{icon || fallbackIcon}</span>
            {!sidebarMinimized && <span className="nav-label">{label}</span>}
          </NavLink>
        </li>
      );
    });

  const renderSection = (label, navItems, extraLabelClass = '') => {
    const isCollapsed = collapsedSections[label] === true;
    return (
      <React.Fragment key={label}>
        {!sidebarMinimized && (
          <li className={`nav-section-label nav-section-toggle${extraLabelClass ? ' ' + extraLabelClass : ''}`} onClick={() => toggleSection(label)}>
            <span>{label}</span>
            <span className={`section-chevron${isCollapsed ? ' collapsed' : ''}`}>▾</span>
          </li>
        )}
        {!isCollapsed && renderNavGroup(navItems)}
      </React.Fragment>
    );
  };

  return (
    <div className={`layout${isEnterpriseRoute ? ' enterprise-layout' : ''}`}>
      {/*  SIDEBAR  */}
      <nav className={`sidebar${sidebarMinimized ? ' minimized' : ''}`} aria-label="Main navigation">

        {/* Brand Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <LogoMark size={24} />
            {!sidebarMinimized && <span className="sidebar-organization-name">{currentOrganization?.name || 'AtonixCorp'}</span>}
          </div>
          {!sidebarMinimized && (
            <NavLink to="/app/console" className="sidebar-console-link" title="All Organizations">
              ← All Organizations
            </NavLink>
          )}

        </div>

        {/* Navigation */}
        <ul className="nav-menu">
          {visibleSections.overview && renderSection('Overview', overviewNav)}
          {visibleSections.overview && <li className="nav-divider" role="separator" />}

          {visibleSections.workspace && renderSection('Workspace', workspaceNav, 'workspace-label')}
          {visibleSections.workspace && <li className="nav-divider" role="separator" />}

          {visibleSections.accounting && renderSection('Accounting', accountingNav)}
          {visibleSections.accounting && <li className="nav-divider" role="separator" />}

          {visibleSections.billing && renderSection('Billing & Payments', billingNav)}
          {visibleSections.billing && <li className="nav-divider" role="separator" />}

          {visibleSections.reporting && renderSection('Financial Reporting', reportingNav)}
          {visibleSections.reporting && <li className="nav-divider" role="separator" />}

          {visibleSections.budgeting && renderSection('Budgeting & Forecasting', budgetingNav)}
          {visibleSections.budgeting && <li className="nav-divider" role="separator" />}

          {visibleSections.compliance && renderSection('Tax & Compliance', complianceNav)}
          {visibleSections.compliance && <li className="nav-divider" role="separator" />}

          {visibleSections.documents && renderSection('Document Management', documentsNav)}
          {visibleSections.documents && <li className="nav-divider" role="separator" />}

          {visibleSections.clients && renderSection('Client Management', clientsNav)}
          {visibleSections.clients && <li className="nav-divider" role="separator" />}

          {visibleSections.automation && renderSection('Automation', automationNav)}
          {visibleSections.automation && <li className="nav-divider" role="separator" />}

          {visibleSections.integrations && renderSection('Integrations', integrationsNav)}
          {visibleSections.integrations && <li className="nav-divider" role="separator" />}

          {visibleSections.firm && renderSection('Firm Management', firmNav)}
          {visibleSections.firm && <li className="nav-divider" role="separator" />}

          {renderSection('Support', supportNav)}
        </ul>

        {/* Sidebar toggle button at the bottom */}
        <div className="sidebar-footer">
          <button className="sidebar-collapse-btn" onClick={toggleSidebar} title={sidebarMinimized ? 'Expand sidebar' : 'Collapse sidebar'}>
            {sidebarMinimized ? '→' : '←'}
          </button>
        </div>
      </nav>

      {/*  MAIN CONTENT  */}
      <div className={`main-wrapper${sidebarMinimized ? ' sidebar-minimized' : ''}${isEnterpriseRoute ? ' enterprise-main-wrapper' : ''}`}>
        {/* Top Bar */}
        <header className="topbar">
          <div className="topbar-left">
            {isEnterpriseRoute && <LogoMark size={24} />}
            <h2 className="topbar-title">{isEnterpriseRoute ? 'Enterprise Console' : (currentOrganization?.name || 'AtonixCorp')}</h2>
          </div>
          <div className="topbar-right">
            {isEnterpriseRoute && (
              <>
                <div className="enterprise-header-actions" aria-label="Enterprise quick actions">
                  <button className="enterprise-header-action" onClick={() => navigate('/app/entities/create?mode=accounting')}>Add Entity</button>
                  <button className="enterprise-header-action" onClick={() => navigate('/app/workspaces/new')}>Add Workspace</button>
                  <button className="enterprise-header-action" onClick={() => navigate('/app/equity/create')}>Add Equity</button>
                </div>
                <NavLink className="enterprise-notification-link" to="/app/overview/notifications" aria-label="Notifications, 0 unread">
                  <span aria-hidden="true">&#128276;</span>
                  <span className="enterprise-notification-badge">0</span>
                </NavLink>
              </>
            )}
            <div className="profile-menu" ref={profileRef}>
              <button
                className="profile-avatar-btn"
                onClick={() => setProfileOpen(o => !o)}
                aria-label="Open profile menu"
                title="Profile"
              >
                {userInitial}
              </button>
              {profileOpen && (
                <div className="profile-dropdown">
                  <div className="profile-dropdown-header">
                    <div className="profile-dropdown-avatar">{userInitial}</div>
                    <div>
                      <div className="profile-dropdown-name">{user?.name || 'User'}</div>
                      <div className="profile-dropdown-email">{user?.email || ''}</div>
                    </div>
                  </div>
                  <div className="profile-dropdown-divider" />
                  <NavLink to="/app/console/settings" className="profile-dropdown-item" onClick={() => setProfileOpen(false)}>
                    Settings Console
                  </NavLink>
                  <NavLink to="/app/console/settings/support-center" className="profile-dropdown-item" onClick={() => setProfileOpen(false)} target="_blank" rel="noreferrer noopener">
                    Help Center
                  </NavLink>
                  <NavLink to="/support-tickets" className="profile-dropdown-item" onClick={() => setProfileOpen(false)} target="_blank" rel="noreferrer noopener">
                    Support Tickets
                  </NavLink>
                  <div className="profile-dropdown-divider" />
                  <button className="profile-dropdown-item profile-dropdown-logout" onClick={handleLogout}>
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="main-content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
