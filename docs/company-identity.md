# Company Identity

`Organization` is the platform's company record. Its database `id` is the internal company ID and its `registration_number` is the canonical external company identity.

## Registration Rules

- A company name is globally unique, case-insensitively.
- A registration number is globally unique after normalization.
- Registration APIs require both a company name and registration number.
- Allowed input characters are letters, digits, spaces, periods, underscores, slashes, and hyphens.
- Separators are removed and the identifier is uppercased before storage. For example, `za-2024 / 123456` becomes `ZA2024123456`.
- The canonical identifier must contain 4-64 characters after normalization and include a digit.

## Identity Scope

Users and roles remain company-scoped through `TeamMember.organization`. The LDAP-compatible directory projects the company registration number into the root DN and user attributes, so Founder and member identities inherit the same company root. Governance YAML recovery verifies the registration number before any records are restored.

## Verification API

`POST /api/organizations/verify_registration_number/` validates syntax and reports whether the normalized identifier is available. It intentionally reports `external_registry_verified: false` until a country-specific registry provider is configured. A future CIPC, SEC, or other provider must validate the already-normalized identifier and never replace the local uniqueness check.

## Legacy Records

Existing organizations without a registration number remain readable so deployments can migrate data safely. New organization registrations cannot omit the number. Backfill legacy companies before enabling external registry verification as a mandatory control.