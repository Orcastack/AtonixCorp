import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import LedgoraLogo from '../../components/branding/LedgoraLogo';
import { countryDropdownOptions } from '../../utils/countryDropdowns';
import '../Workspace/CreateWorkspace.css';

/* ─────────────────────────────────────────────────────────────────────────────
   CREATE EQUITY FLOW
   Dedicated flow for creating an Equity structure.
   Separate from Organization, Workspace, and Entity creation.
───────────────────────────────────────────────────────────────────────────── */

const EQUITY_TYPES = [
  { value: 'cap_table',         label: 'Cap Table',          desc: 'Track ownership across all shareholders' },
  { value: 'share_class',       label: 'Share Class',        desc: 'Define common, preferred, or custom share classes' },
  { value: 'vesting_plan',      label: 'Vesting Plan',       desc: 'Equity grants with cliff and vesting schedules' },
  { value: 'investor_ledger',   label: 'Investor Ledger',    desc: 'Track investor contributions and terms' },
  { value: 'convertible_notes', label: 'Convertible Notes',  desc: 'Debt instruments that convert to equity' },
  { value: 'safe_agreements',   label: 'SAFE Agreements',    desc: 'Simple Agreement for Future Equity' },
];

const SHAREHOLDER_ROLES = ['Founder', 'Investor', 'Employee', 'Advisor', 'Other'];

const EMPTY_FORM = {
  // Step 1 — Structure type + name
  structureName: '',
  equityType: '',
  country: '',
  // Step 2 — Shareholders
  shareholders: [{ name: '', email: '', role: 'Founder', percentage: '', shareClass: '' }],
  // Step 3 — Capital
  totalShares: '',
  issuedShares: '',
  valuation: '',
  fundingRounds: '',
  dilutionModel: '',
};

const TOTAL_STEPS = 3;
const STEPS = [
  { number: 1, label: 'Structure' },
  { number: 2, label: 'Shareholders' },
  { number: 3, label: 'Capital' },
];

