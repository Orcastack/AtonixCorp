import React from 'react';
import { Link } from 'react-router-dom';

import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import './Deployment.css';

const releaseStages = [
  {
    name: 'Validate',
    detail: 'GitHub Actions runs API tests, app build validation, and release checks before publication.'
  },
  {
    name: 'Package',
    detail: 'Production Docker images are built from the app and API production Dockerfiles and tagged with the commit SHA.'
  },
  {
    name: 'Promote',
    detail: 'Kubernetes overlays move the same release through dev, staging, and production with environment-specific values only.'
  },
  {
    name: 'Verify',
    detail: 'Rollout status, /api/health/, and deployment event logging confirm release integrity after each promotion.'
  }
];

const stackRows = [
  ['App', 'React 18 build served by NGINX'],
  ['API', 'Django + Django REST Framework on Gunicorn'],
  ['Local stack', 'Docker Compose for app, API, database, and banking sync'],
  ['Runtime orchestration', 'Kubernetes base manifests with dev, staging, and prod overlays'],
  ['Infrastructure', 'Terraform environment stacks and shared modules'],
  ['Delivery model', 'GitHub Actions validation with a GitHub Pages app publish surface'],
];

const envCards = [
  {
    env: 'Development',
    path: 'deploy/k8s/overlays/dev',
    summary: 'Integration environment for merged changes, smoke verification, and fast operational feedback.'
  },
  {
    env: 'Staging',
    path: 'deploy/k8s/overlays/staging',
    summary: 'Pre-production environment for approval-driven release promotion and realistic platform checks.'
  },
  {
    env: 'Production',
    path: 'deploy/k8s/overlays/prod',
    summary: 'Controlled release target for immutable images, health validation, and platform event observability.'
  }
];

const secretKeys = ['django-secret-key', 'database-url', 'platform-event-token'];

