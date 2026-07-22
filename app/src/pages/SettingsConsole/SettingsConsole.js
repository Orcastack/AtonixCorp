import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import { useEquity } from '../../context/EquityContext';
import { entitiesAPI, equityAPI, workspaceLogsAPI, workspaceSettingsAPI } from '../../services/api';
import '../../styles/premiumDashboards.css';
import './SettingsConsole.css';

const SECTIONS = [
  { key: 'workspace', label: 'Workspace' },
  { key: 'entity', label: 'Entity' },
  { key: 'equity', label: 'Equity' },
  { key: 'enterprise', label: 'Enterprise' },
  { key: 'billing', label: 'Billing' },
  { key: 'governance', label: 'Governance' },
];

const FORMATTER = new Intl.NumberFormat('en-US');

const SETTINGS_DEFAULTS = {
  orgName: '',
  orgCountry: '',
  currency: 'USD',
  fiscalYearEnd: '12-31',
  taxFilingFrequency: 'annual',
  accountingStandard: 'IFRS',
  subscriptionTier: 'enterprise',
  billingContactEmail: '',
};

const WORKSPACE_DEFAULTS = {
  workspace_label: '',
  timezone: 'UTC',
  default_currency: 'USD',
  collaboration_mode: 'standard',
  kpi_focus: '',
  audit_retention_days: '365',
};

const ENTITY_DEFAULTS = {
  name: '',
  country: '',
  local_currency: 'USD',
  entity_type: 'operating',
  status: 'active',
  workspace_type: 'accounting',
  workspace_mode: 'shared',
};

const EQUITY_PROFILE_DEFAULTS = {
  workspace_type: 'accounting',
  equity_enabled: true,
  ownership_registry_enabled: true,
  cap_table_enabled: true,
  valuation_enabled: true,
  equity_transactions_enabled: true,
  governance_reporting_enabled: true,
};

const EQUITY_POLICY_DEFAULTS = {
  require_explicit_reviewers: false,
  require_designated_backups: false,
  board_sla_hours: 72,
  legal_sla_hours: 72,
  escalation_enabled: true,
  escalation_grace_hours: 24,
  reminder_frequency_hours: 24,
};

const normalizeObject = (value) => (value && typeof value === 'object' ? value : {});

