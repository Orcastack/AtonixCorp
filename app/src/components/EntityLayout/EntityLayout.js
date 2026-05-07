import React, { useState, useRef, useEffect, useMemo } from 'react';
import { NavLink, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import '../Layout/Layout.css';
import '../../styles/EntityPages.css';
import './EntityLayout.css';

const EntityLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { entityId } = useParams();
  const { entities, activeWorkspace } = useEnterprise();

  const resolvedEntityId = useMemo(() => {
    const directEntityId = Number(entityId);
    if (Number.isInteger(directEntityId) && String(directEntityId) === String(entityId).trim()) {
      return directEntityId;
    }

    const workspaceCandidates = [activeWorkspace];
    try {
      const savedWorkspace = localStorage.getItem('ledgora_active_workspace');
      if (savedWorkspace) {
        workspaceCandidates.push(JSON.parse(savedWorkspace));
      }
    } catch {
      // Ignore malformed saved workspace state.
    }

    const matchingWorkspace = workspaceCandidates.find((workspace) => workspace && String(workspace.id) === String(entityId));
    const linkedEntityId = matchingWorkspace?.linked_entity_id || matchingWorkspace?.linked_entity?.id;
    const numericLinkedEntityId = Number(linkedEntityId);

    return Number.isInteger(numericLinkedEntityId) ? numericLinkedEntityId : null;
  }, [activeWorkspace, entityId]);

  const entity = (entities || []).find(e => e.id?.toString() === (resolvedEntityId || entityId)?.toString());
  const entityName = entity?.name || 'Entity';

  const [sidebarMinimized, setSidebarMinimized] = useState(false);
  const [expandedMenus, setExpandedMenus] = useState({});
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

  const handleLogout = () => { logout(); navigate('/'); };
  const toggleSidebar = () => setSidebarMinimized(v => !v);
  const toggleMenu = (label) => setExpandedMenus(prev => ({ ...prev, [label]: !prev[label] }));

  const userInitial = (user?.name || user?.email || 'U').charAt(0).toUpperCase();

  const id = resolvedEntityId || entityId;

  const navSections = [
    {
      label: 'Entity',
      items: [
        { to: `/app/enterprise/entities/${id}/dashboard`, label: 'Dashboard' },
        {
          label: 'Bookkeeping',
          submenu: [
            { to: `/enterprise/entity/${id}/bookkeeping`, label: 'Overview' },
            { to: `/enterprise/entity/${id}/bookkeeping/transactions`, label: 'Transactions' },
            { to: `/enterprise/entity/${id}/bookkeeping/categories`, label: 'Categories' },
            { to: `/enterprise/entity/${id}/bookkeeping/accounts`, label: 'Accounts' },
            { to: `/enterprise/entity/${id}/bookkeeping/reports`, label: 'Reports' },
            { to: `/enterprise/entity/${id}/bookkeeping/staff-hr`, label: 'Staff & HR' },
          ],
        },
        { to: `/enterprise/entity/${id}/expenses`, label: 'Expenses' },
        { to: `/enterprise/entity/${id}/income`, label: 'Income' },
        { to: `/enterprise/entity/${id}/budgets`, label: 'Budgets' },
        { to: `/enterprise/entity/${id}/cashflow-treasury`, label: 'Cashflow & Treasury' },
      ],
    },
    {
      label: 'Accounting',
      items: [
        { to: `/enterprise/entity/${id}/chart-of-accounts`, label: 'Chart of Accounts' },
        { to: `/enterprise/entity/${id}/general-ledger`, label: 'General Ledger' },
        { to: `/enterprise/entity/${id}/journal-entries`, label: 'Journal Entries' },
        { to: `/enterprise/entity/${id}/intercompany`, label: 'Intercompany Console' },
        { to: `/enterprise/entity/${id}/approval-inbox`, label: 'Approval Inbox' },
        {
          label: 'Sub-Ledgers',
          submenu: [
            { to: `/enterprise/entity/${id}/accounts-receivable`, label: 'Accounts Receivable' },
            { to: `/enterprise/entity/${id}/accounts-payable`, label: 'Accounts Payable' },
            { to: `/enterprise/entity/${id}/bank-reconciliation`, label: 'Bank Reconciliation' },
            { to: `/enterprise/entity/${id}/inventory`, label: 'Inventory' },
            { to: `/enterprise/entity/${id}/revenue-recognition`, label: 'Revenue Recognition' },
            { to: `/enterprise/entity/${id}/fx-accounting`, label: 'FX Accounting' },
          ],
        },
        { to: `/enterprise/entity/${id}/period-close`, label: 'Period Close' },
        { to: `/enterprise/entity/${id}/notifications`, label: 'Notifications' },
      ],
    },
  ];

  const renderItem = (item) => {
    if (item.submenu) {
      const isOpen = expandedMenus[item.label];
      return (
        <li key={item.label}>
          <button
            className="entity-nav-link entity-submenu-toggle"
            onClick={() => toggleMenu(item.label)}
            title={sidebarMinimized ? item.label : undefined}
          >
            {!sidebarMinimized && (
              <>
                <span>{item.label}</span>
                <span className={`entity-submenu-chevron${isOpen ? ' open' : ''}`}>▶</span>
              </>
            )}
            {sidebarMinimized && <span style={{ fontSize: 16 }}>≡</span>}
          </button>
          {isOpen && !sidebarMinimized && (
            <ul className="entity-submenu">
              {item.submenu.map(sub => (
                <li key={sub.to}>
                  <NavLink
                    to={sub.to}
                    end
                    className={({ isActive }) => `entity-nav-link${isActive ? ' active' : ''}`}
                  >
                    {sub.label}
                  </NavLink>
                </li>
              ))}
            </ul>
          )}
        </li>
      );
    }
    return (
      <li key={item.to}>
        <NavLink
          to={item.to}
          end
          className={({ isActive }) => `entity-nav-link${isActive ? ' active' : ''}`}
          title={sidebarMinimized ? item.label : undefined}
        >
          {!sidebarMinimized && item.label}
          {sidebarMinimized && (
            <span style={{ fontSize: 14 }}>{(item.label || '?').charAt(0)}</span>
          )}
        </NavLink>
      </li>
    );
  };

  return (
    <div className="layout">
      {/* SIDEBAR */}
      <nav className={`entity-sidebar${sidebarMinimized ? ' minimized' : ''}`} aria-label="Entity navigation">

        {/* Entity Header */}
        <div className="entity-sidebar-header">
          <div className="entity-sidebar-brand">
            <span className="entity-sidebar-accent" />
            {!sidebarMinimized && (
              <span className="entity-sidebar-name">{entityName}</span>
            )}
          </div>
        </div>

        {/* Back link */}
        <div className="entity-back-nav">
          <button
            onClick={() => navigate('/app/enterprise/entities')}
            className="entity-back-btn"
            title="Back to Ledgora"
          >
            <span className="entity-back-arrow">←</span>
            {!sidebarMinimized && <span className="entity-back-label">Ledgora</span>}
          </button>
        </div>

        {/* Nav */}
        <ul className="entity-nav-menu">
          {navSections.map(section => (
            <React.Fragment key={section.label}>
              {!sidebarMinimized && (
                <li className="entity-nav-section-label">{section.label}</li>
              )}
              {section.items.map(renderItem)}
              <li className="entity-nav-divider" role="separator" />
            </React.Fragment>
          ))}
        </ul>

        {/* Sidebar collapse button */}
        <div className="entity-sidebar-footer">
          <button
            className="entity-collapse-btn"
            onClick={toggleSidebar}
            title={sidebarMinimized ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <span className="entity-collapse-icon">←</span>
            {!sidebarMinimized && <span style={{ fontSize: 12 }}>Collapse</span>}
          </button>
        </div>
      </nav>

      {/* MAIN CONTENT */}
      <div className={`entity-main-wrapper${sidebarMinimized ? ' sidebar-minimized' : ''}`}>
        {/* Topbar */}
        <header className="entity-topbar">
          <div className="entity-topbar-left">
            <h2 className="entity-topbar-title">{entityName}</h2>
            {entity?.country && (
              <span className="entity-topbar-meta">
                {entity.country} · {entity.entity_type?.replace(/_/g, ' ')}
              </span>
            )}
          </div>
          <div className="entity-topbar-right">
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
                    <span className="profile-dropdown-name">{user?.name || user?.email}</span>
                    <span className="profile-dropdown-email">{user?.email}</span>
                  </div>
                  <div className="profile-dropdown-divider" />
                  <button className="profile-dropdown-item" onClick={() => { navigate('/app/settings/firm'); setProfileOpen(false); }}>
                    Settings
                  </button>
                  <button className="profile-dropdown-item profile-dropdown-logout" onClick={handleLogout}>
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="entity-main-content">
          {children}
        </main>
      </div>
    </div>
  );
};

export default EntityLayout;
