import React, { useMemo, useState } from 'react';
import FooterColumn from './FooterColumn';

export const footerLinks = {
  company: {
    title: 'Company',
    links: [
      { label: 'About AtonixCorp', to: '/about' },
      { label: 'Leadership', to: '/about#leadership' },
      { label: 'Careers', to: '/about#careers' },
      { label: 'Press & Media', to: '/contact#media' },
      { label: 'Corporate Governance', to: '/about#governance' },
    ],
  },
  platform: {
    title: 'Platform',
    links: [
      { label: 'Accounting Management Suite', to: '/product' },
      { label: 'Client Account Management', to: '/app/clients/directory' },
      { label: 'Document Vault', to: '/app/documents/vault' },
      { label: 'Workflow Automation', to: '/app/automation/rules' },
      { label: 'Financial Reporting', to: '/app/reporting/analytics' },
      { label: 'Audit Trail System', to: '/app/compliance/audit-trail' },
      { label: 'Multi-Firm Dashboard', to: '/app/firm/dashboard' },
      { label: 'Firm Dashboard', to: '/app/firm/dashboard' },
      { label: 'Client Accounts', to: '/app/billing/customers' },
      { label: 'Client Documents', to: '/app/documents/vault' },
      { label: 'Client Activity Logs', to: '/app/compliance/audit-trail' },
      { label: 'Client Reporting', to: '/app/reporting/statements' },
    ],
  },
  resources: {
    title: 'Resources',
    links: [
      { label: 'Resources', to: '/help-center' },
      { label: 'Deployment', to: '/deployment' },
      { label: 'Security Center', to: '/app/console/settings' },
      { label: 'Documentation', to: '/help-center' },
      { label: 'API Reference', to: '/v1/docs' },
      { label: 'Developer Guides', to: '/v1/docs' },
      { label: 'Integration Guides', to: '/app/integrations/list' },
      { label: 'System Status', to: '/support#system-status' },
      { label: 'Release Notes', to: '/deployment#release-notes' },
      { label: 'Support Center', to: '/support' },
      { label: 'API Docs', to: '/v1/docs' },
    ],
  },
  compliance: {
    title: 'Compliance & Legal',
    links: [
      { label: 'Privacy Policy', to: '/privacy' },
      { label: 'Terms of Service', to: '/privacy#terms-of-service' },
      { label: 'Data Protection Standards', to: '/privacy#data-protection' },
      { label: 'Audit & Reporting', to: '/app/compliance/audit-trail' },
      { label: 'Record Retention Policy', to: '/privacy#record-retention' },
      { label: 'SOC 2 & ISO Compliance', to: '/privacy#compliance' },
      { label: 'Audit Logs', to: '/app/compliance/audit-trail' },
      { label: 'Data Retention', to: '/privacy#data-retention' },
      { label: 'Access Control', to: '/app/console/settings' },
      { label: 'Security Overview', to: '/app/console/settings' },
    ],
  },
  operations: {
    title: 'Accounting Operations',
    links: [
      { label: 'Client Onboarding', to: '/app/clients/directory' },
      { label: 'Financial Data Import', to: '/app/subledgers/inventory' },
      { label: 'Data Import', to: '/app/subledgers/inventory' },
      { label: 'Data Mapping', to: '/app/accounting/chart-of-accounts' },
      { label: 'Reconciliation Tools', to: '/app/accounting/reconciliation' },
      { label: 'Ledger Views', to: '/app/accounting/general-ledger' },
      { label: 'Reporting Templates', to: '/app/reporting/analytics' },
      { label: 'Year-End Close', to: '/app/compliance/period-close' },
      { label: 'Document Management', to: '/app/documents/vault' },
      { label: 'Workflow Templates', to: '/app/automation/rules' },
      { label: 'Task Automation', to: '/app/overview/tasks' },
    ],
  },
  contact: {
    title: 'Contact',
    links: [
      { label: 'Contact Us', to: '/contact' },
      { label: 'Sales', to: '/contact#sales' },
      { label: 'Partnerships', to: '/contact#partnerships' },
      { label: 'Enterprise Support', to: '/support' },
    ],
  },
};

const mobileDefaults = {
  company: true,
  platform: false,
  resources: false,
  compliance: false,
  operations: false,
  contact: false,
};

function FooterPrimary() {
  const [openColumns, setOpenColumns] = useState(mobileDefaults);
  const columns = useMemo(() => Object.entries(footerLinks), []);

  const handleToggle = (key) => {
    setOpenColumns((current) => ({
      ...current,
      [key]: !current[key],
    }));
  };

  return (
    <div className="footer-primary">
      <div className="footer-shell">
        <div className="footer-primary__grid">
          {columns.map(([key, value]) => (
            <FooterColumn
              key={key}
              columnKey={key}
              title={value.title}
              links={value.links}
              isOpen={openColumns[key]}
              onToggle={() => handleToggle(key)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default FooterPrimary;