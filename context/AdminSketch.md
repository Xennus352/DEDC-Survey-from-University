# MASTER CODEX PROMPT — Complete Admin Dashboard Transformation & Dynamic Survey Management System

Act as a Senior Full-Stack Engineer, UI/UX Designer, Database Architect, Security Engineer, and Product Designer.

I want you to completely audit, repair, redesign, and upgrade my existing application into a production-ready, modern survey management platform.

Do not just create mockups or static UI. Every feature must work with the actual backend and database.

**IMPORTANT: First inspect the entire existing repository before making changes. Understand the existing architecture, frontend, backend, authentication, database schema, API endpoints, and current implementation. Preserve working functionality and improve the existing project rather than unnecessarily rebuilding everything.**

---

# 1. CRITICAL AUTHENTICATION AND LOGOUT BUG

There is a serious authentication issue.

Current behavior:
- I log in as an administrator.
- I enter the admin dashboard.
- I click Logout.
- After logging out, I can still access `/dashboard/*` routes.
- The application does not properly prevent unauthenticated users from accessing protected admin pages.

Fix this completely.

Requirements:

1. Implement proper authentication state management.
2. When an administrator clicks Logout:
   - Immediately invalidate the frontend authentication state.
   - Revoke or invalidate the backend session/token where applicable.
   - Remove authentication credentials securely.
   - Clear user-specific cached data.
   - Disconnect authenticated WebSocket connections.
   - Redirect to the login page.
3. Protect ALL `/dashboard/*` routes.
4. Prevent users from accessing dashboard pages by manually entering URLs.
5. Implement proper frontend route guards.
6. Implement backend authentication and authorization middleware/dependencies.
7. Never rely only on frontend route protection.
8. Verify authentication on every protected API request.
9. Prevent browser back-button navigation from restoring an authenticated dashboard after logout.
10. Handle expired access tokens and refresh tokens correctly.
11. Implement role-based access control if multiple administrator roles exist.
12. Ensure unauthorized users receive appropriate 401 or 403 responses.

Security requirements:
- Do not store sensitive authentication tokens in insecure locations.
- Prefer secure HttpOnly cookies where compatible with the existing architecture.
- Implement appropriate CSRF protection when using cookie authentication.
- Never expose passwords, secrets, or authentication tokens in frontend code or logs.

**Acceptance tests:**
- Login → dashboard works.
- Logout → redirects to login.
- Manually entering `/dashboard` after logout → redirects to login.
- Manually entering `/dashboard/forms` after logout → redirects to login.
- Refreshing a protected page without authentication → redirects to login.
- Expired authentication → redirects to login.
- Authenticated administrator → can access authorized pages.
- Normal user → cannot access administrator APIs.

Do not consider this task complete until these scenarios have been tested.

---

# 2. INSTALL AND APPLY ALL DESIGN SKILLS

I want you to investigate, install, and use the following design resources to improve the application.

Repositories:

1. https://github.com/Nutlope/hallmark.git
2. https://github.com/nexu-io/open-design
3. https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git
4. https://github.com/Leonxlnx/taste-skill.git
5. https://github.com/greensock/gsap-skills.git
6. https://github.com/stevembarclay/pencilplaybook.git
7. https://github.com/bergside/design-md-chrome.git
8. https://github.com/freshtechbro/claudedesignskills.git
9. https://github.com/felix-huber/ui-landingpage-generator-skill.git
10. https://github.com/akseolabs-seo/cinematic-ui.git

Installation instructions:

- Inspect each repository and its README.
- Identify whether it provides an agent skill, design system, component library, MCP integration, or another development tool.
- Identify its supported agent environments.
- Install compatible skills in the appropriate project-level or global skill directories supported by the installed Codex environment.
- Do not assume every repository is a Codex-compatible skill.
- Adapt compatible resources for Codex where necessary.
- Resolve dependencies and verify installations.
- Do not blindly execute untrusted installation scripts.
- Avoid duplicate skills and conflicting configurations.
- Do not replace the existing project's framework just to accommodate a design tool.

**Most importantly: Do not just install the skills. ACTUALLY APPLY THEIR DESIGN PRINCIPLES AND CAPABILITIES throughout the application.**

Use them to improve:
- Visual hierarchy.
- Layout composition.
- Typography.
- Color systems.
- Spacing.
- Component consistency.
- Data visualization.
- Responsive design.
- Animation.
- Interaction design.
- Accessibility.
- Micro-interactions.
- Form-builder usability.

