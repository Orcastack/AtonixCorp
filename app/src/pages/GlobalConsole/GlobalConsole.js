import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import AtonixCorpLogo from '../../components/branding/AtonixCorpLogo';
import { globalInviteAPI, platformAuditEventsAPI, platformTasksAPI } from '../../services/api';
import './GlobalConsole.css';

/* ─────────────────────────────────────────────────────────────────────────────
  AtonixCorp — Global Capital Console
   The cross-company control center a user sees immediately after login.
   Shows: My Entities · Global Notifications · Global Tasks · Quick Actions
───────────────────────────────────────────────────────────────────────────── */

const formatDate = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return '—';
  }
};

const PALETTE = ['ws-indigo', 'ws-teal', 'ws-violet', 'ws-rose', 'ws-amber', 'ws-sky'];
const palette = (idx) => PALETTE[idx % PALETTE.length];

const openStandalonePath = (path) => {
  window.open(`${process.env.PUBLIC_URL || ''}${path}`, '_blank', 'noopener,noreferrer');
};

const normalizeCollection = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
};

const toTaskPriority = (task) => {
  if (task.state === 'blocked') return 'overdue';
  if (task.priority === 'high' || task.priority === 'urgent') return 'high';
  return 'medium';
};

const formatRelativeTime = (value) => {
  if (!value) return 'Just now';
  const deltaMs = new Date(value).getTime() - Date.now();
  const deltaDays = Math.round(deltaMs / 86400000);
  if (deltaDays === 0) return 'Today';
  if (deltaDays > 0) return `In ${deltaDays}d`;
  return `${Math.abs(deltaDays)}d ago`;
};

const auditSeverity = (event) => {
  if (['approval_rejected', 'workflow_run_failed', 'deadline_deleted'].includes(event.action)) return 'critical';
  if (['approval_requested', 'approval_progressed', 'workflow_run_started'].includes(event.action)) return 'high';
  return 'medium';
};

const EmptyWorkspaceIllustration = () => (
  <div className="gc-empty-illustration" aria-hidden="true">
    <div className="gc-empty-illustration-frame">
      <div className="gc-empty-illustration-dot" />
      <div className="gc-empty-illustration-line gc-empty-illustration-line-short" />
      <div className="gc-empty-illustration-grid">
        <span />
        <span />
        <span />
        <span />
      </div>
    </div>
  </div>
);

const emitAnalyticsEvent = (eventName, payload = {}) => {
  if (typeof window === 'undefined') return;

  const eventPayload = {
    event: eventName,
    timestamp: new Date().toISOString(),
    ...payload,
  };

  if (Array.isArray(window.dataLayer)) {
    window.dataLayer.push(eventPayload);
  }

  window.__ATONIXCORP_ANALYTICS_QUEUE__ = window.__ATONIXCORP_ANALYTICS_QUEUE__ || [];
  window.__ATONIXCORP_ANALYTICS_QUEUE__.push(eventPayload);
  window.dispatchEvent(new CustomEvent('atonixcorp:analytics', { detail: eventPayload }));
};

