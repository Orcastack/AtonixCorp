import React, { useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../../context/EnterpriseContext';
import { hasEquityModule } from '../../../utils/workspaceModules';
import './WorkspaceModules.css';
import './WorkspaceOverview.css';

const ENTITY_TYPE_LABELS = {
  sole_proprietor: 'Sole Proprietor',
  llc: 'LLC',
  partnership: 'Partnership',
  corporation: 'Corporation',
  nonprofit: 'Non-Profit',
  subsidiary: 'Subsidiary',
  branch: 'Branch',
  other: 'Other',
  holding_company: 'Holding Company',
  non_profit: 'Non-Profit',
  sole_proprietorship: 'Sole Proprietorship',
  trust: 'Trust',
};

const STATUS_CONFIG = {
  active: { label: 'Active', cls: 'wso-badge-active' },
  dormant: { label: 'Dormant', cls: 'wso-badge-dormant' },
  wind_down: { label: 'Wind-Down', cls: 'wso-badge-winddown' },
  suspended: { label: 'Suspended', cls: 'wso-badge-dormant' },
  archived: { label: 'Archived', cls: 'wso-badge-winddown' },
  draft: { label: 'Draft', cls: 'wso-badge-dormant' },
};

const MEMBER_ROLE_COUNTS = [
  { label: 'Owners', value: 1 },
  { label: 'Admins', value: 0 },
  { label: 'Members', value: 0 },
  { label: 'Viewers', value: 0 },
];

const PERMISSION_PREVIEW = [
  { action: 'Invite members', owner: true, admin: true, member: false, viewer: false },
  { action: 'Schedule meetings', owner: true, admin: true, member: true, viewer: false },
  { action: 'Upload files', owner: true, admin: true, member: true, viewer: false },
  { action: 'Edit settings', owner: true, admin: true, member: false, viewer: false },
];

const REQUIRED_MODULES = [
  { key: 'members', name: 'Members' },
  { key: 'groups', name: 'Departments' },
  { key: 'meetings', name: 'Meetings' },
  { key: 'calendar', name: 'Calendar' },
  { key: 'files', name: 'Files' },
  { key: 'permissions', name: 'Permissions' },
  { key: 'settings', name: 'Settings' },
];

const OPTIONAL_MODULES = [
  { key: 'email', name: 'Email' },
  { key: 'marketing', name: 'Marketing' },
];

const CALENDAR_DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const MAIL_FOLDERS = ['Inbox', 'Sent', 'Drafts', 'Trash'];
const MARKETING_FILTERS = ['All', 'Draft', 'Active', 'Completed'];

const fmtDate = (val) => {
  if (!val) return null;
  try {
    return new Date(val).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  } catch {
    return val;
  }
};

const fmtShortDate = (val) => {
  if (!val) return null;
  try {
    return new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return val;
  }
};

const DetailRow = ({ label, value, capitalize }) =>
  value ? (
    <tr className="wso-detail-row">
      <td className="wso-detail-label">{label}</td>
      <td className="wso-detail-value" style={capitalize ? { textTransform: 'capitalize' } : {}}>
        {value}
      </td>
    </tr>
  ) : null;

const ModuleToggleCard = ({ name, enabled }) => (
  <div className={`wso-toggle-card${enabled ? ' enabled' : ''}`}>
    <span>{name}</span>
    <strong>{enabled ? 'On' : 'Off'}</strong>
  </div>
);

const WorkspaceOverview = () => {
  const { workspaceId } = useParams();
  const navigate = useNavigate();
  const { activeWorkspace, entities, getWorkspacePermissionSummary } = useEnterprise();
  const [mailFolder, setMailFolder] = useState('Inbox');
  const [marketingFilter, setMarketingFilter] = useState('All');

  const ws = useMemo(() => {
    if (workspaceId) {
      const fromList = (entities || []).find((entity) => String(entity.id) === String(workspaceId));
      if (fromList) return fromList;
      if (activeWorkspace && String(activeWorkspace.id) === String(workspaceId)) return activeWorkspace;
      try {
        const saved = localStorage.getItem('ledgora_active_workspace');
        if (saved) {
          const parsed = JSON.parse(saved);
          if (String(parsed.id) === String(workspaceId)) return parsed;
        }
      } catch {
        return activeWorkspace || {};
      }
    }
    return activeWorkspace || {};
  }, [workspaceId, activeWorkspace, entities]);
  const permissionSummary = getWorkspacePermissionSummary(ws.id || workspaceId);

  const statusCfg = STATUS_CONFIG[ws.status] || { label: ws.status || 'Active', cls: 'wso-badge-active' };
  const entityLabel = ENTITY_TYPE_LABELS[ws.entity_type] || ws.entity_type || '—';
  const initials = (ws.name || 'W').slice(0, 2).toUpperCase();
  const equityEnabled = hasEquityModule(ws);
  const workspaceTypeLabel = ws.workspace_type_label || ws.workspace_type || ws.hierarchy_metadata?.workspace_type_label || null;
  const hierarchyMetadata = ws.hierarchy_metadata || {};
  const dashboardNames = ws.dashboard_config?.dashboards || [];
  const branchLabel = hierarchyMetadata.selected_branch_label || hierarchyMetadata.selected_branch || null;
  const subBranchLabel = hierarchyMetadata.selected_sub_branch_label || hierarchyMetadata.selected_sub_branch || null;
  const enabledModules = useMemo(() => {
    const fallbackModules = [
      ...REQUIRED_MODULES.map((module) => module.key),
      ...OPTIONAL_MODULES.map((module) => module.key),
    ];
    return new Set(
      Array.isArray(ws.enabled_modules) && ws.enabled_modules.length > 0
        ? ws.enabled_modules
        : fallbackModules
    );
  }, [ws.enabled_modules]);

  const goToWorkspaceModule = (module) => {
    if (!ws.id) return;
    navigate(`/app/workspace/${ws.id}/${module}`);
  };

  const canOpenEntityDashboard = Boolean(permissionSummary?.dashboards?.entity_dashboard);

  return (
    <div className="wsm-page wso-root">
      <div className="wsm-page-header">
        <div>
          <h1 className="wsm-page-title">{ws.name || 'Workspace Overview'}</h1>
        </div>
      </div>

      <div className="wso-entity-card">
        <div className="wso-entity-hero">
          <div className="wso-entity-avatar">{initials}</div>
          <div className="wso-entity-identity">
            <h2 className="wso-entity-name">{ws.name || '—'}</h2>
            <div className="wso-entity-badges">
              <span className={`wso-badge ${statusCfg.cls}`}>{statusCfg.label}</span>
              {ws.entity_type && <span className="wso-badge wso-badge-type">{entityLabel}</span>}
              {ws.local_currency && <span className="wso-badge wso-badge-currency">{ws.local_currency}</span>}
            </div>
          </div>
        </div>

        <div className="wso-entity-details">
          <div className="wso-detail-col">
            <div className="wso-detail-col-title">Registration</div>
            <table className="wso-detail-table">
              <tbody>
                <DetailRow label="Legal Name" value={ws.name} />
                <DetailRow label="Entity Type" value={entityLabel} />
                <DetailRow label="Workspace Type" value={workspaceTypeLabel} />
                <DetailRow label="Branch" value={branchLabel} />
                <DetailRow label="Sub-branch" value={subBranchLabel} />
                <DetailRow label="Registration No." value={ws.registration_number} />
                <DetailRow label="Country" value={ws.country} />
                <DetailRow label="Status" value={statusCfg.label} />
              </tbody>
            </table>
          </div>

          <div className="wso-detail-col">
            <div className="wso-detail-col-title">Finance & Compliance</div>
            <table className="wso-detail-table">
              <tbody>
                <DetailRow label="Functional Currency" value={ws.local_currency} />
                <DetailRow label="Fiscal Year End" value={fmtDate(ws.fiscal_year_end)} />
                <DetailRow label="Next Filing Date" value={fmtShortDate(ws.next_filing_date)} />
                <DetailRow label="Main Bank" value={ws.main_bank} />
                <DetailRow
                  label="Tax Authority"
                  value={
                    ws.tax_authority_url ? (
                      <a href={ws.tax_authority_url} target="_blank" rel="noreferrer" className="wso-link">
                        {ws.tax_authority_url}
                      </a>
                    ) : null
                  }
                />
              </tbody>
            </table>
          </div>
        </div>

        <div className="wso-entity-footer">
          {(ws.parent_entity_name || ws.parent_entity) && (
            <span className="wso-footer-item">
              <span className="wso-footer-label">Parent Entity</span>
              {ws.parent_entity_name || `#${ws.parent_entity}`}
            </span>
          )}
          {ws.created_at && (
            <span className="wso-footer-item">
              <span className="wso-footer-label">Created</span>
              {fmtDate(ws.created_at)}
            </span>
          )}
          {dashboardNames.length > 0 && (
            <span className="wso-footer-item">
              <span className="wso-footer-label">Dashboards</span>
              {dashboardNames.join(', ')}
            </span>
          )}
          {canOpenEntityDashboard && (
            <button className="wso-btn-primary" onClick={() => navigate(`/app/enterprise/entities/${ws.id}/dashboard`)}>
              Open Entity Dashboard →
            </button>
          )}
          {equityEnabled && canOpenEntityDashboard && (
            <button className="wso-btn-primary" onClick={() => navigate(`/app/equity/${ws.id}/registry`)}>
              Open Equity Management →
            </button>
          )}
        </div>
      </div>

      <div className="wso-dashboard-grid">
        <section className="wso-dashboard-section">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Members</h2>
              <p className="wso-section-sub">Membership and role coverage for this workspace.</p>
            </div>
            <button className="wso-section-link" onClick={() => goToWorkspaceModule('members')}>Open Members</button>
          </div>
          <div className="wso-card-grid compact">
            {MEMBER_ROLE_COUNTS.map((role) => (
              <div key={role.label} className="wso-mini-stat-card">
                <span className="wso-mini-stat-label">{role.label}</span>
                <span className="wso-mini-stat-value">{role.value}</span>
              </div>
            ))}
          </div>
          <div className="wso-inline-empty">No invited members yet. Invite someone from the members module.</div>
        </section>

        <section className="wso-dashboard-section">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Departments</h2>
              <p className="wso-section-sub">Organize members into finance departments, teams, and operating units.</p>
            </div>
            <button className="wso-section-link" onClick={() => goToWorkspaceModule('departments')}>Open Departments</button>
          </div>
          <div className="wso-inline-empty">No departments yet. Create one to structure ownership, permissions, and collaboration.</div>
        </section>

        <section className="wso-dashboard-section">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Meetings</h2>
              <p className="wso-section-sub">Upcoming board calls, internal syncs, and workspace reviews.</p>
            </div>
            <button className="wso-section-link" onClick={() => goToWorkspaceModule('meetings')}>Open Meetings</button>
          </div>
          <div className="wso-inline-empty">No upcoming meetings. Schedule one from the meetings workspace module.</div>
        </section>

        <section className="wso-dashboard-section">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Calendar</h2>
              <p className="wso-section-sub">Deadlines, milestones, and workspace-wide timing in one view.</p>
            </div>
            <button className="wso-section-link" onClick={() => goToWorkspaceModule('calendar')}>Open Calendar</button>
          </div>
          <div className="wso-calendar-preview">
            {CALENDAR_DAYS.map((day) => (
              <span key={day} className="wso-calendar-day">{day}</span>
            ))}
            {Array.from({ length: 14 }).map((_, index) => (
              <div key={index} className={`wso-calendar-cell${index === 5 ? ' today' : ''}`}>
                {index + 1}
              </div>
            ))}
          </div>
        </section>

        <section className="wso-dashboard-section full-width">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Files</h2>
              <p className="wso-section-sub">Uploads, shared documents, and operational working files.</p>
            </div>
            <button className="wso-section-link" onClick={() => goToWorkspaceModule('files')}>Open Files</button>
          </div>
          <div className="wso-file-dropzone">Drop files here or open the Files module to upload and organize documents.</div>
          <div className="wso-inline-empty">No workspace files uploaded yet.</div>
        </section>

        <section className="wso-dashboard-section full-width">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Management</h2>
              <p className="wso-section-sub">Permissions and settings brought into the same workspace dashboard.</p>
            </div>
          </div>
          <div className="wso-management-grid">
            <div className="wso-management-panel">
              <div className="wso-panel-header">
                <h3>Permissions</h3>
                <button className="wso-section-link" onClick={() => goToWorkspaceModule('permissions')}>Open Permissions</button>
              </div>
              <div className="wso-permission-matrix">
                <div className="wso-permission-row header">
                  <span>Permission</span>
                  <span>Owner</span>
                  <span>Admin</span>
                  <span>Member</span>
                  <span>Viewer</span>
                </div>
                {PERMISSION_PREVIEW.map((permission) => (
                  <div key={permission.action} className="wso-permission-row">
                    <span>{permission.action}</span>
                    <span>{permission.owner ? '+' : '—'}</span>
                    <span>{permission.admin ? '+' : '—'}</span>
                    <span>{permission.member ? '+' : '—'}</span>
                    <span>{permission.viewer ? '+' : '—'}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="wso-management-panel">
              <div className="wso-panel-header">
                <h3>Settings</h3>
                <button className="wso-section-link" onClick={() => goToWorkspaceModule('settings')}>Open Settings</button>
              </div>
              <div className="wso-settings-summary">
                <div className="wso-settings-row"><span>Workspace Name</span><strong>{ws.name || '—'}</strong></div>
                <div className="wso-settings-row"><span>Status</span><strong>{statusCfg.label}</strong></div>
                <div className="wso-settings-row"><span>Currency</span><strong>{ws.local_currency || '—'}</strong></div>
                <div className="wso-settings-row"><span>Entity Type</span><strong>{entityLabel}</strong></div>
              </div>
              <div className="wso-toggle-grid">
                {REQUIRED_MODULES.map((module) => (
                  <ModuleToggleCard key={module.key} name={module.name} enabled={enabledModules.has(module.key)} />
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="wso-dashboard-section full-width">
          <div className="wso-section-header">
            <div>
              <h2 className="wso-section-title">Optional</h2>
              <p className="wso-section-sub">Email and marketing live here when the workspace turns them on.</p>
            </div>
          </div>
          <div className="wso-management-grid">
            <div className="wso-management-panel">
              <div className="wso-panel-header">
                <h3>Email</h3>
                <button className="wso-section-link" onClick={() => goToWorkspaceModule('email')}>Open Email</button>
              </div>
              <div className="wso-chip-row">
                {MAIL_FOLDERS.map((folder) => (
                  <button
                    key={folder}
                    type="button"
                    className={`wso-chip${mailFolder === folder ? ' active' : ''}`}
                    onClick={() => setMailFolder(folder)}
                  >
                    {folder}
                  </button>
                ))}
              </div>
              <div className="wso-inline-empty">No messages in {mailFolder.toLowerCase()}.</div>
            </div>

            <div className="wso-management-panel">
              <div className="wso-panel-header">
                <h3>Marketing</h3>
                <button className="wso-section-link" onClick={() => goToWorkspaceModule('marketing')}>Open Marketing</button>
              </div>
              <div className="wso-card-grid compact">
                <div className="wso-mini-stat-card">
                  <span className="wso-mini-stat-label">Campaigns</span>
                  <span className="wso-mini-stat-value">0</span>
                </div>
                <div className="wso-mini-stat-card">
                  <span className="wso-mini-stat-label">Active</span>
                  <span className="wso-mini-stat-value">0</span>
                </div>
                <div className="wso-mini-stat-card">
                  <span className="wso-mini-stat-label">Open Rate</span>
                  <span className="wso-mini-stat-value">—</span>
                </div>
              </div>
              <div className="wso-chip-row">
                {MARKETING_FILTERS.map((status) => (
                  <button
                    key={status}
                    type="button"
                    className={`wso-chip${marketingFilter === status ? ' active' : ''}`}
                    onClick={() => setMarketingFilter(status)}
                  >
                    {status}
                  </button>
                ))}
              </div>
              <div className="wso-inline-empty">No {marketingFilter.toLowerCase()} campaigns yet.</div>
            </div>
          </div>
          <div className="wso-toggle-grid">
            {OPTIONAL_MODULES.map((module) => (
              <ModuleToggleCard key={module.key} name={module.name} enabled={enabledModules.has(module.key)} />
            ))}
          </div>
        </section>
      </div>

      <div className="wsm-stats-row">
        <div className="wsm-stat-card">
          <span className="wsm-stat-label">Status</span>
          <span className="wsm-stat-value wsm-stat-value-caps">{statusCfg.label}</span>
        </div>
        <div className="wsm-stat-card">
          <span className="wsm-stat-label">Country</span>
          <span className="wsm-stat-value">{ws.country || '—'}</span>
        </div>
        <div className="wsm-stat-card">
          <span className="wsm-stat-label">Currency</span>
          <span className="wsm-stat-value">{ws.local_currency || '—'}</span>
        </div>
        <div className="wsm-stat-card">
          <span className="wsm-stat-label">Entity Type</span>
          <span className="wsm-stat-value">{entityLabel}</span>
        </div>
        {ws.fiscal_year_end && (
          <div className="wsm-stat-card">
            <span className="wsm-stat-label">Fiscal Year End</span>
            <span className="wsm-stat-value">{fmtDate(ws.fiscal_year_end)}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkspaceOverview;
