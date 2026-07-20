import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEnterprise } from '../../context/EnterpriseContext';
import AtonixCorpLogo from '../../components/branding/AtonixCorpLogo';
import { countryDropdownOptions } from '../../utils/countryDropdowns';
import { getWorkspaceTypeDefinition, WORKSPACE_TYPE_OPTIONS } from '../../utils/workspaceTypeRegistry';
import EnterpriseDepartmentSelector from '../../components/EnterpriseDepartmentSelector';
import './CreateWorkspace.css';

/* ─────────────────────────────────────────────────────────────────────────────
   CREATE WORKSPACE FLOW
   Dedicated flow for creating an Operational Workspace.
   Separate from Organization creation and Entity creation.
───────────────────────────────────────────────────────────────────────────── */

const EMPTY_FORM = {
  name: '',
  workspaceType: '',
  parentEntity: '',
  country: '',
  address: '',
  registrationNumber: '',
  industry: '',
  selectedBranch: '',
  selectedSubBranch: '',
  departments: '',
  teams: '',
  staffCount: '',
  ownershipHierarchy: '',
  departmentSelections: [],
  enabledModules: [],
};

const TOTAL_STEPS = 4;

const STEPS = [
  { number: 1, label: 'Workspace Type' },
  { number: 2, label: 'Business Info' },
  { number: 3, label: 'Structure' },
  { number: 4, label: 'Modules' },
];