const GlobalConsole = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const {
    currentOrganization,
    entities,
    organizations,
    globalNotifications,
    fetchGlobalNotifications,
    teamMembers,
    loading,
    complianceDeadlines,
  } = useEnterprise();

  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [profileOpen, setProfileOpen] = useState(false);
  const [taskFilter, setTaskFilter] = useState('open');
  const [departmentFilter, setDepartmentFilter] = useState('all');
  const [costCenterFilter, setCostCenterFilter] = useState('all');
  const [tasks, setTasks] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [taskActionPendingId, setTaskActionPendingId] = useState(null);
  const [currentTime, setCurrentTime] = useState(() => new Date());
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteSaving, setInviteSaving] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');
  const [inviteForm, setInviteForm] = useState({ invitee: '', workspaceId: '' });
  const profileRef = useRef(null);
  const onboardingEnteredAtRef = useRef(null);
  const onboardingCtaClickedRef = useRef(false);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setProfileOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (fetchGlobalNotifications) fetchGlobalNotifications();
  }, [fetchGlobalNotifications]);

  useEffect(() => {
    const tick = () => setCurrentTime(new Date());
    tick();
    const timer = window.setInterval(tick, 60 * 1000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    let active = true;

    const loadPlatformData = async () => {
      try {
        const [taskResponse, auditResponse] = await Promise.all([
          platformTasksAPI.getAll({
            assignee_id: user?.id,
            state: taskFilter === 'all' ? undefined : taskFilter,
            department_name: departmentFilter === 'all' ? undefined : departmentFilter,
            cost_center: costCenterFilter === 'all' ? undefined : costCenterFilter,
          }),
          platformAuditEventsAPI.getAll({ actor_id: user?.id }),
        ]);
        if (!active) return;
        setTasks(normalizeCollection(taskResponse.data).slice(0, 8));
        setAuditEvents(normalizeCollection(auditResponse.data).slice(0, 8));
      } catch (error) {
        if (!active) return;
        setTasks([]);
        setAuditEvents([]);
      }
    };

    if (user?.id) {
      loadPlatformData();
    }

    return () => {
      active = false;
    };
  }, [costCenterFilter, departmentFilter, taskFilter, user?.id]);

  const entityCount = entities.length;
  const showOrganizationOnboarding = !loading && organizations.length === 0;
  const pendingInvitations = Array.isArray(teamMembers)
    ? teamMembers.filter((member) => member?.accepted_at == null || member?.invitation_status === 'pending' || member?.status === 'pending').length
    : 0;
  const workspaceSelectOptions = organizations.map((org) => ({
    value: String(org.id),
    label: org.name,
  }));

  const handleInviteUser = async () => {
    setInviteError('');
    setInviteSuccess('');

    const workspaceId = String(inviteForm.workspaceId || '').trim();
    const invitee = String(inviteForm.invitee || '').trim();

    if (!workspaceId || !invitee) {
      setInviteError('Organization and invitee are required.');
      return;
    }

    setInviteSaving(true);
    try {
      const payload = { workspace_id: workspaceId };
      if (/^\d+$/.test(invitee)) {
        payload.user_id = Number(invitee);
      } else {
        payload.email = invitee.toLowerCase();
      }
      await globalInviteAPI.create(payload);
      setInviteSuccess('Organization invitation sent.');
      setInviteForm({ invitee: '', workspaceId: '' });
      fetchGlobalNotifications?.();
      setTimeout(() => {
        setInviteModalOpen(false);
        setInviteSuccess('');
      }, 700);
    } catch (error) {
      setInviteError(error?.response?.data?.detail || error?.response?.data?.user_id?.[0] || error?.response?.data?.email?.[0] || 'Failed to invite user to the organization.');
    } finally {
      setInviteSaving(false);
    }
  };

  const scrollToWorkspaces = () => {
    navigate('/app/organizations/select');
  };

  const notifs = auditEvents.length > 0
    ? auditEvents.slice(0, 4).map((event) => ({
        id: event.id,
        message: event.summary,
        severity: auditSeverity(event),
        daysLeft: null,
      }))
    : globalNotifications && globalNotifications.length > 0
      ? globalNotifications
      : (complianceDeadlines || []).slice(0, 4).map((d, i) => {
          const dl = d.deadline_date ? new Date(d.deadline_date) : null;
          const days = dl ? Math.ceil((dl - new Date()) / 86400000) : null;
          return {
            id: d.id || i,
            type: 'tax_deadline',
            message: `${d.title} — due ${d.deadline_date || '—'}`,
            severity: days !== null && days <= 0 ? 'critical' : days !== null && days <= 7 ? 'high' : 'medium',
            daysLeft: days,
          };
        });

  const handleTaskAction = async (task, action) => {
    setTaskActionPendingId(task.id);
    try {
      if (action === 'start') {
        await platformTasksAPI.start(task.id);
      } else if (action === 'complete') {
        await platformTasksAPI.complete(task.id, {});
      } else if (action === 'assign') {
        await platformTasksAPI.update(task.id, { assignee_type: 'user', assignee_id: user.id });
      }

      const [taskResponse, auditResponse] = await Promise.all([
        platformTasksAPI.getAll({
          assignee_id: user?.id,
          state: taskFilter === 'all' ? undefined : taskFilter,
          department_name: departmentFilter === 'all' ? undefined : departmentFilter,
          cost_center: costCenterFilter === 'all' ? undefined : costCenterFilter,
        }),
        platformAuditEventsAPI.getAll({ actor_id: user?.id }),
      ]);
      setTasks(normalizeCollection(taskResponse.data).slice(0, 8));
      setAuditEvents(normalizeCollection(auditResponse.data).slice(0, 8));
    } finally {
      setTaskActionPendingId(null);
    }
  };

  const firstName = (user?.name || user?.email || 'User').split(' ')[0];
  const userInitial = (user?.name || user?.email || 'U').charAt(0).toUpperCase();
  const departmentOptions = Array.from(new Set(tasks.map((task) => task.department_name).filter(Boolean))).sort();
  const costCenterOptions = Array.from(new Set(tasks.map((task) => task.cost_center).filter(Boolean))).sort();

  const trackWorkspaceLandingEvent = useCallback((eventName, payload = {}) => {
    emitAnalyticsEvent(eventName, {
      organizationId: currentOrganization?.id || null,
      organizationName: currentOrganization?.name || null,
      userId: user?.id || null,
      entityCount,
      ...payload,
    });
  }, [currentOrganization?.id, currentOrganization?.name, user?.id, entityCount]);

  useEffect(() => {
    if (!showOrganizationOnboarding) {
      onboardingEnteredAtRef.current = null;
      onboardingCtaClickedRef.current = false;
      return undefined;
    }

    onboardingEnteredAtRef.current = Date.now();
    onboardingCtaClickedRef.current = false;
    trackWorkspaceLandingEvent('workspace_empty_state_load');

    return () => {
      if (!onboardingEnteredAtRef.current) return;
      const elapsedSeconds = Math.max(1, Math.round((Date.now() - onboardingEnteredAtRef.current) / 1000));
      trackWorkspaceLandingEvent('workspace_empty_state_time_on_page', { elapsedSeconds });
      if (!onboardingCtaClickedRef.current) {
        trackWorkspaceLandingEvent('workspace_empty_state_dropoff', { elapsedSeconds });
      }
    };
  }, [showOrganizationOnboarding, trackWorkspaceLandingEvent]);

  const handleCreateWorkspace = useCallback((source = 'console') => {
    if (source === 'empty_state') {
      onboardingCtaClickedRef.current = true;
    }
    trackWorkspaceLandingEvent('workspace_create_cta_click', { source });
    navigate('/app/organizations/create');
  }, [navigate, trackWorkspaceLandingEvent]);

  const handleNotificationsClick = useCallback(() => {
    trackWorkspaceLandingEvent('workspace_landing_notifications_click', { notificationCount: notifs.length });
    if (showOrganizationOnboarding) return;
    const target = document.querySelector('.gc-notif-section');
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [notifs.length, showOrganizationOnboarding, trackWorkspaceLandingEvent]);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const activeOrganizationCount = organizations.length;
  const complianceAlertCount = notifs.filter((item) => item.severity === 'critical' || item.severity === 'high').length;
  const pendingCapitalTasks = tasks.length;
  const marketPulse = [
    { label: 'Global Equity Index', value: 'No data connected', tone: 'muted' },
    { label: 'Volatility Index', value: 'Stable', tone: 'positive' },
    { label: 'Portfolio NAV', value: 'Not yet configured', tone: 'muted' },
    { label: 'Compliance Status', value: 'Current', tone: 'positive' },
  ];
  const equityTools = [
    'Capital Tables',
    'Vesting Schedules',
    'Equity Events',
    'Compliance Filings',
    'Organization Management',
  ];
  const todaysOverview = [
    'No active filings',
    'No pending equity events',
    'No capital movements scheduled',
  ];

  return (
    <div className="global-console-page">

      {/* ── TOP NAVBAR ──────────────────────────────────────────────── */}
      <header className="gc-topnav">
        <div className="gc-topnav-left">
          <div className="gc-topnav-brand">
            <AtonixCorpLogo variant="white" size="small" withText text="AtonixCorp" />
          </div>
          <div className="gc-topnav-org-block">
            <span className="gc-topnav-org-label">Organization</span>
            <strong className="gc-topnav-org-name">{currentOrganization?.name || 'AtonixCorp Organization'}</strong>
          </div>
        </div>
        <div className="gc-topnav-right" ref={profileRef}>
          <div className="gc-topnav-clock" aria-label="Current date and time">
            <span>{currentTime.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })}</span>
            <strong>{currentTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong>
          </div>
          <button className="gc-topnav-notifications" onClick={handleNotificationsClick} aria-label="Notifications">
            <span className="gc-topnav-notifications-label">Notifications</span>
            <span className="gc-topnav-notifications-count">{notifs.length}</span>
          </button>
          <button
            className="gc-topnav-avatar"
            onClick={() => setProfileOpen((o) => !o)}
            aria-label="Profile menu"
          >
            {userInitial}
          </button>
          {profileOpen && (
            <div className="gc-topnav-dropdown">
              <div className="gc-topnav-dd-header">
                <div className="gc-topnav-dd-avatar">{userInitial}</div>
                <div>
                  <div className="gc-topnav-dd-name">{user?.name || 'User'}</div>
                  <div className="gc-topnav-dd-email">{user?.email || ''}</div>
                </div>
              </div>
              <div className="gc-topnav-dd-divider" />
              <button className="gc-topnav-dd-item" onClick={() => { setProfileOpen(false); openStandalonePath('/security-center'); }}>
                Security
              </button>
              <button className="gc-topnav-dd-item" onClick={() => { setProfileOpen(false); openStandalonePath('/support-center'); }}>
                Help Center
              </button>
              <div className="gc-topnav-dd-divider" />
              <button className="gc-topnav-dd-item gc-topnav-dd-logout" onClick={handleLogout}>
                Sign Out
              </button>
            </div>
          )}
        </div>
      </header>

      <section className="gc-capital-hero">
        <div className="gc-capital-hero-copy">
          <p className="gc-capital-subtitle">Oversight • Risk • Compliance • Liquidity</p>
          <div className="gc-capital-meta-row">
            <span className="gc-capital-pill">Prime capital posture</span>
            <span className="gc-capital-pill gc-capital-pill--muted">Market pulse enabled</span>
          </div>
        </div>
        <div className="gc-capital-badges">
          <span className="gc-compliance-badge">Compliance: Current</span>
          <span className="gc-capital-watermark">ATONIXCORP GLOBAL</span>
        </div>
      </section>

      <div className="gc-body">
        <div className="global-console">

          <section className="gc-market-strip">
            <div className="gc-section-header gc-section-header--tight">
              <div>
                <h2>Market Pulse (Live)</h2>
                <p>Institutional readout</p>
              </div>
            </div>
            <div className="gc-market-grid">
              {marketPulse.map((signal) => (
                <article key={signal.label} className={`gc-market-card gc-market-card--${signal.tone}`}>
                  <span>{signal.label}</span>
                  <strong>{signal.value}</strong>
                </article>
              ))}
            </div>
          </section>

          <section className="gc-action-ribbon" aria-label="Institutional actions">
            <button className="gc-action-btn gc-action-primary gc-action-btn--ribbon" onClick={() => handleCreateWorkspace('institutional_ribbon')}>
              New Organization
            </button>
            <button className="gc-action-btn gc-action-secondary gc-action-btn--ribbon" onClick={() => setInviteModalOpen(true)}>
              New Organization
            </button>
            <button className="gc-action-btn gc-action-secondary gc-action-btn--ribbon" onClick={scrollToWorkspaces}>
              Portfolio Organizations
            </button>
          </section>

          <section className="gc-kpi-section">
            <div className="gc-section-header gc-section-header--tight">
              <div>
                <h2>Operational KPIs</h2>
                <p>Institutional control metrics</p>
              </div>
            </div>
            <div className="gc-kpi-grid">
              <article className="gc-kpi-card">
                <span>Active Organizations</span>
                <strong>{activeOrganizationCount}</strong>
              </article>
              <article className="gc-kpi-card">
                <span>Outstanding Compliance Alerts</span>
                <strong>{complianceAlertCount}</strong>
              </article>
              <article className="gc-kpi-card">
                <span>Pending Capital Tasks</span>
                <strong>{pendingCapitalTasks}</strong>
              </article>
            </div>
          </section>

          <div className="gc-main-grid">
            <section className="gc-section gc-overview-panel">
              <div className="gc-section-header gc-section-header--tight">
                <div>
                  <h2>Today’s Equity Overview</h2>
                  <p>Operational readiness</p>
                </div>
              </div>
              <div className="gc-equity-overview">
                {todaysOverview.map((item) => (
                  <div key={item} className="gc-equity-overview-item">
                    <span className="gc-equity-overview-dot" />
                    <p>{item}</p>
                  </div>
                ))}
              </div>
            </section>

            <aside className="gc-side-stack gc-institutional-rail">
              <section className="gc-section gc-tools-section">
                <div className="gc-section-header gc-section-header--tight">
                  <div>
                    <h2>Equity Tools</h2>
                    <p>Capital navigation</p>
                  </div>
                </div>
                <div className="gc-tools-list">
                  {equityTools.map((tool) => (
                    <div key={tool} className="gc-tool-item">{tool}</div>
                  ))}
                </div>
              </section>

              <section className="gc-section gc-notif-section">
                <div className="gc-section-header gc-section-header--tight">
                  <div>
                    <h2>Compliance Feed</h2>
                    <p>Global alerts and status</p>
                  </div>
                  {notifs.length > 0 && <span className="gc-notif-badge">{complianceAlertCount}</span>}
                </div>
                {notifs.length === 0 ? (
                  <div className="gc-notif-empty">
                    <span>All compliance obligations are current</span>
                  </div>
                ) : (
                  <ul className="gc-notif-list">
                    {notifs.slice(0, 5).map((n, i) => (
                      <li key={n.id || i} className={`gc-notif-item sev-${n.severity}`}>
                        <div className="gc-notif-dot" />
                        <div className="gc-notif-content">
                          <p className="gc-notif-msg">{n.message}</p>
                          {n.daysLeft !== null && (
                            <span className="gc-notif-time">
                              {n.daysLeft <= 0 ? `Overdue by ${Math.abs(n.daysLeft)}d` : `Due in ${n.daysLeft} days`}
                            </span>
                          )}
                        </div>
                        <span className={`gc-notif-sev gc-sev-${n.severity}`}>
                          {n.severity === 'critical' ? 'Critical' : n.severity === 'high' ? 'High' : 'Medium'}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            </aside>
          </div>

          <footer className="gc-capital-footer">
            <span>PrimeSource Equity • Global Capital Infrastructure • Systems Operational</span>
          </footer>

      {inviteModalOpen && (
        <div className="gc-modal-backdrop" role="presentation" onClick={() => !inviteSaving && setInviteModalOpen(false)}>
          <div className="gc-modal" role="dialog" aria-modal="true" aria-labelledby="global-invite-title" onClick={(event) => event.stopPropagation()}>
            <div className="gc-modal-header">
              <div>
                <p className="gc-modal-kicker">Global Invite</p>
                <h3 id="global-invite-title">Invite User to an Organization</h3>
              </div>
              <button className="gc-modal-close" onClick={() => setInviteModalOpen(false)} disabled={inviteSaving} aria-label="Close invite dialog">
                ×
              </button>
            </div>
            <p className="gc-modal-copy">
              Use a user ID to attach someone to an organization. Department, role, and module access stay inside that organization environment.
            </p>
            <div className="gc-modal-grid">
              <label className="gc-modal-field">
                <span>Email or User ID</span>
                <input
                  type="text"
                  value={inviteForm.invitee}
                  onChange={(event) => setInviteForm((current) => ({ ...current, invitee: event.target.value }))}
                  placeholder="e.g. ada@example.com or 42"
                />
              </label>
              <label className="gc-modal-field">
                <span>Organization</span>
                <select
                  value={inviteForm.workspaceId}
                  onChange={(event) => setInviteForm((current) => ({ ...current, workspaceId: event.target.value }))}
                >
                  <option value="">Select an organization</option>
                  {workspaceSelectOptions.map((workspace) => (
                    <option key={workspace.value} value={workspace.value}>{workspace.label}</option>
                  ))}
                </select>
              </label>
            </div>
            {inviteError && <div className="gc-modal-error">{inviteError}</div>}
            {inviteSuccess && <div className="gc-modal-success">{inviteSuccess}</div>}
            <div className="gc-modal-actions">
              <button className="gc-action-btn gc-action-secondary" onClick={() => setInviteModalOpen(false)} disabled={inviteSaving}>Cancel</button>
              <button className="gc-action-btn gc-action-primary" onClick={handleInviteUser} disabled={inviteSaving}>
                {inviteSaving ? 'Inviting…' : 'Send Global Invite'}
              </button>
            </div>
          </div>
        </div>
      )}
      </div>{/* /.global-console */}
      </div>{/* /.gc-body */}
    </div>
  );
};

export default GlobalConsole;
