import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import LedgoraLogo from '../../components/branding/LedgoraLogo';
import { countryDropdownOptions } from '../../utils/countryDropdowns';
import '../Workspace/CreateWorkspace.css';

/* ─────────────────────────────────────────────────────────────────────────────
   CREATE ENTITY FLOW
   Dedicated flow for creating a legal Company / Entity.
   Separate from Organization, Workspace, and Equity creation.
───────────────────────────────────────────────────────────────────────────── */

const ENTITY_TYPES = [
  { value: 'llc',              label: 'LLC' },
  { value: 'corporation',      label: 'Corporation' },
  { value: 'partnership',      label: 'Partnership' },
  { value: 'sole_proprietor',  label: 'Sole Proprietor' },
  { value: 'nonprofit',        label: 'Nonprofit' },
  { value: 'foreign_entity',   label: 'Foreign Entity' },
];

const CURRENCIES = [
  { code: 'USD', label: 'USD — US Dollar' },
  { code: 'EUR', label: 'EUR — Euro' },
  { code: 'GBP', label: 'GBP — British Pound' },
  { code: 'AED', label: 'AED — UAE Dirham' },
  { code: 'SGD', label: 'SGD — Singapore Dollar' },
  { code: 'CHF', label: 'CHF — Swiss Franc' },
  { code: 'JPY', label: 'JPY — Japanese Yen' },
  { code: 'CAD', label: 'CAD — Canadian Dollar' },
  { code: 'AUD', label: 'AUD — Australian Dollar' },
  { code: 'INR', label: 'INR — Indian Rupee' },
  { code: 'PKR', label: 'PKR — Pakistani Rupee' },
  { code: 'ZAR', label: 'ZAR — South African Rand' },
  { code: 'NGN', label: 'NGN — Nigerian Naira' },
  { code: 'BRL', label: 'BRL — Brazilian Real' },
];

const EMPTY_FORM = {
  // Step 1 — Entity Type + Name
  entityType: '',
  registeredName: '',
  // Step 2 — Legal Information
  registeredAddress: '',
  country: '',
  stateProvince: '',
  taxId: '',
  incorporationDate: '',
  // Step 3 — Ownership Structure
  founders: '',
  shareholders: '',
  ownershipPercentages: '',
  votingRights: '',
  // Step 4 — Financial Structure
  bankAccounts: '',
  capitalStructure: '',
  reportingCurrency: 'USD',
};

const TOTAL_STEPS = 4;
const STEPS = [
  { number: 1, label: 'Entity Type' },
  { number: 2, label: 'Legal Info' },
  { number: 3, label: 'Ownership' },
  { number: 4, label: 'Financials' },
];

