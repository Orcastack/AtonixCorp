import React, { useState } from 'react';
import { useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import AtonixCorpLogo from '../../components/branding/AtonixCorpLogo';
import { organizationsAPI } from '../../services/api';
import { countryDropdownOptions } from '../../utils/countryDropdowns';
import {
  WORKSPACE_MODE_LABELS,
  WORKSPACE_PACKAGE_OPTIONS,
} from '../../utils/workspaceModules';
import './CreateWorkspace.css';

/* ─────────────────────────────────────────────────────────────────────────────
   AtonixCorp — Create Organization
   Form to create a new organization record.
  On success: provisions the organization record and returns the user to the console.
───────────────────────────────────────────────────────────────────────────── */
const CURRENCIES = [
  { code: 'AED', label: 'AED — UAE Dirham' },
  { code: 'PKR', label: 'PKR — Pakistani Rupee' },
  { code: 'PLN', label: 'PLN — Polish Złoty' },
  { code: 'PYG', label: 'PYG — Paraguayan Guaraní' },
  { code: 'QAR', label: 'QAR — Qatari Riyal' },
  { code: 'RON', label: 'RON — Romanian Leu' },
  { code: 'RSD', label: 'RSD — Serbian Dinar' },
  { code: 'RUB', label: 'RUB — Russian Ruble' },
  { code: 'RWF', label: 'RWF — Rwandan Franc' },
  { code: 'SAR', label: 'SAR — Saudi Riyal' },
  { code: 'SBD', label: 'SBD — Solomon Islands Dollar' },
  { code: 'SCR', label: 'SCR — Seychellois Rupee' },
  { code: 'SDG', label: 'SDG — Sudanese Pound' },
  { code: 'SEK', label: 'SEK — Swedish Krona' },
  { code: 'SGD', label: 'SGD — Singapore Dollar' },
  { code: 'SLL', label: 'SLL — Sierra Leonean Leone' },
  { code: 'SOS', label: 'SOS — Somali Shilling' },
  { code: 'SRD', label: 'SRD — Surinamese Dollar' },
  { code: 'SSP', label: 'SSP — South Sudanese Pound' },
  { code: 'STN', label: 'STN — São Tomé Dobra' },
  { code: 'SYP', label: 'SYP — Syrian Pound' },
  { code: 'SZL', label: 'SZL — Swazi Lilangeni' },
  { code: 'THB', label: 'THB — Thai Baht' },
  { code: 'TJS', label: 'TJS — Tajikistani Somoni' },
  { code: 'TMT', label: 'TMT — Turkmenistani Manat' },
  { code: 'TND', label: 'TND — Tunisian Dinar' },
  { code: 'TOP', label: 'TOP — Tongan Paʻanga' },
  { code: 'TRY', label: 'TRY — Turkish Lira' },
  { code: 'TTD', label: 'TTD — Trinidad and Tobago Dollar' },
  { code: 'TWD', label: 'TWD — New Taiwan Dollar' },
  { code: 'TZS', label: 'TZS — Tanzanian Shilling' },
  { code: 'UAH', label: 'UAH — Ukrainian Hryvnia' },
  { code: 'UGX', label: 'UGX — Ugandan Shilling' },
  { code: 'USD', label: 'USD — US Dollar' },
  { code: 'UYU', label: 'UYU — Uruguayan Peso' },
  { code: 'UZS', label: 'UZS — Uzbekistani Som' },
  { code: 'VES', label: 'VES — Venezuelan Bolívar' },
  { code: 'VND', label: 'VND — Vietnamese Dong' },
  { code: 'VUV', label: 'VUV — Vanuatu Vatu' },
  { code: 'WST', label: 'WST — Samoan Tālā' },
  { code: 'XAF', label: 'XAF — Central African CFA Franc' },
  { code: 'XOF', label: 'XOF — West African CFA Franc' },
  { code: 'YER', label: 'YER — Yemeni Rial' },
  { code: 'ZAR', label: 'ZAR — South African Rand' },
  { code: 'ZMW', label: 'ZMW — Zambian Kwacha' },
  { code: 'ZWL', label: 'ZWL — Zimbabwean Dollar' },
];

const COUNTRIES = countryDropdownOptions;

const ENTITY_TYPES = [
  { value: 'corporation', label: 'Corporation' },
  { value: 'llc', label: 'LLC' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'sole_proprietorship', label: 'Sole Proprietorship' },
  { value: 'non_profit', label: 'Non-Profit' },
  { value: 'holding_company', label: 'Holding Company' },
  { value: 'branch', label: 'Branch / Subsidiary' },
  { value: 'trust', label: 'Trust' },
];

const INDUSTRIES = [
  { value: 'technology', label: 'Technology' },
  
  { value: 'engineering', label: 'Engineering' },
  { value: 'accounting', label: 'Accounting' },
  { value: 'education', label: 'Education' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'media_entertainment', label: 'Media/Entertainment' },
  { value: 'retail_commerce', label: 'Retail/Commerce' },
  { value: 'construction', label: 'Construction' },
  { value: 'manufacturing', label: 'Manufacturing' },
  { value: 'research', label: 'Research' },
  { value: 'real_estate', label: 'Real Estate' },
  { value: 'consulting', label: 'Consulting & Professional Services' },
  { value: 'hospitality', label: 'Hospitality & Tourism' },
  { value: 'logistics', label: 'Logistics & Supply Chain' },
  { value: 'energy', label: 'Energy & Utilities' },
  { value: 'agriculture', label: 'Agriculture' },
  { value: 'other', label: 'Other' },
];

const FISCAL_YEAR_ENDS = [
  { value: '12-31', label: 'December 31 (Calendar Year)' },
  { value: '01-31', label: 'January 31' },
  { value: '02-28', label: 'February 28' },
  { value: '03-31', label: 'March 31' },
  { value: '04-30', label: 'April 30' },
  { value: '05-31', label: 'May 31' },
  { value: '06-30', label: 'June 30' },
  { value: '07-31', label: 'July 31' },
  { value: '08-31', label: 'August 31' },
  { value: '09-30', label: 'September 30' },
  { value: '10-31', label: 'October 31' },
  { value: '11-30', label: 'November 30' },
];

/* Convert MM-DD picker value → YYYY-MM-DD for the API.
   Uses the next upcoming occurrence of that date. */
const toFiscalYearEndDate = (monthDay) => {
  const [mm, dd] = monthDay.split('-').map(Number);
  const now = new Date();
  const curYear = now.getFullYear();
  const candidate = new Date(curYear, mm - 1, dd);
  const year = candidate > now ? curYear : curYear + 1;
  return `${year}-${String(mm).padStart(2, '0')}-${String(dd).padStart(2, '0')}`;
};

/* ─── Steps ──────────────────────────────────────────────────────────────── */
const STEPS = [
  { id: 1, label: 'Company Identity' },
  { id: 2, label: 'Jurisdiction & Currency' },
  { id: 3, label: 'Fiscal & Structure' },
  { id: 4, label: 'Modules & License' },
  { id: 5, label: 'Launch' },
];

const EMPTY_FORM = {
  name: '',
  registrationNumber: '',
  businessType: 'corporation',
  industry: '',
  logoUrl: '',
  website: '',
  employeeCount: '1',
  country: '',
  currency: 'USD',
  email: '',
  address: '',
  serviceTime: '',
  fiscalYearEnd: '12-31',
  taxRegime: '',
  workspaceMode: '',
  enabledModules: [],
  subscriptionTier: 'professional',
};

const SUBSCRIPTION_TIERS = [
  { id: 'basic', label: 'Basic', detail: 'Core governance workspace and system notices.' },
  { id: 'professional', label: 'Professional', detail: 'Operational sender identities and 2,500 monthly sends.' },
  { id: 'enterprise', label: 'Enterprise', detail: 'Marketing controls and 25,000 monthly sends.' },
];

const ACCOUNTING_MODULE_OPTIONS = [
  { key: 'overview', label: 'Organization Overview', detail: 'Home dashboard and entity launchpad.' },
  { key: 'members', label: 'Members', detail: 'Team invitations and membership visibility.' },
  { key: 'groups', label: 'Departments', detail: 'Finance department structure, ownership, and access grouping.' },
  { key: 'meetings', label: 'Meetings', detail: 'Meeting scheduling, records, and follow-ups.' },
  { key: 'calendar', label: 'Calendar', detail: 'Operational timeline and key dates.' },
  { key: 'files', label: 'Files', detail: 'Document storage and organization file access.' },
  { key: 'permissions', label: 'Permissions', detail: 'Organization access and approval controls.' },
  { key: 'settings', label: 'Settings', detail: 'Organization-level configuration and policies.' },
  { key: 'email', label: 'Email', detail: 'Messaging and communication workflows.' },
  { key: 'marketing', label: 'Marketing', detail: 'Growth and outbound organization tools.' },
];

const EQUITY_MODULE_OPTIONS = [
  { key: 'equity_registry', label: 'Ownership Registry', detail: 'Registered holders and beneficial owner records.' },
  { key: 'equity_cap_table', label: 'Cap Table', detail: 'Share classes, issuances, and dilution structure.' },
  { key: 'equity_vesting', label: 'Vesting & Grants', detail: 'Grant schedules, cliffs, accelerations, and forfeiture logic.' },
  { key: 'equity_exercises', label: 'Exercise Center', detail: 'Exercise requests, certificates, approvals, and payroll tax sync.' },
  { key: 'equity_valuation', label: 'Valuation', detail: 'Pricing history and board-approved value points.' },
  { key: 'equity_transactions', label: 'Equity Transactions', detail: 'Issuances, transfers, conversions, and approvals.' },
  { key: 'equity_governance', label: 'Governance & Reporting', detail: 'Board packs, reports, and regulatory artifacts.' },
];

const CreateWorkspace = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { createWorkspace, createEntity, createOrganization, currentOrganization, setActiveWorkspace } = useEnterprise();
  const location = useLocation();
  const isOrgCreate = location.pathname.includes('/organizations/create');
  const isEntityCreate = location.pathname.includes('/entities/create');
  const flowLabel = isEntityCreate ? 'Entity' : 'Organization';
  const flowKicker = isEntityCreate ? 'New Legal Entity' : 'New Organization';
  const flowSubtitle = isEntityCreate
    ? 'A legal entity represents a registered company, subsidiary, or branch. Configure its jurisdiction, currency, fiscal year, and operating modules.'
    : 'An organization represents the primary operating container. You can provision it for accounting, equity management, a combined operating system, or a standalone shell.';

  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [identityStatus, setIdentityStatus] = useState(null);
  const [verifyingIdentity, setVerifyingIdentity] = useState(false);
  const [fyOpen, setFyOpen] = useState(false);
  const [fyMonth, setFyMonth] = useState(null);
  const fyRef = React.useRef(null);

  // Pre-select workspace mode from URL param e.g. ?mode=equity
  React.useEffect(() => {
    const modeParam = searchParams.get('mode');
    if (modeParam) {
      selectPackage(modeParam);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Close fiscal picker when clicking outside
  React.useEffect(() => {
    if (!fyOpen) return;
    const handler = (e) => {
      if (fyRef.current && !fyRef.current.contains(e.target)) setFyOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [fyOpen]);

  const update = (field, value) => {
    if (field === 'name' || field === 'registrationNumber') setIdentityStatus(null);
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const verifyIdentity = async () => {
    if (!form.name.trim() || !form.registrationNumber.trim()) {
      setError('Enter the company name and registration number before verification.');
      return false;
    }
    setVerifyingIdentity(true);
    setError(null);
    try {
      const response = await organizationsAPI.verifyIdentity({
        name: form.name.trim(),
        registration_number: form.registrationNumber.trim(),
      });
      const result = response.data;
      setIdentityStatus(result);
      if (!result.name_available || !result.available) {
        setError(!result.name_available
          ? 'A company with this name already exists.'
          : 'This company registration number is already in use.');
        return false;
      }
      setForm((previous) => ({ ...previous, registrationNumber: result.registration_number }));
      return true;
    } catch (requestError) {
      const details = requestError.response?.data;
      setError(details?.name || details?.registration_number || 'Company identity could not be verified.');
      return false;
    } finally {
      setVerifyingIdentity(false);
    }
  };

  // Parse current MM-DD value
  const [fySelMonth, fySelDay] = form.fiscalYearEnd.split('-').map(Number);
  const fyLabel = (() => {
    const d = new Date(2000, fySelMonth - 1, fySelDay);
    return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric' });
  })();

  const MONTH_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const MONTH_FULL  = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  const daysInMonth = (m) => new Date(2000, m, 0).getDate(); // m is 1-based

  const selectPackage = (mode) => {
    const selected = WORKSPACE_PACKAGE_OPTIONS.find((option) => option.id === mode);
    setForm((prev) => ({
      ...prev,
      workspaceMode: mode,
      enabledModules: selected ? [...selected.modules] : prev.enabledModules,
    }));
  };

  const canGoNext = () => {
    if (step === 1) {
      return form.name.trim().length >= 2
        && (!isOrgCreate || form.registrationNumber.trim().length >= 4)
        && (!isOrgCreate || (identityStatus?.available && identityStatus?.name_available));
    }
    if (step === 2) return !!form.country && !!form.currency;
    if (step === 4) return !!form.workspaceMode && !!form.subscriptionTier && (form.enabledModules.length > 0 || form.workspaceMode === 'standalone');
    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { setError('Company name is required'); return; }
    if (isOrgCreate && !form.registrationNumber.trim()) { setError('Company registration number is required'); return; }
    if (!form.country)     { setError('Country is required'); return; }
    if (!form.workspaceMode) { setError('Select an organization package before launch.'); return; }
    if (!isOrgCreate && !currentOrganization?.id) { setError('No active organization is selected for this account.'); return; }

    setSubmitting(true);
    setError(null);

    try {
      if (isOrgCreate) {
        // Creating a top-level organization — no currentOrganization required
        const newOrg = await createOrganization({
          name: form.name.trim(),
          registration_number: form.registrationNumber.trim(),
          primary_country: form.country,
          primary_currency: form.currency,
          industry: form.industry.trim() || form.businessType,
          description: '',
          logo_url: form.logoUrl.trim(),
          website: form.website.trim(),
          employee_count: Number(form.employeeCount) || 1,
          settings: {
            email: form.email.trim(),
            address: form.address.trim(),
            service_time: form.serviceTime.trim(),
            tax_regime: form.taxRegime.trim(),
            subscription_tier: form.subscriptionTier,
          },
        });
        if (newOrg) {
          navigate('/app/console');
        }
      } else {
        // Creating an entity within the current organization
        const payload = {
          name: form.name.trim(),
          country: form.country,
          entity_type: form.businessType,
          local_currency: form.currency,
          fiscal_year_end: toFiscalYearEndDate(form.fiscalYearEnd),
          status: 'active',
          organization_id: currentOrganization?.id,
          registration_number: form.registrationNumber || undefined,
          workspace_mode: form.workspaceMode,
          enabled_modules: form.enabledModules,
        };

        let newWorkspace;
        if (typeof createWorkspace === 'function') {
          newWorkspace = await createWorkspace({
            organizationId: currentOrganization?.id,
            ...form,
            fiscalYearEnd: toFiscalYearEndDate(form.fiscalYearEnd),
            fiscal_year_end: toFiscalYearEndDate(form.fiscalYearEnd),
            workspace_mode: form.workspaceMode,
            enabled_modules: form.enabledModules,
          });
        } else {
          newWorkspace = await createEntity(payload);
          if (newWorkspace && typeof setActiveWorkspace === 'function') {
            setActiveWorkspace(newWorkspace);
          }
        }

        if (newWorkspace) {
          navigate('/app/console');
        }
      }
    } catch (err) {
      setError(err?.message || `Failed to create ${flowLabel.toLowerCase()}. Please try again.`);
    } finally {
      setSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Company Name <span className="cw-required">*</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Acme Holdings Ltd"
          value={form.name}
          onChange={(e) => update('name', e.target.value)}
          autoFocus
        />
        {isOrgCreate && (
          <div className={`cw-identity-status${identityStatus?.available && identityStatus?.name_available ? ' is-verified' : ''}`}>
            <span>{identityStatus?.available && identityStatus?.name_available ? 'Identity available and normalized' : 'Verify identity before continuing'}</span>
            <button type="button" className="cw-verify-btn" onClick={verifyIdentity} disabled={verifyingIdentity}>
              {verifyingIdentity ? 'Verifying...' : 'Verify company identity'}
            </button>
          </div>
        )}
        <span className="cw-hint">This will be displayed as the organization name throughout AtonixCorp.</span>
      </div>
      <div className="cw-field">
        <label className="cw-label">Company Registration Number {isOrgCreate && <span className="cw-required">*</span>}</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. 12345678"
          value={form.registrationNumber}
          onChange={(e) => update('registrationNumber', e.target.value)}
          required={isOrgCreate}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Business Type</label>
        <select className="cw-select" value={form.businessType} onChange={(e) => update('businessType', e.target.value)}>
          {ENTITY_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Industry</label>
        <select className="cw-select" value={form.industry} onChange={(e) => update('industry', e.target.value)}>
          <option value="">Select industry…</option>
          {INDUSTRIES.map((i) => <option key={i.value} value={i.value}>{i.label}</option>)}
        </select>
      </div>
      <div className="cw-field">
        <label className="cw-label">Employees</label>
        <input
          className="cw-input"
          type="number"
          min="1"
          placeholder="e.g. 1"
          value={form.employeeCount}
          onChange={(e) => update('employeeCount', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Organization Email <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="email"
          placeholder="e.g. finance@company.com"
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
        />
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Logo URL <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="url"
          placeholder="https://example.com/logo.png"
          value={form.logoUrl}
          onChange={(e) => update('logoUrl', e.target.value)}
        />
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Country of Incorporation <span className="cw-required">*</span></label>
        <select className="cw-select" value={form.country} onChange={(e) => update('country', e.target.value)}>
          <option value="">Select country…</option>
          {COUNTRIES.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select>
        <span className="cw-hint">Determines the default tax jurisdiction and compliance requirements.</span>
      </div>
      <div className="cw-field">
        <label className="cw-label">Functional Currency <span className="cw-required">*</span></label>
        <select className="cw-select" value={form.currency} onChange={(e) => update('currency', e.target.value)}>
          {CURRENCIES.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
        </select>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Website <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="url"
          placeholder="https://company.com"
          value={form.website}
          onChange={(e) => update('website', e.target.value)}
        />
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="cw-step-fields">
      <div className="cw-field" ref={fyRef} style={{ position: 'relative' }}>
        <label className="cw-label">Fiscal Year End</label>

        {/* Trigger button */}
        <button
          type="button"
          className="cw-fy-trigger"
          onClick={() => { setFyOpen(o => !o); setFyMonth(null); }}
        >
          <span>{fyLabel}</span>
          <span className="cw-fy-trigger-arrow">{fyOpen ? '▲' : '▼'}</span>
        </button>
        <span className="cw-hint">Determines your accounting period and tax return windows.</span>

        {/* Picker popover */}
        {fyOpen && (
          <div className="cw-fy-picker">
            {fyMonth === null ? (
              /* ── Month grid ── */
              <>
                <div className="cw-fy-picker-title">Select Month</div>
                <div className="cw-fy-months">
                  {MONTH_NAMES.map((mn, i) => (
                    <button
                      key={mn}
                      type="button"
                      className={`cw-fy-month-btn${fySelMonth === i + 1 ? ' selected' : ''}`}
                      onClick={() => setFyMonth(i + 1)}
                    >
                      {mn}
                    </button>
                  ))}
                </div>
              </>
            ) : (
              /* ── Day grid ── */
              <>
                <div className="cw-fy-picker-nav">
                  <button type="button" className="cw-fy-back" onClick={() => setFyMonth(null)}>← Months</button>
                  <span className="cw-fy-picker-title" style={{ flex: 1, textAlign: 'center' }}>{MONTH_FULL[fyMonth - 1]}</span>
                </div>
                <div className="cw-fy-days">
                  {Array.from({ length: daysInMonth(fyMonth) }, (_, i) => i + 1).map(d => (
                    <button
                      key={d}
                      type="button"
                      className={`cw-fy-day-btn${fySelMonth === fyMonth && fySelDay === d ? ' selected' : ''}`}
                      onClick={() => {
                        update('fiscalYearEnd', `${String(fyMonth).padStart(2,'0')}-${String(d).padStart(2,'0')}`);
                        setFyOpen(false);
                        setFyMonth(null);
                      }}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
      <div className="cw-field">
        <label className="cw-label">Tax Regime <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Corporate Income Tax, VAT"
          value={form.taxRegime}
          onChange={(e) => update('taxRegime', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Service Time <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Mon-Fri, 9:00 AM - 6:00 PM"
          value={form.serviceTime}
          onChange={(e) => update('serviceTime', e.target.value)}
        />
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Address <span className="cw-optional">(optional)</span></label>
        <textarea
          className="cw-input"
          rows="3"
          placeholder="Street, city, state, postal code"
          value={form.address}
          onChange={(e) => update('address', e.target.value)}
        />
      </div>

      {/* Summary Review */}
      <div className="cw-field cw-field-wide">
        <div className="cw-review-card creation-summary-card">
          <h4 className="cw-review-title">Review — New {flowLabel}</h4>
          <div className="cw-review-rows">
            <div className="cw-review-row"><span>Name</span><strong>{form.name}</strong></div>
            <div className="cw-review-row"><span>Type</span><strong>{ENTITY_TYPES.find(t => t.value === form.businessType)?.label}</strong></div>
            {form.industry && <div className="cw-review-row"><span>Industry</span><strong>{INDUSTRIES.find(i => i.value === form.industry)?.label}</strong></div>}
            <div className="cw-review-row"><span>Country</span><strong>{COUNTRIES.find(c => c.code === form.country)?.name || form.country}</strong></div>
            <div className="cw-review-row"><span>Currency</span><strong>{form.currency}</strong></div>
            <div className="cw-review-row"><span>Employees</span><strong>{form.employeeCount || '1'}</strong></div>
            {form.email && <div className="cw-review-row"><span>Email</span><strong>{form.email}</strong></div>}
            {form.website && <div className="cw-review-row"><span>Website</span><strong>{form.website}</strong></div>}
            {form.serviceTime && <div className="cw-review-row"><span>Service Time</span><strong>{form.serviceTime}</strong></div>}
            {form.address && <div className="cw-review-row"><span>Address</span><strong>{form.address}</strong></div>}
            <div className="cw-review-row"><span>Fiscal Year End</span><strong>{FISCAL_YEAR_ENDS.find(f => f.value === form.fiscalYearEnd)?.label}</strong></div>
          </div>
          <div className="cw-review-note">
            AtonixCorp will automatically set up your chart of accounts and default tax profile based on the country and business type selected.
          </div>
        </div>
      </div>
    </div>
  );

  const renderStep4 = () => {
    const selectedPackage = WORKSPACE_PACKAGE_OPTIONS.find((option) => option.id === form.workspaceMode) || null;
    const accountingModules = ACCOUNTING_MODULE_OPTIONS.filter((module) => form.enabledModules.includes(module.key));
    const equityModules = EQUITY_MODULE_OPTIONS.filter((module) => form.enabledModules.includes(module.key));
    const governanceModules = equityModules.filter((module) => module.key === 'equity_governance');
    const preinstalledCount = selectedPackage?.modules?.length || 0;
    const packageLabel = WORKSPACE_MODE_LABELS[form.workspaceMode] || 'Select';

    return (
      <div className="cw-launch-template">
        <section className="cw-launch-section cw-launch-section--summary">
          <div className="cw-launch-section-header">
            <div>
              <h4 className="cw-launch-section-title">Organization Summary</h4>
            </div>
            <span className="cw-launch-section-pill">Configure</span>
          </div>

          <div className="cw-launch-summary-grid">
            <div className="cw-launch-summary-row">
              <span>Package</span>
              <strong>{packageLabel}</strong>
            </div>
            <div className="cw-launch-summary-row">
              <span>Modules</span>
              <strong>{preinstalledCount}</strong>
            </div>
            <div className="cw-launch-summary-row">
              <span>Plan</span>
              <strong>{form.subscriptionTier}</strong>
            </div>
          </div>

          <div className="cw-launch-package-grid" aria-label="Organization packages">
            {WORKSPACE_PACKAGE_OPTIONS.map((option) => (
              <button
                key={option.id}
                type="button"
                className={`cw-launch-package-card${form.workspaceMode === option.id ? ' selected' : ''}`}
                onClick={() => selectPackage(option.id)}
                aria-pressed={form.workspaceMode === option.id}
              >
                <span className="cw-launch-package-title">{WORKSPACE_MODE_LABELS[option.id]}</span>
              </button>
            ))}
          </div>
          <div className="cw-tier-grid" aria-label="Subscription tiers">
            {SUBSCRIPTION_TIERS.map((tier) => (
              <button
                key={tier.id}
                type="button"
                className={`cw-tier-card${form.subscriptionTier === tier.id ? ' selected' : ''}`}
                onClick={() => update('subscriptionTier', tier.id)}
                aria-pressed={form.subscriptionTier === tier.id}
              >
                <span>{tier.label}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="cw-launch-section cw-launch-section--modules">
          <div className="cw-launch-section-header">
            <div>
              <h4 className="cw-launch-section-title">Module Overview</h4>
            </div>
          </div>

          <div className="cw-launch-module-grid">
            <article className="cw-launch-module-card">
              <span className="cw-launch-module-label">Accounting modules</span>
              <strong>{accountingModules.length} selected</strong>
            </article>
            <article className="cw-launch-module-card">
              <span className="cw-launch-module-label">Equity modules</span>
              <strong>{equityModules.length} selected</strong>
            </article>
            <article className="cw-launch-module-card">
              <span className="cw-launch-module-label">Governance modules</span>
              <strong>{governanceModules.length} selected</strong>
            </article>
          </div>
        </section>

      </div>
    );
  };

  const renderStep5 = () => {
    const selectedTier = SUBSCRIPTION_TIERS.find((tier) => tier.id === form.subscriptionTier);
    return (
      <section className="cw-launch-confirmation-card cw-launch-review">
        <div className="cw-launch-section-header cw-launch-section-header--center">
          <div>
            <h4 className="cw-launch-section-title">Launch Review</h4>
            <p className="cw-launch-section-subtitle">Confirm the company identity, operating configuration, modules, and license.</p>
          </div>
        </div>
        <div className="cw-final-summary-grid">
          <div><span>Company</span><strong>{form.name}</strong></div>
          <div><span>Registration</span><strong>{form.registrationNumber}</strong></div>
          <div><span>Jurisdiction</span><strong>{COUNTRIES.find((country) => country.code === form.country)?.name || form.country}</strong></div>
          <div><span>Currency</span><strong>{form.currency}</strong></div>
          <div><span>Package</span><strong>{selectedPackage?.title || 'Not selected'}</strong></div>
          <div><span>License</span><strong>{selectedTier?.label || 'Not selected'}</strong></div>
        </div>
        <div className="cw-launch-confirmation-actions">
          <button type="submit" className="cw-btn cw-btn-create" disabled={submitting || !canGoNext() || (!isOrgCreate && !currentOrganization?.id)}>
            {submitting ? `Creating ${flowLabel}...` : `Launch ${flowLabel}`}
          </button>
        </div>
      </section>
    );
  };

  const selectedPackage = WORKSPACE_PACKAGE_OPTIONS.find((option) => option.id === form.workspaceMode) || null;
  const dashboardGuide = isEntityCreate ? [
    {
      title: 'Returns to Organization Dashboard',
      description: 'After creation, the new entity is linked to the active organization and visible in the Entities section.',
    },
    {
      title: 'Entity-level accounting',
      description: 'Each entity has its own chart of accounts, tax jurisdiction, and reporting currency.',
    },
    {
      title: 'Dashboards stay intact',
      description: 'Internal dashboards, modules, and permissions remain unchanged.',
    },
  ] : [
    {
      title: 'Returns to AtonixCorp Console',
      description: 'After creation, you return to the console where the new organization is available from the top-level flow.',
    },
    {
      title: 'Organization-first operating model',
      description: 'The organization becomes the first operational layer, with workspaces remaining a lower-tier environment.',
    },
    {
      title: 'Dashboards stay intact',
      description: 'Internal dashboards, modules, and permissions remain unchanged while entry now starts from the console.',
    },
  ];

  return (
    <div className="cw-page creation-flow">
      {/* Top Navbar */}
      <header className="cw-topnav">
        <div className="cw-topnav-brand">
          <AtonixCorpLogo variant="white" size="small" withText text="AtonixCorp" />
        </div>
        <button className="cw-topnav-back" onClick={() => navigate('/app/console')}>
          ← {isEntityCreate ? 'All Entities' : 'All Organizations'}
        </button>
      </header>

      <div className="create-workspace">
      {/* Back link — hidden (kept for CSS compat) */}
      <button className="cw-back-btn" style={{display:'none'}} onClick={() => navigate('/app/console')}>
        ← Back to Console
      </button>

      <div className="cw-card creation-card">
        {/* Header */}
        <div className="cw-header">
          <span className="cw-kicker">{flowKicker}</span>
          <h1 className="cw-title">Create {flowLabel}</h1>
          <p className="cw-subtitle">
            {flowSubtitle}
          </p>
        </div>

        {/* Steps Indicator */}
        <div className="cw-steps">
          {STEPS.map((s, idx) => (
            <React.Fragment key={s.id}>
              <div className={`cw-step-dot ${step === s.id ? 'cw-step-active' : step > s.id ? 'cw-step-done' : ''}`}>
                <span>{step > s.id ? '+' : s.id}</span>
                <span className="cw-step-label">{s.label}</span>
              </div>
              {idx < STEPS.length - 1 && <div className={`cw-step-line ${step > s.id ? 'cw-step-line-done' : ''}`} />}
            </React.Fragment>
          ))}
        </div>

        {/* Error */}
        {error && <div className="cw-error">{error}</div>}

        {/* Form */}
        <form onSubmit={handleSubmit} className="cw-form">
          {step === 1 && renderStep1()}
          {step === 2 && renderStep2()}
          {step === 3 && renderStep3()}
          {step === 4 && renderStep4()}
          {step === 5 && renderStep5()}

          {/* Navigation */}
          {step < 5 && (
            <div className="cw-nav">
              {step > 1 && (
                <button type="button" className="cw-btn cw-btn-secondary" onClick={() => setStep(step - 1)}>
                  ← Previous
                </button>
              )}
              <div className="cw-nav-spacer" />
              <button
                type="button"
                className="cw-btn cw-btn-primary"
                onClick={async () => {
                  if (step === 1 && isOrgCreate && !(await verifyIdentity())) return;
                  setStep(step + 1);
                }}
                disabled={!canGoNext()}
              >
                Next →
              </button>
            </div>
          )}
        </form>
      </div>

      {/* Info sidebar */}
      <aside className="cw-sidebar">
        <section className="cw-org-summary" aria-label="Organization summary">
          <div className="cw-org-summary-head">
            <span>Organization Summary</span>
            <strong>Step {step} of {STEPS.length}</strong>
          </div>
          <div className="cw-org-summary-row"><span>Company</span><strong>{form.name || 'Not entered'}</strong></div>
          <div className="cw-org-summary-row"><span>Registration</span><strong>{form.registrationNumber || 'Not entered'}</strong></div>
          <div className="cw-org-summary-row"><span>Jurisdiction</span><strong>{COUNTRIES.find((country) => country.code === form.country)?.name || 'Not selected'}</strong></div>
          <div className="cw-org-summary-row"><span>Modules</span><strong>{form.enabledModules.length || 'None'}</strong></div>
          <div className="cw-org-summary-row"><span>License</span><strong>{SUBSCRIPTION_TIERS.find((tier) => tier.id === form.subscriptionTier)?.label}</strong></div>
        </section>
        <h3>What happens next</h3>
        <ul className="cw-info-list">
          <li>
            <div>
              <strong>Chart of Accounts</strong>
              <p>A default chart of accounts based on your country and business type will be created automatically.</p>
            </div>
          </li>
          <li>
            <div>
              <strong>Tax Profile</strong>
              <p>A default tax profile will be set up for the selected jurisdiction.</p>
            </div>
          </li>
          <li>
            <div>
              <strong>You are the Owner</strong>
              <p>You will be assigned the Owner role. You can invite team members and configure permissions later.</p>
            </div>
          </li>
          <li>
            <div>
              <strong>Scoped Environment</strong>
              <p>All financial data — ledger entries, invoices, budgets, tax filings — is scoped inside this organization environment.</p>
            </div>
          </li>
          <li>
            <div>
              <strong>Dedicated Equity Sidebar</strong>
              <p>If you enable equity management, the organization gets a separate AtonixCorp Equity Management navigation with registry, cap table, valuation, transactions, and governance flows.</p>
            </div>
          </li>
        </ul>

        <div className="cw-sidebar-panel">
          <h3>After Creation</h3>
          <div className="cw-dashboard-guide">
            {dashboardGuide.map((item) => (
              <article key={item.title} className="cw-dashboard-guide-card">
                <strong>{item.title}</strong>
                <p>{item.description}</p>
              </article>
            ))}
          </div>
        </div>

      </aside>
    </div>{/* /.create-workspace */}
    </div>
  );
};

export default CreateWorkspace;