const Deployment = () => {
  return (
    <div className="deployment-page">
      <Header />

      <section className="deployment-hero">
        <div className="deployment-shell deployment-hero__grid">
          <div className="deployment-hero__copy">
            <p className="deployment-eyebrow">Deployment Architecture</p>
            <h1>Ledgora deployment is now visible through the app.</h1>
            <p className="deployment-hero__lede">
              This page translates the repository deployment model into a user-facing product surface. It explains
              how the React app, Django API, Docker images, Kubernetes overlays, and Terraform stacks work
              together when Ledgora is published from GitHub.
            </p>
            <div className="deployment-hero__actions">
              <Link to="/features" className="deployment-btn deployment-btn--primary">
                Explore Platform Features
              </Link>
              <Link to="/v1/docs" className="deployment-btn deployment-btn--secondary">
                Open API Portal
              </Link>
            </div>
          </div>

          <div className="deployment-hero__panel">
            <div className="deployment-status-card">
              <div className="deployment-status-card__header">
                <span>Release Surface</span>
                <span className="deployment-status-card__live">App Published</span>
              </div>
              <div className="deployment-status-card__metric">3 Environments</div>
              <p className="deployment-status-card__subtext">One codebase, immutable image tags, and overlay-based promotion.</p>
              <div className="deployment-status-card__list">
                <div>
                  <span>Public surface</span>
                  <strong>React app</strong>
                </div>
                <div>
                  <span>API runtime</span>
                  <strong>Django API</strong>
                </div>
                <div>
                  <span>Health endpoint</span>
                  <strong>/api/health/</strong>
                </div>
                <div>
                  <span>Release identity</span>
                  <strong>Commit SHA</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="deployment-strip">
        <div className="deployment-shell deployment-strip__grid">
          {releaseStages.map((stage) => (
            <article key={stage.name} className="deployment-strip__card">
              <p className="deployment-strip__label">{stage.name}</p>
              <p className="deployment-strip__text">{stage.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="deployment-section deployment-section--light">
        <div className="deployment-shell">
          <div className="deployment-section__header">
            <p className="deployment-eyebrow">App Surface</p>
            <h2>The deployment story lives in the product, not only in Markdown.</h2>
            <p>
              Users visiting the public site can now understand how Ledgora is delivered, what environments exist,
              and what release contracts protect platform stability without leaving the app experience.
            </p>
          </div>

          <div className="deployment-surface-grid">
            <article className="deployment-surface-card deployment-surface-card--primary">
              <h3>Public deployment page</h3>
              <p>
                The GitHub Pages site can present deployment architecture directly through the React app rather
                than forcing users to read repository files first.
              </p>
            </article>
            <article className="deployment-surface-card">
              <h3>Consistent UI system</h3>
              <p>
                Deployment content uses the same Ledgora app design language, navigation, and footer structure
                as the rest of the public product site.
              </p>
            </article>
            <article className="deployment-surface-card">
              <h3>Operational transparency</h3>
              <p>
                The visible page maps directly to the repo runtime model: Docker, Kubernetes overlays, health checks,
                and infrastructure contracts.
              </p>
            </article>
          </div>
        </div>
      </section>

      <section className="deployment-section">
        <div className="deployment-shell deployment-stack-layout">
          <div>
            <div className="deployment-section__header deployment-section__header--compact">
              <p className="deployment-eyebrow">Platform Stack</p>
              <h2>How the deployment model maps to the codebase.</h2>
            </div>
            <div className="deployment-stack-table">
              {stackRows.map(([label, value]) => (
                <div key={label} className="deployment-stack-table__row">
                  <span>{label}</span>
                  <strong>{value}</strong>
                </div>
              ))}
            </div>
          </div>

          <aside className="deployment-callout">
            <p className="deployment-callout__eyebrow">Release Position</p>
            <h3>App publishing is ready for GitHub Pages visibility.</h3>
            <p>
              The app is now wired to support the repository base path used by GitHub Pages, making
              ledgora.github.io/ledgora/ the correct public surface for this repository deployment.
            </p>
          </aside>
        </div>
      </section>

      <section className="deployment-section deployment-section--light">
        <div className="deployment-shell">
          <div className="deployment-section__header">
            <p className="deployment-eyebrow">Environment Promotion</p>
            <h2>Promotion stays consistent from development to production.</h2>
          </div>

          <div className="deployment-env-grid">
            {envCards.map((card) => (
              <article key={card.env} className="deployment-env-card">
                <p className="deployment-env-card__label">{card.env}</p>
                <h3>{card.path}</h3>
                <p>{card.summary}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="deployment-section">
        <div className="deployment-shell deployment-contracts-layout">
          <div>
            <div className="deployment-section__header deployment-section__header--compact">
              <p className="deployment-eyebrow">Runtime Contracts</p>
              <h2>Production stability depends on explicit contracts.</h2>
              <p>
                These runtime expectations define whether a deployment is complete and trustworthy across environments.
              </p>
            </div>

            <div className="deployment-contract-box">
              <h3>Kubernetes secret contract</h3>
              <p>The cluster expects <strong>ledgora-app-secrets</strong> with the following minimum keys:</p>
              <div className="deployment-chip-row">
                {secretKeys.map((key) => (
                  <span key={key} className="deployment-chip">{key}</span>
                ))}
              </div>
            </div>
          </div>

          <div className="deployment-health-card">
            <p className="deployment-health-card__eyebrow">Health Contract</p>
            <div className="deployment-health-card__path">GET /api/health/</div>
            <p>
              A release should not be treated as complete until the API, app, and health contract all succeed.
            </p>
            <ul>
              <li>API rollout succeeds</li>
              <li>App rollout succeeds</li>
              <li>Health endpoint responds successfully</li>
              <li>Deployment event logging remains intact</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="deployment-section deployment-section--accent">
        <div className="deployment-shell deployment-cta">
          <div>
            <p className="deployment-eyebrow deployment-eyebrow--inverse">GitHub Pages Target</p>
            <h2>This app page is designed to be visible at ledgora.github.io/ledgora/.</h2>
            <p>
              It gives users a clean public view of how Ledgora is shipped, promoted, and verified without exposing
              them directly to internal deployment files first.
            </p>
          </div>
          <div className="deployment-cta__actions">
            <Link to="/" className="deployment-btn deployment-btn--ghost">Back To Home</Link>
            <Link to="/product" className="deployment-btn deployment-btn--light">View Platform</Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Deployment;