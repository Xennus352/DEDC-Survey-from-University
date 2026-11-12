---
name: DEDC administration
description: Myanmar-first survey operations workspace for Ministry administrators.
colors:
  primary: "#1556a6"
  primary-hover: "#10447f"
  primary-soft: "#eaf3ff"
  on-primary: "#ffffff"
  sidebar: "#102e50"
  sidebar-hover: "#1b426d"
  sidebar-active: "#2763a2"
  sidebar-text: "#c4d5e8"
  canvas: "#f4f7fb"
  surface: "#ffffff"
  surface-hover: "#eef4fb"
  border: "#e1e8f1"
  ink: "#172b45"
  muted: "#596b80"
  success: "#256343"
  success-soft: "#edf5f0"
  danger: "#a32c39"
  danger-soft: "#fbeff0"
  status-published: "#2c8c6b"
  status-draft: "#f59e0b"
  status-archived: "#ef4444"
  dark-canvas: "#111b29"
  dark-surface: "#1b293a"
  dark-surface-hover: "#25374c"
  dark-border: "#354b63"
  dark-ink: "#eef4fb"
  dark-muted: "#b1c0d0"
  dark-primary: "#92c1fa"
  dark-primary-hover: "#bedbff"
  dark-primary-soft: "#243951"
  dark-on-primary: "#102943"
typography:
  headline:
    fontFamily: "DM Sans, Noto Sans Myanmar, system-ui, sans-serif"
    fontSize: "clamp(24px, 2.2vw, 29px)"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: "DM Sans, Noto Sans Myanmar, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 600
    lineHeight: 1.5
  body:
    fontFamily: "DM Sans, Noto Sans Myanmar, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "DM Sans, Noto Sans Myanmar, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.5
rounded:
  control: "9px"
  navigation: "10px"
  card: "14px"
  pill: "999px"
spacing:
  compact: "8px"
  field: "12px"
  card-gap: "14px"
  panel: "16px"
  section: "24px"
  content: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
    height: "42px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 14px"
    height: "42px"
  field:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
    height: "42px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
---

# Design System: DEDC administration

## Overview

**Creative North Star: "The Civic Survey Register"**

A focused government survey workspace. The Ministry logo anchors a navy navigation rail; a pale blue-gray canvas holds white working surfaces, dark navy type, DEDC blue actions, and thin borders. Myanmar is the first reading language, with Latin type for mixed content and numerical data.

**Key Characteristics:**

- Pending review leads in a solid blue KPI; submissions follow in pale blue, with forms and questions as quieter totals.
- Real counts and statuses lead; color clarifies their state.
- Rounded, mostly flat panels keep dense records readable.

## Colors

The authenticated dashboard uses DEDC blue for actions and emphasis, navy for navigation and text, and a pale blue-gray field behind white panels.

### Primary

- **DEDC blue:** filled primary buttons, chart line, selected data points, focus treatment, and the leading review KPI.
- **Deep blue:** primary button hover.
- **Pale blue:** supporting submission KPI, icon tiles, hover surfaces, and selected supporting controls.
- **Navy rail:** the sidebar carries the Ministry logo and uses a brighter blue active route with white text.

### Neutral

- **Blue-gray canvas:** the page field behind working panels.
- **White surface:** cards, form fields, tables, and the translucent sticky header.
- **Navy ink and slate muted text:** heading and body contrast, then secondary descriptions.
- **Quiet blue-gray border:** divides cards, table rows, inputs, and navigation without heavy shadows.
- **Dark mode:** the same roles switch to the recorded dark canvas, surfaces, border, ink, and light blue accent through `data-theme="dark"`.

### State accents

- **Success green:** approved or published status.
- **Amber draft and red archived:** distinct overview ring segments and legend dots; each status also has a text label and count.
- **Danger red:** destructive actions and error surfaces.

**The Evidence Color Rule.** Use chart and state colors only for records and statuses returned by the application. Never use decorative data as content.

## Typography

**Display Font:** DM Sans with Noto Sans Myanmar, then system sans serif fallbacks.  
**Body Font:** DM Sans with Noto Sans Myanmar, then system sans serif fallbacks.

The dashboard loads DM Sans and Noto Sans Myanmar, including a bundled Myanmar font. The type hierarchy is compact for long Burmese labels and dense administrative tables.

### Hierarchy

