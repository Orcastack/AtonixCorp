# AtonixCorp

AtonixCorp is a financial operations platform for multi-tenant financial management, governance, collaboration, banking integrations, and developer workflows. The repository contains the Django API, React web application, React Native mobile application, Python SDK and CLI, infrastructure definitions, and deployment tooling.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `api/` | Django REST API, financial and governance domains, email templates, and API documentation. |
| `app/` | React web application. |
| `atonixcorpmobile/` | React Native mobile application for iOS and Android. |
| `atonixcorpSdk/` | Python SDK for the Developer Console Integration (DCI). |
| `atonixcorpCli/` | Python command-line client for developer and governance workflows. |
| `toolbox/` | Validation, sandbox-fixture, and audit-diagnostic utilities. |
| `deploy/`, `k8s/`, `infra/` | Docker, Apache, Kubernetes, and infrastructure-as-code deployment assets. |
| `docs/` | Product, design, governance, and implementation references. |
| `email-templates/` | Shared email-template catalog and sources. |

## Prerequisites

- Python 3.13
- Node.js 20 for the web application (see `app/.nvmrc`)
- npm
- Docker and Docker Compose for containerized development
- Xcode and/or Android Studio only when developing the mobile application

## Quick Start

From the repository root, run the guided setup script:

```bash
./setup.sh
```

The script creates the API virtual environment, installs API dependencies plus the local SDK and CLI, applies Django migrations, installs web dependencies, and creates local environment files from their examples when needed. It optionally prompts you to create a Django administrator account.

Then start the web application and API:

```bash
./start.sh
```

Local services are available at:

| Service | URL |
| --- | --- |
| Web app | http://localhost:3000 |
| API root | http://localhost:8000/api/ |
| Django admin | http://localhost:8000/admin/ |
| API health check | http://localhost:8000/api/health/ |

`start.sh` also starts the banking-sync and approval-digest schedulers by default. Set `ENABLE_BANKING_SYNC_SCHEDULER=0` or `ENABLE_APPROVAL_DIGEST_SCHEDULER=0` in `api/.env` to disable either scheduler locally.

### Manual Setup

Use this when you need to run the API and web app separately:

```bash
cd api
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip install -e ../atonixcorpSdk
.venv/bin/python -m pip install -e ../atonixcorpCli
cp .env.example .env # Only if api/.env does not already exist
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

In another terminal:

```bash
cd app
nvm use
npm install
npm start
```

## Configuration and Secrets

Start with [`api/.env.example`](api/.env.example). Never commit local `.env` files, API keys, SMTP passwords, provider credentials, or encryption/signing keys.

For local development, set a unique `BANKING_TOKEN_ENCRYPTION_KEY`; `setup.sh` generates one when it creates `api/.env`. Production deployments must use a secret manager and configure at least:

- `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=False`, `DJANGO_ALLOWED_HOSTS`
- `DATABASE_URL` for PostgreSQL
- `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, and `FRONTEND_BASE_URL`
- `BANKING_TOKEN_ENCRYPTION_KEY`, `WORKSPACE_FILE_ENCRYPTION_KEY`, and `GOVERNANCE_SIGNING_KEY`
- SMTP settings and any enabled banking, storage, OAuth, or AI-provider credentials

Banking-provider webhooks use this route:

```text
/api/banking-integrations/webhooks/<provider_code>/
```

See [`api/README.md`](api/README.md) for API deployment and integration details.

## Docker Development

The Compose stack starts the API, web app, PostgreSQL, banking-sync worker, approval-digest worker, and Apache reverse proxy:

```bash
docker compose up --build
```

The API and web-app development ports are bound to loopback at `127.0.0.1:8000` and `127.0.0.1:3000`. Apache exposes ports 80 and 443, so provide the certificates expected by the Apache configuration before using the full proxy stack.

## Testing and Quality Checks

Run the same primary checks used in CI:

```bash
cd api
.venv/bin/python manage.py check --deploy
.venv/bin/python manage.py test
```

```bash
cd app
npm run standards:check
CI=true npm test -- --watch=false --passWithNoTests
npm run build
```

CI also audits Python and npm dependencies and verifies production image builds. The complete pipeline is defined in [`bitbucket-pipelines.yml`](bitbucket-pipelines.yml).

## SDK, CLI, and Toolbox

Install the local developer tools in dependency order:

```bash
python3 -m pip install -e ./atonixcorpSdk
python3 -m pip install -e ./atonixcorpCli
python3 -m pip install -e ./toolbox
```

After the API is running, try the local sandbox tools:

```bash
atonixcorp sandbox-status
atonixcorp-toolbox sandbox-entity 1
```

The SDK defaults to the local API at `http://localhost:8000` and permits plain HTTP only for the loopback sandbox. Read [`docs/developer-ecosystem.md`](docs/developer-ecosystem.md) for DCI, security, and sandbox guidance.

## Mobile Application

The mobile app has an independent Node.js requirement of 22.11 or newer:

```bash
cd atonixcorpmobile
npm install
npm start
npm run ios      # macOS with Xcode
npm run android  # Android tooling required
```

## Further Documentation

- [`api/README.md`](api/README.md): API development, endpoints, integrations, deployment, and testing.
- [`app/README.md`](app/README.md): Web-app commands and structure.
- [`docs/developer-ecosystem.md`](docs/developer-ecosystem.md): SDK, CLI, toolbox, DCI, and security model.
- [`docs/company-identity.md`](docs/company-identity.md): Company identity and architecture reference.
- [`k8s/README.md`](k8s/README.md): Kubernetes deployment guidance.
- [`deploy/apache2/README.md`](deploy/apache2/README.md): Apache and TLS deployment guidance.