Use GSAP only where animation provides genuine value. Keep animations smooth and lightweight.

After installation, document which resources were successfully installed, adapted, or could not be integrated and why.

---

# 3. COMPLETE ADMIN DASHBOARD REDESIGN

The current admin design is ugly and needs a complete professional redesign.

I want a modern, minimal, powerful, premium administrative interface.

Design inspiration:
- Modern SaaS dashboards.
- Linear.
- Stripe Dashboard.
- Vercel Dashboard.
- Notion.
- Modern enterprise analytics platforms.
- Apple-inspired interaction design.

Do not simply copy these products. Create a cohesive design system.

### Design direction

Visual characteristics:
- Minimal and sophisticated.
- Clean typography.
- Excellent whitespace.
- Beautiful card compositions.
- Subtle borders.
- Soft shadows.
- Refined surfaces.
- Carefully designed hover states.
- Smooth transitions.
- Responsive layouts.
- Consistent iconography.
- Professional charts and tables.

Avoid:
- Excessive gradients.
- Excessive glass effects.
- Too many colorful cards.
- Oversized headings.
- Unnecessary animations.
- Huge empty spaces.
- Generic AI-generated dashboard appearance.
- Cluttered sidebars.
- Inconsistent spacing.
- Decorative elements that reduce usability.

### Layout

Create a professional dashboard shell:

**Sidebar**
- Overview
- Survey Forms
- Question Bank
- Form Submissions
- Reports & Analytics
- Users & Enumerators
- Data Management
- Settings

Use collapsible sidebar navigation with clear active states.

**Top navigation**
- Breadcrumb navigation.
- Current page title.
- Global search.
- Notifications.
- Administrator profile.
- Logout.

**Main content**
- Responsive page layouts.
- Consistent spacing.
- Professional typography.
- Reusable components.
- Skeleton loading states.
- Empty states.
- Error states.
- Toast notifications.
- Confirmation dialogs.

Implement light and dark themes if appropriate for the existing architecture.

All pages must use the same design system.

---

# 4. DYNAMIC SURVEY FORM BUILDER — MOST IMPORTANT FEATURE

I want the administrator to have FULL CONTROL over survey questions and forms.

The administrator must be able to create, edit, delete, organize, publish, and manage survey questions dynamically.

Do not hardcode the survey questions into React or Flutter.

Questions, sections, options, validation rules, and form configurations must come from the database.

### 4.1 Form Management

Create a complete Form Management module.

Administrators can:

- Create a new survey form.
- Edit an existing draft.
- Duplicate an existing form.
- Delete an unpublished form.
- Archive old forms.
- Change form title.
- Add descriptions and instructions.
- Configure language.
- Configure form status.
- Configure form availability.
- Set start and end dates.
- Manage form versions.
- Preview the form.
- Publish a form.
- Unpublish or archive a form according to submission/version rules.

Form statuses:
- Draft
- Published
- Archived

Published forms must have versioning.

Do not silently modify published form versions that already have submissions.

Use immutable published versions and create a new draft/version for subsequent changes.

### 4.2 Dynamic Section Builder

Administrators must be able to:

- Add sections.
- Edit sections.
- Delete sections.
- Reorder sections using drag and drop.
- Duplicate sections.
- Enable or disable sections.
- Add descriptions.
- Configure section-level conditions.
- Organize questions inside sections.

### 4.3 Dynamic Question Builder

Create a professional question builder.

Supported question types:

1. Short text.
2. Long text.
3. Number.
4. Decimal.
5. Single choice.
6. Multiple choice.
7. Dropdown.
8. Radio buttons.
9. Checkboxes.
10. Date.
11. Time.
12. Date and time.
13. Yes/No.
14. Image upload.
15. File upload.
16. Location/GPS.
17. Repeating group.
18. Calculated field.
19. Read-only/information field.

Each question must support:

- Question title.
- Burmese question title.
- English question title.
- Unique question key.
- Description/help text.
- Placeholder.
- Required/optional.
- Default value.
- Validation rules.
- Minimum value.
- Maximum value.
- Minimum length.
- Maximum length.
- Custom validation.
- Display order.
- Visibility conditions.
- Conditional logic.
- Answer options.
- Other-specify option.
- Database mapping.
- Enabled/disabled status.

