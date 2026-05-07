# Financial Dashboard Design Bible

## Part 1. Foundations

### 1. Purpose of This Document

This document defines the visual identity, layout structure, component behavior, and design system rules for the financial dashboard. It is intentionally design-only. It does not define features, backend behavior, calculations, or business logic.

The objective is to produce a dashboard that feels financial, mature, institutional, clean, predictable, professional, zero-noise, and zero-freestyle. The experience should communicate trust and discipline before any user reads a single metric. It should feel like a financial intelligence environment, not a consumer app with decorative charts and casual styling.

The reference quality is the MoneyPilot interface you described, adapted to the Ledgora brand and the platform’s financial ecosystem. The visual standard is high. Every page, card, and control must look as though it belongs to the same system.

### 2. Core Design Philosophy

The dashboard must feel calm, precise, and systematic. The design should communicate trust, clarity, stability, financial discipline, educational guidance, and predictable structure.

Every pixel must be intentional. Every component must follow the same rules. Every page must feel like part of one financial operating system. This is the opposite of freestyle design. There should be no visual improvisation, no random color usage, no inconsistent spacing, and no one-off components that break the language of the interface.

The design principle is simple: the interface should help users understand their financial situation quickly and confidently. The UI should never fight for attention. It should organize information with discipline.

### 3. Design System Requirement

The dashboard must use a design system. It cannot rely on scattered inline styles, ad hoc CSS, or one-off component logic.

Approved approaches:

- Ant Design, recommended for its mature dashboard structure, grid discipline, and predictable components.
- Material UI, if a more modern learning-module aesthetic is preferred.
- Custom design tokens, only if spacing, typography, color, radius, shadow, and component tokens are explicitly defined and enforced.

If a custom system is used, it must define:

- Spacing tokens.
- Typography tokens.
- Color tokens.
- Border radius tokens.
- Shadow tokens.
- Component tokens.

The rules are strict: no freestyle CSS, no random padding, no hardcoded colors, and no inconsistent component behaviors.

### 4. Global Layout Structure

Every page must follow the same structural pattern:

- Left sidebar navigation.
- Thin top header.
- Main content area.
- Bottom breathing room.

The sidebar must be fixed, minimal, and clean, using icon plus label navigation with predictable spacing. The top header should carry the page title and quick stats without crowding the main content. The main content area should contain overview cards, learning modules, or financial metrics in a clean grid. Every page should end with generous breathing room so the layout never feels cramped.

This structure must remain stable across the product. Users should always know where to find navigation, context, and content.

### 5. Color System

The palette must feel financial, calm, and institutional.

Primary colors:

- Deep Navy: `#0A1A2F`
- Institutional Blue: `#1A3E7A`
- Soft Blue: `#E8F0FF`

Secondary colors:

- Soft Green: `#DFF5E3`
- Soft Purple: `#EEE8FF`
- Neutral Gray: `#F5F6F7`

Text colors:

- Primary: `#1A1D21`
- Secondary: `#6A6F75`
- Muted: `#9EA3A8`

Rules:

- No neon colors.
- No bright gradients.
- No heavy shadows.
- No random color usage.

The palette should feel like a financial institution: controlled, trustworthy, and quiet.

### 6. Typography System

Use Inter or IBM Plex Sans. Typography must be consistent everywhere.

Recommended size scale:

- Page titles: 22–24px.
- Section titles: 18px.
- Card titles: 14–16px.
- Body text: 14px.
- Labels: 12px.

Font weights:

- Titles: 500–600.
- Body: 400.
- Labels: 400.

Rules:

- No random bolding.
- No mixed fonts.
- No oversized display text.
- No inconsistent line heights.

Typography should create hierarchy, not decoration.

### 7. Component Design Rules

All components should share the same language.

#### 7.1 Cards

Cards should use an 8px radius, a soft shadow, 16px padding, and 12px spacing between text blocks. Each card should include a title, a main number, a sub-label, and optionally a small icon or progress bar.

Card colors must stay muted. No gradients, no bright borders, no playful shapes. Cards should feel like financial panels, not marketing blocks.

#### 7.2 Buttons

Buttons must come from the design system. Use 14–15px text, medium weight, consistent padding, hover states, and no custom shapes.

Button types:

- Primary: blue.
- Secondary: gray.
- Text button: minimal.

