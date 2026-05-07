import React, { useState } from 'react';
import { PageHeader, Card, Button, Input } from '../../components/ui';

const FONT_OPTIONS = ['Inter', 'Roboto', 'Poppins', 'Lato', 'Montserrat', 'Open Sans', 'Nunito'];

export default function Branding() {
  const [saved, setSaved] = useState(false);
  const [form, setForm] = useState({
    firmName: 'Ledgora',
    tagline: 'Institutional-Grade Financial Intelligence',
    primaryColor: '#00B5E2',
    secondaryColor: '#0B0C10',
    accentColor: '#10B981',
    font: 'Inter',
    logoText: 'LGX',
    supportEmail: 'support@ledgora.com',
    website: 'https://ledgora.com',
    footerText: '© 2026 Ledgora. All rights reserved.',
    showPoweredBy: false,
  });

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }));

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="module-page">
      <PageHeader
        title="Branding"
        subtitle="Customize the look and feel of your firm's workspace"
        actions={
          <Button variant="primary" onClick={handleSave}>
            {saved ? 'Saved' : 'Save Changes'}
          </Button>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        {/* Identity */}
        <Card header="Firm Identity">
          <div className="stack-md">
            <div>
              <label className="input-label">Firm / Workspace Name</label>
              <Input value={form.firmName} onChange={e => set('firmName', e.target.value)} />
            </div>
            <div>
              <label className="input-label">Tagline</label>
              <Input value={form.tagline} onChange={e => set('tagline', e.target.value)} />
            </div>
            <div>
              <label className="input-label">Support Email</label>
              <Input value={form.supportEmail} onChange={e => set('supportEmail', e.target.value)} />
            </div>
            <div>
              <label className="input-label">Website</label>
              <Input value={form.website} onChange={e => set('website', e.target.value)} />
            </div>
            <div>
              <label className="input-label">Footer Text</label>
              <Input value={form.footerText} onChange={e => set('footerText', e.target.value)} />
            </div>
          </div>
        </Card>

        {/* Logo */}
        <Card header="Logo & Avatar">
          <div className="stack-md">
            <div style={{ display: 'flex', alignItems: 'center', gap: 24, marginBottom: 16 }}>
              <div style={{
                width: 72, height: 72, borderRadius: 8,
                background: form.primaryColor,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff', fontSize: 28, fontWeight: 700,
              }}>
                {form.logoText.slice(0, 3)}
              </div>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 4 }}>{form.firmName}</div>
                <div style={{ fontSize: 12, color: 'var(--color-silver-dark)' }}>{form.tagline}</div>
              </div>
            </div>
            <div>
              <label className="input-label">Logo Text / Initials</label>
              <Input value={form.logoText} onChange={e => set('logoText', e.target.value.slice(0, 4))} maxLength={4} />
            </div>
            <div>
              <label className="input-label">Logo Image URL (optional)</label>
              <Input placeholder="https://cdn.example.com/logo.png" />
            </div>
            <div style={{ fontSize: 12, color: 'var(--color-silver-dark)', marginTop: 4 }}>
              Recommended: 200×200px PNG or SVG with transparent background.
            </div>
          </div>
        </Card>

        {/* Colors */}
        <Card header="Color Palette">
          <div className="stack-md">
            {[
              { key: 'primaryColor', label: 'Primary (Action / Accent)' },
              { key: 'secondaryColor', label: 'Secondary (Backgrounds)' },
              { key: 'accentColor', label: 'Accent (Success / Positive)' },
            ].map(({ key, label }) => (
              <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <input
                  type="color"
                  value={form[key]}
                  onChange={e => set(key, e.target.value)}
                  style={{ width: 40, height: 36, border: '1px solid var(--border-color-default)', cursor: 'pointer', padding: 2 }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-midnight)', marginBottom: 2 }}>{label}</div>
                  <code style={{ fontSize: 11, color: 'var(--color-silver-dark)' }}>{form[key]}</code>
                </div>
                <div style={{ width: 36, height: 36, background: form[key], border: '1px solid var(--border-color-default)' }} />
              </div>
            ))}

            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              {[form.primaryColor, form.secondaryColor, form.accentColor].map((c, i) => (
                <div key={i} style={{ flex: 1, height: 12, background: c }} />
              ))}
            </div>
          </div>
        </Card>

        {/* Typography & Options */}
        <Card header="Typography & Options">
          <div className="stack-md">
            <div>
              <label className="input-label">Primary Font</label>
              <select
                className="filter-select" style={{ width: '100%', height: 40 }}
                value={form.font} onChange={e => set('font', e.target.value)}
              >
                {FONT_OPTIONS.map(f => <option key={f} value={f}>{f}</option>)}
              </select>
              <div style={{ marginTop: 8, fontFamily: form.font, fontSize: 15, color: 'var(--color-midnight)' }}>
                The quick brown fox jumps over the lazy dog.
              </div>
            </div>

            <div style={{ borderTop: '1px solid var(--border-color-default)', paddingTop: 16 }}>
              <label className="input-label" style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={form.showPoweredBy}
                  onChange={e => set('showPoweredBy', e.target.checked)}
                  style={{ width: 16, height: 16 }}
                />
                Show "Powered by Ledgora" in client-facing views
              </label>
            </div>
          </div>
        </Card>
      </div>

      <Card header="Preview" style={{ marginTop: 24 }}>
        <div style={{
          border: '1px solid var(--border-color-default)',
          borderTop: `4px solid ${form.primaryColor}`,
          padding: 24,
          background: 'var(--color-silver-very-light)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{
              width: 44, height: 44, background: form.primaryColor,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', fontWeight: 700, fontSize: 16,
            }}>
              {form.logoText.slice(0, 2)}
            </div>
            <div>
              <div style={{ fontFamily: form.font, fontWeight: 700, fontSize: 16, color: form.secondaryColor }}>{form.firmName}</div>
              <div style={{ fontFamily: form.font, fontSize: 12, color: 'var(--color-silver-dark)' }}>{form.tagline}</div>
            </div>
          </div>
          <div style={{ fontFamily: form.font, fontSize: 12, color: 'var(--color-silver-dark)' }}>{form.footerText}</div>
        </div>
      </Card>
    </div>
  );
}