For choice-based questions, administrators must be able to dynamically manage options.

For example:

Question: What type of livestock do you own?

Options:
- Cattle
- Buffalo
- Goat
- Sheep
- Pig
- Other

Administrators can add, edit, remove, and reorder those options without changing application source code.

### 4.4 Conditional Logic

Implement a proper conditional question engine.

Examples:

IF question A = Yes:
    Show question B.

IF question A = No:
    Hide question B.

IF livestock_count > 0:
    Show livestock details.

Support:
- Equals.
- Not equals.
- Greater than.
- Less than.
- Contains.
- Is empty.
- Is not empty.
- AND conditions.
- OR conditions.

Conditions must be evaluated dynamically by the form renderer.

### 4.5 Database-Driven Architecture

Design a normalized and maintainable database schema.

Consider entities such as:

- survey_forms
- survey_form_versions
- survey_sections
- survey_questions
- survey_question_options
- survey_question_rules
- survey_submissions
- survey_answers
- survey_answer_files
- survey_users
- audit_logs

Adapt these entities to the actual existing database rather than creating duplicate tables unnecessarily.

Requirements:
- Use proper foreign keys.
- Add appropriate indexes.
- Use database transactions.
- Preserve historical submissions.
- Implement migrations.
- Validate data on the backend.
- Use JSON only where it is genuinely appropriate for flexible configuration.
- Avoid an unstructured single JSON column for the entire application.

The frontend must retrieve the published form schema through API endpoints.

Example API design:

GET /api/forms
GET /api/forms/{id}
GET /api/forms/{id}/schema
POST /api/forms
PUT /api/forms/{id}
DELETE /api/forms/{id}

POST /api/forms/{id}/sections
PUT /api/sections/{id}
DELETE /api/sections/{id}

POST /api/questions
PUT /api/questions/{id}
DELETE /api/questions/{id}

POST /api/forms/{id}/publish

GET /api/forms/{id}/versions

Adapt endpoint naming and response structures to the existing backend conventions.

---

# 5. USE MY EXCEL FILE AS THE QUESTION FORMAT REFERENCE

This is extremely important.

Sample Excel file:

`/home/kazue/Downloads/Telegram Desktop/DEDC_Survey_Form_University_of_Computer_Studies_Taungoo_27875ea2.xlsx`

Inspect this workbook thoroughly.

Do not invent a new question structure without examining the actual Excel file.

Requirements:

1. Read every worksheet.
2. Identify all sections.
3. Extract question numbers.
4. Extract Burmese question labels.
5. Extract English question labels, if available.
6. Identify question types.
7. Identify answer options.
8. Identify tables and repeating structures.
9. Identify dependent questions.
10. Identify required fields.
11. Identify validation rules.
12. Identify row and column relationships.
13. Preserve the original question order.
14. Preserve the original wording.
15. Identify any special formatting that communicates question relationships.

Build an Excel import feature for administrators.

The administrator should be able to upload an Excel workbook and import the questions into a draft form.

Import process:

Excel upload
    ↓
Workbook parsing
    ↓
Worksheet detection
    ↓
Question and section extraction
    ↓
Question type detection
    ↓
Option and dependency extraction
    ↓
Import preview
    ↓
Validation and error reporting
    ↓
Administrator confirmation
    ↓
Save to database as draft

The import preview must show:
- Detected sections.
- Total questions.
- Detected question types.
- Options.
- Missing information.
- Duplicate question identifiers.
- Invalid structures.
- Import warnings.

Allow administrators to manually correct the imported structure before saving.

Do not automatically publish imported forms.

If the Excel workbook cannot be accessed, clearly report that and request access to the file. Do not pretend it was inspected.

---

# 6. PROFESSIONAL FORM PREVIEW

The administrator should be able to preview the actual survey experience before publishing.

Create:
- Desktop preview.
- Tablet preview.
- Mobile preview.
- Burmese preview.
- English preview.

The preview must use the same dynamic form renderer used by the actual survey application.

Do not create a separate hardcoded preview implementation.

The preview must reflect:
- Question ordering.
- Required fields.
- Options.
- Conditional logic.
- Validation.
- Sections.
- Repeating groups.
- Form navigation.

---

# 7. REPORTS AND ANALYTICS DASHBOARD

Administrators must be able to view all survey reports and filter the data comprehensively.