#### 7.3 Tabs

Tabs should be minimal and underlined on active state. Use 14px text, 12px spacing, and soft hover states. Avoid heavy borders and filled tab styles.

#### 7.4 Progress Bars

Progress bars must be thin, clean, and soft-colored. They should feel financial rather than playful. No thick bars and no gradients.

### 8. Sidebar Design

The sidebar is the backbone of the dashboard.

Sidebar items should include:

- Search.
- Budget Calculator.
- Set New Goal.
- Ask Coach.
- Courses.
- Inbox.
- Help Center.
- Settings.

Sidebar rules:

- 16px icons.
- 15px text.
- 12px vertical padding.
- 8px spacing between icon and text.
- Background `#F7F9FC`.
- Text `#1A1D21`.
- Icons `#6A6F75`.
- Active highlight `#2D6CDF`.

Behavior must remain stable: always visible, no collapsing, no floating elements, no animation-heavy interactions.

### 9. Top Header Design

The header should be thin, clean, and non-intrusive.

Left side:

- Page title.

Right side:

- Streak.
- Modules completed.
- Level.

Spacing:

- 24px between items.
- 16px vertical padding.

Typography:

- Title: 22px, medium.
- Stats: 14px, medium.
- Labels: 12px, regular.

The header should support context without overwhelming the main layout.

## Part 2. Advanced Layout, Component Architecture, and React Structure

### 10. Main Dashboard Overview

The dashboard overview is the heart of the experience. It must feel clean, calm, financial, intelligent, and predictable.

#### 10.1 Overview Grid Structure

Use a four-card grid:

- Monthly Income.
- Monthly Savings.
- Savings Progress.
- Learning Progress.

Spacing rules:

- 24px between cards.
- 32px top margin.
- 48px bottom margin.
- Baselines must align cleanly.

#### 10.2 Card Types

Each overview card should share the same structure:

- Title: 14px, medium.
- Main number: 28–32px, semi-bold.
- Sub-label: 12px, muted.
- Optional icon or progress bar.

Card colors:

- Income: soft blue.
- Savings: soft green.
- Savings progress: neutral gray.
- Learning progress: soft purple.

Shadows should stay extremely soft. Cards should feel elevated but not floating.

### 11. Learning Opportunities Section

This section should feel like a financial academy inside the dashboard.

#### 11.1 Section Header

Include a section title, “Learning Opportunities,” and tabs for All Topics, Budgeting, Saving, and Investing.

Spacing:

- 24px below the title.
- 16px below the tabs.

Typography:

- Title: 20px, medium.
- Tabs: 14px, medium.

#### 11.2 Tabs Behavior

Tabs should be minimal, with underlines on active state and soft hover states. They should never use heavy borders or background fills.

#### 11.3 Course Cards

Course cards should follow a disciplined structure:

- Width: 300–340px.
- Height: 180–220px.
- 16px internal padding.
- 12px spacing between text blocks.
- 8px spacing between metadata items.

Card content:

- Title: 16px, medium.
- Level: 12px, muted.
- Description: 14px, regular.
- Duration and sections: 12px, muted.
- Start Learning button: 14px, medium.

Course cards should hover softly, with no dramatic motion.

### 12. Spacing System

Spacing is a central design discipline. The platform must use a four-point grid.

Spacing tokens:

- 4px.
- 8px.
- 12px.
- 16px.
- 24px.
- 32px.
- 48px.

Rules:

- Never invent spacing values.
- Never eyeball spacing.
- Never use values like 5px, 7px, 10px, 18px, or 26px.
- Never mix unrelated spacing values on the same surface.

Spacing must be mathematically consistent.

### 13. React Design Architecture

This section describes the UI architecture in React, but not application logic.

#### 13.1 Component-Based Design

Build reusable UI primitives such as:

- `<Sidebar />`
- `<Header />`
- `<OverviewCard />`
- `<CourseCard />`
- `<ProgressBar />`
- `<TabGroup />`
- `<SectionHeader />`
- `<Grid />`

Layout components should include:

- `<DashboardLayout />`
- `<PageContainer />`
- `<ContentWrapper />`

Typography components should include:

- `<Title />`
- `<Subtitle />`
- `<BodyText />`
- `<Label />`

Button components should include:

- `<PrimaryButton />`
- `<SecondaryButton />`
- `<TextButton />`