export default function CreateWorkspaceFlow() {
  const navigate = useNavigate();
  const { createWorkspace, currentOrganization, entities } = useEnterprise();
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const selectedType = getWorkspaceTypeDefinition(form.workspaceType);
  const availableBranches = selectedType?.branches || [];
  const selectedBranch = availableBranches.find((branch) => branch.key === form.selectedBranch) || null;
  const moduleCards = (selectedType?.modules || []).map((moduleKey) => ({
    key: moduleKey,
    label: moduleKey.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
    desc: 'Provisioned from the selected workspace template.',
  }));
  const workspaceParents = (entities || []).filter((entity) => entity.workspace_mode === 'workspace');

  const update = (field, value) => setForm((prev) => {
    if (field === 'workspaceType') {
      const definition = getWorkspaceTypeDefinition(value);
      return {
        ...prev,
        workspaceType: value,
        industry: definition?.industryLabel || prev.industry,
        selectedBranch: '',
        selectedSubBranch: '',
        enabledModules: definition?.modules || [],
      };
    }

    if (field === 'selectedBranch') {
      return {
        ...prev,
        selectedBranch: value,
        selectedSubBranch: '',
      };
    }

    return { ...prev, [field]: value };
  });

  const toggleModule = (key) => {
    setForm((prev) => {
      const modules = new Set(prev.enabledModules);
      modules.has(key) ? modules.delete(key) : modules.add(key);
      return { ...prev, enabledModules: Array.from(modules) };
    });
  };

  const canGoNext = () => {
    if (step === 1) return form.name.trim().length >= 2 && !!form.workspaceType;
    if (step === 2) return !!form.country;
    if (step === 3) return availableBranches.length === 0 || !!form.selectedBranch;
    if (step === 4) return form.enabledModules.length > 0;
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
        organizationId: currentOrganization.id,
        name: form.name.trim(),
        country: form.country,
        currency: 'USD',
        entity_type: 'other',
        workspace_mode: 'workspace',
        workspace_type: form.workspaceType,
        parent_entity: form.parentEntity || undefined,
        address: form.address.trim(),
        registration_number: form.registrationNumber.trim() || undefined,
        industry: form.industry.trim() || selectedType?.industryLabel || form.workspaceType,
        hierarchy_metadata: {
          workspace_type: form.workspaceType,
          workspace_type_label: selectedType?.label || form.workspaceType,
          selected_branch: form.selectedBranch,
          selected_branch_label: selectedBranch?.label || '',
          selected_sub_branch: form.selectedSubBranch,
          selected_sub_branch_label: form.selectedSubBranch || '',
          available_branches: availableBranches,
          departments_text: form.departments.trim(),
          teams_text: form.teams.trim(),
          staff_count: Number(form.staffCount) || 0,
          ownership_hierarchy: form.ownershipHierarchy.trim(),
        },
        dashboard_config: {
          dashboards: selectedType?.dashboards || [],
          landing: 'overview',
        },
        rbac_config: selectedType?.rbac || {},
        departments: form.departments.trim(),
        teams: form.teams.trim(),
        staff_count: Number(form.staffCount) || 0,
        ownership_hierarchy: form.ownershipHierarchy.trim(),
        department_selections: form.departmentSelections,
        enabled_modules: form.enabledModules,
        status: 'active',
      };
      const newWorkspace = await createWorkspace(payload);
      if (newWorkspace?.id) {
        navigate(`/app/workspace/${newWorkspace.id}/overview`);
      } else {
        navigate('/app/enterprise/org-overview');
      }
    } catch (err) {
      setError(err?.message || 'Failed to create workspace. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const renderStep1 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Workspace Name <span className="cw-required">*</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. North America Operations"
          value={form.name}
          onChange={(e) => update('name', e.target.value)}
          autoFocus
        />
        <span className="cw-hint">The name of this operational workspace.</span>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Workspace Type <span className="cw-required">*</span></label>
        <select
          className="cw-select"
          value={form.workspaceType}
          onChange={(e) => update('workspaceType', e.target.value)}
        >
          <option value="">Select workspace type</option>
          {WORKSPACE_TYPE_OPTIONS.map((t) => (
            <option key={t.value} value={t.value}>{t.label}</option>
          ))}
        </select>
        {selectedType && (
          <div className="cw-field cw-field-wide" style={{ paddingTop: 12 }}>
            <span className="cw-hint">{selectedType.description}</span>
            <span className="cw-hint">Dashboards: {selectedType.dashboards.join(', ')}</span>
            <span className="cw-hint">Branches: {availableBranches.map((branch) => branch.label).join(', ')}</span>
          </div>
        )}
      </div>
    </div>
  );

  const renderStep2 = () => (
    <div className="cw-step-fields">
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Business Address</label>
        <input
          className="cw-input"
          type="text"
          placeholder="Street address"
          value={form.address}
          onChange={(e) => update('address', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Country of Operation <span className="cw-required">*</span></label>
        <select className="cw-select" value={form.country} onChange={(e) => update('country', e.target.value)}>
          <option value="">Select country</option>
          {countryDropdownOptions.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
      </div>
      <div className="cw-field">
        <label className="cw-label">Registration Number <span className="cw-optional">(optional)</span></label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. 12345678"
          value={form.registrationNumber}
          onChange={(e) => update('registrationNumber', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Industry Classification</label>
        <input
          className="cw-input"
          type="text"
          placeholder="Auto-filled from workspace type, but editable"
          value={form.industry}
          onChange={(e) => update('industry', e.target.value)}
        />
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="cw-step-fields">
      <div className="cw-field">
        <label className="cw-label">Parent Workspace <span className="cw-optional">(optional)</span></label>
        <select className="cw-select" value={form.parentEntity} onChange={(e) => update('parentEntity', e.target.value)}>
          <option value="">Top-level workspace</option>
          {workspaceParents.map((workspace) => (
            <option key={workspace.id} value={workspace.id}>{workspace.name}</option>
          ))}
        </select>
      </div>
      <div className="cw-field">
        <label className="cw-label">Branch <span className="cw-required">*</span></label>
        <select className="cw-select" value={form.selectedBranch} onChange={(e) => update('selectedBranch', e.target.value)}>
          <option value="">Select branch</option>
          {availableBranches.map((branch) => (
            <option key={branch.key} value={branch.key}>{branch.label}</option>
          ))}
        </select>
      </div>
      <div className="cw-field">
        <label className="cw-label">Sub-branch</label>
        <select className="cw-select" value={form.selectedSubBranch} onChange={(e) => update('selectedSubBranch', e.target.value)} disabled={!selectedBranch}>
          <option value="">Select sub-branch</option>
          {(selectedBranch?.children || []).map((child) => (
            <option key={child} value={child}>{child}</option>
          ))}
        </select>
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Departments</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Finance, Engineering, Sales"
          value={form.departments}
          onChange={(e) => update('departments', e.target.value)}
        />
        <span className="cw-hint">Comma-separated list of departments in this workspace.</span>
      </div>
      <div className="cw-field">
        <label className="cw-label">Teams</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. Core Team, Advisory, Growth"
          value={form.teams}
          onChange={(e) => update('teams', e.target.value)}
        />
      </div>
      <div className="cw-field">
        <label className="cw-label">Number of Staff</label>
        <input
          className="cw-input"
          type="number"
          min="1"
          placeholder="e.g. 12"
          value={form.staffCount}
          onChange={(e) => update('staffCount', e.target.value)}
        />
      </div>
      <div className="cw-field cw-field-wide">
        <label className="cw-label">Ownership Hierarchy</label>
        <input
          className="cw-input"
          type="text"
          placeholder="e.g. CEO → CFO → Manager"
          value={form.ownershipHierarchy}
          onChange={(e) => update('ownershipHierarchy', e.target.value)}
        />
        <span className="cw-hint">Briefly describe the reporting or ownership structure.</span>
      </div>
      <div className="cw-field cw-field-wide">
        <EnterpriseDepartmentSelector
          value={form.departmentSelections}
          onChange={(departmentSelections) => update('departmentSelections', departmentSelections)}
        />
      </div>
      {selectedType && (
        <div className="cw-field cw-field-wide">
          <span className="cw-hint">Template hierarchy: {availableBranches.map((branch) => `${branch.label} (${branch.children.join(', ')})`).join(' • ')}</span>
        </div>
      )}
    </div>
  );

  const renderStep4 = () => (
    <div className="cw-step-fields">
      <p className="cw-section-desc">Select the modules to activate in this workspace. You can add more later.</p>
      <div className="cw-module-grid">
        {moduleCards.map((mod) => {
          const active = form.enabledModules.includes(mod.key);
          return (
            <button
              key={mod.key}
              type="button"
              className={`cw-module-card${active ? ' cw-module-card--active' : ''}`}
              onClick={() => toggleModule(mod.key)}
            >
              <span className="cw-module-name">{mod.label}</span>
              <span className="cw-module-desc">{mod.desc}</span>
              {active && <span className="cw-module-check">✓</span>}
            </button>
          );
        })}
      </div>
      {form.enabledModules.length === 0 && (
        <p className="cw-hint cw-hint--warn">Select at least one module to continue.</p>
      )}
      {selectedType && (
        <p className="cw-hint">RBAC template: {Object.keys(selectedType.rbac).join(', ')}</p>
      )}
    </div>
  );

  const stepContent = [null, renderStep1, renderStep2, renderStep3, renderStep4];

  return (
    <div className="cw-page cw-workspace-creation">
      {/* Top Nav */}
      <nav className="cw-topnav">
        <div className="cw-topnav-brand">
          <AtonixCorpLogo variant="white" size={28} withText={false} />
          <span className="cw-topnav-title">Create Workspace</span>
        </div>
        <button className="cw-topnav-cancel" onClick={() => navigate('/app/enterprise/org-overview')}>
          Cancel
        </button>
      </nav>

      {/* Step progress */}
      <div className="cw-progress-bar cw-workspace-progress">
        {STEPS.map((s) => (
          <div key={s.number} className={`cw-progress-step${step >= s.number ? ' cw-progress-step--done' : ''}${step === s.number ? ' cw-progress-step--active' : ''}`}>
            <span className="cw-progress-num">{step > s.number ? '✓' : s.number}</span>
            <span className="cw-progress-label">{s.label}</span>
          </div>
        ))}
      </div>

      {/* Form body */}
      <main className="cw-main cw-workspace-main">
        <form className="cw-card cw-workspace-card" onSubmit={handleSubmit}>
          <div className="cw-step-header cw-workspace-step-header">
            <span className="cw-step-eyebrow">Step {step} of {TOTAL_STEPS}</span>
            <h2 className="cw-step-title">{STEPS[step - 1].label}</h2>
          </div>

          {stepContent[step]()}

          {error && <p className="cw-error">{error}</p>}

          <div className="cw-actions cw-workspace-actions">
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
                {submitting ? 'Creating Workspace…' : 'Create Workspace'}
              </button>
            )}
          </div>
        </form>
      </main>
    </div>
  );
}