Build a dedicated Reports & Analytics module.

### 7.1 Overview Analytics

Display:

- Total submissions.
- Completed submissions.
- In-progress submissions.
- Rejected submissions, if applicable.
- Total enumerators.
- Active enumerators.
- Submissions by day.
- Submissions by week.
- Submissions by month.
- Completion percentage.
- Average completion time.

All metrics must be calculated from actual database records.

No fake statistics or hardcoded charts.

### 7.2 Advanced Report Filtering

Implement comprehensive filters:

**Date filters**
- Today.
- Yesterday.
- Last 7 days.
- Last 30 days.
- This month.
- Previous month.
- Custom date range.

**Form filters**
- Form name.
- Form version.
- Form status.

**Submission filters**
- Completed.
- In progress.
- Pending review.
- Approved.
- Rejected.

**User filters**
- Enumerator.
- Administrator.
- User ID.

**Location filters**
- Region/State.
- District.
- Township.
- Village tract.
- Village.

The location filters should be hierarchical and dependent on one another where the database supports that structure.

**Question filters**

Allow administrators to filter responses based on selected questions and answers.

For example:

- Find households with more than 10 cattle.
- Find submissions where the answer to a particular question is Yes.
- Find submissions from a specific township.
- Find records submitted by a particular enumerator.

Support combining multiple filters.

### 7.3 Reports Table

Build a powerful data table with:

- Search.
- Sorting.
- Pagination.
- Column visibility.
- Column resizing if appropriate.
- Filter chips.
- Row selection.
- Bulk actions.
- Submission detail view.
- Export functionality.

Clicking a submission should open a detailed view of all answers, grouped by their original survey sections.

### 7.4 Data Visualization

Create professional charts:

- Submission trends.
- Geographic distribution.
- Completion rates.
- Question response distribution.
- Livestock population distribution where applicable.
- Enumerator performance.

Use appropriate chart types.

Charts must be interactive and respond to the selected filters.

### 7.5 Export

Support:

- Excel export.
- CSV export.
- PDF report export.

Exported reports must respect active filters.

Include:
- Form title.
- Form version.
- Date range.
- Applied filters.
- Export timestamp.
- Relevant summary statistics.

For sensitive survey data, enforce backend authorization and export permissions.

---

# 8. USER AND ENUMERATOR MANAGEMENT

Build a professional user management module.

Administrators should be able to:

- View all users.
- Search users.
- Filter users.
- Create users.
- Edit user information.
- Activate/deactivate accounts.
- Assign roles.
- View individual submission history.
- View enumerator performance.
- Export user lists.

Implement role-based permissions in the backend.

Do not allow administrators to perform unauthorized actions.

---

# 9. AUDIT LOGGING

Implement an audit trail for important administrator actions.

Track:
- Form creation.
- Form editing.
- Question creation.
- Question modification.
- Question deletion.
- Form publishing.
- Form archiving.
- User management.
- Report exports.
- Authentication events.

Store:
- Actor ID.
- Action.
- Target entity.
- Timestamp.
- Relevant before/after changes where appropriate.

Do not store passwords, tokens, or other secrets in audit logs.

Provide an audit log page with search and filters.

---

# 10. BACKEND AND API QUALITY

Inspect the current backend before implementing anything.

If the existing backend is FastAPI, maintain that architecture.

Requirements:
- Clean separation of routers.
- Services.
- Database models.
- Pydantic schemas.
- Authentication dependencies.
- Authorization dependencies.
- Centralized exception handling.
- Request validation.
- Pagination.
- Database transactions.
- API documentation.
- Appropriate HTTP status codes.

Implement database migrations using the project's existing migration system or an appropriate migration tool.

Do not break existing mobile app APIs.

If API changes are necessary, preserve backward compatibility where possible.

---

# 11. FRONTEND ENGINEERING

Follow the existing frontend framework.

Build reusable components such as:

- DashboardLayout
- Sidebar
- Topbar
- StatCard
- DataTable
- FilterPanel
- FormBuilder
- SectionEditor
- QuestionEditor
- QuestionTypeSelector
- ConditionalLogicBuilder
- FormPreview
- SubmissionDetails
- AnalyticsChart
- ExportDialog
- ConfirmDialog

Requirements:
- Type-safe API integration where applicable.
- Centralized API client.
- Proper authentication state.
- Loading states.
- Error handling.
- Optimistic updates only where safe.
- Responsive layouts.
- Accessible keyboard interactions.
- Proper form validation.