No inline styling. No duplicated layouts. No one-off logic disguised as components.

#### 13.2 Component Rules

Every component should use tokens for spacing, typography, colors, shadows, and border radius.

Border radius tokens:

- Cards: 8px.
- Buttons: 6px.
- Inputs: 6px.
- Modals: 12px.

Shadow tokens should stay minimal. The default should be a soft, institutional shadow only.

### 14. Grid System

Use a 12-column grid with 24px gutters. Outer margins should stay consistent so pages line up from screen to screen. Breakpoints should reduce columns, not redesign the system.

## Part 3. Page-Level Design, Financial UI Patterns, and Visual Logic

### 18. Page-Level Design Principles

Every page must follow the same structure:

1. Page title.
2. Section header.
3. Content grid.
4. Bottom spacing.

This structure must never change.

#### 18.1 Page Title Rules

- 22–24px.
- Medium weight.
- Left aligned.
- No icons.
- No decorations.
- 24px margin below.

#### 18.2 Section Header Rules

- 18px.
- Medium weight.
- 16px margin below.
- Optional muted subtitle.

#### 18.3 Content Grid Rules

- 12 columns.
- 24px gutters.
- 32px outer margins.
- Cards aligned to the grid.

#### 18.4 Bottom Spacing

Every page should end with 48px of breathing room.

### 19. Financial UI Patterns

Financial dashboards communicate trust through repeatable visual patterns.

#### 19.1 At-a-Glance Metrics

At-a-glance metrics should use four equal cards with soft colors, large numbers, small labels, and minimal icons. Users should understand the dashboard state in seconds.

#### 19.2 Progress Indicators

Progress bars should be thin, clean, softly colored, and never cartoonish. They may represent savings, learning, or goal progress.

#### 19.3 Financial Modules Grid

Modules should appear in a clean 3- or 4-column grid with equal card sizes and consistent typography. The user should feel like they are inside a financial suite.

#### 19.4 Learning Cards

Learning cards should guide rather than overwhelm, and must include title, level, description, duration, sections, and action button.

### 20. Advanced Visual Logic

#### 20.1 Visual Weight Distribution

Place heavier elements at the top and lighter elements below. This creates a natural reading flow and reduces fatigue.

#### 20.2 Color Weight Distribution

Use strong colors only for important metrics. Use soft colors for background panels and muted tones for labels.

#### 20.3 Typography Weight Distribution

Follow clear hierarchy:

- Titles: medium.
- Section headers: medium.
- Card titles: medium.
- Body text: regular.
- Labels: muted.

### 21. React Design Structure

Layout components define the shell. UI components define the surfaces.

#### 21.1 Layout Components

- `<DashboardLayout />` contains sidebar, header, and content wrapper.
- `<PageContainer />` handles page title, section spacing, and grid alignment.
- `<ContentWrapper />` controls internal spacing, max width, and vertical rhythm.

#### 21.2 UI Components

- `<OverviewCard />` accepts title, value, label, color, and icon.
- `<CourseCard />` accepts title, level, description, duration, and sections.
- `<ProgressBar />` accepts value and color.
- `<TabGroup />` accepts tabs and activeTab.

#### 21.3 Typography Components

- `<Title />` for 22–24px medium headings.
- `<SectionTitle />` for 18px medium headings.
- `<BodyText />` for 14px regular text.
- `<Label />` for 12px muted labels.

### 22. Design Tokens

#### 22.1 Spacing Tokens

- spacing-4: 4px.
- spacing-8: 8px.
- spacing-12: 12px.
- spacing-16: 16px.
- spacing-24: 24px.
- spacing-32: 32px.
- spacing-48: 48px.

#### 22.2 Color Tokens

- primary-blue: `#1A3E7A`.
- primary-navy: `#0A1A2F`.
- primary-soft-blue: `#E8F0FF`.
- secondary-green: `#DFF5E3`.
- secondary-purple: `#EEE8FF`.
- secondary-gray: `#F5F6F7`.
- text-primary: `#1A1D21`.
- text-secondary: `#6A6F75`.
- text-muted: `#9EA3A8`.

#### 22.3 Typography Tokens

- font-title: 22px.
- font-section: 18px.
- font-card-title: 16px.
- font-body: 14px.
- font-label: 12px.

### 23. Visual Consistency Rules

