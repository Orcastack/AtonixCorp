import React, { useEffect, useMemo, useRef, useState } from 'react';
import { NavLink, useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import AtonixCorpLogo from '../branding/AtonixCorpLogo';
import { getWorkspaceLandingPath } from '../../utils/workspaceModules';
import { reportUiError } from '../../utils/errorReporting';
import { Icon } from '../ui';
import {
  LuBadgeDollarSign,
  LuBot,
  LuClipboardCheck,
  LuFileText,
  LuGitBranch,
  LuHandshake,
  LuListTree,
  LuScale,
  LuScrollText,
  LuTableProperties,
  LuUserRound,
} from 'react-icons/lu';
import './EquityLayout.css';

const EquityLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const { activeWorkspace, entities, setActiveWorkspace, getWorkspacePermissionSummary } = useEnterprise();
  const navigate = useNavigate();
  const { workspaceId } = useParams();
  const [sidebarMinimized, setSidebarMinimized] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const profileRef = useRef(null);

  const resolvedWorkspace = useMemo(() => {
    if (!workspaceId) return activeWorkspace;
    if (activeWorkspace && String(activeWorkspace.id) === String(workspaceId)) {
      return activeWorkspace;
    }
    const fromList = (entities || []).find((entity) => String(entity.id) === String(workspaceId));
    if (fromList) return fromList;
    try {
      const saved = localStorage.getItem('atonixcorp_active_workspace');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (String(parsed.id) === String(workspaceId)) return parsed;
      }
    } catch {
      return activeWorkspace;
    }
    return activeWorkspace;
  }, [activeWorkspace, entities, workspaceId]);

  useEffect(() => {
    if (resolvedWorkspace && String(resolvedWorkspace.id) !== String(activeWorkspace?.id)) {
      setActiveWorkspace(resolvedWorkspace);
    }
  }, [activeWorkspace, resolvedWorkspace, setActiveWorkspace]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
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

  const base = workspaceId ? `/app/equity/${workspaceId}` : '/app/equity';
  const permissionSummary = getWorkspacePermissionSummary(workspaceId || resolvedWorkspace?.id);
  const navItems = [
    { key: 'me', to: `${base}/me`, label: 'My Equity', icon: LuUserRound },
    { key: 'registry', to: `${base}/registry`, label: 'Ownership Registry', icon: LuListTree },
    { key: 'cap-table', to: `${base}/cap-table`, label: 'Cap Table', icon: LuTableProperties },
    { key: 'grants', to: `${base}/grants`, label: 'Vesting & Grants', icon: LuHandshake },
    { key: 'exercises', to: `${base}/exercises`, label: 'Exercise Center', icon: LuBadgeDollarSign },
    { key: 'automation', to: `${base}/automation`, label: 'Automation Center', icon: LuBot },
    { key: 'valuation', to: `${base}/valuation`, label: 'Valuation', icon: LuScale },
    { key: 'approvals', to: `${base}/approvals`, label: 'Approval Inbox', icon: LuClipboardCheck },
    { key: 'scenarios', to: `${base}/scenarios`, label: 'Scenario Modeling', icon: LuGitBranch },
    { key: 'transactions', to: `${base}/transactions`, label: 'Equity Transactions', icon: LuScrollText },
    { key: 'governance', to: `${base}/governance`, label: 'Governance & Reporting', icon: LuFileText },
  ];

  const handleDeniedNavigation = (label) => {
    reportUiError({
      title: 'Access restricted',
      message: `You do not have access to the ${label} module.`,
      severity: 'warning',
      source: 'equity',
      autoHideMs: 5000,
    });
  };

  const userInitial = (user?.name || user?.email || 'U').charAt(0).toUpperCase();

  return (
    <div className={`eq-layout${sidebarMinimized ? ' eq-sidebar-minimized' : ''}`}>
      <nav className={`eq-sidebar${sidebarMinimized ? ' minimized' : ''}`} aria-label="Equity navigation">
        <div className="eq-sidebar-header">
          <div className="eq-brand-block">
            <AtonixCorpLogo variant="white" size="small" withText={false} />
            {!sidebarMinimized && (
              <div>
                <div className="eq-brand-title">AtonixCorp Equity</div>
                <div className="eq-brand-sub">{resolvedWorkspace?.name || 'Workspace'}</div>
              </div>
            )}
          </div>
          <button className="eq-sidebar-toggle" onClick={() => setSidebarMinimized((value) => !value)}>
            {sidebarMinimized ? '→' : '←'}
          </button>
        </div>

        {!sidebarMinimized && (
          <div className="eq-sidebar-copy">
            Equity management runs independently from the accounting workspace sidebar while staying bound to the same entity.
          </div>
        )}

        <ul className="eq-nav-list">
          {navItems.map((item) => {
            const hasAccess = !permissionSummary || Boolean(permissionSummary.equity_sections?.[item.key]);
            return (
            <li key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) => `eq-nav-link${isActive ? ' active' : ''}${hasAccess ? '' : ' eq-nav-link-denied'}`}
                title={sidebarMinimized ? item.label : undefined}
                onClick={(event) => {
                  if (!hasAccess) {
                    event.preventDefault();
                    handleDeniedNavigation(item.label);
                  }
                }}
              >
                <span className="eq-nav-icon-wrap">
                  <Icon icon={item.icon} size="sm" tone="dark" className="nav-icon" />
                </span>
                <span>{sidebarMinimized ? item.label.charAt(0) : item.label}</span>
              </NavLink>
            </li>
          );})}
        </ul>

        <div className="eq-sidebar-footer">
          <button className="eq-sidebar-btn" onClick={() => navigate(getWorkspaceLandingPath(resolvedWorkspace || {}))}>
            {sidebarMinimized ? 'F' : 'Finance Workspace'}
          </button>
          <button className="eq-sidebar-btn secondary" onClick={() => navigate('/app/console')}>
            {sidebarMinimized ? 'C' : 'Console'}
          </button>
        </div>
      </nav>

      <div className="eq-main-shell">
        <header className="eq-topbar">
          <div>
            <div className="eq-topbar-kicker">AtonixCorp Equity Management</div>
            <h1 className="eq-topbar-title">{resolvedWorkspace?.name || 'Equity Workspace'}</h1>
          </div>
          <div className="eq-topbar-right" ref={profileRef}>
            <span className="eq-topbar-badge">Institutional Governance</span>
            <button className="eq-avatar-btn" onClick={() => setProfileOpen((value) => !value)}>
              {userInitial}
            </button>
            {profileOpen && (
              <div className="eq-profile-menu">
                <div className="eq-profile-name">{user?.name || 'User'}</div>
                <div className="eq-profile-email">{user?.email || ''}</div>
                <button className="eq-profile-item" onClick={() => navigate('/app/console')}>
                  Back to Console
                </button>
                <button className="eq-profile-item" onClick={() => navigate(getWorkspaceLandingPath(resolvedWorkspace || {}))}>
                  Open Finance Workspace
                </button>
                <button className="eq-profile-item danger" onClick={handleLogout}>
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </header>

        <main className="eq-main-content">{children}</main>
      </div>
    </div>
  );
};

export default EquityLayout;
