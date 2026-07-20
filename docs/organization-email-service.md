# Organization Email Service

AtonixCorp provides an organization-scoped, audited outbound email service for governance notices, operational communications, and consent-based marketing campaigns. Organization email controls are available to the organization owner in the Workspace Email module.

## Scope

The application provisions managed sender identities, applies subscription limits, sends through Django's configured SMTP provider, records delivery attempts, and writes immutable platform audit events.

It does not operate an inbound mailbox server, expose IMAP or POP, configure DNS records automatically, or prove inbox placement. Mailbox hosting, SMTP relay operation, DKIM signing, SPF, DMARC, bounce handling, and provider event webhooks remain deployment responsibilities.

## Tiers and Enforcement

| Tier | Active sender identities | Monthly sends | Campaign types |
| --- | ---: | ---: | --- |
| Basic | 0 | 250 | System notifications only |
| Professional | 5 | 2,500 | Governance and operational |
| Enterprise | Unlimited | 25,000 | Governance, operational, and marketing |

The backend, not the user interface, enforces sender-account limits, active subscription status, monthly volume limits, sender ownership, Enterprise-only marketing, and explicit marketing-consent confirmation. Each marketing recipient receives an unsubscribe link.

Tier changes are currently organization-owner control-plane actions. `billing_reference` is retained for a future billing-provider integration; it is not a payment capture workflow.

## API

All organization email endpoints require the authenticated organization owner. A user outside the organization receives `404`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/organizations/{id}/email_service/` | Subscription summary, sender identities, recent campaigns, and delivery events |
| `POST /api/organizations/{id}/configure_email_subscription/` | Set tier and optional billing reference |
| `POST /api/organizations/{id}/provision_email_account/` | Provision a sender identity with `local_part` and optional `display_name` |
| `POST /api/organizations/{id}/send_email_campaign/` | Send a governance, operational, or marketing campaign |

Campaign requests require `sender_id`, `campaign_type`, `recipients`, `subject`, and `html_body`. Marketing campaigns also require `consent_confirmed: true`.

## System Notifications

The service records and delivers automated notifications for:

- account registration;
- organization creation;
- organization role assignment and subsequent role changes;
- organization-linked workspace creation.

Delivery records include recipient, subject, event type, timestamp, status, and a bounded error message. They do not persist SMTP credentials.

## Production Configuration

The deployed relay is Brevo SMTP. Set these deployment variables and store the SMTP key only in a deployment secret manager or the ignored local `api/.env` file:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_HOST_USER=b2acdf001@smtp-brevo.com
EMAIL_HOST_PASSWORD=replace-with-your-brevo-smtp-key
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
DEFAULT_FROM_EMAIL=no-reply@verified-sender-domain.example
ORGANIZATION_EMAIL_DOMAIN=verified-sender-domain.example
FRONTEND_BASE_URL=https://app.example.com
```

For production Django SMTP delivery, AtonixCorp rejects plaintext transport: set exactly one of `EMAIL_USE_TLS=true` or `EMAIL_USE_SSL=true`. The application does not store SMTP credentials; provide them as deployment secrets. Before live sending, replace the local `atonixcorp.local` defaults with a domain and sender address verified in Brevo; Brevo rejects or restricts unverified sender identities.

Configure the provider and DNS before enabling live traffic:

1. Publish SPF for the envelope-sender domain and authorized SMTP provider.
2. Enable DKIM signing at the SMTP provider and publish its selector records.
3. Publish a DMARC policy, begin with monitoring, and review aggregate reports before enforcement.
4. Configure bounce, complaint, and suppression handling through provider webhooks or an operational process.
5. Use a sandbox or allowlisted environment for staging and test sender-domain alignment before production sends.

## Compliance and Operations

Use governance or operational campaigns only for legitimate organization communications. Marketing recipients must have a lawful recorded consent basis, and unsubscribe requests must be honored through the deployed preference/suppression process. The current unsubscribe link provides a recipient preference destination; a production deployment must connect it to durable preference and suppression handling before marketing use.

Review `OrganizationEmailDelivery` records and `PlatformAuditEvent` events such as `email.account_provisioned` and `email.campaign_sent` as part of routine operational monitoring. Retention, access review, export, and deletion policies should align with the organization's regulatory obligations.

## Staging Tests

Use Django's in-memory backend in automated tests:

```python
@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
```

For integration environments, use the SMTP provider's sandbox mode and validate sender identity, TLS negotiation, DKIM signing, SPF alignment, unsubscribe behavior, bounce processing, and audit-event creation.