const SettingsConsole = () => {
  const navigate = useNavigate();
  const {
    currentOrganization,
    entities,
    activeWorkspace,
    hasPermission,
    updateOrganization,
    exportGovernanceConfiguration,
    exportGovernanceConfigurationToCloud,
    fetchGovernanceCloudExports,
    importGovernanceConfiguration,
  } = useEnterprise();
  const {
    workspaceId: equityWorkspaceId,
    profile,
    scenarioApprovalPolicy,
    summary,
    equityEnabled,
    updateScenarioApprovalPolicy,
    refreshEquity,
  } = useEquity();
  const canManageOrgSettings = hasPermission ? hasPermission('manage_org_settings') : true;

  const [activeSection, setActiveSection] = useState('workspace');
  const [workspaceSettings, setWorkspaceSettings] = useState(WORKSPACE_DEFAULTS);
  const [workspaceSaving, setWorkspaceSaving] = useState(false);
  const [workspaceError, setWorkspaceError] = useState(null);
  const [workspaceLogs, setWorkspaceLogs] = useState([]);

  const [orgForm, setOrgForm] = useState(SETTINGS_DEFAULTS);
  const [orgSaving, setOrgSaving] = useState(false);
  const [orgStatus, setOrgStatus] = useState(null);

  const [selectedEntityId, setSelectedEntityId] = useState('');
  const [entityForm, setEntityForm] = useState(ENTITY_DEFAULTS);
  const [entitySaving, setEntitySaving] = useState(false);
  const [entityStatus, setEntityStatus] = useState(null);

  const [equityProfileForm, setEquityProfileForm] = useState(EQUITY_PROFILE_DEFAULTS);
  const [equityPolicyForm, setEquityPolicyForm] = useState(EQUITY_POLICY_DEFAULTS);
  const [equitySaving, setEquitySaving] = useState(false);
  const [equityStatus, setEquityStatus] = useState(null);

  const [governanceBusy, setGovernanceBusy] = useState(false);
  const [governanceStatus, setGovernanceStatus] = useState(null);
  const [cloudExport, setCloudExport] = useState({
    provider: 'google_drive',
    fileName: '',
    oauthAccessToken: '',
    folderId: '',
    oneDrivePath: 'AtonixCorp',
    presignedUrl: '',
    overwrite: false,
  });
  const [cloudExportHistory, setCloudExportHistory] = useState([]);

  useEffect(() => {
    const org = currentOrganization || {};
    const settings = normalizeObject(org.settings);
    setOrgForm({
      orgName: org.name || '',
      orgCountry: org.primary_country || '',
      currency: org.primary_currency || 'USD',
      fiscalYearEnd: settings.fiscalYearEnd || '12-31',
      taxFilingFrequency: settings.taxFilingFrequency || 'annual',
      accountingStandard: settings.accountingStandard || 'IFRS',
      subscriptionTier: settings.subscription_tier || settings.subscriptionTier || 'enterprise',
      billingContactEmail: settings.billing_contact_email || settings.billingContactEmail || '',
    });
  }, [currentOrganization]);

  useEffect(() => {
    if (activeWorkspace?.id) {
      setWorkspaceSettings((current) => ({
        ...WORKSPACE_DEFAULTS,
        workspace_label: activeWorkspace.name ? `${activeWorkspace.name} Settings` : current.workspace_label,
        default_currency: activeWorkspace.local_currency || current.default_currency || 'USD',
      }));
      workspaceSettingsAPI.get(activeWorkspace.id)
        .then((response) => {
          const data = normalizeObject(response.data);
          setWorkspaceSettings((current) => ({ ...current, ...data }));
        })
        .catch((error) => {
          setWorkspaceError(error?.response?.data?.detail || error.message || 'Failed to load workspace settings.');
        });
      workspaceLogsAPI.getAll(activeWorkspace.id)
        .then((response) => setWorkspaceLogs(Array.isArray(response.data) ? response.data : []))
        .catch(() => setWorkspaceLogs([]));
    }
  }, [activeWorkspace?.id, activeWorkspace?.name, activeWorkspace?.local_currency]);

  useEffect(() => {
    const selectedEntity = entities.find((item) => String(item.id) === String(selectedEntityId)) || entities[0];
    if (!selectedEntity) {
      setSelectedEntityId('');
      setEntityForm(ENTITY_DEFAULTS);
      return;
    }

    setSelectedEntityId(String(selectedEntity.id));
    setEntityForm({
      name: selectedEntity.name || '',
      country: selectedEntity.country || '',
      local_currency: selectedEntity.local_currency || 'USD',
      entity_type: selectedEntity.entity_type || 'operating',
      status: selectedEntity.status || 'active',
      workspace_type: selectedEntity.workspace_type || 'accounting',
      workspace_mode: selectedEntity.workspace_mode || 'shared',
    });
  }, [entities, selectedEntityId]);

  useEffect(() => {
    const equityProfile = normalizeObject(profile);
    setEquityProfileForm({
      workspace_type: equityProfile.workspace_type || 'accounting',
      equity_enabled: Boolean(equityProfile.equity_enabled ?? true),
      ownership_registry_enabled: Boolean(equityProfile.ownership_registry_enabled ?? true),
      cap_table_enabled: Boolean(equityProfile.cap_table_enabled ?? true),
      valuation_enabled: Boolean(equityProfile.valuation_enabled ?? true),
      equity_transactions_enabled: Boolean(equityProfile.equity_transactions_enabled ?? true),
      governance_reporting_enabled: Boolean(equityProfile.governance_reporting_enabled ?? true),
    });
  }, [profile]);

  useEffect(() => {
    const policy = normalizeObject(scenarioApprovalPolicy);
    setEquityPolicyForm({
      require_explicit_reviewers: Boolean(policy.require_explicit_reviewers ?? false),
      require_designated_backups: Boolean(policy.require_designated_backups ?? false),
      board_sla_hours: policy.board_sla_hours || 72,
      legal_sla_hours: policy.legal_sla_hours || 72,
      escalation_enabled: Boolean(policy.escalation_enabled ?? true),
      escalation_grace_hours: policy.escalation_grace_hours || 24,
      reminder_frequency_hours: policy.reminder_frequency_hours || 24,
    });
  }, [scenarioApprovalPolicy]);

  useEffect(() => {
    if (!currentOrganization?.id) {
      setCloudExportHistory([]);
      return undefined;
    }

    let active = true;
    fetchGovernanceCloudExports(currentOrganization.id)
      .then((history) => {
        if (active) setCloudExportHistory(Array.isArray(history) ? history : []);
      })
      .catch(() => {
        if (active) setCloudExportHistory([]);
      });

    return () => {
      active = false;
    };
  }, [currentOrganization?.id, fetchGovernanceCloudExports]);

  const profileCards = useMemo(() => ([
    { label: 'Enterprise settings profile', value: `${currentOrganization?.name || 'Enterprise'} Settings`, note: currentOrganization?.enterprise_code || 'Enterprise code unavailable' },
    { label: 'Workspace settings profile', value: `${activeWorkspace?.name || 'Workspace'} Settings`, note: activeWorkspace?.workspace_code || 'Workspace code unavailable' },
    { label: 'Entity settings profile', value: `${(entities.find((item) => String(item.id) === String(selectedEntityId)) || entities[0] || {}).name || 'Entity'} Settings`, note: 'Name-inherited branch settings' },
    { label: 'Equity settings profile', value: `${(profile?.workspace?.name || activeWorkspace?.name || 'Equity')} Settings`, note: equityEnabled ? 'Equity control plane active' : 'Equity control plane disabled' },
  ]), [activeWorkspace?.name, activeWorkspace?.workspace_code, currentOrganization?.enterprise_code, currentOrganization?.name, entities, equityEnabled, profile, selectedEntityId]);

  const selectedEntity = entities.find((item) => String(item.id) === String(selectedEntityId)) || null;

  const handleOrgSave = async () => {
    if (!currentOrganization?.id) return;
    setOrgSaving(true);
    setOrgStatus(null);
    try {
      await updateOrganization(currentOrganization.id, {
        name: orgForm.orgName,
        primary_country: orgForm.orgCountry,
        primary_currency: orgForm.currency,
        settings: {
          ...(normalizeObject(currentOrganization.settings)),
          fiscalYearEnd: orgForm.fiscalYearEnd,
          taxFilingFrequency: orgForm.taxFilingFrequency,
          accountingStandard: orgForm.accountingStandard,
          subscription_tier: orgForm.subscriptionTier,
          billing_contact_email: orgForm.billingContactEmail,
        },
      });
      setOrgStatus('Saved');
    } catch (error) {
      setOrgStatus(error.message || 'Failed to save enterprise settings.');
    } finally {
      setOrgSaving(false);
    }
  };

  const handleWorkspaceSave = async () => {
    if (!activeWorkspace?.id) return;
    setWorkspaceSaving(true);
    setWorkspaceError(null);
    try {
      await workspaceSettingsAPI.update(activeWorkspace.id, workspaceSettings);
      setWorkspaceError(null);
      setWorkspaceSaving(false);
    } catch (error) {
      setWorkspaceError(error?.response?.data?.detail || error.message || 'Failed to save workspace settings.');
    } finally {
      setWorkspaceSaving(false);
    }
  };

  const handleEntitySave = async () => {
    if (!selectedEntity?.id) return;
    setEntitySaving(true);
    setEntityStatus(null);
    try {
      await entitiesAPI.update(selectedEntity.id, {
        ...selectedEntity,
        name: entityForm.name,
        country: entityForm.country,
        local_currency: entityForm.local_currency,
        entity_type: entityForm.entity_type,
        status: entityForm.status,
        workspace_type: entityForm.workspace_type,
        workspace_mode: entityForm.workspace_mode,
      });
      setEntityStatus('Saved');
      if (refreshEquity) {
        await refreshEquity(equityWorkspaceId || activeWorkspace?.linked_entity_id || activeWorkspace?.id);
      }
    } catch (error) {
      setEntityStatus(error.message || 'Failed to save entity settings.');
    } finally {
      setEntitySaving(false);
    }
  };

  const handleEquitySave = async () => {
    if (!profile?.id && !scenarioApprovalPolicy?.id) return;
    setEquitySaving(true);
    setEquityStatus(null);
    try {
      if (profile?.id) {
        await equityAPI.profile.update(equityWorkspaceId || selectedEntity?.id || profile.workspace?.id || activeWorkspace?.linked_entity_id || activeWorkspace?.id, profile.id, {
          ...normalizeObject(profile),
          workspace_type: equityProfileForm.workspace_type,
          equity_enabled: equityProfileForm.equity_enabled,
          ownership_registry_enabled: equityProfileForm.ownership_registry_enabled,
          cap_table_enabled: equityProfileForm.cap_table_enabled,
          valuation_enabled: equityProfileForm.valuation_enabled,
          equity_transactions_enabled: equityProfileForm.equity_transactions_enabled,
          governance_reporting_enabled: equityProfileForm.governance_reporting_enabled,
        });
      }
      if (scenarioApprovalPolicy?.id) {
        await updateScenarioApprovalPolicy(scenarioApprovalPolicy.id, equityPolicyForm);
      }
      if (refreshEquity) {
        await refreshEquity(equityWorkspaceId || activeWorkspace?.linked_entity_id || activeWorkspace?.id);
      }
      setEquityStatus('Saved');
    } catch (error) {
      setEquityStatus(error.message || 'Failed to save equity settings.');
    } finally {
      setEquitySaving(false);
    }
  };

  const handleExportGovernance = async () => {
    if (!currentOrganization?.id) return;
    setGovernanceBusy(true);
    setGovernanceStatus(null);
    try {
      await exportGovernanceConfiguration(currentOrganization.id);
      setGovernanceStatus('Downloaded YAML');
    } catch (error) {
      setGovernanceStatus(error.message || 'Failed to download YAML.');
    } finally {
      setGovernanceBusy(false);
    }
  };

  const handleImportGovernance = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !currentOrganization?.id) return;
    setGovernanceBusy(true);
    setGovernanceStatus(null);
    try {
      await importGovernanceConfiguration(currentOrganization.id, file);
      setGovernanceStatus('Imported YAML');
    } catch (error) {
      setGovernanceStatus(error.message || 'Failed to restore YAML.');
    } finally {
      setGovernanceBusy(false);
    }
  };

  const handleCloudExport = async () => {
    if (!currentOrganization?.id) return;
    setGovernanceBusy(true);
    setGovernanceStatus(null);
    try {
      const destination = {
        provider: cloudExport.provider,
        file_name: cloudExport.fileName || undefined,
        overwrite: cloudExport.overwrite,
      };
      if (cloudExport.provider === 'google_drive') {
        destination.oauth_access_token = cloudExport.oauthAccessToken;
        destination.folder_id = cloudExport.folderId || undefined;
      } else if (cloudExport.provider === 'onedrive') {
        destination.oauth_access_token = cloudExport.oauthAccessToken;
        destination.path = cloudExport.oneDrivePath || undefined;
      } else {
        destination.presigned_url = cloudExport.presignedUrl;
      }
      await exportGovernanceConfigurationToCloud(currentOrganization.id, destination);
      const history = await fetchGovernanceCloudExports(currentOrganization.id);
      setCloudExportHistory(Array.isArray(history) ? history : []);
      setGovernanceStatus('Exported to cloud');
    } catch (error) {
      setGovernanceStatus(error.message || 'Failed to export to cloud.');
    } finally {
      setGovernanceBusy(false);
    }
  };

  const changeCloudField = (field, value) => {
    setCloudExport((current) => ({ ...current, [field]: value }));
  };

  return (
    <section className="settings-console premium-dashboard-shell">
      <div className="premium-shell-body">
        <header className="settings-console-hero premium-hero">
          <div>
            <div className="premium-hero-kicker">Unified settings console</div>
            <h1 className="premium-hero-title">{currentOrganization?.name || 'AtonixCorp'} settings hub</h1>
            <p className="premium-hero-text">
              Workspace, entity, equity, enterprise, billing, and governance settings now live in one premium control surface with YAML export, restore, and cloud delivery.
            </p>
          </div>
          <div className="settings-console-hero-card premium-panel">
            <div className="settings-console-hero-row">
              <span className="premium-status-pill">Centralized</span>
              <span className="settings-console-hero-sub">Profiles inherit the branch name automatically.</span>
            </div>
            {!canManageOrgSettings && (
              <div className="settings-console-summary-copy">
                Limited access: your role can open the unified console, but enterprise billing and governance actions are locked.
              </div>
            )}
            <div className="settings-console-hero-row settings-console-link-row">
              <button type="button" className="eq-inline-btn primary" onClick={() => setActiveSection('governance')}>Open YAML tools</button>
              <button type="button" className="eq-inline-btn" onClick={() => navigate('/app/enterprise/org-overview')}>Back to console</button>
            </div>
          </div>
        </header>

        <div className="eq-metric-grid premium-grid-3 settings-console-summary">
          {profileCards.map((card) => (
            <article key={card.label} className="eq-metric-card premium-metric-card">
              <span className="eq-metric-label premium-metric-label">{card.label}</span>
              <strong className="eq-metric-value premium-metric-value">{card.value}</strong>
              <span className="eq-metric-note premium-metric-note">{card.note}</span>
            </article>
          ))}
        </div>

        <div className="settings-console-layout">
          <aside className="settings-console-sidebar premium-panel">
            {SECTIONS.map((section) => (
              <button
                key={section.key}
                type="button"
                className={`settings-console-tab ${activeSection === section.key ? 'active' : ''}`}
                onClick={() => setActiveSection(section.key)}
              >
                {section.label}
              </button>
            ))}
          </aside>

          <main className="settings-console-content">
            {activeSection === 'workspace' && (
              <section className="settings-console-section premium-panel">
                <div className="eq-data-card-head">
                  <h3>{`${activeWorkspace?.name || 'Workspace'} Settings`}</h3>
                  <span className="eq-status-chip success">Inherited profile</span>
                </div>
                <div className="settings-console-grid">
                  <label className="settings-console-field">
                    <span>Profile name</span>
                    <input value={workspaceSettings.workspace_label} onChange={(event) => setWorkspaceSettings((current) => ({ ...current, workspace_label: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Timezone</span>
                    <input value={workspaceSettings.timezone} onChange={(event) => setWorkspaceSettings((current) => ({ ...current, timezone: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Default currency</span>
                    <input value={workspaceSettings.default_currency} onChange={(event) => setWorkspaceSettings((current) => ({ ...current, default_currency: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Collaboration mode</span>
                    <input value={workspaceSettings.collaboration_mode} onChange={(event) => setWorkspaceSettings((current) => ({ ...current, collaboration_mode: event.target.value }))} />
                  </label>
                  <label className="settings-console-field full">
                    <span>KPI focus</span>
                    <input value={workspaceSettings.kpi_focus} onChange={(event) => setWorkspaceSettings((current) => ({ ...current, kpi_focus: event.target.value }))} placeholder="Cash, compliance, delivery, or growth" />
                  </label>
                  <label className="settings-console-field">
                    <span>Audit retention days</span>
                    <input type="number" min="1" value={workspaceSettings.audit_retention_days} onChange={(event) => setWorkspaceSettings((current) => ({ ...current, audit_retention_days: event.target.value }))} />
                  </label>
                </div>
                <div className="settings-console-actions">
                  <button type="button" className="eq-inline-btn primary" onClick={handleWorkspaceSave} disabled={workspaceSaving}>{workspaceSaving ? 'Saving…' : 'Save Workspace Settings'}</button>
                  <span className="settings-console-status">{workspaceError || 'Workspace settings persist to the branch key/value store.'}</span>
                </div>
                <div className="settings-console-audit">
                  <h4>Recent workspace activity</h4>
                  <div className="settings-console-log-list">
                    {workspaceLogs.slice(0, 6).map((log) => (
                      <article key={log.id} className="settings-console-log-item">
                        <strong>{log.action}</strong>
                        <span>{log.created_at}</span>
                      </article>
                    ))}
                    {!workspaceLogs.length && <p>No workspace audit entries yet.</p>}
                  </div>
                </div>
              </section>
            )}

            {activeSection === 'entity' && (
              <section className="settings-console-section premium-panel">
                <div className="eq-data-card-head">
                  <h3>{`${(selectedEntity?.name || 'Entity')} Settings`}</h3>
                  <span className="eq-status-chip success">Name inherited</span>
                </div>
                <div className="settings-console-grid">
                  <label className="settings-console-field">
                    <span>Entity</span>
                    <select value={selectedEntityId} onChange={(event) => setSelectedEntityId(event.target.value)}>
                      {entities.map((entity) => <option key={entity.id} value={entity.id}>{entity.name}</option>)}
                    </select>
                  </label>
                  <label className="settings-console-field">
                    <span>Name</span>
                    <input value={entityForm.name} onChange={(event) => setEntityForm((current) => ({ ...current, name: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Country</span>
                    <input value={entityForm.country} onChange={(event) => setEntityForm((current) => ({ ...current, country: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Currency</span>
                    <input value={entityForm.local_currency} onChange={(event) => setEntityForm((current) => ({ ...current, local_currency: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Entity type</span>
                    <input value={entityForm.entity_type} onChange={(event) => setEntityForm((current) => ({ ...current, entity_type: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Status</span>
                    <input value={entityForm.status} onChange={(event) => setEntityForm((current) => ({ ...current, status: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Workspace type</span>
                    <input value={entityForm.workspace_type} onChange={(event) => setEntityForm((current) => ({ ...current, workspace_type: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Workspace mode</span>
                    <input value={entityForm.workspace_mode} onChange={(event) => setEntityForm((current) => ({ ...current, workspace_mode: event.target.value }))} />
                  </label>
                </div>
                <div className="settings-console-actions">
                  <button type="button" className="eq-inline-btn primary" onClick={handleEntitySave} disabled={entitySaving}>{entitySaving ? 'Saving…' : 'Save Entity Settings'}</button>
                  <span className="settings-console-status">{entityStatus || 'Entity settings inherit the selected branch name.'}</span>
                </div>
              </section>
            )}

            {activeSection === 'equity' && (
              <section className="settings-console-section premium-panel">
                <div className="eq-data-card-head">
                  <h3>{`${(profile?.workspace?.name || activeWorkspace?.name || 'Equity')} Settings`}</h3>
                  <span className="eq-status-chip success">Flagship equity controls</span>
                </div>
                <div className="settings-console-grid">
                  <label className="settings-console-field">
                    <span>Workspace type</span>
                    <input value={equityProfileForm.workspace_type} onChange={(event) => setEquityProfileForm((current) => ({ ...current, workspace_type: event.target.value }))} />
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityProfileForm.equity_enabled} onChange={(event) => setEquityProfileForm((current) => ({ ...current, equity_enabled: event.target.checked }))} />
                    <span>Enable equity</span>
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityProfileForm.ownership_registry_enabled} onChange={(event) => setEquityProfileForm((current) => ({ ...current, ownership_registry_enabled: event.target.checked }))} />
                    <span>Ownership registry</span>
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityProfileForm.cap_table_enabled} onChange={(event) => setEquityProfileForm((current) => ({ ...current, cap_table_enabled: event.target.checked }))} />
                    <span>Cap table</span>
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityProfileForm.valuation_enabled} onChange={(event) => setEquityProfileForm((current) => ({ ...current, valuation_enabled: event.target.checked }))} />
                    <span>Valuation</span>
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityProfileForm.equity_transactions_enabled} onChange={(event) => setEquityProfileForm((current) => ({ ...current, equity_transactions_enabled: event.target.checked }))} />
                    <span>Equity transactions</span>
                  </label>
                  <label className="settings-console-switch full">
                    <input type="checkbox" checked={equityProfileForm.governance_reporting_enabled} onChange={(event) => setEquityProfileForm((current) => ({ ...current, governance_reporting_enabled: event.target.checked }))} />
                    <span>Governance reporting</span>
                  </label>
                </div>
                <div className="settings-console-grid settings-console-grid-policy">
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityPolicyForm.require_explicit_reviewers} onChange={(event) => setEquityPolicyForm((current) => ({ ...current, require_explicit_reviewers: event.target.checked }))} />
                    <span>Require explicit reviewers</span>
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityPolicyForm.require_designated_backups} onChange={(event) => setEquityPolicyForm((current) => ({ ...current, require_designated_backups: event.target.checked }))} />
                    <span>Require designated backups</span>
                  </label>
                  <label className="settings-console-field">
                    <span>Board SLA hours</span>
                    <input type="number" value={equityPolicyForm.board_sla_hours} onChange={(event) => setEquityPolicyForm((current) => ({ ...current, board_sla_hours: Number(event.target.value || 0) }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Legal SLA hours</span>
                    <input type="number" value={equityPolicyForm.legal_sla_hours} onChange={(event) => setEquityPolicyForm((current) => ({ ...current, legal_sla_hours: Number(event.target.value || 0) }))} />
                  </label>
                  <label className="settings-console-switch">
                    <input type="checkbox" checked={equityPolicyForm.escalation_enabled} onChange={(event) => setEquityPolicyForm((current) => ({ ...current, escalation_enabled: event.target.checked }))} />
                    <span>Escalation enabled</span>
                  </label>
                  <label className="settings-console-field">
                    <span>Grace hours</span>
                    <input type="number" value={equityPolicyForm.escalation_grace_hours} onChange={(event) => setEquityPolicyForm((current) => ({ ...current, escalation_grace_hours: Number(event.target.value || 0) }))} />
                  </label>
                </div>
                <div className="settings-console-actions">
                  <button type="button" className="eq-inline-btn primary" onClick={handleEquitySave} disabled={equitySaving}>{equitySaving ? 'Saving…' : 'Save Equity Settings'}</button>
                  <span className="settings-console-status">{equityStatus || `Equity summary: ${FORMATTER.format(summary?.totalShareholders || 0)} holders, ${FORMATTER.format(summary?.totalGrants || 0)} grants.`}</span>
                </div>
              </section>
            )}

            {activeSection === 'enterprise' && (
              <section className="settings-console-section premium-panel">
                <div className="eq-data-card-head">
                  <h3>{`${currentOrganization?.name || 'Enterprise'} Settings`}</h3>
                  <span className="eq-status-chip success">Organization profile</span>
                </div>
                <div className="settings-console-grid">
                  <label className="settings-console-field">
                    <span>Organization name</span>
                    <input value={orgForm.orgName} onChange={(event) => setOrgForm((current) => ({ ...current, orgName: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Headquarters country</span>
                    <input value={orgForm.orgCountry} onChange={(event) => setOrgForm((current) => ({ ...current, orgCountry: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Primary currency</span>
                    <input value={orgForm.currency} onChange={(event) => setOrgForm((current) => ({ ...current, currency: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Fiscal year end</span>
                    <input value={orgForm.fiscalYearEnd} onChange={(event) => setOrgForm((current) => ({ ...current, fiscalYearEnd: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Tax filing frequency</span>
                    <input value={orgForm.taxFilingFrequency} onChange={(event) => setOrgForm((current) => ({ ...current, taxFilingFrequency: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Accounting standard</span>
                    <input value={orgForm.accountingStandard} onChange={(event) => setOrgForm((current) => ({ ...current, accountingStandard: event.target.value }))} />
                  </label>
                </div>
                <div className="settings-console-actions">
                  <button type="button" className="eq-inline-btn primary" onClick={handleOrgSave} disabled={orgSaving || !canManageOrgSettings}>{orgSaving ? 'Saving…' : 'Save Enterprise Settings'}</button>
                  <span className="settings-console-status">{orgStatus || 'Enterprise settings are the parent profile for all branch consoles.'}</span>
                </div>
              </section>
            )}

            {activeSection === 'billing' && (
              <section className="settings-console-section premium-panel">
                <div className="eq-data-card-head">
                  <h3>Billing Settings</h3>
                  <span className="eq-status-chip">Unified billing</span>
                </div>
                <div className="settings-console-grid">
                  <label className="settings-console-field">
                    <span>Subscription tier</span>
                    <input value={orgForm.subscriptionTier} onChange={(event) => setOrgForm((current) => ({ ...current, subscriptionTier: event.target.value }))} />
                  </label>
                  <label className="settings-console-field">
                    <span>Billing contact email</span>
                    <input value={orgForm.billingContactEmail} onChange={(event) => setOrgForm((current) => ({ ...current, billingContactEmail: event.target.value }))} />
                  </label>
                </div>
                <div className="settings-console-summary-copy">
                  Transparent billing is persisted on the enterprise settings record and inherited by all branch dashboards.
                </div>
                <div className="settings-console-actions">
                  <button type="button" className="eq-inline-btn primary" onClick={handleOrgSave} disabled={orgSaving || !canManageOrgSettings}>{orgSaving ? 'Saving…' : 'Save Billing Settings'}</button>
                </div>
              </section>
            )}

            {activeSection === 'governance' && (
              <section className="settings-console-section premium-panel">
                <div className="eq-data-card-head">
                  <h3>Governance Settings</h3>
                  <span className="eq-status-chip success">YAML source of truth</span>
                </div>
                <div className="settings-console-summary-copy">
                  Export the full enterprise governance document, restore it from YAML, or send it to cloud storage for recovery and distribution.
                </div>
                <div className="settings-console-actions settings-console-actions-wrap">
                  <button type="button" className="eq-inline-btn primary" onClick={handleExportGovernance} disabled={governanceBusy || !canManageOrgSettings}>{governanceBusy ? 'Working…' : 'Download YAML'}</button>
                  <label className="eq-inline-btn" style={{ opacity: canManageOrgSettings ? 1 : 0.55, pointerEvents: canManageOrgSettings ? 'auto' : 'none' }}>
                    {governanceBusy ? 'Working…' : 'Restore YAML'}
                    <input type="file" accept=".yaml,.yml,application/x-yaml,text/yaml" onChange={handleImportGovernance} style={{ display: 'none' }} />
                  </label>
                </div>
                <div className="settings-console-grid settings-console-grid-cloud">
                  <label className="settings-console-field">
                    <span>Destination</span>
                    <select value={cloudExport.provider} onChange={(event) => changeCloudField('provider', event.target.value)}>
                      <option value="google_drive">Google Drive</option>
                      <option value="onedrive">Microsoft OneDrive</option>
                      <option value="aws_s3">AWS S3</option>
                    </select>
                  </label>
                  <label className="settings-console-field">
                    <span>File name</span>
                    <input value={cloudExport.fileName} onChange={(event) => changeCloudField('fileName', event.target.value)} placeholder="organization-governance.yml" />
                  </label>
                </div>
                {cloudExport.provider === 'google_drive' && (
                  <div className="settings-console-grid settings-console-grid-cloud">
                    <label className="settings-console-field">
                      <span>Google OAuth token</span>
                      <input type="password" value={cloudExport.oauthAccessToken} onChange={(event) => changeCloudField('oauthAccessToken', event.target.value)} />
                    </label>
                    <label className="settings-console-field">
                      <span>Folder ID</span>
                      <input value={cloudExport.folderId} onChange={(event) => changeCloudField('folderId', event.target.value)} />
                    </label>
                  </div>
                )}
                {cloudExport.provider === 'onedrive' && (
                  <div className="settings-console-grid settings-console-grid-cloud">
                    <label className="settings-console-field">
                      <span>Microsoft OAuth token</span>
                      <input type="password" value={cloudExport.oauthAccessToken} onChange={(event) => changeCloudField('oauthAccessToken', event.target.value)} />
                    </label>
                    <label className="settings-console-field">
                      <span>OneDrive path</span>
                      <input value={cloudExport.oneDrivePath} onChange={(event) => changeCloudField('oneDrivePath', event.target.value)} />
                    </label>
                  </div>
                )}
                {cloudExport.provider === 'aws_s3' && (
                  <label className="settings-console-field">
                    <span>Pre-signed URL</span>
                    <input type="password" value={cloudExport.presignedUrl} onChange={(event) => changeCloudField('presignedUrl', event.target.value)} />
                  </label>
                )}
                <label className="settings-console-switch">
                  <input type="checkbox" checked={cloudExport.overwrite} onChange={(event) => changeCloudField('overwrite', event.target.checked)} />
                  <span>Allow overwrite</span>
                </label>
                <div className="settings-console-actions">
                  <button type="button" className="eq-inline-btn primary" onClick={handleCloudExport} disabled={governanceBusy || !canManageOrgSettings}>Export YAML to Cloud</button>
                  <span className="settings-console-status">{governanceStatus || `Latest cloud exports: ${cloudExportHistory.length}`}</span>
                </div>
                <div className="settings-console-audit">
                  <h4>Cloud export history</h4>
                  <div className="settings-console-log-list">
                    {cloudExportHistory.slice(0, 6).map((entry) => (
                      <article key={entry.id || entry.file_name || entry.created_at} className="settings-console-log-item">
                        <strong>{entry.provider || 'cloud'}</strong>
                        <span>{entry.file_name || entry.destination || entry.created_at || 'Recent export'}</span>
                      </article>
                    ))}
                    {!cloudExportHistory.length && <p>No cloud exports yet.</p>}
                  </div>
                </div>
              </section>
            )}
          </main>
        </div>
      </div>
    </section>
  );
};

export default SettingsConsole;