export default function CreateEquityFlow() {
  const navigate = useNavigate();
  const { createEntity, currentOrganization } = useEnterprise();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const updateShareholder = (index, field, value) => {
    setForm((prev) => {
      const updated = prev.shareholders.map((sh, i) =>
        i === index ? { ...sh, [field]: value } : sh
      );
      return { ...prev, shareholders: updated };
    });
  };

  const addShareholder = () => {
    setForm((prev) => ({
      ...prev,
      shareholders: [...prev.shareholders, { name: '', email: '', role: 'Founder', percentage: '', shareClass: '' }],
    }));
  };

  const removeShareholder = (index) => {
    setForm((prev) => ({
      ...prev,
      shareholders: prev.shareholders.filter((_, i) => i !== index),
    }));
  };

  const canGoNext = () => {
    if (step === 1) return form.structureName.trim().length >= 2 && !!form.equityType && !!form.country;
    if (step === 2) return form.shareholders.some((s) => s.name.trim().length > 0);
    if (step === 3) return !!form.totalShares;
    return true;
  };

  const handleNext = () => { if (canGoNext()) setStep((s) => s + 1); };
  const handleBack = () => setStep((s) => s - 1);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentOrganization?.id) {
      setError('No active organization found. Please create your organization first.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const payload = {
        organization_id: currentOrganization.id,
        name: form.structureName.trim(),
        country: form.country,
        entity_type: 'corporation',
        workspace_mode: 'equity',
        status: 'active',
        enabled_modules: [
          'equity_registry',
          'equity_cap_table',
          'equity_valuation',
          'equity_transactions',
          'equity_governance',
        ],
        // Store equity-specific metadata in notes fields available on entity
        registration_number: '',
        // Pass equity detail as extra context (backend ignores unknown fields gracefully)
        equity_type: form.equityType,
        shareholders: form.shareholders.filter((s) => s.name.trim()),
        total_shares: Number(form.totalShares) || 0,
        issued_shares: Number(form.issuedShares) || 0,
        valuation: form.valuation.trim(),
        funding_rounds: form.fundingRounds.trim(),
        dilution_model: form.dilutionModel.trim(),
      };
      const newEntity = await createEntity(payload);
      navigate(`/app/equity/${newEntity.id}/registry`);
    } catch (err) {
      setError(err?.message || 'Failed to create equity structure. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Structure Name <span className="cw-required">*</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Series A Cap Table, Employee Vesting Plan"
          value={form.structureName}
          onChange={(e) => update('structureName', e.target.value)}
          autoFocus
        />
        <span className="cw-hint">A descriptive name for this equity structure.</span>
      </div>
      <div className="cw-field">
        <label className="cw-label">Country / Jurisdiction <span className="cw-required">*</span></label>
        <select
          className="cw-select"
          value={form.country}
          onChange={(e) => update('country', e.target.value)}
        >
          <option value="">Select country…</option>
          {countryDropdownOptions.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
        <span className="cw-hint">The jurisdiction where this equity structure is registered.</span>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Equity Structure Type <span className="cw-required">*</span></label>
        <div className="cw-equity-type-grid">
          {EQUITY_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              className={`cw-equity-type-card${form.equityType === t.value ? ' cw-equity-type-card--selected' : ''}`}
              onClick={() => update('equityType', t.value)}
            >
              <span className="cw-equity-type-label">{t.label}</span>
              <span className="cw-equity-type-desc">{t.desc}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="cw-step-fields">
      <p className="cw-section-desc">Add the shareholders for this equity structure. You can edit these later.</p>
      {form.shareholders.map((sh, i) => (
        <div key={i} className="cw-shareholder-row">
          <div className="cw-shareholder-header">
            <span className="cw-shareholder-num">Shareholder {i + 1}</span>
            {form.shareholders.length > 1 && (
              <button type="button" className="cw-remove-btn" onClick={() => removeShareholder(i)}>Remove</button>
            )}
          </div>
          <div className="cw-shareholder-fields">
            <div className="cw-field">
              <label className="cw-label">Name <span className="cw-required">*</span></label>
              <input
                className="cw-input"
                type="text"
                placeholder="Full name"
                value={sh.name}
                onChange={(e) => updateShareholder(i, 'name', e.target.value)}
              />
            </div>
            <div className="cw-field">
              <label className="cw-label">Email</label>
              <input
                className="cw-input"
                type="email"
                placeholder="email@example.com"
                value={sh.email}
                onChange={(e) => updateShareholder(i, 'email', e.target.value)}
              />
            </div>
            <div className="cw-field">
              <label className="cw-label">Role</label>
              <select className="cw-select" value={sh.role} onChange={(e) => updateShareholder(i, 'role', e.target.value)}>
                {SHAREHOLDER_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
            <div className="cw-field">
              <label className="cw-label">Ownership %</label>
              <input
                className="cw-input"
                type="text"
                placeholder="e.g. 25"
                value={sh.percentage}
                onChange={(e) => updateShareholder(i, 'percentage', e.target.value)}
              />
            </div>
            <div className="cw-field">
              <label className="cw-label">Share Class</label>
              <input
                className="cw-input"
                type="text"
                placeholder="e.g. Common A, Preferred B"
                value={sh.shareClass}
                onChange={(e) => updateShareholder(i, 'shareClass', e.target.value)}
              />
            </div>
          </div>
        </div>
      ))}
      <button type="button" className="cw-btn cw-btn--ghost cw-add-shareholder-btn" onClick={addShareholder}>
        + Add Shareholder
      </button>
    </div>
  );

  const renderStep3 = () => (
    <div className="cw-step-fields">
      <div className="cw-field">
        <label className="cw-label">Total Authorized Shares <span className="cw-required">*</span></label>
        <input
          className="cw-input"
          type="number"
          min="1"
          placeholder="e.g. 10000000"
          value={form.totalShares}
          onChange={(e) => update('totalShares', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Issued Shares</label>
        <input
          className="cw-input"
          type="number"
          min="0"
          placeholder="e.g. 7500000"
          value={form.issuedShares}
          onChange={(e) => update('issuedShares', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Valuation</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. $5,000,000"
          value={form.valuation}
          onChange={(e) => update('valuation', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Funding Rounds</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Pre-seed $500K, Seed $1.5M"
          value={form.fundingRounds}
          onChange={(e) => update('fundingRounds', e.target.value)}
        />
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Dilution Model</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Pro-rata, ESOP pool reserved at 15%"
          value={form.dilutionModel}
          onChange={(e) => update('dilutionModel', e.target.value)}
        />
      </div>
    </div>
  );

  const stepContent = [null, renderStep1, renderStep2, renderStep3];

  return (
    <div className="cw-page">
      <nav className="cw-topnav">
        <div className="cw-topnav-brand">
          <LedgoraLogo variant="white" size={28} withText={false} />
          <span className="cw-topnav-title">Create Equity Structure</span>
        </div>
        <button className="cw-topnav-cancel" onClick={() => navigate('/app/enterprise/org-overview')}>
          Cancel
        </button>
      </nav>

      <div className="cw-progress-bar">
        {STEPS.map((s) => (
          <div key={s.number} className={`cw-progress-step${step >= s.number ? ' cw-progress-step--done' : ''}${step === s.number ? ' cw-progress-step--active' : ''}`}>
            <span className="cw-progress-num">{step > s.number ? '✓' : s.number}</span>
            <span className="cw-progress-label">{s.label}</span>
          </div>
        ))}
      </div>

      <main className="cw-main">
        <form className="cw-card" onSubmit={handleSubmit}>
          <div className="cw-step-header">
            <span className="cw-step-eyebrow">Step {step} of {TOTAL_STEPS}</span>
            <h2 className="cw-step-title">{STEPS[step - 1].label}</h2>
          </div>

          {stepContent[step]()}

          {error && <p className="cw-error">{error}</p>}

          <div className="cw-actions">
            {step > 1 && (
              <button type="button" className="cw-btn cw-btn--ghost" onClick={handleBack}>
                Back
              </button>
            )}
            {step < TOTAL_STEPS ? (
              <button
                type="button"
                className="cw-btn cw-btn--primary"
                onClick={handleNext}
                disabled={!canGoNext()}
              >
                Continue
              </button>
            ) : (
              <button
                type="submit"
                className="cw-btn cw-btn--primary"
                disabled={submitting || !canGoNext()}
              >
                {submitting ? 'Creating Equity Structure…' : 'Create Equity Structure'}
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
