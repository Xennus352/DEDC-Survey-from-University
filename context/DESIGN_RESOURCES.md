# Design Resource Review

Reviewed the ten requested GitHub repositories, their READMEs, file trees and relevant skill definitions on 2026-11-02. Exact revisions and declared licenses are recorded in `design-resource-revisions.json`. The selected resources declare MIT licensing. Installation used Codex's trusted skill-installer download helper, not repository install scripts. Project-level skills live in `.agents/skills/`; new skills become discoverable on the next turn.

| Resource | Type / supported environment | Integration decision |
| --- | --- | --- |
| [Hallmark](https://github.com/Nutlope/hallmark) | Agent skill; Codex, Claude Code, Cursor, OpenCode | Installed `hallmark` with references/scripts. Use app-mode hierarchy, tokens, focus and honest data; its browser lint needs Chrome/Puppeteer and has not been run. |
| [Open Design](https://github.com/nexu-io/open-design) | Standalone design workspace, daemon/MCP, design templates; supports Codex | Inspected dashboard template and runtime integration. Adapt layout/state/token principles; do not install a separate daemon or its prototype template, which requests invented metrics and standalone HTML artifacts. Existing application and real data take precedence. |
| [UI UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Agent skill with local Python search/data; Codex and other agents | Installed `ui-ux-pro-max`, including references, CSV catalogs and search dependencies. Verified local search. The broad design-system query suggested marketing/video patterns; rejected that mismatch and reran focused dashboard/style and keyboard/form searches. |
| [Taste Skill](https://github.com/Leonxlnx/taste-skill) | Agent skill; explicit Codex support; Node/browser tooling | Installed `taste-skill`. Adopt app-screen density, restrained colors, aligned numbers and responsive navigation. Its Chrome-based inspection scripts have not been run. Do not apply marketing-page rules where the product specification requests table borders or cards. |
| [GSAP Skills](https://github.com/greensock/gsap-skills) | Official agent skills; Codex and others; vanilla/framework references | Installed core, performance, timeline, utilities, plugins, ScrollTrigger and frameworks guidance. React-specific skill excluded because this app is not React. No GSAP runtime or decorative animation added. |
| [PencilPlaybook](https://github.com/stevembarclay/pencilplaybook) | Pencil.dev workflows and Claude Code skill | Not installed as an active workflow: no Pencil canvas/MCP is available here. Adapt clear hover/focus, minimum touch targets and consistent design tokens into the application design system. |
| [DESIGN.md Chrome](https://github.com/bergside/design-md-chrome) | Chrome extension that generates DESIGN.md / SKILL.md; output usable by Codex | Not an installable agent skill; requires manual browser-extension installation. Adapt its mission/foundations/accessibility/component/state quality-gate documentation structure. No browser profile modified. |
| [Claude Design Skills](https://github.com/freshtechbro/claudedesignskills) | Agent-skill collection for Claude and compatible skill loaders | Installed the framework-neutral `modern-web-design` skill with references. Excluded unrelated React, 3D, duplicated bundles and skill-creator copies. Apply performance, semantic markup and progressive enhancement. |
| [UI Landing Page Generator](https://github.com/felix-huber/ui-landingpage-generator-skill) | Gemini CLI + Claude Code shell pipeline | Not installed as a working pipeline: requires separate authenticated CLIs and targets standalone marketing pages. Adopt context-first review and consistent typography; reject dramatic animation/gradient recommendations that conflict with the admin specification. No external AI pipeline was executed. |
| [Cinematic UI](https://github.com/akseolabs-seo/cinematic-ui) | Agent skill with Codex-compatible app mode and browser tooling | Installed `cinematic-ui` with app-mode references. Use task continuity, permission/error/empty states and quiet working surfaces. Bundled fixtures, standalone router and 3D runtime are not used in production. Its own full screening suite has not been run. |

## What was actually applied so far

The authentication UI now disables duplicate logout attempts, exposes a pending state, focuses an accessible error on failed logout, keeps the working session after a failed request, and revalidates private views on browser history and tab activation. These apply the resources' interaction/state principles to working code. Browser checks cover both successful and failed logout.

The implementation now applies those principles to the responsive administrator shell, login, dynamic builder/preview, workbook review, reports, users and audit pages. The supplied local logo defines navy/gold accents; real data drives every view. Native transitions, visible focus, reduced-motion handling, inline errors, pending states, responsive tables and light/dark tokens are implemented. Ten administrator routes passed Firefox viewport checks. `DESIGN_SYSTEM.md` records the shared rules. This does not claim that third-party visual-lint suites were run.

## Verification and dependencies

- Python 3 and Node 24 are available. Installed skill definitions and referenced local search/catalog files were checked.
- UI UX Pro Max search runs without extra packages. Reproduce:
  `python3 .agents/skills/ui-ux-pro-max/scripts/search.py 'enterprise dashboard' --domain style --max-results 1`.
- The application still has no Node build dependency. GSAP runtime is intentionally deferred until a useful interaction is implemented.
- Browser auth checks use Playwright/Firefox on a disposable database. This is distinct from running each design repository's Chrome/Puppeteer visual lint.
- No third-party installer, generated fixture, external service credential, MCP daemon, or browser extension was added to the application's runtime.
