# Dropdown Visibility and Responsive Menus

All dropdowns use the `--color-dropdown-*` tokens in `app/src/styles/tokens.css`.
Native `select`, `option`, and `optgroup` controls receive an explicit surface and
text color in `app/src/styles/unified.css`, so they cannot inherit white text on a
white popup. Reusable profile and workspace menus use the same contract, including
hover, active, keyboard-focus, and touch-safe mobile target styles.

At widths below 1024px, profile and workspace dropdowns reassert their tokenized
surface, border, and text colors and use 48px menu-item targets. At widths below
768px, native selects reassert the same surface and text colors. Regular mobile
navigation links use the dropdown ink token; white utility-link text is reserved
for the explicit dark utility surface. This keeps phone, tablet, and desktop menus
legible in both light and dark themes.

For a future dark theme, set `data-theme="dark"` on the application root. The
dropdown tokens then switch together; do not set isolated menu text or background
colors in feature CSS.

# AtonixCorp CSS System

AtonixCorp uses one shared CSS contract for public pages, authenticated dashboards, subscription views, and future modules.

## Import order

The stylesheet spine is loaded from `app/src/index.js`:

1. `styles/theme.css` provides compatibility aliases.
2. `styles/globals.css` loads tokens, base elements, components, and layout rules.
3. Page-specific styles provide local layout details.
4. `styles/unified.css` enforces the shared visual contract.
5. `styles/creation-system.css` is loaded after the unified baseline and defines the provisioning-flow contract.

New feature styles should use the existing tokens and should not introduce a second font, palette, spacing scale, or button system.

## Typography

The platform uses bundled IBM Plex Sans for interface text and IBM Plex Mono for code or data that benefits from fixed-width alignment.

- Page titles (`h1`): 24-32px, bold.
- Section titles (`h2`): 20-24px, bold.
- Body text: 16px, regular, 1.5 line height.
- Labels and metadata: 14px, semibold.

## Palette

Use the semantic variables instead of raw color values:

- Authority: `--color-navy-950`, `--color-navy-900`, `--color-navy-800`.
- Technology accents: `--color-blue-700`, `--color-blue-600`, `--color-blue-100`.
- Surfaces and borders: `--color-white`, `--color-silver-100`, `--color-silver-200`, `--color-silver-300`.
- Text: `--color-heading`, `--color-text`, `--color-silver-700`.
- Status: `--color-success`, `--color-warning`, `--color-error`, `--color-info`.

Avoid raw colors, neon effects, glow treatments, decorative gradients, and page-specific brand colors.

## Layout and components

Use the 12-column grid patterns already established by page shells. The standard rhythm is 16px for controls and local spacing, 24px for grouped content, and 32px for section separation. Cards use an 8px maximum radius, a 1px silver border, and the shared shadow tokens.

Use the shared classes when they apply:

- `.page-header`, `.page-title`, `.page-subtitle`, `.page-actions`
- `.card`, `.surface-card`, `.panel`, `.table-wrapper`
- `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-outline`
- `.badge`, `.status-badge`, `.pill`
- `.ui-table`

Forms inherit consistent input sizing, focus rings, labels, and borders from `globals.css` and `unified.css`.

## Creation Flows

Organization, company, department, entity, and workspace creation flows use `styles/creation-system.css`. Apply `.creation-flow` to the page root and compose its reusable primitives with local layout classes:

- `.creation-card` for a primary step surface.
- `.creation-summary-card` for review, license, user, package, or module summaries.
- `.creation-option-card` and `.creation-module-card` for selectable cards.
- `.creation-field`, `.creation-label`, and `.creation-control` for form controls.
- `.creation-description` for helper or supporting copy.

Creation surfaces and controls are deliberately square: `--creation-radius` is `0`. All text uses IBM Plex Sans, controls are 44px high, labels are 13px semibold, helper text is 13px with a 20px line height, and spacing uses 8px, 16px, 24px, and 32px increments. Do not add gradients, decorative shapes, pills, or a local card/input system to these flows.

## Adding a module

1. Import only the module stylesheet needed for layout-specific rules.
2. Use semantic variables from `tokens.css` for colors, spacing, typography, borders, and elevation.
3. Prefer shared primitives over new card, button, or form variants.
4. Keep mobile behavior within the module stylesheet or the shared breakpoint at 760px.
5. Run `npm run build` before opening a pull request.
