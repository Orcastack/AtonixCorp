import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import { LogoMark } from '../Brand/LogoMark';
import './Layout.css';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const { currentOrganization } = useEnterprise();
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

  //  Navigation definitions

  const overviewNav = [
    { to: '/app/enterprise/org-overview',    label: 'Overview' },
    { to: '/app/overview/notifications',     label: 'Notifications' },
    { to: '/app/overview/tasks',             label: 'Tasks' },
  ];

  const workspaceNav = [
    { to: '/app/enterprise/team',            label: 'Team & Permissions' },
    { to: '/app/enterprise/reports',         label: 'Reports' },
    { to: '/app/enterprise/audit-explorer',  label: 'Platform Audit' },
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
    { to: '/app/integrations/api-keys', label: 'API Keys' },
    { to: '/app/integrations/list',     label: 'Connected Apps' },
  ];

  const settingsNav = [
    { to: '/app/settings/firm',         label: 'Firm Settings' },
    { to: '/app/settings/team',         label: 'Team & Permissions' },
    { to: '/security-center',           label: 'Security', target: '_blank', rel: 'noreferrer noopener' },
    { to: '/app/settings/subscription', label: 'Subscription' },
  ];

  const supportNav = [
    { to: '/support-center',      label: 'Help Center', target: '_blank', rel: 'noreferrer noopener' },
    { to: '/support-tickets',     label: 'Support Tickets', target: '_blank', rel: 'noreferrer noopener' },
  ];

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
      return (
        <li key={to}>
          <NavLink
            to={to}
            className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
            title={sidebarMinimized ? label : undefined}
            target={target}
            rel={rel}
          >
            <span className="nav-icon">{icon}</span>
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
    <div className="layout">
      {/*  SIDEBAR  */}
      <nav className={`sidebar${sidebarMinimized ? ' minimized' : ''}`} aria-label="Main navigation">

        {/* Brand Header */}
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <LogoMark size={24} />
            {!sidebarMinimized && <span style={{ color: '#FFFFFF', fontWeight: 700, fontSize: 13, letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>{currentOrganization?.name || 'Ledgora'}</span>}
          </div>
          {!sidebarMinimized && (
            <NavLink to="/app/console" className="sidebar-console-link" title="All Organizations">
              ← All Organizations
            </NavLink>
          )}

        </div>

        {/* Navigation */}
        <ul className="nav-menu">
          {renderSection('Overview', overviewNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Workspace', workspaceNav, 'workspace-label')}
          <li className="nav-divider" role="separator" />

          {renderSection('Accounting', accountingNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Billing & Payments', billingNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Financial Reporting', reportingNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Budgeting & Forecasting', budgetingNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Tax & Compliance', complianceNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Document Management', documentsNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Client Management', clientsNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Automation', automationNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Integrations', integrationsNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Firm Management', firmNav)}
          <li className="nav-divider" role="separator" />

          {renderSection('Settings', settingsNav)}
          <li className="nav-divider" role="separator" />

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
      <div className={`main-wrapper${sidebarMinimized ? ' sidebar-minimized' : ''}`}>
        {/* Top Bar */}
        <header className="topbar">
          <div className="topbar-left">
            <h2 className="topbar-title">{currentOrganization?.name || 'Ledgora'}</h2>
          </div>
          <div className="topbar-right">
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
                  <NavLink to="/app/settings/firm" className="profile-dropdown-item" onClick={() => setProfileOpen(false)}>
                    Firm Settings
                  </NavLink>
                  <NavLink to="/security-center" className="profile-dropdown-item" onClick={() => setProfileOpen(false)} target="_blank" rel="noreferrer noopener">
                    Security
                  </NavLink>
                  <NavLink to="/support-center" className="profile-dropdown-item" onClick={() => setProfileOpen(false)} target="_blank" rel="noreferrer noopener">
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
