# Onboarding UI Standards

The organization onboarding flow is an operational console, not a marketing surface. It uses a five-step sequence: Company Identity, Jurisdiction and Currency, Fiscal and Structure, Modules and License, and Launch.

## Layout

- Use the onboarding 12-column responsive container with a primary form region and a persistent organization summary on desktop.
- Keep summary data visible as the user progresses: company, registration identity, jurisdiction, module count, license, and step progress.
- Collapse the layout to a single column below 900px without hiding the summary.
- Use consistent spacing increments of 8px and stable input, button, and summary-row heights.

## Surfaces And Typography

- Use the scoped `creation-flow` styles and its navy (`#102a43`), blue (`#1769e0`), charcoal, and light neutral tokens.
- Use Montserrat, Roboto, or the established application sans-serif fallback; headings and labels must remain readable at compact console sizes.
- Keep cards, controls, status panels, and summary rows square or nearly square with a 2px radius and visible borders. Avoid gradients, decorative shapes, and dark content surfaces.
- Reserve navy for headers and blue for the active step, focus state, and selected license.

## Identity And Compliance

- The server remains authoritative for normalized registration-number validation and case-insensitive company-name uniqueness.
- The UI calls the identity preflight endpoint before allowing an organization user past the Company Identity step. Server-side creation validation remains mandatory because preflight results can become stale.
- Record creation through the existing immutable `company.created` platform audit event. Never place registration numbers in browser-only audit state.

## Subscription And Launch

- Present Basic, Professional, and Enterprise tiers as selectable license controls.
- Persist the selected tier in onboarding settings and synchronize it with the organization email subscription after organization creation.
- The launch review must display company identity, jurisdiction, currency, package, and license before submission.