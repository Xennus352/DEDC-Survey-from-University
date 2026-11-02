# DEDC Administration Design System

## Mission and hierarchy

Build a quiet, readable survey administration workspace for Burmese and English content. Frequent jobs are editing question structure, reviewing submissions and filtering reports. Publication, bulk changes and exports need explicit scope and feedback. `AdminSketch.md` overrides third-party aesthetics, sample content and framework suggestions.

Use the existing FastAPI/Jinja/vanilla-JavaScript architecture. Reuse macros/partials for sidebar, topbar, fields, tables, status, empty/error states and dialogs. Keep public-site styles isolated from administrative changes.

## Foundations

- Use `/static/img/logo.png` as the ministry identity. Its navy cog (`--primary: #232550`) and gold outline (`--accent: #b58a35`) define the accent palette, using gold sparingly for identity rather than body text on white.
- Define administrator tokens in one scoped stylesheet: surface, canvas, text, muted text, border, focus, action, success, warning and danger. Components reference semantic tokens, with no arbitrary per-page palettes.
- Keep DM Sans with Noto Sans Myanmar and installed Myanmar fallbacks. Body text 16px; dense table labels 13–14px; page titles 24–28px. Allow Myanmar line-height around 1.8 and avoid fixed-height text boxes. Use tabular numerals and right-aligned numeric columns.
- Spacing scale: 4, 8, 12, 16, 24, 32px. Sidebar approximately 240px, topbar approximately 64px. Use compact surfaces with 8–12px radii, subtle borders and shadows only for floating controls/dialogs.
- Neutral canvas and white working surfaces; navy for primary actions and selection. Status always includes words or symbols, never color alone. No decorative gradients, orbit art, oversized greetings, fabricated KPI deltas or hero compositions inside working views.

## Layout and navigation

Use the eight requested navigation destinations, but expose a destination only when its real page and backend exist. Collapse the sidebar on tablets/phones, keeping a labeled keyboard-accessible toggle. Breadcrumbs identify context and preserve list filters in URLs. Tables may scroll within their own region; the page itself must not overflow horizontally. Mobile record views prioritize essential fields and actions.

Search and notifications must query actual data/events. Do not add inactive controls to suggest completeness. Light theme is the first implementation; a dark theme must cover all surfaces, fields, charts and states before being offered.

## Interaction and accessibility

- Visible labels, immediate focus rings, logical heading structure and semantic tables. Target WCAG AA contrast: 4.5:1 body text and 3:1 large text/UI boundaries; verify actual colors rather than assuming token names imply contrast.
- Touch targets at least 44px. Reordering requires keyboard controls as well as drag/drop.
- Each data region defines loading, populated, empty, filtered-to-zero, error, permission-denied and large-data behavior where applicable. Render real empty states when records are absent.
- Errors explain the failed action and recovery path. Forms keep entered data and show field-level feedback plus a focusable summary. Disable repeated submissions while a request runs and restore controls after failure.
- Preserve native navigation and progressive enhancement. Use stateful updates when they help retain edits or filters. Confirm irreversible actions; never silently alter a published version.
- Use 120–200ms opacity/transform transitions only to explain state. Honor reduced-motion preferences. GSAP is installed as agent guidance, not loaded into the app; add the runtime only when a specific interaction benefits enough to justify it.

## Forms, charts and data integrity

The workbook's four section groups and multi-field question rows guide the builder. Show import confidence/warnings and source cells; never infer requirements or translations silently. Preview and the public survey use the same renderer and validation definitions.

Charts and counts come from backend queries using active filters, with accessible labels and a table alternative. Use consistent date ranges, time zones and units. Paginate large tables on the server; exports must use the same filter definition and enforce authorization.

## Resource application and verification

See `DESIGN_RESOURCES.md` for the ten-source review and exact revisions. Adopt Hallmark/Taste's task-first app density, UI UX Pro Max's accessibility/form guidance, Modern Web Design's performance/progressive enhancement, Cinematic UI's view-state continuity, PencilPlaybook's target/focus discipline, and GSAP's restrained motion/performance principles. Do not copy prototype fixture data, replace the framework, or follow conflicting decorative rules.

Applied across the current administrator/respondent/login pages: shared logo-based tokens, neutral working surfaces, responsive navigation/tables, visible pending/empty/error states, accessible dialogs, dark mode and purposeful native transitions. The form experience begins with From/To reporting dates and then navigates dynamic sections. Original-format Excel exports preserve workbook formatting separately from report-table exports. See the implementation plan for advanced features still pending.

Validate at 390, 768, 1024 and 1440px, with keyboard-only navigation, long Burmese labels, no records, denied access, failed requests and reduced motion. Do not claim a full design audit from authentication tests alone.
