import React, { useState } from 'react';
import { PageHeader, Card, Button, Input } from '../../components/ui';
import StandaloneModuleShell from '../../components/StandaloneModuleShell';
import './HelpCenter.css';

const FAQ_CATEGORIES = ['Getting Started', 'Accounting', 'Billing', 'Integrations', 'Security', 'Reporting'];

const FAQ_ITEMS = [
  {
    category: 'Getting Started',
    q: 'How do I create my first entity?',
    a: 'Navigate to Settings → Entity Management and click "Add Entity". Fill in the legal name, entity type, country, and functional currency. Your entity will be active immediately.',
  },
  {
    category: 'Getting Started',
    q: 'How do I invite team members?',
    a: 'Go to Settings → Team & Permissions, click "Invite User", enter their email and assign a role. They will receive an invitation email with login instructions.',
  },
  {
    category: 'Accounting',
    q: 'How do I set up the Chart of Accounts?',
    a: 'Go to Accounting → Chart of Accounts. You can start from our pre-built GAAP/IFRS template or create accounts manually. Each account requires a code, name, type (Asset/Liability/Equity/Revenue/Expense), and a currency.',
  },
  {
    category: 'Accounting',
    q: 'What is the difference between a Journal Entry and a General Ledger?',
    a: 'Journal Entries are the raw double-entry transactions you post. The General Ledger is the compiled view of all posted entries organized by account, showing running balances.',
  },
  {
    category: 'Accounting',
    q: 'How does bank reconciliation work?',
    a: 'In Accounting → Reconciliation, connect your bank feed or import a CSV statement. The system matches transactions against your ledger entries and highlights discrepancies for you to review.',
  },
  {
    category: 'Billing',
    q: 'How do I create and send an invoice?',
    a: 'Navigate to Billing & Payments → Invoices, click "New Invoice". Add line items, set payment terms, and click "Send". Clients receive a secure payment link via email.',
  },
  {
    category: 'Billing',
    q: 'What payment methods are supported?',
    a: 'ACH bank transfer, wire transfer, credit/debit card (via Stripe), and manual recording. Payment method availability depends on your jurisdiction and plan.',
  },
  {
    category: 'Integrations',
    q: 'How do I connect my bank account?',
    a: 'Go to Integrations → Connected Apps and select your bank. We use Plaid for US/CA banks and Open Banking APIs for European institutions. The connection is read-only.',
  },
  {
    category: 'Integrations',
    q: 'Is there a REST API available?',
    a: 'Yes. Go to Integrations → API Keys to generate your API key. Full API documentation is available at ledgora.com/api-docs. All endpoints use Bearer token authentication.',
  },
  {
    category: 'Security',
    q: 'How is my data protected?',
    a: 'All data is encrypted at rest (AES-256) and in transit (TLS 1.3). We are SOC 2 Type II certified and comply with GDPR, CCPA, and regional data residency requirements.',
  },
  {
    category: 'Security',
    q: 'Can I enable two-factor authentication?',
    a: 'Yes. Go to Settings → Security → Two-Factor Authentication. We support TOTP authenticator apps (Google Authenticator, Authy) and SMS codes.',
  },
  {
    category: 'Reporting',
    q: 'How do I generate a financial statement?',
    a: 'Navigate to Financial Reporting → Financial Statements. Choose your statement type (Income Statement, Balance Sheet, or Cash Flow), set the date range and entity, then click "Generate" or "Export CSV".',
  },
];

export default function HelpCenter() {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const [expanded, setExpanded] = useState(null);

  const filtered = FAQ_ITEMS.filter(item => {
    const matchSearch = !search || item.q.toLowerCase().includes(search.toLowerCase()) || item.a.toLowerCase().includes(search.toLowerCase());
    const matchCat = activeCategory === 'All' || item.category === activeCategory;
    return matchSearch && matchCat;
  });

  return (
    <StandaloneModuleShell title="Help Center" eyebrow="Support Surface" backLabel="Return to Console">
      <div className="module-page">
        <PageHeader
          title="Help Center"
          subtitle="Find answers, guides, and documentation"
          actions={<Button variant="primary">Contact Support</Button>}
        />

      {/* Search */}
      <Card>
        <div className="help-center-search-row">
          <Input
            placeholder="Search help articles…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="help-center-search"
          />
          {search && (
            <Button variant="secondary" onClick={() => setSearch('')}>Clear</Button>
          )}
        </div>
        <div className="help-center-categories">
          {['All', ...FAQ_CATEGORIES].map(cat => (
            <button
              key={cat}
              onClick={() => setActiveCategory(cat)}
              className={`help-center-chip ${activeCategory === cat ? 'active' : ''}`}
            >
              {cat}
            </button>
          ))}
        </div>
      </Card>

      {/* Quick Links */}
      {!search && activeCategory === 'All' && (
        <div className="help-center-links-grid">
          {[
            { title: 'Quick Start Guide', desc: 'Set up your first entity and chart of accounts in under 10 minutes.' },
            { title: 'API Documentation', desc: 'Full REST API reference with code examples in Python, JS, and cURL.' },
            { title: 'Security Whitepaper', desc: 'Learn about our encryption, SOC 2 compliance, and data residency.' },
            { title: 'Reporting Guide', desc: 'Step-by-step guide to financial statements, trial balance, and exports.' },
            { title: 'Bank Integrations', desc: 'Supported banks, connection methods, and troubleshooting.' },
            { title: 'Video Tutorials', desc: 'Watch walkthroughs of every major feature in the platform.' },
          ].map(link => (
            <Card key={link.title} className="help-center-link-card">
              <div className="help-center-link-title">{link.title}</div>
              <div className="help-center-link-desc">{link.desc}</div>
            </Card>
          ))}
        </div>
      )}

      {/* FAQs */}
        <Card header={`Frequently Asked Questions ${filtered.length < FAQ_ITEMS.length ? `— ${filtered.length} results` : ''}`}>
        {filtered.length === 0 ? (
          <p className="help-center-empty">
            No articles found for "{search}". <Button variant="secondary" size="small" onClick={() => { setSearch(''); setActiveCategory('All'); }}>Clear filters</Button>
          </p>
        ) : (
          <div className="help-center-faq-list">
            {filtered.map((item, i) => (
              <div
                key={i}
                className="help-center-faq-item"
              >
                <button
                  onClick={() => setExpanded(expanded === i ? null : i)}
                  className="help-center-faq-question"
                >
                  <div className="help-center-faq-question-copy">
                    <span className="help-center-faq-category">{item.category}</span>
                    <span className="help-center-faq-title">{item.q}</span>
                  </div>
                  <span className="help-center-faq-toggle">
                    {expanded === i ? '−' : '+'}
                  </span>
                </button>
                {expanded === i && (
                  <div className="help-center-faq-answer">
                    {item.a}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
        </Card>
      </div>
    </StandaloneModuleShell>
  );
}
