import React from 'react';
import Header from '../../components/Header/Header';
import Footer from '../../components/Footer/Footer';
import './CLIDocs.css';

const authCommands = [
  'ledgora login --api-key <API_KEY> --org org_123 --profile prod',
  'ledgora whoami',
  'ledgora profiles',
  'ledgora use prod',
  'ledgora logout',
];

const businessCommands = [
  'ledgora organizations list',
  'ledgora accounts list',
  'ledgora customers list',
  'ledgora vendors list',
  'ledgora reports trial-balance --as-of-date 2026-03-31',
  'ledgora reports profit-and-loss --from-date 2026-03-01 --to-date 2026-03-31',
  'ledgora reports balance-sheet --as-of-date 2026-03-31',
  'ledgora reports cash-flow --from-date 2026-03-01 --to-date 2026-03-31',
];

const storageItems = [
  'Profile metadata is stored in config.json with 0600 permissions.',
  'Secrets are encrypted with Fernet before they are persisted locally.',
  'The encryption key is stored in the OS keyring when available.',
  'If no keyring backend exists, the CLI falls back to a local key file with 0600 permissions.',
  'The CLI never stores plaintext API keys or access tokens in the config file.',
];

const endpointRows = [
  { method: 'POST', path: '/auth/cli-login', description: 'Exchange a composite API key for a short-lived bearer token.' },
  { method: 'POST', path: '/auth/refresh', description: 'Refresh the current CLI session using the stored API key.' },
  { method: 'GET', path: '/auth/me', description: 'Validate the active CLI session and return user and organization identity.' },
  { method: 'POST', path: '/v1/api-keys', description: 'Create a long-lived integration key that can be used by the CLI.' },
];

const CLIDocs = () => {
  return (
    <div className="cli-docs-page">
      <Header />

      <section className="cli-docs-hero">
        <div className="container">
          <span className="cli-docs-kicker">Ledgora CLI</span>
          <h1>CLI Authentication and Usage Guide</h1>
          <p>
            This page documents the Ledgora CLI login flow, secure local session storage,
            automatic token refresh, and the currently available authenticated business commands.
          </p>
          <div className="cli-docs-hero-links">
            <a href="http://localhost:8000/v1/docs" target="_blank" rel="noreferrer">Backend Redoc</a>
            <a href="http://localhost:8000/v1/swagger" target="_blank" rel="noreferrer">Swagger UI</a>
            <a href="http://localhost:8000/v1/openapi.yaml" target="_blank" rel="noreferrer">OpenAPI YAML</a>
          </div>
        </div>
      </section>

      <section className="cli-docs-section">
        <div className="container cli-docs-grid">
          <article className="cli-docs-card cli-docs-card-wide">
            <h2>Install</h2>
            <p>Bootstrap the backend environment and install the CLI into the backend virtual environment.</p>
            <pre>{`./setup.sh`}</pre>
            <p>Or install the package directly in editable mode:</p>
            <pre>{`cd tools/ledgora_cli\n/home/atonixdev/ledgora/api/.venv/bin/python -m pip install -e .`}</pre>
          </article>

          <article className="cli-docs-card">
            <h2>Authentication Model</h2>
            <p>
              The CLI uses a long-lived API credential emitted by the platform as a composite key in the form
              <strong> client_id.client_secret</strong>. That key is exchanged for a short-lived bearer token.
            </p>
            <pre>{`<client_id>.<client_secret>`}</pre>
          </article>

          <article className="cli-docs-card">
            <h2>Session Behavior</h2>
            <p>
              Each authenticated CLI request sends an <strong>Authorization</strong> bearer token,
              <strong> X-Organization-Id</strong>, and a <strong>Ledgora-CLI/&lt;version&gt;</strong> user agent.
            </p>
            <p>
              If the access token is close to expiry, or a request returns <strong>401</strong>, the CLI refreshes the session
              automatically and retries once.
            </p>
          </article>
        </div>
      </section>

      <section className="cli-docs-section cli-docs-section-alt">
        <div className="container cli-docs-grid">
          <article className="cli-docs-card">
            <h2>Core Commands</h2>
            <div className="cli-command-list">
              {authCommands.map((command) => (
                <pre key={command}>{command}</pre>
              ))}
            </div>
          </article>

          <article className="cli-docs-card cli-docs-card-wide">
            <h2>Business Commands</h2>
            <div className="cli-command-list">
              {businessCommands.map((command) => (
                <pre key={command}>{command}</pre>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="cli-docs-section">
        <div className="container cli-docs-grid">
          <article className="cli-docs-card">
            <h2>Secure Storage</h2>
            <ul className="cli-docs-list">
              {storageItems.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </article>

          <article className="cli-docs-card cli-docs-card-wide">
            <h2>Backend Endpoints</h2>
            <div className="cli-endpoints-table" role="table" aria-label="CLI endpoints">
              <div className="cli-endpoints-row cli-endpoints-head" role="row">
                <span role="columnheader">Method</span>
                <span role="columnheader">Path</span>
                <span role="columnheader">Purpose</span>
              </div>
              {endpointRows.map((endpoint) => (
                <div className="cli-endpoints-row" role="row" key={`${endpoint.method}-${endpoint.path}`}>
                  <span role="cell">{endpoint.method}</span>
                  <span role="cell">{endpoint.path}</span>
                  <span role="cell">{endpoint.description}</span>
                </div>
              ))}
            </div>
          </article>
        </div>
      </section>

      <section className="cli-docs-section cli-docs-section-alt">
        <div className="container cli-docs-grid">
          <article className="cli-docs-card">
            <h2>Example Login</h2>
            <pre>{`ledgora login --api-key <API_KEY> --org org_123 --profile prod\nledgora whoami`}</pre>
          </article>

          <article className="cli-docs-card">
            <h2>Safer Secret Input</h2>
            <pre>{`/home/atonixdev/ledgora/api/.venv/bin/python - <<'PY' | ledgora login --api-key-stdin --org org_123 --profile prod\nimport getpass\nimport sys\n\nsys.stdout.write(getpass.getpass('Ledgora API key: '))\nPY`}</pre>
          </article>

          <article className="cli-docs-card">
            <h2>Operational Notes</h2>
            <ul className="cli-docs-list">
              <li>HTTP is accepted only for local development hosts such as localhost.</li>
              <li>The CLI supports multiple saved profiles and lets you switch with a single command.</li>
              <li>Error output is normalized as a message and code pair for scripting and support workflows.</li>
            </ul>
          </article>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default CLIDocs;