- **Headline:** page titles use the responsive headline token. The overview title grows to `clamp(25px, 2.3vw, 32px)` at weight 700.
- **Title:** panel headings use the title token; overview panel headings tighten to 15px.
- **Body:** operational copy uses the body token; descriptions and table text step down to 12–13px where the interface requires density.
- **Label:** controls, metadata, table headers, and status chips use the label token or its nearby 11px small-text treatment.
- **Numerals:** KPI values and chart counts use tabular numerals. The two leading overview values grow to `clamp(38px, 3.5vw, 48px)`; supporting values are 30px.

**The Myanmar First Rule.** Put Burmese labels and task descriptions first; preserve room for their full wording before tightening type or truncating it.

## Layout

On desktop, a 252px sticky navy sidebar sits beside a flexible content column. A 64px translucent header stays at the top; the main area has a 1600px maximum width and horizontal padding that grows from 20px to 40px. The overview begins with four separate KPI cards: two wider operational totals, then two smaller supporting totals. A slim quick-action row follows. The wide trend panel sits beside a narrower status panel; recent submissions, forms, and activity continue below.

At 1080px and below, the sidebar becomes an off-canvas navigation drawer. Below 1200px, the overview KPIs become a two-column grid. At 800px and below, the overview's main and lower columns stack. At 600px and below, content padding is 16px, actions become two equal columns, and the topbar hides its date. Tables keep their minimum width inside horizontal scroll containers rather than squeezing record labels.

Use the recorded compact, field, card-gap, panel, section, and content spacing steps to keep repeated groups consistent. Panel bodies commonly use 16–24px of padding; compact mobile overview panels use 12px.

## Elevation & Depth

Cards, sidebar, and primary working panels are flat at rest. Their border and the difference between the pale canvas and white surfaces establish depth. The sticky header uses a translucent surface and 8px blur. Shadows appear for temporary layers such as the account menu and dialog; the selected trend control has a slight inset shadow.

**The Flat Work Surface Rule.** Keep routine panels and navigation flat; reserve shadow for temporary layers or control state.

## Shapes

Panels and KPI cards use gently rounded 14px corners. Buttons and fields use 9px corners, while sidebar links use 10px. Avatars, donut charts, and status dots are circular. Thin strokes and rounded corners give controls a consistent, restrained form without ornamental outlines.

## Components

### Buttons

- **Primary:** DEDC blue fill with white text, 42px minimum height, and the control radius; hover deepens the blue.
- **Secondary:** white with a quiet border and navy text; hover uses the pale blue surface tint.
- **Focus and motion:** `:focus-visible` has a clear blue outline. Small hover lifts and 140–160ms transitions are suppressed under reduced motion.

### Cards / Containers

- **Overview KPIs:** pending review has a solid blue fill; submissions have a pale blue fill; forms and questions remain white. All four have a bordered card, small icon tile, label, tabular number, and explanatory line. Hover changes the border and lifts slightly without a shadow.
- **Panels:** white, bordered, 14px corners, and no resting shadow. A divided header separates title from records or charts.

### Inputs / Fields

- **Style:** white fill, thin border, 9px corners, and compact inset padding. Header search is a compact icon button that opens workspace search.
- **Focus:** preserve the visible blue focus outline. Error and disabled states stay legible without relying on color alone.

### Navigation

- **Sidebar:** navy rail with the Ministry logo, Burmese labels, pale default links, and a brighter blue active item with white text. The active route is also marked by `aria-current="page"`.
- **Responsive state:** the rail opens as a drawer under the desktop breakpoint; a backdrop closes it. The current route and keyboard focus remain distinguishable.

### Charts and statuses

- **Trend:** a blue line and pale area over thin grid lines. Day, week, and month controls change grouping of the same API trend, and the selected point reads out its real date and count.
- **Status:** a ring chart pairs green, amber, and red form-state segments with a count and labeled legend. Keep the legend even when the ring has no data.
- **Chips:** compact rounded status badges pair semantic tint with readable text.

## Do's and Don'ts

### Do:

- **Do** use the Ministry logo and Myanmar labels in authenticated navigation.
- **Do** let pending review and submissions lead overview hierarchy, with forms and questions in supporting roles.
- **Do** read dashboard metrics, trend points, review states, and recent records from protected application data; show an honest empty state when none exists.
- **Do** preserve visible keyboard focus, labeled chart values, and reduced-motion behavior.

### Don't:

- **Don't** invent weather, alerts, submission counts, or activity to fill an empty dashboard.
- **Don't** show a language switch unless it changes the actual interface language and announces its state truthfully.
- **Don't** replace DEDC blue and the navy navigation rail with mint styling on authenticated surfaces.
