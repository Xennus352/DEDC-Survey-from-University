---
version: 1
slug: "templates-admin-layout-html"
primary_target: "templates/admin/layout.html"
related_targets: ["static/css/admin/dashboard.css","static/js/admin/workspace.js"]
---

# DEDC administration dashboard

Mode: Operate. Audience: Ministry administrators managing survey forms, submissions, users, and reports. Scope: all authenticated dashboard routes, preserving backend behavior and existing links.

## Direction contract

THESIS: A focused survey operations workspace. Pending review and submission totals lead, with forms and questions supporting them. Real work stays visible without stacking equal-weight cards.

OWN-WORLD: The original DEDC blue identity: a navy sidebar, pale blue-gray canvas, white working surfaces, blue actions, dark navy text, and semantic colors for review status. The Ministry logo anchors navigation. Rounded panels, clean Myanmar type, thin rules, and a compact sticky header form one system.

STORY: An administrator sees the pending review count first, checks submissions and the 30-day trend, opens a record, and moves directly to forms, people, or reports. Search remains available through a compact button and Ctrl+K. Every number and status comes from the protected API.

FIRST VIEWPORT: Fixed navy sidebar and compact header without a search field; a short task heading with date and real actions; two prominent operational totals, two supporting totals, a slim quick-action row, and a wide trend chart beside the review-status donut. Recent submissions and activity follow. Tablet and phone stack without page overflow.

FORM: Civic survey register, candidate 3 of seven grounded directions; seed:d7729d37e8deccbb. Signature move: a selected trend point reveals its real date and count while the adjacent review state stays fixed and legible.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
