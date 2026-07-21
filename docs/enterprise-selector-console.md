# Enterprise Selector and Console

## Organization Selector

The organization selector presents each accessible organization with its canonical registration number and recorded owner. These values come from the organization API and make the company identity visible before a user enters an operating context.

Organization creation requires a normalized, unique registration number. The backend also rejects duplicate normalized registration numbers and case-insensitive duplicate organization names.

## Organization Invitations

`POST /api/global/invite` now supports an explicit organization invitation payload:

```json
{
  "organization_id": 42,
  "email": "member@example.com",
  "role_code": "VIEWER"
}
```

Only the organization owner can use this branch. It creates or reopens a pending `TeamMember` invitation, rejects an already active member, and records an `AuditLog` entry with the actor, invitation target, email, and requested role. The legacy `workspace_id` invitation contract remains available for workspace collaboration invitations.

The Global Console only offers organization invite choices for organizations owned by the signed-in user. Server-side owner enforcement remains the authoritative control.

## Validation

Focused API coverage verifies owner invitations, audit records, and non-owner denial. Frontend production builds validate the selector and console UI integration. The UI consumes live organization data; deployment-level monitoring and external identity-provider policy controls remain operational configuration responsibilities.