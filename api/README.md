# AI Financial Modeling Integration System - API

## Overview

This is the Django REST API for the AI Financial Modeling Integration System. It provides enterprise-grade financial analysis capabilities with AI-driven insights, multi-tenant architecture, and comprehensive compliance features.

## Features

### 🏗️ System Architecture
- **6-Layer Architecture**: Core calculations, input processing, AI interpretation, advanced analytics, scenarios, and enterprise features
- **Multi-Tenant Support**: Complete data isolation with role-based access control
- **Audit Trail**: Comprehensive change tracking with compliance verification
- **Real-time Processing**: High-performance calculation engines

### 💰 Financial Modeling
- **DCF Analysis**: Discounted Cash Flow with terminal value calculations
- **Comparable Companies**: Market-based valuation multiples
- **Merger Analysis**: M&A modeling with synergies and financing
- **40+ Country Tax Library**: Comprehensive international tax calculations
- **Multi-currency Support**: Real-time currency conversion

### 🤖 AI & Analytics
- **Pattern Recognition**: Automated financial pattern detection
- **Anomaly Detection**: Statistical outlier identification
- **Predictive Analytics**: Trend forecasting with confidence intervals
- **Custom KPIs**: Formula-based key performance indicators
- **Benchmarking**: Industry peer comparison

### 🎯 Scenario Planning
- **Best/Base/Worst Cases**: Multi-scenario analysis
- **Sensitivity Testing**: Tornado diagrams and what-if analysis
- **Monte Carlo Simulation**: Probabilistic modeling
- **Risk Assessment**: Scenario-based risk quantification

### 🏢 Enterprise Features
- **Consolidation Engine**: Multi-entity financial consolidation
- **Intercompany Eliminations**: Automatic IC transaction removal
- **Minority Interest**: Ownership-based MI calculations
- **Compliance Verification**: GAAP/IFRS/SOX compliance checking

## Quick Start

### Prerequisites
- Python 3.13 (the supported runtime for the production image)
- Django 5.2 LTS
- Virtual environment

### Installation

