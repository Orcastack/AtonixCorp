import React from 'react';

export const ENTERPRISE_DEPARTMENTS = [
  { key: 'finance', label: 'Finance', detail: 'Accounting, treasury, and reporting.' },
  { key: 'operations', label: 'Operations', detail: 'Service delivery and process ownership.' },
  { key: 'legal_compliance', label: 'Legal and Compliance', detail: 'Policy, legal, and regulatory controls.' },
  { key: 'human_resources', label: 'Human Resources', detail: 'People operations and workforce controls.' },
  { key: 'technology', label: 'Technology', detail: 'Systems, data, and security operations.' },
  { key: 'sales', label: 'Sales', detail: 'Commercial pipeline and revenue operations.' },
  { key: 'marketing', label: 'Marketing', detail: 'Brand and market operations.' },
  { key: 'risk_audit', label: 'Risk and Audit', detail: 'Risk management and assurance.' },
  { key: 'equity_governance', label: 'Equity and Governance', detail: 'Shareholder records and governance.' },
];

export default function EnterpriseDepartmentSelector({ value = [], onChange, equityOnly = false }) {
  const departments = equityOnly
    ? ENTERPRISE_DEPARTMENTS.filter((department) => ['finance', 'legal_compliance', 'risk_audit', 'equity_governance'].includes(department.key))
    : ENTERPRISE_DEPARTMENTS;
  const selected = new Set(value);

  const toggle = (key) => {
    const next = new Set(selected);
    next.has(key) ? next.delete(key) : next.add(key);
    onChange([...next]);
  };

  return (
    <section className="enterprise-department-selector" aria-label="Governed department selection">
      <div className="enterprise-department-selector-head">
        <div>
          <h3>Governed Departments</h3>
          <p>Select the enterprise departments to provision with this record.</p>
        </div>
        <span>{selected.size} selected</span>
      </div>
      <div className="enterprise-department-options">
        {departments.map((department) => {
          const isSelected = selected.has(department.key);
          return (
            <button
              key={department.key}
              type="button"
              className={`enterprise-department-option${isSelected ? ' is-selected' : ''}`}
              onClick={() => toggle(department.key)}
              aria-pressed={isSelected}
            >
              <span className="enterprise-department-option-mark" aria-hidden="true">{isSelected ? '✓' : ''}</span>
              <span>
                <strong>{department.label}</strong>
                <small>{department.detail}</small>
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
