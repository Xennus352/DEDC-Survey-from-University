# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

DEDC/Ministry administrators are the primary day-to-day users. They manage survey forms and their lifecycle. Respondents use published surveys to submit information.

## Product Purpose

DEDC supports the survey lifecycle: prepare and publish forms, collect responses, and review survey data and reports.

## Positioning

DEDC combines versioned survey administration with compatibility for the Ministry's existing ten-table database and supplied Excel workbook. It preserves original workbook content separately from new survey responses.

## Operating Context

Administrators create or import forms, edit and preview drafts, publish forms, manage responses, and use reports and exports. Respondents enter From/To reporting dates before completing a published survey. Burmese labels and Myanmar text are part of normal use, with English fallback in supported areas.

## Capabilities and Constraints

- The application is built with Python 3.12+, FastAPI, SQLAlchemy, Jinja2, and plain JavaScript.
- Survey forms use versioned drafts. Published versions are immutable; changes require a new draft. Archiving a form stops new responses while preserving its history.
- Excel imports create drafts. Original workbook answers remain separate from new submissions. Original-format exports preserve the supplied workbook layout and styles.
- Filtered reports support CSV, XLSX, and PDF exports.
- Preserve the existing ten-table database without adding schema objects or requiring data conversion.
- Do not treat historical workbook answers as defaults, question choices, or new submission data.

## Brand Commitments

Keep the DEDC and Ministry identity and Burmese labels. The existing Ministry logo is `static/img/logo.png`; the bundled Myanmar font is `static/fonts/NotoSansMyanmar-Regular.ttf`. Do not invent an expansion of “DEDC.”

## Evidence on Hand

- Ministry logo: `static/img/logo.png`.
- Myanmar font: `static/fonts/NotoSansMyanmar-Regular.ttf`.
- Workbook structure and preservation requirements: `context/WORKBOOK_AUDIT.md` and `README.md`.
- Existing product workflows and constraints: `README.md`, `docs/admin-portal.md`, and `context/IMPLEMENTATION_REPORT.md`.

## Product Principles

- Preserve the meaning and structure of the supplied workbook and legacy database.
- Keep original historical answers distinct from newly submitted responses.
- Make form publication explicit and preserve published versions as history.
- Keep survey administration usable with Burmese-language content.