All cards must match. All buttons must match. All spacing must match. All typography must match. All icons must match. Consistency is the difference between a professional financial dashboard and a messy interface.

### 24. Accessibility Design

The dashboard must satisfy accessible contrast, readable typography, visible hover and focus states, and sufficiently large controls. Accessibility is not optional. It is part of the professional standard.

## Part 4. Motion, Empty States, Errors, Responsive Rules, Branding, and Final Checklist

### 25. Motion Design

Motion should be subtle and minimal. Financial platforms should not feel dramatic.

#### 25.1 Hover Animations

Hover states should use 100–150ms ease-in-out transitions and only a slight elevation or background tint.

#### 25.2 Button Animations

Buttons should darken slightly on hover and lighten slightly on active. No bounce, shake, glow, or cartoon transitions.

#### 25.3 Card Animations

Cards may elevate by 1–2px on hover and scale very slightly on active.

#### 25.4 Tab Animations

Tabs may slide the underline from left to right with 150ms soft easing.

#### 25.5 Progress Bar Animations

Progress bars should fill smoothly over 300–400ms without overshoot.

#### 25.6 Modal Animations

Modals should fade in and slide up 8px over 150–200ms.

#### 25.7 Forbidden Animations

Never use bounce, spin, flash, pulse, wiggle, neon glow, or cartoon transitions.

### 26. Empty States

Empty states should feel clean, encouraging, professional, and helpful.

#### 26.1 Structure

Include:

1. Minimal icon or illustration.
2. Title.
3. Description.
4. Optional action button.

#### 26.2 Examples

- No income data yet.
- No savings recorded.
- Start your first lesson.

#### 26.3 Empty State Colors

- Background: white.
- Icon: `#6A6F75`.
- Title: `#1A1D21`.
- Description: `#9EA3A8`.

#### 26.4 Rules

No bright colors. No cartoons. No emojis. No jokes. No clutter.

### 27. Error States

Errors should be clear, calm, non-alarming, and professional.

#### 27.1 Structure

Include:

1. Thin warning icon.
2. Title.
3. Description.
4. Retry button.

#### 27.2 Examples

- Unable to load data.
- Courses unavailable.

#### 27.3 Error Colors

- Icon: `#D9534F`.
- Title: `#1A1D21`.
- Description: `#6A6F75`.
- Button: primary blue.

#### 27.4 Rules

No red backgrounds. No flashing icons. No aggressive wording. No technical jargon.

### 28. Responsive Design

The dashboard must work on desktop, tablet, and mobile.

Desktop uses the full 12-column grid with the sidebar visible and four overview cards. Tablet may collapse the sidebar to icons and reduce cards to two columns. Mobile should stack cards full width, turn tabs into scrollable controls, and keep the hierarchy intact.

Typography should shrink modestly on smaller screens, but the voice of the interface should remain consistent. Spacing tokens remain the same even when layout breaks change.

### 29. Branding Rules

The dashboard should feel like a financial brand, not a generic template.

Logo placement belongs at the top left of the sidebar with adequate margin. Brand colors should stay within navy, institutional blue, and soft blue. Brand typography should use Inter or IBM Plex Sans. Brand voice should be clear, direct, professional, encouraging, and non-technical.

The personality of the platform should feel like a financial coach, advisor, mentor, and assistant.

### 30. Microcopy Rules

Microcopy should be short, clear, and helpful.

Good examples:

- Start Learning.
- View Details.
- Add Income.
- Track Savings.
- Continue Lesson.

Bad examples:

- Click here to proceed.
- Submit data.
- Load module.
- Execute action.

The tone should be friendly but professional, with no slang, no jokes, and no emojis.

### 31. Final Developer Checklist

Before shipping any screen, verify:

- Sidebar alignment.
- Header alignment.
- Grid alignment.
- Spacing token usage.
- Typography consistency.
- Color token compliance.
- Component consistency.
- Hover and focus states.
- Accessibility contrast.
- No visual noise.
- No clutter.
- No freestyle design.

### 32. Conclusion

This design bible defines the visual identity, layout system, component architecture, spacing rules, typography rules, color system, motion rules, accessibility standards, responsive behavior, branding, and developer checklist for the financial dashboard.

If developers follow this specification exactly, the dashboard will feel financial, mature, institutional, clean, professional, and world-class.