Avoid massive components and duplicated business logic.

---

# 12. PERFORMANCE AND RESPONSIVENESS

The application must work smoothly on:

- Desktop.
- Laptop.
- Tablet.
- Mobile.

Optimize:
- Large submission tables.
- Report queries.
- Question rendering.
- Excel imports.
- Chart rendering.
- API requests.

Implement server-side pagination and filtering for large datasets.

Avoid loading all survey submissions into the browser.

---

# 13. IMPLEMENTATION WORKFLOW

Follow this order.

**Phase 1 — Repository Audit**
- Inspect the complete project.
- Identify frameworks and dependencies.
- Inspect backend and database.
- Inspect current authentication.
- Identify existing bugs.
- Inspect the Excel workbook.
- Document the current architecture.

**Phase 2 — Design Skills**
- Inspect all 10 GitHub repositories.
- Install compatible resources.
- Verify their installation.
- Establish a unified design system.

**Phase 3 — Authentication Repair**
- Fix logout.
- Fix route protection.
- Fix backend authorization.
- Test all authentication scenarios.

**Phase 4 — Database and Backend**
- Design migrations.
- Implement dynamic form models.
- Implement CRUD APIs.
- Implement form versioning.
- Implement submission and reporting APIs.

**Phase 5 — Admin Dashboard Redesign**
- Build the dashboard shell.
- Implement navigation.
- Build reusable UI components.
- Apply the design system to every page.

**Phase 6 — Dynamic Form Builder**
- Implement form management.
- Implement section management.
- Implement question management.
- Implement conditional logic.
- Implement Excel import.
- Implement preview and publishing.

**Phase 7 — Reports**
- Implement analytics.
- Implement advanced filtering.
- Implement submission details.
- Implement exports.

**Phase 8 — Quality Assurance**
- Run database migrations.
- Run backend tests.
- Run frontend tests.
- Test authentication.
- Test every CRUD operation.
- Test Excel imports.
- Test form publishing.
- Test reports and exports.
- Test responsive layouts.
- Fix all errors.

---

# 14. STRICT DEVELOPMENT RULES

1. Do not build a static demonstration.
2. Do not use fake data for production features.
3. Do not hardcode survey questions.
4. Do not hardcode report statistics.
5. Do not bypass backend authorization.
6. Do not break existing Flutter/mobile APIs.
7. Do not delete existing database records.
8. Do not unnecessarily replace the existing framework.
9. Do not introduce duplicate database entities.
10. Do not leave unfinished buttons or placeholder pages.
11. Do not claim a feature works without testing it.
12. Do not sacrifice functionality for visual appearance.
13. Keep the architecture maintainable and extensible.
14. Use database migrations for schema changes.
15. Preserve published survey versions and historical responses.
16. Make all administrator actions actually work.

If an existing feature conflicts with a new requirement, inspect its dependencies and implement a backward-compatible solution wherever possible.

---

# 15. FINAL ACCEPTANCE CRITERIA

The project is complete only when:

- Logout completely prevents access to `/dashboard/*`.
- Authentication and authorization work correctly.
- The entire admin interface has a professional modern redesign.
- All 10 design repositories have been investigated and compatible resources applied.
- Administrators can create forms dynamically.
- Administrators can create, edit, delete, reorder, and manage questions.
- Questions and options are stored in the database.
- Conditional logic works.
- Excel import works with the supplied workbook structure.
- The administrator can preview forms.
- Published forms have immutable versions.
- Existing submissions remain accessible.
- Administrators can view comprehensive reports.
- Advanced report filters work against real database data.
- Excel, CSV, and PDF exports work.
- User management works.
- Audit logging works.
- Existing mobile app functionality remains operational.
- No critical frontend or backend errors remain.

At the end, provide a detailed implementation report:

1. What was broken.
2. What was fixed.
3. What design resources were installed.
4. What design resources were applied.
5. Database changes and migrations.
6. New API endpoints.
7. New frontend pages and components.
8. Excel import results.
9. Authentication test results.
10. CRUD test results.
11. Reporting and export test results.
12. Remaining issues, if any.

**FINAL GOAL: Transform the existing application into a production-ready, modern, database-driven survey administration platform where administrators have complete control over survey forms, questions, submissions, users, and reports.**