import React, { useEffect, useState } from 'react';
import { useEnterprise } from '../../context/EnterpriseContext';
import { countryDropdownOptions, countryDropdownOptionsByName } from '../../utils/countryDropdowns';

const COUNTRIES_SERVED = countryDropdownOptions;

const CURRENCIES = [
  { code: 'USD', name: 'US Dollar (USD)' },
  { code: 'EUR', name: 'Euro (EUR)' },
  { code: 'GBP', name: 'British Pound (GBP)' },
  { code: 'NGN', name: 'Nigerian Naira (NGN)' },
  { code: 'KES', name: 'Kenyan Shilling (KES)' },
  { code: 'ZAR', name: 'South African Rand (ZAR)' },
  { code: 'GHS', name: 'Ghanaian Cedi (GHS)' },
  { code: 'CHF', name: 'Swiss Franc (CHF)' },
  { code: 'SGD', name: 'Singapore Dollar (SGD)' },
  { code: 'AUD', name: 'Australian Dollar (AUD)' },
  { code: 'INR', name: 'Indian Rupee (INR)' },
  { code: 'AED', name: 'UAE Dirham (AED)' },
  { code: 'CAD', name: 'Canadian Dollar (CAD)' },
  { code: 'SEK', name: 'Swedish Krona (SEK)' },
  { code: 'HKD', name: 'Hong Kong Dollar (HKD)' },
  { code: 'XOF', name: 'West African CFA franc (XOF)' },
  { code: 'XAF', name: 'Central African CFA franc (XAF)' },
  { code: 'BWP', name: 'Botswana Pula (BWP)' },
  { code: 'ZWL', name: 'Zimbabwe Dollar (ZWL)' },
  { code: 'NAD', name: 'Namibia Dollar (NAD)' },
  { code: 'MWK', name: 'Malawi Kwacha (MWK)' },
  { code: 'ZMW', name: 'Zambia Kwacha (ZMW)' },
  { code: 'TZS', name: 'Tanzania Shilling (TZS)' },
  { code: 'UGX', name: 'Uganda Shilling (UGX)' },
  { code: 'ETB', name: 'Ethiopian Birr (ETB)' },
  { code: 'RWF', name: 'Rwanda Franc (RWF)' },
  { code: 'MZN', name: 'Mozambique Metical (MZN)' },
  { code: 'LRD', name: 'Liberian Dollar (LRD)' },
  { code: 'SLL', name: 'Sierra Leone Leone (SLL)' },
];

