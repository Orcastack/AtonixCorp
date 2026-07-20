import React, { useEffect, useState } from 'react';
import { PageHeader, Card, Button } from '../../components/ui';
import StandaloneModuleShell from '../../components/StandaloneModuleShell';
import { useEnterprise } from '../../context/EnterpriseContext';
import './Security.css';

export default function Security() {
  const [mfa, setMfa] = useState(true);
  const [ipRestrict, setIpRestrict] = useState(false);
  const [sessionTimeout, setSessionTimeout] = useState('60');
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState('');
  const [permissionContext, setPermissionContext] = useState(null);
  const { currentOrganization, updateOrganization, fetchPermissionContext } = useEnterprise();

  useEffect(() => {
    const securitySettings = currentOrganization?.settings?.security;
    if (!securitySettings) return;
    setMfa(Boolean(securitySettings.twoFactorAuth));
    setIpRestrict(Boolean(securitySettings.ipWhitelist));
    setSessionTimeout(String(securitySettings.sessionTimeout || '60'));
  }, [currentOrganization]);

  useEffect(() => {
    if (!currentOrganization?.id) {
      setPermissionContext(null);
      return;
    }
    let active = true;
    fetchPermissionContext(currentOrganization.id)
      .then((context) => {
        if (active) setPermissionContext(context);
      })
      .catch(() => {
        if (active) setPermissionContext(null);
      });
    return () => {
      active = false;
    };
  }, [currentOrganization?.id, fetchPermissionContext]);

  const saveSecuritySettings = async () => {
    if (!currentOrganization?.id || saving) return;
    setSaving(true);
    setSaveMessage('');
    try {
      await updateOrganization(currentOrganization.id, {
        settings: {
          ...(currentOrganization.settings || {}),
          security: {
            ...(currentOrganization.settings?.security || {}),
            twoFactorAuth: mfa,
            ipWhitelist: ipRestrict,
            sessionTimeout,
            auditLogging: true,
          },
        },
      });
      setSaveMessage('Security policies saved.');
    } catch (error) {
      setSaveMessage(error.message || 'Unable to save security policies.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <StandaloneModuleShell title="Security" eyebrow="Admin Surface" backLabel="Return to Console">
      <div className="module-page">
        <PageHeader
          title="Security"
          subtitle="Configure authentication, session management, and access policies"
          actions={
            <Button variant="primary" size="small" onClick={saveSecuritySettings} disabled={saving || !currentOrganization?.id}>
              {saving ? 'Saving...' : 'Save Security Settings'}
            </Button>
          }
        />

        <div className="security-grid">
          <Card title="Authentication">
            <div className="security-options">
              {[
                { label: 'Require MFA for all users', value: mfa, setter: setMfa, desc: 'All team members must use two-factor authentication to sign in.' },
                { label: 'IP Address Restrictions', value: ipRestrict, setter: setIpRestrict, desc: 'Restrict access to specific IP addresses or CIDR ranges.' },
              ].map((item, i) => (
                <div key={i} className="security-option">
                  <div className="security-option-copy">
                    <div className="security-option-title">{item.label}</div>
                    <div className="security-option-desc">{item.desc}</div>
                  </div>
                  <button className={`security-toggle${item.value ? ' is-on' : ''}`} onClick={() => item.setter(!item.value)} aria-pressed={item.value}>
                    <span className="security-toggle-knob" />
                  </button>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Session Management">
            <div className="security-session-row">
              <div className="security-session-copy">
                <div className="security-option-title">Session Timeout</div>
                <div className="security-option-desc">Automatically sign out inactive users after the specified duration.</div>
              </div>
              <select
                className="security-select"
                value={sessionTimeout}
                onChange={(e) => setSessionTimeout(e.target.value)}
              >
                <option value="15">15 minutes</option>
                <option value="30">30 minutes</option>
                <option value="60">1 hour</option>
                <option value="240">4 hours</option>
                <option value="480">8 hours</option>
              </select>
            </div>
          </Card>

          <Card title="Security Summary">
            <div className="security-summary-list">
              {[
              { label: 'MFA Enabled', ok: mfa },
              { label: 'HTTPS / TLS Enforced', ok: true },
              { label: 'Audit Logging Active', ok: true },
              { label: 'IP Restrictions Active', ok: ipRestrict },
              { label: 'API Key Expiry Configured', ok: false },
            ].map((item, i) => (
              <div key={i} className="security-summary-item">
                <span className={`security-summary-label${item.ok ? ' is-ok' : ' is-muted'}`}>{item.label}</span>
              </div>
            ))}
            </div>
          </Card>

          <Card title="Access Control Validation">
            <div className="security-summary-list">
              <div className="security-summary-item">
                <span className="security-summary-label is-ok">Effective role: {permissionContext?.role_name || 'Loading'}</span>
              </div>
              <div className="security-summary-item">
                <span className={`security-summary-label ${permissionContext?.permission_codes?.includes('manage_org_settings') ? 'is-ok' : 'is-muted'}`}>
                  Organization security administration {permissionContext?.permission_codes?.includes('manage_org_settings') ? 'granted' : 'not granted'}
                </span>
              </div>
              <div className="security-summary-item">
                <span className="security-summary-label is-ok">Audit logging enforced for organization changes</span>
              </div>
            </div>
          </Card>
        </div>
        {saveMessage && <p className="security-save-message">{saveMessage}</p>}
      </div>
    </StandaloneModuleShell>
  );
}
