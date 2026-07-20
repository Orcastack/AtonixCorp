import React, { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { FiDownload, FiMonitor } from 'react-icons/fi';
import { FaApple } from 'react-icons/fa';
import { SiGoogleplay } from 'react-icons/si';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import { useAuth } from '../../context/AuthContext';
import './Landing.css';

const systemSteps = [
  {
    step: '01',
    title: 'Define the governance model',
    text: 'Map organizational hierarchy, roles, permissions, and policy boundaries into one controlled environment.',
  },
  {
    step: '02',
    title: 'Automate policy execution',
    text: 'Move approvals, compliance checks, workflows, and exception handling through clear, reviewable stages.',
  },
  {
    step: '03',
    title: 'Stay inspection-ready',
    text: 'Surface decisions, audit trails, subscription access, and supporting evidence in a form that withstands scrutiny.',
  },
];

const operatingPrinciples = [
  'One environment for governance, finance, equity, and workflows — without losing enterprise visibility.',
  'Controllers, administrators, compliance leads, and finance teams share one source of operational truth.',
  'Execution stays structured enough for audits, board reviews, policy enforcement, and regulated reporting cycles.',
  'Subscription tiers control access to the right modules, dashboards, and integrations for each organization.',
];

const operationalPillars = [
  {
    title: 'Governance engine',
    text: 'Maintain organizational hierarchy, role-based access, policy rules, and board-ready evidence in one controlled environment.',
  },
  {
    title: 'Finance and equity',
    text: 'Keep ledger activity, allocations, ownership, reconciliations, and reporting aligned across entities and divisions.',
  },
  {
    title: 'Policy and workflow enforcement',
    text: 'Track obligations, filing calendars, subscription entitlements, approvals, and review checkpoints without losing traceability.',
  },
];

const dashboardTabs = {
  Governance: {
    eyebrow: 'Organization controls',
    title: 'Governance workspace',
    metrics: [
      { label: 'Active entities', value: '24', trend: 'Across 6 jurisdictions' },
      { label: 'Approvals due', value: '8', trend: '3 due this week' },
      { label: 'Control coverage', value: '96%', trend: 'Policies reviewed' },
    ],
    activity: [
      ['Board resolution', 'Ready for review', 'Today'],
      ['Director appointment', 'Awaiting signature', 'Tomorrow'],
      ['Delegated authority', 'Published', '14 Jun'],
    ],
  },
  Finance: {
    eyebrow: 'Financial control',
    title: 'Finance command center',
    metrics: [
      { label: 'Cash position', value: '$4.8m', trend: 'Consolidated entities' },
      { label: 'Close tasks', value: '12', trend: '7 completed this month' },
      { label: 'Reconciled', value: '98%', trend: 'Bank and ledger accounts' },
    ],
    activity: [
      ['Cash forecast', 'Updated', 'Today'],
      ['Intercompany review', 'Needs approval', 'Tomorrow'],
      ['Period close', 'On track', '28 Jun'],
    ],
  },
  Equity: {
    eyebrow: 'Ownership records',
    title: 'Equity administration',
    metrics: [
      { label: 'Issued shares', value: '4.2m', trend: 'Across 3 classes' },
      { label: 'Pending grants', value: '16', trend: 'Approvals in motion' },
      { label: 'Cap table status', value: 'Current', trend: 'Last updated today' },
    ],
    activity: [
      ['Option grant batch', 'Ready for approval', 'Today'],
      ['Transfer register', 'Verified', 'Yesterday'],
      ['Valuation record', 'Filed', '12 Jun'],
    ],
  },
  Policy: {
    eyebrow: 'Policy execution',
    title: 'Policy and compliance',
    metrics: [
      { label: 'Open obligations', value: '18', trend: 'Across the organization' },
      { label: 'On-time filings', value: '100%', trend: 'Current reporting cycle' },
      { label: 'Evidence complete', value: '94%', trend: 'Audit-ready records' },
    ],
    activity: [
      ['Tax filing calendar', 'On track', 'Today'],
      ['Policy attestation', '7 responses due', 'Friday'],
      ['Evidence request', 'Assigned', '18 Jun'],
    ],
  },
  Analytics: {
    eyebrow: 'Executive intelligence',
    title: 'Analytics overview',
    metrics: [
      { label: 'Decision readiness', value: '92%', trend: 'Management reporting' },
      { label: 'Risk signals', value: '3', trend: 'Require attention' },
      { label: 'Reports delivered', value: '41', trend: 'This reporting period' },
    ],
    activity: [
      ['Board pack', 'Prepared', 'Today'],
      ['Risk review', 'Scheduled', 'Thursday'],
      ['Entity report', 'Delivered', '10 Jun'],
    ],
  },
};

const subscriptionTiers = ['Basic', 'Professional', 'Enterprise', 'Institutional'];

const downloads = [
  { label: 'Mac', detail: 'Desktop client', icon: FiMonitor },
  { label: 'Windows', detail: 'Desktop client', icon: FiDownload },
  { label: 'Google Play', detail: 'Android app', icon: SiGoogleplay },
  { label: 'App Store', detail: 'iOS app', icon: FaApple },
];

const Landing = () => {
  const { isAuthenticated, loading } = useAuth();
  const [activeDashboard, setActiveDashboard] = useState('Governance');
  const dashboard = dashboardTabs[activeDashboard];

  if (loading) {
    return (
      <div className="landing-page landing-page--loading">
        Loading...
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/app/console" replace />;
  }

  return (
    <div className="landing-page">
      <Header />

      <main className="landing-main">
        <section className="landing-hero" aria-label="AtonixCorp overview">
          <div className="landing-shell landing-hero__layout">
            <div className="landing-hero__copy">
              <p className="landing-kicker">Governance-as-a-Service for modern institutions</p>
              <h1>The operating system for accountable institutions.</h1>
              <p className="landing-lead">
                AtonixCorp connects governance, finance, equity, policy execution, and analytics in one
                controlled workspace built for boards, executives, and operating teams.
              </p>

              <div className="landing-actions">
                <Link to="/register" className="landing-button landing-button--primary">Open Account</Link>
                <Link to="/features" className="landing-button landing-button--secondary">Review Modules</Link>
              </div>

              <div className="landing-downloads" aria-label="AtonixCorp downloads">
                {downloads.map(({ label, detail, icon: DownloadIcon }) => (
                  <a className="landing-download" href="#downloads" key={label}>
                    <DownloadIcon aria-hidden="true" />
                    <span><strong>{label}</strong><small>{detail}</small></span>
                  </a>
                ))}
              </div>
              <p className="landing-hero__microcopy">
                Available across desktop and mobile for secure work wherever decisions are made.
              </p>
            </div>

            <aside className="landing-dashboard-preview" aria-label="AtonixCorp dashboard preview">
              <div className="landing-dashboard-preview__bar">
                <div>
                  <p>{dashboard.eyebrow}</p>
                  <strong>{dashboard.title}</strong>
                </div>
                <span className="landing-dashboard-preview__status">Live preview</span>
              </div>
              <div className="landing-dashboard-tabs" role="tablist" aria-label="Platform dashboards">
                {Object.keys(dashboardTabs).map((tab) => (
                  <button
                    key={tab}
                    type="button"
                    role="tab"
                    aria-selected={activeDashboard === tab}
                    className={activeDashboard === tab ? 'is-active' : ''}
                    onClick={() => setActiveDashboard(tab)}
                  >
                    {tab}
                  </button>
                ))}
              </div>
              <div className="landing-dashboard-metrics">
                {dashboard.metrics.map((metric) => (
                  <div className="landing-dashboard-metric" key={metric.label}>
                    <span>{metric.label}</span>
                    <strong>{metric.value}</strong>
                    <small>{metric.trend}</small>
                  </div>
                ))}
              </div>
              <div className="landing-dashboard-activity">
                <div className="landing-dashboard-activity__heading"><span>Priority work</span><span>Due</span></div>
                {dashboard.activity.map(([item, status, due]) => (
                  <div className="landing-dashboard-activity__row" key={item}>
                    <div><strong>{item}</strong><small>{status}</small></div>
                    <span>{due}</span>
                  </div>
                ))}
              </div>
              <div className="landing-dashboard-tiers">
                <span>Subscription access</span>
                <div>
                  {subscriptionTiers.map((tier) => <span key={tier}>{tier}</span>)}
                </div>
                <Link to="/pricing">Compare plans</Link>
              </div>
            </aside>
          </div>
        </section>

        <section className="landing-section landing-section--system">
          <div className="landing-shell">
            <div className="landing-section__intro">
              <p className="landing-kicker">What the platform does</p>
              <h2>It turns governance into a digital operating framework.</h2>
              <p>
                Organizations subscribe to AtonixCorp to manage policy, finance, equity, approvals, and records from one dashboard.
                Each tier unlocks the right modules and integrations for the organization’s size and complexity.
              </p>
            </div>
            <div className="landing-system-grid">
              {systemSteps.map((lane) => (
                <article key={lane.step} className="landing-system-card">
                  <span className="landing-system-card__step">{lane.step}</span>
                  <h3>{lane.title}</h3>
                  <p>{lane.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="landing-section">
          <div className="landing-shell landing-philosophy">
            <ul className="landing-principles">
              {operatingPrinciples.map((principle) => (
                <li key={principle}>{principle}</li>
              ))}
            </ul>
          </div>
        </section>

        <section className="landing-section landing-section--pillars">
          <div className="landing-shell">
            <div className="landing-pillars-grid">
              {operationalPillars.map((pillar) => (
                <article key={pillar.title} className="landing-pillar-card">
                  <h3>{pillar.title}</h3>
                  <p>{pillar.text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default Landing;
