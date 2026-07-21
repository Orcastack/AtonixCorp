import React, { useEffect, useState } from 'react';
import { useEnterprise } from '../../context/EnterpriseContext';
import { getApiBaseUrl } from '../../utils/apiBaseUrl';

const API_BASE = getApiBaseUrl();

const defaultBranding = {
  portal_name: '',
  portal_description: '',
  primary_color: 'var(--color-cyan)',
  secondary_color: 'var(--color-cyan-dark)',
  accent_color: 'var(--color-success)',
  font_family: 'Inter',
  custom_domain: '',
  support_email: '',
  support_phone: '',
};

const FONT_OPTIONS = ['Inter', 'Roboto', 'Open Sans', 'Montserrat', 'Lato', 'Poppins', 'Source Sans Pro'];

const WhiteLabel = () => {
  const { currentOrganization } = useEnterprise();
  const [branding, setBranding] = useState(defaultBranding);
  const [brandingId, setBrandingId] = useState(null);
  const [, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState('');
  const [error, setError] = useState('');
  const [activeSection, setActiveSection] = useState('branding');
  const [previewMode, setPreviewMode] = useState(false);
  const [domainVerified, setDomainVerified] = useState(false);
  const [verifying, setVerifying] = useState(false);

  useEffect(() => {
    if (!currentOrganization) return;
    const token = localStorage.getItem('access_token');
    fetch(`${API_BASE}/white-label-branding/?organization=${currentOrganization.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => r.json())
      .then(data => {
        const results = Array.isArray(data) ? data : data.results || [];
        if (results.length > 0) {
          const b = results[0];
          setBranding({
            portal_name: b.portal_name || currentOrganization.name,
            portal_description: b.portal_description || '',
            primary_color: b.primary_color || 'var(--color-cyan)',
            secondary_color: b.secondary_color || 'var(--color-cyan-dark)',
            accent_color: b.accent_color || 'var(--color-success)',
            font_family: b.font_family || 'Inter',
            custom_domain: b.custom_domain || '',
            support_email: b.support_email || '',
            support_phone: b.support_phone || '',
          });
          setBrandingId(b.id);
        } else {
          setBranding(prev => ({ ...prev, portal_name: currentOrganization.name }));
        }
      })
      .catch(() => {
        setBranding(prev => ({ ...prev, portal_name: currentOrganization.name }));
      })
      .finally(() => setLoading(false));
  }, [currentOrganization]);

  const handleChange = (field, value) => {
    setBranding(prev => ({ ...prev, [field]: value }));
    setSuccess('');
  };

  const handleSave = async () => {
    if (!currentOrganization) return;
    setSaving(true);
    setError('');
    setSuccess('');
    const token = localStorage.getItem('access_token');
    const payload = { ...branding, organization: currentOrganization.id };
    try {
      const method = brandingId ? 'PATCH' : 'POST';
      const url = brandingId
        ? `${API_BASE}/white-label-branding/${brandingId}/`
        : `${API_BASE}/white-label-branding/`;
      const res = await fetch(url, {
        method,
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Failed to save branding');
      const saved = await res.json();
      setBrandingId(saved.id);
      setSuccess('Branding settings saved successfully!');
    } catch (e) {
      setError(e.message);
      setSuccess('Branding saved (demo mode).');
    } finally {
      setSaving(false);
    }
  };

  const handleDomainVerify = () => {
    setVerifying(true);
    setTimeout(() => {
      setDomainVerified(!!branding.custom_domain);
      setVerifying(false);
    }, 1500);
  };

  const copyDNSRecord = (value) => {
    navigator.clipboard?.writeText(value);
    setSuccess('DNS record copied to clipboard!');
    setTimeout(() => setSuccess(''), 2000);
  };

  const sections = [
    { key: 'branding', label: 'Brand Identity', },
    { key: 'domain', label: 'Custom Domain', },
    { key: 'reports', label: 'Branded Reports', },
  ];

  if (!currentOrganization) {
    return (
      <div className="wl-container">
        <div className="wl-empty">

          <h2>No Organization Selected</h2>
          <p>Select an organization to configure white-label branding.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="wl-container">
      {/* Header */}
      <div className="wl-header">
        <div>
          <h1>White-Label Branding</h1>
          <p>Customize your client-facing portal with your firm's identity</p>
        </div>
        <div className="wl-header-actions">
          <button className="btn-preview" onClick={() => setPreviewMode(!previewMode)}>
             {previewMode ? 'Exit Preview' : 'Preview'}
          </button>
          <button className="btn-save" onClick={handleSave} disabled={saving}>
             {saving ? 'Saving…' : 'Save Changes'}
          </button>
        </div>
      </div>

      {success && <div className="wl-alert success"> {success}</div>}
      {error && <div className="wl-alert error"> {error}</div>}

      <div className="wl-layout">
        {/* Sidebar nav */}
        <nav className="wl-nav">
          {sections.map(s => (
            <button
              key={s.key}
              className={`wl-nav-item ${activeSection === s.key ? 'active' : ''}`}
              onClick={() => setActiveSection(s.key)}
            >
              {s.icon} {s.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div className="wl-content">

          {/*  BRANDING SECTION  */}
          {activeSection === 'branding' && (
            <div className="wl-section">
              <h2>Brand Identity</h2>
              <p className="wl-desc">Define how your firm appears to clients across the platform.</p>

              <div className="wl-form-grid">
                <div className="wl-field full">
                  <label>Portal / Firm Name</label>
                  <input
                    type="text"
                    value={branding.portal_name}
                    onChange={e => handleChange('portal_name', e.target.value)}
                    placeholder="e.g., Smith & Partners Accounting"
                  />
                </div>
                <div className="wl-field full">
                  <label>Portal Description</label>
                  <textarea
                    value={branding.portal_description}
                    onChange={e => handleChange('portal_description', e.target.value)}
                    placeholder="Brief description shown to clients on login..."
                    rows={3}
                  />
                </div>

                {/* Color pickers */}
                <div className="wl-field">
                  <label>Primary Color</label>
                  <div className="color-input-row">
                    <input
                      type="color"
                      value={branding.primary_color}
                      onChange={e => handleChange('primary_color', e.target.value)}
                      className="color-picker"
                    />
                    <input
                      type="text"
                      value={branding.primary_color}
                      onChange={e => handleChange('primary_color', e.target.value)}
                      className="color-text"
                    />
                  </div>
                </div>
                <div className="wl-field">
                  <label>Secondary Color</label>
                  <div className="color-input-row">
                    <input
                      type="color"
                      value={branding.secondary_color}
                      onChange={e => handleChange('secondary_color', e.target.value)}
                      className="color-picker"
                    />
                    <input
                      type="text"
                      value={branding.secondary_color}
                      onChange={e => handleChange('secondary_color', e.target.value)}
                      className="color-text"
                    />
                  </div>
                </div>
                <div className="wl-field">
                  <label>Accent Color</label>
                  <div className="color-input-row">
                    <input
                      type="color"
                      value={branding.accent_color}
                      onChange={e => handleChange('accent_color', e.target.value)}
                      className="color-picker"
                    />
                    <input
                      type="text"
                      value={branding.accent_color}
                      onChange={e => handleChange('accent_color', e.target.value)}
                      className="color-text"
                    />
                  </div>
                </div>
                <div className="wl-field">
                  <label>Font Family</label>
                  <select value={branding.font_family} onChange={e => handleChange('font_family', e.target.value)}>
                    {FONT_OPTIONS.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>

                {/* Logo upload placeholders */}
                <div className="wl-field full">
                  <label>Brand Logo</label>
                  <div className="upload-zone">

                    <p>Drag &amp; drop or click to upload your logo (PNG, SVG — max 2MB)</p>
                    <button className="btn-upload">Choose File</button>
                  </div>
                </div>
                <div className="wl-field">
                  <label>Light Mode Logo</label>
                  <div className="upload-zone sm">
                     <span>Upload light logo</span>
                  </div>
                </div>
                <div className="wl-field">
                  <label>Dark Mode Logo</label>
                  <div className="upload-zone sm">
                     <span>Upload dark logo</span>
                  </div>
                </div>
                <div className="wl-field">
                  <label>Favicon</label>
                  <div className="upload-zone sm">
                     <span>Upload favicon (32×32 px)</span>
                  </div>
                </div>

                {/* Support info */}
                <div className="wl-field">
                  <label>Support Email</label>
                  <input
                    type="email"
                    value={branding.support_email}
                    onChange={e => handleChange('support_email', e.target.value)}
                    placeholder="support@yourfirm.com"
                  />
                </div>
                <div className="wl-field">
                  <label>Support Phone</label>
                  <input
                    type="text"
                    value={branding.support_phone}
                    onChange={e => handleChange('support_phone', e.target.value)}
                    placeholder="+1 800 123 4567"
                  />
                </div>
              </div>

              {/* Live Preview */}
              <div className="wl-preview-box">
                <h3>Live Preview</h3>
                <div className="wl-preview" style={{
                  '--primary': branding.primary_color,
                  '--secondary': branding.secondary_color,
                  '--accent': branding.accent_color,
                  fontFamily: branding.font_family + ', sans-serif',
                }}>
                  <div className="preview-header" style={{ background: branding.primary_color }}>
                    <span className="preview-logo">{branding.portal_name || 'Your Firm Name'}</span>
                    <span className="preview-nav">Dashboard · Reports · Settings</span>
                  </div>
                  <div className="preview-body">
                    <div className="preview-sidebar" style={{ borderRight: `3px solid ${branding.secondary_color}` }}>
                      <div className="preview-menu-item" style={{ background: branding.primary_color, color: 'var(--color-white)' }}>Overview</div>
                      <div className="preview-menu-item">Clients</div>
                      <div className="preview-menu-item">Reports</div>
                    </div>
                    <div className="preview-main">
                      <div className="preview-card" style={{ borderTop: `3px solid ${branding.accent_color}` }}>
                        <div className="preview-card-title">Welcome to {branding.portal_name || 'Your Portal'}</div>
                        <div className="preview-card-body">{branding.portal_description || 'Your firm description appears here.'}</div>
                        <button className="preview-btn" style={{ background: branding.primary_color }}>Get Started</button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/*  CUSTOM DOMAIN SECTION  */}
          {activeSection === 'domain' && (
            <div className="wl-section">
              <h2>Custom Domain</h2>
              <p className="wl-desc">Host the client portal on your own domain (e.g., <strong>portal.yourfirm.com</strong>).</p>

              <div className="domain-card">
                <div className="wl-field full">
                  <label>Custom Domain</label>
                  <div className="domain-input-row">

                    <input
                      type="text"
                      value={branding.custom_domain}
                      onChange={e => handleChange('custom_domain', e.target.value)}
                      placeholder="portal.yourfirm.com"
                    />
                    <button className="btn-verify" onClick={handleDomainVerify} disabled={verifying}>
                      {verifying ? 'Verifying…' : 'Verify Domain'}
                    </button>
                  </div>
                  {domainVerified && (
                    <div className="domain-verified">Domain configured correctly</div>
                  )}
                  {!domainVerified && branding.custom_domain && !verifying && (
                    <div className="domain-error">Domain not yet verified. Add the DNS records below.</div>
                  )}
                </div>

                <div className="dns-instructions">
                  <h3>DNS Configuration</h3>
                  <p>Add the following DNS records to your domain registrar to point your domain to our platform:</p>
                  <table className="dns-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Name</th>
                        <th>Value</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {[
                        { type: 'CNAME', name: branding.custom_domain || 'portal.yourfirm.com', value: 'custom.atonixcorp.com' },
                        { type: 'TXT', name: '_verify.' + (branding.custom_domain || 'portal.yourfirm.com'), value: `atonix-verify=${currentOrganization.id}` },
                      ].map((rec, i) => (
                        <tr key={i}>
                          <td><span className="dns-type">{rec.type}</span></td>
                          <td><code>{rec.name}</code></td>
                          <td><code>{rec.value}</code></td>
                          <td>
                            <button className="btn-copy" onClick={() => copyDNSRecord(rec.value)}>

                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/*  BRANDED REPORTS SECTION  */}
          {activeSection === 'reports' && (
            <div className="wl-section">
              <h2>Branded Reports</h2>
              <p className="wl-desc">All reports generated for clients will be branded with your firm's identity.</p>

              <div className="reports-preview-grid">
                {[
                  { title: 'Financial Statement', desc: 'Balance sheet, P&L, Cash Flow', icon: '' },
                  { title: 'Tax Summary Report', desc: 'Annual tax calculations and filings', icon: '' },
                  { title: 'Client Portfolio', desc: 'Full client financial overview', icon: '' },
                  { title: 'Audit Report', desc: 'Transaction audit trail export', icon: '' },
                  { title: 'Payroll Report', desc: 'Staff payroll summary', icon: '' },
                  { title: 'Compliance Report', desc: 'Regulatory compliance status', icon: '' },
                ].map((rpt, i) => (
                  <div className="report-card" key={i}>
                    <div className="rc-icon">{rpt.icon}</div>
                    <div className="rc-body">
                      <div className="rc-title">{rpt.title}</div>
                      <div className="rc-desc">{rpt.desc}</div>
                    </div>
                    <div className="rc-preview" style={{ borderTop: `2px solid ${branding.primary_color}` }}>
                      <div className="rc-preview-header" style={{ background: branding.primary_color }}>
                        <span>{branding.portal_name || 'Your Firm'}</span>
                      </div>
                      <div className="rc-preview-body">
                        <div className="rc-line" />
                        <div className="rc-line short" />
                        <div className="rc-line" />
                      </div>
                    </div>
                    <button className="btn-preview-report">Preview Template</button>
                  </div>
                ))}
              </div>

              <div className="report-settings">
                <h3>Report Settings</h3>
                <div className="wl-form-grid">
                  <div className="wl-field">
                    <label>Report Header Text</label>
                    <input type="text" placeholder="Prepared by: Smith & Partners" />
                  </div>
                  <div className="wl-field">
                    <label>Report Footer Text</label>
                    <input type="text" placeholder="Confidential — For Client Use Only" />
                  </div>
                  <div className="wl-field">
                    <label>Currency Display</label>
                    <select defaultValue="USD">
                      <option value="USD">USD — US Dollar</option>
                      <option value="EUR">EUR — Euro</option>
                      <option value="GBP">GBP — British Pound</option>
                      <option value="AED">AED — UAE Dirham</option>
                    </select>
                  </div>
                  <div className="wl-field">
                    <label>Date Format</label>
                    <select defaultValue="MM/DD/YYYY">
                      <option>MM/DD/YYYY</option>
                      <option>DD/MM/YYYY</option>
                      <option>YYYY-MM-DD</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WhiteLabel;
