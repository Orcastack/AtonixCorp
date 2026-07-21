# Email Template System

Templates live in `email-templates/email/` and are rendered by `atonixcorp.email_template_service` using Django templates. Each template has an HTML and plain-text version; update both files together.

The template variable catalog is maintained in `email-templates/catalog.yaml`. Supported templates are `verification`, `system_notification`, `marketing_campaign`, and `order_notification`.

Marketing messages must use the `marketing_campaign` template and provide an unsubscribe URL. The current campaign service records delivery attempts in `OrganizationEmailDelivery`; configure Brevo event webhooks before using provider open/click events as product metrics. SMTP TLS, DKIM, SPF, and DMARC are provider/domain controls and must be enabled in the production Brevo account and DNS zone.

Preview template changes with Django's locmem backend in tests before deployment. Do not put credentials, personal data, or unescaped untrusted HTML into templates.