# AtonixCorp CSS System

AtonixCorp uses one shared CSS contract for public pages, authenticated dashboards, subscription views, and future modules.

## Import order

The stylesheet spine is loaded from `app/src/index.js`:

1. `styles/theme.css` provides compatibility aliases.
2. `styles/globals.css` loads tokens, base elements, components, and layout rules.
3. Page-specific styles provide local layout details.
4. `styles/unified.css` is loaded last and enforces the shared visual contract.

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

## Adding a module

1. Import only the module stylesheet needed for layout-specific rules.
2. Use semantic variables from `tokens.css` for colors, spacing, typography, borders, and elevation.
3. Prefer shared primitives over new card, button, or form variants.
4. Keep mobile behavior within the module stylesheet or the shared breakpoint at 760px.
5. Run `npm run build` before opening a pull request.