const EnterpriseSettings = () => {
  const {
    currentOrganization,
    deleteOrganization,
    updateOrganization,
    exportGovernanceConfiguration,
    importGovernanceConfiguration,
  } = useEnterprise();
  const [activeTab, setActiveTab] = useState('organization');
  const [saved, setSaved] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [governanceBusy, setGovernanceBusy] = useState(false);

  // Organization Settings State
  const [orgSettings, setOrgSettings] = useState({
    orgName: '',
    orgCountry: '',
    fiscalYearEnd: '12-31',
    taxFilingFrequency: 'annual',
    accountingStandard: 'IFRS',
    currency: 'USD'
  });

  // Integration Settings State
  const [integrations, setIntegrations] = useState({
    slack: { enabled: false, connected: false, workspace: '' },
    google: { enabled: false, connected: false, email: '' },
    microsoft: { enabled: false, connected: false, email: '' },
    api: { enabled: true, apiKey: '****-****-****-****', regenerate: false }
  });

  // Notification Settings State
  const [notifications, setNotifications] = useState({
    taxDeadlineAlerts: true,
    complianceReminders: true,
    teamNotifications: true,
    reportGeneration: true,
    securityAlerts: true,
    monthlyDigest: true
  });

  // Security Settings State
  const [security, setSecurity] = useState({
    twoFactorAuth: true,
    dataEncryption: true,
    auditLogging: true,
    sessionTimeout: '30',
    ipWhitelist: false,
    apiRateLimiting: true
  });

  const handleOrgSettingChange = (field, value) => {
    let updates = { [field]: value };

    // If country is changed, automatically set the currency
    if (field === 'orgCountry') {
      const selectedCountry = countryDropdownOptionsByName.get(value);
      if (selectedCountry) {
        updates.currency = selectedCountry.currency?.code || selectedCountry.currency || 'USD';
      }
    }

    setOrgSettings({ ...orgSettings, ...updates });
    setSaved(false);
    setSaveError(null);
  };

  const handleNotificationChange = (field) => {
    setNotifications({ ...notifications, [field]: !notifications[field] });
    setSaved(false);
    setSaveError(null);
  };

  const handleSecurityChange = (field, value) => {
    setSecurity({ ...security, [field]: value });
    setSaved(false);
    setSaveError(null);
  };

  const handleIntegrationToggle = (service) => {
    setIntegrations({
      ...integrations,
      [service]: {
        ...integrations[service],
        enabled: !integrations[service].enabled
      }
    });
    setSaved(false);
    setSaveError(null);
  };

  useEffect(() => {
    const org = currentOrganization;
    if (!org) return;

    const orgCountry = org.primary_country || org.country || '';
    const orgCurrency = org.primary_currency || org.currency || 'USD';
    const orgSettingsFromServer = org.settings || {};

    setOrgSettings(prev => ({
      ...prev,
      orgName: org.name || '',
      orgCountry,
      currency: orgCurrency,
      fiscalYearEnd: orgSettingsFromServer.fiscalYearEnd || prev.fiscalYearEnd,
      taxFilingFrequency: orgSettingsFromServer.taxFilingFrequency || prev.taxFilingFrequency,
      accountingStandard: orgSettingsFromServer.accountingStandard || prev.accountingStandard,
    }));

    if (orgSettingsFromServer.integrations) {
      setIntegrations(prev => ({ ...prev, ...orgSettingsFromServer.integrations }));
    }
    if (orgSettingsFromServer.notifications) {
      setNotifications(prev => ({ ...prev, ...orgSettingsFromServer.notifications }));
    }
    if (orgSettingsFromServer.security) {
      setSecurity(prev => ({ ...prev, ...orgSettingsFromServer.security }));
    }
  }, [currentOrganization]);

  const handleSaveSettings = async () => {
    if (!currentOrganization?.id) return;
    setSaveError(null);

    const existingSettings = currentOrganization.settings || {};

    const payload = {
      name: orgSettings.orgName,
      primary_country: orgSettings.orgCountry,
      primary_currency: orgSettings.currency,
      settings: {
        ...existingSettings,
        fiscalYearEnd: orgSettings.fiscalYearEnd,
        taxFilingFrequency: orgSettings.taxFilingFrequency,
        accountingStandard: orgSettings.accountingStandard,
        integrations,
        notifications,
        security,
      },
    };

    try {
      await updateOrganization(currentOrganization.id, payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err.message || 'Failed to save settings');
    }
  };

  const handleRegenerateApiKey = () => {
    setIntegrations({
      ...integrations,
      api: {
        ...integrations.api,
        apiKey: 'sk-' + Math.random().toString(36).substr(2, 9) + '-' + Math.random().toString(36).substr(2, 9)
      }
    });
    setSaved(false);
    setSaveError(null);
  };

  const handleDeleteOrganization = async () => {
    if (!currentOrganization?.id || deleteBusy) return;

    const confirmed = window.confirm(
      `Delete organization "${currentOrganization.name}"? This will only succeed if there is no data inside the organization.`
    );
    if (!confirmed) return;

    setDeleteBusy(true);
    setSaveError(null);

    try {
      await deleteOrganization(currentOrganization.id);
    } catch (err) {
      setSaveError(err.message || 'Failed to delete organization');
    } finally {
      setDeleteBusy(false);
    }
  };

  const handleExportGovernanceConfiguration = async () => {
    if (!currentOrganization?.id || governanceBusy) return;
    setGovernanceBusy(true);
    setSaveError(null);
    try {
      await exportGovernanceConfiguration(currentOrganization.id);
    } catch (err) {
      setSaveError(err.message || 'Failed to export governance configuration');
    } finally {
      setGovernanceBusy(false);
    }
  };

  const handleImportGovernanceConfiguration = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !currentOrganization?.id || governanceBusy) return;
    setGovernanceBusy(true);
    setSaveError(null);
    try {
      await importGovernanceConfiguration(currentOrganization.id, file);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setSaveError(err.message || 'Failed to restore governance configuration');
    } finally {
      setGovernanceBusy(false);
    }
  };

  return (
    <div className="page-container enterprise-settings">
      <div className="settings-header">
        <h1 className="page-title">
          Settings & Integrations
        </h1>
        <p className="subtitle">Manage organization settings, integrations, and security</p>
      </div>

      {/* Save Confirmation */}
      {saved && (
        <div className="save-confirmation">
          Settings saved successfully
        </div>
      )}

      {saveError && (
        <div className="save-confirmation">
           {saveError}
        </div>
      )}

      <div className="settings-layout">
        {/* Sidebar Navigation */}
        <aside className="settings-sidebar">
          <button
            className={`settings-tab ${activeTab === 'organization' ? 'active' : ''}`}
            onClick={() => setActiveTab('organization')}
          >
            Organization
          </button>
          <button
            className={`settings-tab ${activeTab === 'integrations' ? 'active' : ''}`}
            onClick={() => setActiveTab('integrations')}
          >
            Integrations
          </button>
          <button
            className={`settings-tab ${activeTab === 'notifications' ? 'active' : ''}`}
            onClick={() => setActiveTab('notifications')}
          >
            Notifications
          </button>
          <button
            className={`settings-tab ${activeTab === 'security' ? 'active' : ''}`}
            onClick={() => setActiveTab('security')}
          >
            Security & Privacy
          </button>
        </aside>

        {/* Content Area */}
        <div className="settings-content">
          {/* ORGANIZATION SETTINGS */}
          {activeTab === 'organization' && (
            <div className="settings-section">
              <h2>Organization Settings</h2>

              <div className="settings-card">
                <h3>Basic Information</h3>
                <div className="form-group">
                  <label>Organization Name</label>
                  <input
                    type="text"
                    value={orgSettings.orgName}
                    onChange={(e) => handleOrgSettingChange('orgName', e.target.value)}
                    placeholder="Enter organization name"
                  />
                </div>

                <div className="form-row">
                  <div className="form-group">
                    <label>Headquarters Country</label>
                    <select
                      value={orgSettings.orgCountry}
                      onChange={(e) => handleOrgSettingChange('orgCountry', e.target.value)}
                    >
                      <option value="">-- Select Country --</option>
                      {['Africa', 'Americas', 'Asia', 'Europe', 'Oceania'].map((region) => (
                        <optgroup key={region} label={region}>
                          {COUNTRIES_SERVED.filter((country) => country.region === region).map((country) => (
                            <option key={country.code} value={country.name}>{country.name}</option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Primary Currency</label>
                    <select
                      value={orgSettings.currency}
                      onChange={(e) => handleOrgSettingChange('currency', e.target.value)}
                    >
                      <option value="">-- Select Currency --</option>
                      {CURRENCIES.map(currency => (
                        <option key={currency.code} value={currency.code}>{currency.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              <div className="settings-card">
                <h3>Accounting & Compliance</h3>
                <div className="form-row">
                  <div className="form-group">
                    <label>Fiscal Year End</label>
                    <input
                      type="text"
                      value={orgSettings.fiscalYearEnd}
                      placeholder="MM-DD"
                      onChange={(e) => handleOrgSettingChange('fiscalYearEnd', e.target.value)}
                    />
                  </div>
                  <div className="form-group">
                    <label>Tax Filing Frequency</label>
                    <select
                      value={orgSettings.taxFilingFrequency}
                      onChange={(e) => handleOrgSettingChange('taxFilingFrequency', e.target.value)}
                    >
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="annual">Annual</option>
                    </select>
                  </div>
                </div>

                <div className="form-group">
                  <label>Accounting Standard</label>
                  <select
                    value={orgSettings.accountingStandard}
                    onChange={(e) => handleOrgSettingChange('accountingStandard', e.target.value)}
                  >
                    <option value="IFRS">IFRS (International)</option>
                    <option value="GAAP">GAAP (US)</option>
                    <option value="LOCAL">Local Standards</option>
                  </select>
                </div>
              </div>

              <button className="btn-primary" onClick={handleSaveSettings}>
                Save Organization Settings
              </button>

              <div className="settings-card" style={{ marginTop: '1.5rem' }}>
                <h3>Governance Configuration</h3>
                <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
                  Download the versioned YAML record of your organization structure, roles, permissions, offices, and workflows, or restore it after a migration or recovery event.
                </p>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
                  <button
                    className="btn-secondary"
                    type="button"
                    onClick={handleExportGovernanceConfiguration}
                    disabled={governanceBusy || !currentOrganization?.id}
                  >
                    {governanceBusy ? 'Working...' : 'Download YAML'}
                  </button>
                  <label className="btn-secondary" style={{ cursor: governanceBusy ? 'not-allowed' : 'pointer', margin: 0 }}>
                    {governanceBusy ? 'Working...' : 'Restore YAML'}
                    <input
                      type="file"
                      accept=".yaml,.yml,application/x-yaml,text/yaml"
                      onChange={handleImportGovernanceConfiguration}
                      disabled={governanceBusy || !currentOrganization?.id}
                      style={{ display: 'none' }}
                    />
                  </label>
                </div>
              </div>

              <div className="settings-card" style={{ marginTop: '1.5rem', borderColor: '#f3c2b8', background: '#fff7f5' }}>
                <h3>Delete Organization</h3>
                <p style={{ marginBottom: '1rem', color: '#6b7280' }}>
                  The organization can only be deleted when there is no data inside it. Remove entities, team members, clients, workflows, and other organization records first.
                </p>
                <button
                  className="btn-secondary"
                  onClick={handleDeleteOrganization}
                  disabled={deleteBusy || !currentOrganization?.id}
                  style={{ borderColor: '#dc2626', color: '#dc2626' }}
                >
                  {deleteBusy ? 'Deleting...' : 'Delete Organization'}
                </button>
              </div>
            </div>
          )}

          {/* INTEGRATIONS */}
          {activeTab === 'integrations' && (
            <div className="settings-section">
              <h2>Integrations</h2>
              <p className="section-description">Connect third-party services to enhance your workflow</p>

              <div className="integrations-grid">
                {/* Slack Integration */}
                <div className="integration-card">
                  <div className="integration-header">

                    <h3>Slack</h3>
                  </div>
                  <p>Get tax alerts and compliance reminders in Slack</p>
                  <div className="integration-status">
                    {integrations.slack.connected ? (
                      <span className="status-connected">Connected</span>
                    ) : (
                      <span className="status-disconnected">Not connected</span>
                    )}
                  </div>
                  <button
                    className={`btn-integration ${integrations.slack.enabled ? 'enabled' : 'disabled'}`}
                    onClick={() => handleIntegrationToggle('slack')}
                  >

                    {integrations.slack.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </div>

                {/* Google Integration */}
                <div className="integration-card">
                  <div className="integration-header">

                    <h3>Google Drive</h3>
                  </div>
                  <p>Auto-sync documents to your Google Drive</p>
                  <div className="integration-status">
                    {integrations.google.connected ? (
                      <span className="status-connected">Connected</span>
                    ) : (
                      <span className="status-disconnected">Not connected</span>
                    )}
                  </div>
                  <button
                    className={`btn-integration ${integrations.google.enabled ? 'enabled' : 'disabled'}`}
                    onClick={() => handleIntegrationToggle('google')}
                  >

                    {integrations.google.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </div>

                {/* Microsoft Integration */}
                <div className="integration-card">
                  <div className="integration-header">

                    <h3>Microsoft 365</h3>
                  </div>
                  <p>Integrate with OneDrive and Teams</p>
                  <div className="integration-status">
                    {integrations.microsoft.connected ? (
                      <span className="status-connected">Connected</span>
                    ) : (
                      <span className="status-disconnected">Not connected</span>
                    )}
                  </div>
                  <button
                    className={`btn-integration ${integrations.microsoft.enabled ? 'enabled' : 'disabled'}`}
                    onClick={() => handleIntegrationToggle('microsoft')}
                  >

                    {integrations.microsoft.enabled ? 'Enabled' : 'Disabled'}
                  </button>
                </div>
              </div>

              {/* API Configuration */}
              <div className="settings-card">
                <h3>API Configuration</h3>
                <p>Use the API key to programmatically access your organization data</p>

                <div className="api-config">
                  <div className="api-key-section">
                    <label>API Key</label>
                    <div className="api-key-display">
                      <code>{integrations.api.apiKey}</code>
                      <button className="btn-small" onClick={handleRegenerateApiKey}>Regenerate
                      </button>
                    </div>
                    <small>Keep your API key confidential. Anyone with this key can access your organization data.</small>
                  </div>

                  <div className="api-docs">
                    <h4>API Documentation</h4>
                    <p>Read our comprehensive API docs to get started:</p>
                    <a href="/api/docs" className="link" target="_blank" rel="noreferrer">View API Documentation →</a>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* NOTIFICATIONS */}
          {activeTab === 'notifications' && (
            <div className="settings-section">
              <h2>Notification Preferences</h2>
              <p className="section-description">Choose how and when you want to be notified</p>

              <div className="settings-card">
                <h3>Alert Types</h3>

                <div className="notification-group">
                  <div className="notification-item">
                    <div className="notification-info">
                      <h4>Tax Deadline Alerts</h4>
                      <p>Reminders for upcoming tax deadlines and filings</p>
                    </div>
                    <button
                      className={`toggle-btn ${notifications.taxDeadlineAlerts ? 'on' : 'off'}`}
                      onClick={() => handleNotificationChange('taxDeadlineAlerts')}
                    >

                    </button>
                  </div>

                  <div className="notification-item">
                    <div className="notification-info">
                      <h4>Compliance Reminders</h4>
                      <p>Status updates on compliance tasks and obligations</p>
                    </div>
                    <button
                      className={`toggle-btn ${notifications.complianceReminders ? 'on' : 'off'}`}
                      onClick={() => handleNotificationChange('complianceReminders')}
                    >

                    </button>
                  </div>

                  <div className="notification-item">
                    <div className="notification-info">
                      <h4>Team Notifications</h4>
                      <p>Updates about team member activity and changes</p>
                    </div>
                    <button
                      className={`toggle-btn ${notifications.teamNotifications ? 'on' : 'off'}`}
                      onClick={() => handleNotificationChange('teamNotifications')}
                    >

                    </button>
                  </div>

                  <div className="notification-item">
                    <div className="notification-info">
                      <h4>Report Generation</h4>
                      <p>Notifications when reports are ready for download</p>
                    </div>
                    <button
                      className={`toggle-btn ${notifications.reportGeneration ? 'on' : 'off'}`}
                      onClick={() => handleNotificationChange('reportGeneration')}
                    >

                    </button>
                  </div>

                  <div className="notification-item">
                    <div className="notification-info">
                      <h4>Security Alerts</h4>
                      <p>Important security and access notifications</p>
                    </div>
                    <button
                      className={`toggle-btn ${notifications.securityAlerts ? 'on' : 'off'}`}
                      onClick={() => handleNotificationChange('securityAlerts')}
                    >

                    </button>
                  </div>

                  <div className="notification-item">
                    <div className="notification-info">
                      <h4>Monthly Digest</h4>
                      <p>A summary of your organization's activity each month</p>
                    </div>
                    <button
                      className={`toggle-btn ${notifications.monthlyDigest ? 'on' : 'off'}`}
                      onClick={() => handleNotificationChange('monthlyDigest')}
                    >

                    </button>
                  </div>
                </div>

                <button className="btn-primary" onClick={handleSaveSettings}>
                  Save Notification Settings
                </button>
              </div>
            </div>
          )}

          {/* SECURITY & PRIVACY */}
          {activeTab === 'security' && (
            <div className="settings-section">
              <h2>Security & Privacy</h2>
              <p className="section-description">Protect your organization's data and manage access</p>

              <div className="settings-card security-features">
                <h3>Security Features</h3>

                <div className="security-feature">
                  <div className="feature-info">
                    <h4>Two-Factor Authentication</h4>
                    <p>Require 2FA for all team members</p>
                  </div>
                  <button
                    className={`toggle-btn ${security.twoFactorAuth ? 'on' : 'off'}`}
                    onClick={() => handleSecurityChange('twoFactorAuth', !security.twoFactorAuth)}
                  >

                  </button>
                </div>

                <div className="security-feature">
                  <div className="feature-info">
                    <h4>Data Encryption</h4>
                    <p>End-to-end encryption for all data at rest and in transit</p>
                  </div>
                  <button
                    className={`toggle-btn ${security.dataEncryption ? 'on' : 'off'}`}
                    onClick={() => handleSecurityChange('dataEncryption', !security.dataEncryption)}
                  >

                  </button>
                </div>

                <div className="security-feature">
                  <div className="feature-info">
                    <h4>Audit Logging</h4>
                    <p>Track all changes and access to organization data</p>
                  </div>
                  <button
                    className={`toggle-btn ${security.auditLogging ? 'on' : 'off'}`}
                    onClick={() => handleSecurityChange('auditLogging', !security.auditLogging)}
                  >

                  </button>
                </div>

                <div className="security-feature">
                  <div className="feature-info">
                    <h4>Session Timeout</h4>
                    <p>Automatically log out inactive users</p>
                  </div>
                  <select
                    value={security.sessionTimeout}
                    onChange={(e) => handleSecurityChange('sessionTimeout', e.target.value)}
                  >
                    <option value="15">15 minutes</option>
                    <option value="30">30 minutes</option>
                    <option value="60">1 hour</option>
                    <option value="480">8 hours</option>
                  </select>
                </div>

                <div className="security-feature">
                  <div className="feature-info">
                    <h4>API Rate Limiting</h4>
                    <p>Protect against abuse with request rate limits</p>
                  </div>
                  <button
                    className={`toggle-btn ${security.apiRateLimiting ? 'on' : 'off'}`}
                    onClick={() => handleSecurityChange('apiRateLimiting', !security.apiRateLimiting)}
                  >

                  </button>
                </div>
              </div>

              <div className="settings-card info-box">
                 <strong>Privacy Notice:</strong>Your data is encrypted and never shared with third parties. We comply with GDPR, CCPA, and local data protection regulations.
              </div>

              <button className="btn-primary" onClick={handleSaveSettings}>
                Save Security Settings
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnterpriseSettings;