export default function CreateEntityFlow() {
  const navigate = useNavigate();
  const { createEntity, currentOrganization } = useEnterprise();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const update = (field, value) => setForm((prev) => ({ ...prev, [field]: value }));

  const canGoNext = () => {
    if (step === 1) return form.registeredName.trim().length >= 2 && !!form.entityType;
    if (step === 2) return !!form.country;
    if (step === 3) return true;
    if (step === 4) return true; // all financial fields are optional
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
        name: form.registeredName.trim(),
        entity_type: form.entityType,
        registered_address: form.registeredAddress.trim(),
        country: form.country,
        state_province: form.stateProvince.trim(),
        tax_id: form.taxId.trim() || undefined,
        incorporation_date: form.incorporationDate || undefined,
        founders: form.founders.trim(),
        shareholders: form.shareholders.trim(),
        ownership_percentages: form.ownershipPercentages.trim(),
        voting_rights: form.votingRights.trim(),
        bank_accounts: form.bankAccounts.trim(),
        capital_structure: form.capitalStructure.trim(),
        local_currency: form.reportingCurrency,
        workspace_mode: 'accounting',
        enabled_modules: ['finance', 'compliance'],
        status: 'active',
      };
      const newEntity = await createEntity(payload);
      if (newEntity?.id) {
        navigate(`/app/enterprise/entities/${newEntity.id}/dashboard`);
      } else {
        navigate('/app/enterprise/org-overview');
      }
    } catch (err) {
      const msg = err?.message || '';
      if (msg.toLowerCase().includes('registration number')) {
        setError('This registration number is already used for an entity in this country.');
      } else {
        setError(msg || 'Failed to create entity. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Registered Name <span className="cw-required">*</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Acme Holdings Ltd"
          value={form.registeredName}
          onChange={(e) => update('registeredName', e.target.value)}
          autoFocus
        />
        <span className="cw-hint">The legal registered name of this entity.</span>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Entity Type <span className="cw-required">*</span></label>
        <div className="cw-tile-grid">
          {ENTITY_TYPES.map((t) => (
            <button
              key={t.value}
              type="button"
              className={`cw-tile${form.entityType === t.value ? ' cw-tile--selected' : ''}`}
              onClick={() => update('entityType', t.value)}
            >
              <span className="cw-tile-label">{t.label}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Registered Address</label>
        <input
          className="cw-input"
          type="text"
          placeholder="Full registered address"
          value={form.registeredAddress}
          onChange={(e) => update('registeredAddress', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Country <span className="cw-required">*</span></label>
        <select className="cw-select" value={form.country} onChange={(e) => update('country', e.target.value)}>
          <option value="">Select country</option>
          {countryDropdownOptions.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="cw-field">
        <label className="cw-label">State / Province</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Delaware, Ontario"
          value={form.stateProvince}
          onChange={(e) => update('stateProvince', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Tax ID / EIN <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. 12-3456789"
          value={form.taxId}
          onChange={(e) => update('taxId', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Incorporation Date <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="date"
          value={form.incorporationDate}
          onChange={(e) => update('incorporationDate', e.target.value)}
        />
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Founders</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. John Smith, Jane Doe"
          value={form.founders}
          onChange={(e) => update('founders', e.target.value)}
        />
        <span className="cw-hint">Comma-separated list of founders.</span>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Shareholders</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. John Smith, Investor A, Employee Pool"
          value={form.shareholders}
          onChange={(e) => update('shareholders', e.target.value)}
        />
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Ownership Percentages</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. John 60%, Jane 30%, Pool 10%"
          value={form.ownershipPercentages}
          onChange={(e) => update('ownershipPercentages', e.target.value)}
        />
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Voting Rights</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. 1 share = 1 vote, Class A has 10x votes"
          value={form.votingRights}
          onChange={(e) => update('votingRights', e.target.value)}
        />
      </div>
    </div>
  );

  const renderStep4 = () => (
    <div className="cw-step-fields">
      <p className="cw-section-desc">All financial fields are optional. You can update them later in Entity Settings.</p>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Bank Accounts</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Operations Account (USD), Payroll Account"
          value={form.bankAccounts}
          onChange={(e) => update('bankAccounts', e.target.value)}
        />
        <span className="cw-hint">Describe the bank accounts associated with this entity.</span>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Capital Structure</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. $1M seed, $500K debt, $200K equity"
          value={form.capitalStructure}
          onChange={(e) => update('capitalStructure', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Reporting Currency <span style={{fontSize:11,color:'rgba(0,0,0,0.44)',fontWeight:400}}>(optional)</span></label>
        <select className="cw-select" value={form.reportingCurrency} onChange={(e) => update('reportingCurrency', e.target.value)}>
          {CURRENCIES.map((c) => (
            <option key={c.code} value={c.code}>{c.label}</option>
          ))}
        </select>
      </div>
    </div>
  );

  const stepContent = [null, renderStep1, renderStep2, renderStep3, renderStep4];

  return (
    <div className="cw-page">
      <nav className="cw-topnav">
        <div className="cw-topnav-brand">
          <LedgoraLogo variant="white" size={28} withText={false} />
          <span className="cw-topnav-title">Create Entity</span>
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

          {error && (
            <div className="cw-error" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
              <span>{error}</span>
              <button
                type="button"
                onClick={() => setError(null)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, lineHeight: 1, color: 'inherit', flexShrink: 0 }}
                aria-label="Dismiss error"
              >
                ✕
              </button>
            </div>
          )}

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
                {submitting ? 'Creating Entity…' : 'Create Entity'}
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
