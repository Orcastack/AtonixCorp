import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useEnterprise } from '../../context/EnterpriseContext';
import AtonixCorpLogo from '../../components/branding/AtonixCorpLogo';
import { globalInviteAPI, platformAuditEventsAPI, platformTasksAPI } from '../../services/api';
import { buildBalancedMetricOrder, useAnimatedNumber } from '../../utils/dashboardMetrics';
import '../../styles/premiumDashboards.css';
import './GlobalConsole.css';

/* ─────────────────────────────────────────────────────────────────────────────
  AtonixCorp Console
  The organization control center a user sees immediately after login.
  Shows: My Entities · Notifications · Tasks · Quick Actions
───────────────────────────────────────────────────────────────────────────── */

const openStandalonePath = (path) => {
  window.open(`${process.env.PUBLIC_URL || ''}${path}`, '_blank', 'noopener,noreferrer');
};

const normalizeCollection = (payload) => {
  if (Array.isArray(payload)) return payload;
  if (Array.isArray(payload?.results)) return payload.results;
  return [];
};

const auditSeverity = (event) => {
  if (['approval_rejected', 'workflow_run_failed', 'deadline_deleted'].includes(event.action)) return 'critical';
  if (['approval_requested', 'approval_progressed', 'workflow_run_started'].includes(event.action)) return 'high';
  return 'medium';
};

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
    loading,
    complianceDeadlines,
    hasPermission,
    PERMISSIONS,
  } = useEnterprise();

  const [profileOpen, setProfileOpen] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [currentTime, setCurrentTime] = useState(() => new Date());
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [inviteSaving, setInviteSaving] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');
  const [inviteForm, setInviteForm] = useState({ invitee: '', workspaceId: '' });
  const profileRef = useRef(null);
  const onboardingEnteredAtRef = useRef(null);
  const onboardingCtaClickedRef = useRef(false);
  const panelPreferenceKey = `atonixcorp_console_panels_${user?.id || 'guest'}`;
  const [expandedPanels, setExpandedPanels] = useState({});

  useEffect(() => {
    try {
      const savedPanels = JSON.parse(localStorage.getItem(panelPreferenceKey) || '{}');
      setExpandedPanels(savedPanels && typeof savedPanels === 'object' ? savedPanels : {});
    } catch {
      setExpandedPanels({});
    }
  }, [panelPreferenceKey]);

  const togglePanel = useCallback((panel) => {
    setExpandedPanels((current) => {
      const next = { ...current, [panel]: !current[panel] };
      localStorage.setItem(panelPreferenceKey, JSON.stringify(next));
      emitAnalyticsEvent('console_panel_toggle', {
        panel,
        expanded: next[panel],
        userId: user?.id || null,
        organizationId: currentOrganization?.id || null,
      });
      return next;
    });
  }, [currentOrganization?.id, panelPreferenceKey, user?.id]);

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

  const loadPlatformData = useCallback(async () => {
    if (!user?.id) return;
    try {
      const [taskResponse, auditResponse] = await Promise.all([
        platformTasksAPI.getAll({
          assignee_id: user?.id,
          state: 'open',
        }),
        platformAuditEventsAPI.getAll({ actor_id: user?.id }),
      ]);
      setTasks(normalizeCollection(taskResponse.data).slice(0, 8));
      setAuditEvents(normalizeCollection(auditResponse.data).slice(0, 8));
    } catch (error) {
      setTasks([]);
      setAuditEvents([]);
    }
  }, [user?.id]);

  useEffect(() => {
    let active = true;

    const syncConsole = async () => {
      if (!active) return;
      await loadPlatformData();
    };

    if (user?.id) {
      syncConsole();
    }

    const handleFocus = () => {
      if (user?.id) {
        syncConsole();
      }
    };

    const timer = window.setInterval(() => {
      if (user?.id) {
        syncConsole();
      }
    }, 30000);

    window.addEventListener('focus', handleFocus);

    return () => {
      active = false;
      window.clearInterval(timer);
      window.removeEventListener('focus', handleFocus);
    };
  }, [loadPlatformData, user?.id]);

  const entityCount = entities.length;
  const showOrganizationOnboarding = !loading && organizations.length === 0;
  const ownedOrganizationOptions = organizations.filter((org) => (
    org.owner_email && org.owner_email === user?.email
  )).map((org) => ({
    value: String(org.id),
    label: `${org.name} (${org.registration_number || 'Registration pending'})`,
  }));

  const handleInviteUser = async () => {
    setInviteError('');
    setInviteSuccess('');

    const workspaceId = String(inviteForm.workspaceId || '').trim();
    const invitee = String(inviteForm.invitee || '').trim().toLowerCase();

    if (!workspaceId || !invitee) {
      setInviteError('Organization and invitee are required.');
      return;
    }

    if (!/^\S+@\S+\.\S+$/.test(invitee)) {
      setInviteError('Enter a valid email address for the invitation.');
      return;
    }

    setInviteSaving(true);
    try {
      const payload = { organization_id: Number(workspaceId), email: invitee, role_code: 'VIEWER' };
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


      const newsItems = [
        ...auditEvents.slice(0, 3).map((event) => ({
          id: `audit-${event.id}`,
          tag: 'Update',
          title: event.summary,
          body: event.action || 'Organizational activity',
        })),
        ...((globalNotifications || []).slice(0, 2).map((item, index) => ({
          id: `notification-${item.id || index}`,
          tag: 'Alert',
          title: item.message || item.summary || 'Organization alert',
          body: item.type || 'News component',
        }))),
        ...((complianceDeadlines || []).slice(0, 2).map((deadline, index) => ({
          id: `deadline-${deadline.id || index}`,
          tag: 'Market',
          title: deadline.title || 'Compliance update',
          body: deadline.deadline_date ? `Due ${deadline.deadline_date}` : 'Compliance deadline',
        }))),
      ].slice(0, 6);
  const userInitial = (user?.name || user?.email || 'U').charAt(0).toUpperCase();
  const consoleIdentity = user?.is_superuser ? 'Curated by Samuel' : (currentOrganization?.name || 'AtonixCorp Console');

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
  const visibleAuditCount = auditEvents.length;
  const liveMetricCards = buildBalancedMetricOrder([
    { label: 'Active Organizations', value: activeOrganizationCount, note: 'Available through the premium console' },
    { label: 'Open Tasks', value: pendingCapitalTasks, note: 'Action items awaiting review' },
    { label: 'Compliance Alerts', value: complianceAlertCount, note: 'High-priority items requiring attention' },
    { label: 'Audit Events', value: visibleAuditCount, note: 'Recent governance activity' },
  ], user?.id || activeOrganizationCount);
  const animatedOrganizationCount = useAnimatedNumber(activeOrganizationCount, 700);
  const animatedTaskCount = useAnimatedNumber(pendingCapitalTasks, 700);
  const animatedAlertCount = useAnimatedNumber(complianceAlertCount, 700);
  const animatedAuditCount = useAnimatedNumber(visibleAuditCount, 700);
  const marketPulse = [
    { label: 'Equity Market Index', value: 'No data connected', tone: 'muted' },
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
  const canSeeEnterprise = hasPermission(PERMISSIONS.VIEW_ORG_OVERVIEW);
  const canSeeEntity = hasPermission(PERMISSIONS.VIEW_ENTITIES);
  const canSeeWorkspace = hasPermission(PERMISSIONS.VIEW_TEAM) || canSeeEnterprise;
  const visibleConsoleSections = [
    canSeeWorkspace && { key: 'workspace', label: 'Workspace', note: 'Tasks, collaboration, and shared work' },
    canSeeEntity && { key: 'entity', label: 'Entity', note: 'Compliance, governance, and filings' },
    canSeeEntity && { key: 'equity', label: 'Equity', note: 'Capital tables and vesting schedules' },
    canSeeEnterprise && { key: 'enterprise', label: 'Enterprise', note: 'Organizations, policies, and global oversight' },
  ].filter(Boolean);

  return (
    <div className="global-console-page premium-dashboard-shell">

      {/* ── TOP NAVBAR ──────────────────────────────────────────────── */}
      <header className="gc-topnav">
        <div className="gc-topnav-left">
          <div className="gc-topnav-brand">
            <AtonixCorpLogo variant="white" size="small" withText text="AtonixCorp" />
          </div>
          <span className="gc-topnav-identity">{consoleIdentity}</span>
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
              <button className="gc-topnav-dd-item" onClick={() => { setProfileOpen(false); navigate('/app/console/settings'); }}>
                Settings Console
              </button>
              <button className="gc-topnav-dd-item" onClick={() => { setProfileOpen(false); openStandalonePath('/app/console/settings/support-center'); }}>
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

      <section className="premium-shell-body">
        <div className="premium-hero premium-glow-on-update">
          <div className="premium-hero-copy">
            <div className="premium-hero-kicker">Workspace command center</div>
            <h1 className="premium-hero-title">Operational clarity for tasks, projects, and collaboration.</h1>
            <p className="premium-hero-text">
              The console now uses the unified premium dashboard language: deep navy structure, platinum surfaces,
              gold accents, and balanced metric cards with subtle motion.
            </p>
            <div className="premium-hero-tags">
              <span className="premium-hero-tag">{Math.round(animatedOrganizationCount)} active organizations</span>
              <span className="premium-hero-tag">{Math.round(animatedTaskCount)} open tasks</span>
              <span className="premium-hero-tag">{Math.round(animatedAlertCount)} compliance alerts</span>
              <span className="premium-hero-tag">{Math.round(animatedAuditCount)} audit events</span>
            </div>
          </div>
          <div className="premium-hero-meta">
            {liveMetricCards.map((card) => (
              <article key={card.label} className={`premium-metric-card ${card.metricClassName || ''}`}>
                <span className="premium-metric-label">{card.label}</span>
                <strong className="premium-metric-value premium-countup">{card.value}</strong>
                <span className="premium-metric-note">{card.note}</span>
              </article>
            ))}
          </div>
        </div>

        {(expandedPanels.workspace || expandedPanels.entity || expandedPanels.enterprise) && (
        <div className="premium-dashboard-grid premium-grid-3 gc-expandable-content">
          <section className="premium-panel premium-section">
            <div className="premium-section-header">
              <div>

              <section className="gc-console-sections" aria-label="Authorized dashboard sections">
                <div className="gc-console-sections-header">
                  <div>
                    <div className="premium-section-kicker">Unified command surface</div>
                    <h2 className="premium-section-title">Your operating views</h2>
                  </div>
                  <span>{visibleConsoleSections.length} authorized views</span>
                </div>
                <div className="gc-console-section-list">
                  {visibleConsoleSections.map((section) => (
                    <button
                      type="button"
                      key={section.key}
                      className={`gc-console-section-toggle${expandedPanels[section.key] ? ' is-expanded' : ''}`}
                      aria-expanded={Boolean(expandedPanels[section.key])}
                      onClick={() => togglePanel(section.key)}
                    >
                      <span className="gc-console-section-icon" aria-hidden="true">{section.label.slice(0, 1)}</span>
                      <span className="gc-console-section-copy">
                        <strong>{section.label}</strong>
                        <small>{section.note}</small>
                      </span>
                      <span className="gc-console-section-state">{expandedPanels[section.key] ? 'Open' : 'View'}</span>
                    </button>
                  ))}
                </div>
              </section>
                <div className="premium-section-kicker">Team activity</div>
                <h2 className="premium-section-title">Collaboration and task flow</h2>
                <p className="premium-section-subtitle">Live operational work, grouped into a calm premium card layout.</p>
              </div>
            </div>
            <div className="gc-center-checks">
              {tasks.slice(0, 4).map((task) => (
                <div key={task.id}>
                  <span>{task.title || task.summary || 'Task'}</span>
                  <strong>{task.state || task.status || 'open'}</strong>
                </div>
              ))}
              {tasks.length === 0 && (
                <div>
                  <span>No open tasks</span>
                  <strong>Everything is currently clear</strong>
                </div>
              )}
            </div>
          </section>

          <section className="premium-panel premium-section">
            <div className="premium-section-header">
              <div>
                <div className="premium-section-kicker">Compliance feed</div>
                <h2 className="premium-section-title">Alerts and audit trail</h2>
                <p className="premium-section-subtitle">Compliance status remains visible in the same visual language across the console.</p>
              </div>
            </div>
            <div className="premium-compliance-feed">
              {notifs.slice(0, 4).map((item) => (
                <div key={item.id} className="premium-compliance-item">
                  <strong>{item.severity || 'info'}</strong>
                  <span>{item.message}</span>
                </div>
              ))}
            </div>
          </section>

        </div>
        )}
      </section>

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
          <span className="gc-capital-watermark">ATONIXCORP</span>
        </div>
      </section>

      <section className="gc-news-strip" aria-label="News feed">
        <div className="gc-section-header gc-section-header--tight">
          <div>
            <h2>News</h2>
            <p>Live organizational updates, compliance alerts, and market headlines</p>
          </div>
        </div>
        {newsItems.length === 0 ? (
          <div className="gc-news-empty">No news items yet.</div>
        ) : (
          <div className="gc-news-grid">
            {newsItems.map((item) => (
              <article key={item.id} className="gc-news-card">
                <span className="gc-news-tag">{item.tag}</span>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        )}
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
              Invite Member
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
                    <p>Organization alerts and status</p>
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
            <span>AtonixCorp • Financial Management Platform • Systems Operational</span>
          </footer>

          <footer className="premium-footer">
            <div className="premium-footer-group">
              <span className="premium-status-pill">Compliance current</span>
              <span className="premium-footer-note">AtonixCorp premium console shell</span>
            </div>
            <div className="premium-footer-group">
              <span className="premium-footer-note">Unified workspace, entity, and equity design system</span>
            </div>
          </footer>

      {inviteModalOpen && (
        <div className="gc-modal-backdrop" role="presentation" onClick={() => !inviteSaving && setInviteModalOpen(false)}>
          <div className="gc-modal" role="dialog" aria-modal="true" aria-labelledby="organization-invite-title" onClick={(event) => event.stopPropagation()}>
            <div className="gc-modal-header">
              <div>
                <p className="gc-modal-kicker">Organization Invite</p>
                <h3 id="organization-invite-title">Invite User to an Organization</h3>
              </div>
              <button className="gc-modal-close" onClick={() => setInviteModalOpen(false)} disabled={inviteSaving} aria-label="Close invite dialog">
                ×
              </button>
            </div>
            <p className="gc-modal-copy">
              Invite an email address to an organization you own. The invitation is assigned a Viewer role, recorded in the organization audit trail, and remains pending until accepted.
            </p>
            <div className="gc-modal-grid">
              <label className="gc-modal-field">
                <span>Invitee Email</span>
                <input
                  type="text"
                  value={inviteForm.invitee}
                  onChange={(event) => setInviteForm((current) => ({ ...current, invitee: event.target.value }))}
                  placeholder="e.g. ada@example.com"
                />
              </label>
              <label className="gc-modal-field">
                <span>Organization</span>
                <select
                  value={inviteForm.workspaceId}
                  onChange={(event) => setInviteForm((current) => ({ ...current, workspaceId: event.target.value }))}
                >
                  <option value="">Select an organization</option>
                  {ownedOrganizationOptions.map((workspace) => (
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
                {inviteSaving ? 'Inviting…' : 'Send Organization Invite'}
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