1. **Clone and navigate to the API directory:**
   ```bash
   cd api/
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run migrations:**
   ```bash
   python manage.py migrate
   ```

5. **Start development server:**
   ```bash
   python manage.py runserver
   ```

6. **Access the application:**
   - **Landing Page**: http://localhost:8000/
   - **API Root**: http://localhost:8000/api/
   - **Admin Panel**: http://localhost:8000/admin/

## Production Deployment

Build and run the production image with a supported Python 3.13 runtime:

```bash
docker build -f Dockerfile.prod -t atonixcorp-api:latest .
docker run --rm -p 8000:8000 --env-file .env atonixcorp-api:latest
```

Before deployment, set these values in `.env`:

```dotenv
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<a unique random value of at least 50 characters>
DJANGO_ALLOWED_HOSTS=api.example.com
DATABASE_URL=postgres://<user>:<password>@<host>:5432/<database>
CORS_ALLOWED_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
FRONTEND_BASE_URL=https://app.example.com
DJANGO_SECURE_SSL_REDIRECT=True
```

Run migrations as a release step before starting new application instances:

```bash
docker run --rm --env-file .env atonixcorp-api:latest python manage.py migrate --noinput
```

The container health check calls `GET /status`; route TLS termination through a reverse proxy or load balancer that sets `X-Forwarded-Proto: https`.

## API Endpoints

### Core Financial API v1 Documentation
- OpenAPI blueprint: `openapi/atonixcorp-v1-openapi.yaml`
- External developer guide: Core financial API v1 developer guide
- Redoc UI: `/v1/docs`
- Swagger UI: `/v1/swagger`
- CLI authentication guide: `../README/CLI_AUTHENTICATION_GUIDE.md`
- CLI auth endpoints: `/auth/cli-login`, `/auth/refresh`, `/auth/me`

### Core APIs
- `GET /` - Landing page with system overview
- `GET /api/` - API root with available endpoints
- `GET /admin/` - Django admin panel

### Financial Modeling
- `POST /api/models/calculate/` - Run financial model calculations
- `GET /api/models/{id}/` - Retrieve model results
- `GET /api/tax/countries/` - List supported tax jurisdictions
- `GET /api/tax/countries/{code}/` - Get country-specific tax data

### AI & Analytics
- `POST /api/ai/insights/` - Generate AI-driven insights
- `POST /api/analytics/kpis/` - Calculate custom KPIs
- `POST /api/analytics/trends/` - Perform trend analysis
- `POST /api/analytics/benchmark/` - Industry benchmarking

### Scenario Planning
- `POST /api/scenarios/` - Generate scenario analysis
- `POST /api/sensitivity/` - Run sensitivity testing
- `GET /api/scenarios/{id}/` - Retrieve scenario results

### Enterprise Features
- `GET /api/organizations/` - Multi-tenant organization management
- `GET /api/audit-logs/` - Audit trail and compliance logs
- `POST /api/consolidation/` - Multi-entity consolidation
- `GET /api/compliance/` - Compliance verification

### Reporting
- `POST /api/reports/` - Generate financial reports
- `GET /api/reports/{id}/` - Retrieve report
- `POST /api/export/` - Export data (JSON/CSV/PDF)

## Data Models

### Core Models
- **Organization**: Multi-tenant organization structure
- **Entity**: Business entities for consolidation
- **TeamMember**: User management with roles
- **Expense/Income/Budget**: Personal finance tracking

### Enterprise Models
- **TaxExposure**: Tax liability tracking
- **ComplianceDeadline**: Regulatory deadline management
- **CashflowForecast**: Cash flow projections
- **AuditLog**: Complete audit trail

## Authentication & Security

### Multi-Tenant Architecture
- **Data Isolation**: Row-level security by tenant
- **Role-Based Access**: Admin, Analyst, Editor, Viewer roles
- **Resource Quotas**: Configurable limits per tenant
- **API Key Management**: Secure API access

### Compliance & Audit
- **GAAP/IFRS/SOX**: Regulatory compliance verification
- **Change Tracking**: All data modifications logged
- **Data Lineage**: Complete source-to-use traceability
- **Retention Policies**: 7-year audit retention

## Development

### Project Structure
```
api/
├── atonixcorp_api/       # Main Django project
│   ├── settings.py      # Django settings
│   ├── urls.py         # URL configuration
│   └── wsgi.py         # WSGI application
├── finances/            # Main app
│   ├── models.py       # Database models
│   ├── views.py        # API views
│   ├── serializers.py  # DRF serializers
│   ├── urls.py         # App URLs
│   └── enterprise_views.py  # Enterprise features
├── templates/           # Django templates
│   └── landing_page.html
├── data/               # Static data files
│   └── tax/
│       └── countries.json
├── manage.py           # Django management script
└── requirements.txt    # Python dependencies
```

### Key Technologies
- **Django 4.2**: Web framework
- **Django REST Framework**: API development
- **SQLite**: Development database
- **CORS Headers**: Cross-origin support
- **JSON**: Data interchange format

## Deployment

### Production Setup
1. **Database**: Configure PostgreSQL
2. **Static Files**: Set up CDN/static file serving
3. **Security**: Configure HTTPS and security headers
4. **Monitoring**: Set up logging and monitoring
5. **Scaling**: Configure load balancing and caching

### Docker Deployment
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
EXPOSE 8000
CMD ["gunicorn", "atonixcorp_api.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### Banking Integration Environment
- Copy `api/.env.example` to `api/.env` and set a strong `BANKING_TOKEN_ENCRYPTION_KEY`.
- Configure the provider variables for the aggregator you are using: `PLAID_*`, `YODLEE_*`, or `FINICITY_*`.
- App consent callbacks can return to the integrations page after the provider completes the OAuth flow.
- Provider webhooks should target `https://<your-domain>/api/banking-integrations/webhooks/<provider_code>/`.
- Nightly fallback syncs run through `python manage.py sync_banking_integrations`; `docker-compose.yml` now includes a `banking-sync` service that executes this every 24 hours by default.
- Run `python manage.py seed_source_filter_demo --reset` to recreate the mixed manual-plus-imported verification dataset used for source-filter QA.

### Approval Notification Scheduling
- Daily approval digests run through `python manage.py send_approval_notification_digest --hours 24`.
- `start.sh` can run the digest loop automatically when `ENABLE_APPROVAL_DIGEST_SCHEDULER=1`.
- `docker-compose.yml` includes an `approval-digest` service that executes the digest command every 24 hours by default.
- Scheduler controls:
   - `APPROVAL_DIGEST_INTERVAL_SECONDS` controls how often the digest loop runs.
   - `APPROVAL_DIGEST_LOOKBACK_HOURS` controls the unread-approval lookback window included in each digest.

### Approval Email Branding
- Finance approval emails and digests render from `templates/email/base.html` and the approval-specific templates under `templates/email/`.
- Configure production branding and links with these environment variables:
   - `FRONTEND_BASE_URL` or `APPROVAL_NOTIFICATION_BASE_URL` for deep links back into the approval inbox.
   - `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `EMAIL_USE_SSL`, and `DEFAULT_FROM_EMAIL` for outbound delivery.
   - `EMAIL_BRAND_NAME`, `EMAIL_BRAND_TITLE`, `EMAIL_BRAND_FOOTER`, `EMAIL_SUPPORT_EMAIL`, and `EMAIL_SUPPORT_URL` for production-facing brand copy in finance emails.

## Testing

### Run Tests
```bash
python manage.py test
```

### API Testing
```bash
# Test health endpoint
curl http://localhost:8000/api/health/

# Test tax countries
curl http://localhost:8000/api/tax/countries/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit pull request

## License

© 2025 AtonixCorp. All rights reserved.

## Support

For support and questions:
- **Documentation**: See inline code documentation
- **API Docs**: Available at `/api/docs/` when running
- **Issues**: Create GitHub issues for bugs/features
