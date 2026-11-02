import { api } from "./api.js";
import {
  escape as e,
  badge,
  button,
  empty,
  date,
  table,
  setContent,
  describe,
  actions,
  toast,
  modal,
  errorMessage,
  busy,
  pagination,
  bindFilters,
  searchFilter,
} from "./ui.js";
import { loadEditor, loadPreview } from "./editor.js";
import { loadImport } from "./workbook.js";

const page = document.body.dataset.page;
const content = document.querySelector("#content");
try {
  document.documentElement.dataset.theme =
    localStorage.getItem("dedc-theme") || "light";
} catch {}
document.querySelector("[data-sidebar-toggle]").onclick = (event) => {
  if (matchMedia("(max-width:760px)").matches)
    document.body.classList.toggle("sidebar-open");
  else document.body.classList.toggle("sidebar-collapsed");
  event.currentTarget.setAttribute(
    "aria-expanded",
    String(!document.body.classList.contains("sidebar-collapsed")),
  );
};
document.querySelector(".topbar .search").onsubmit = async (event) => {
  event.preventDefault();
  const query = document.querySelector("#global-search").value;
  if (query.trim().length < 2) return toast("Enter at least two characters.");
  try {
    const data = await api("/search?q=" + encodeURIComponent(query));
    modal(
      "Search workspace",
      data.items.length
        ? data.items
            .map(
              (item) =>
                `<a class="quick-link" href="${e(item.url)}"><div><strong>${e(item.title)}</strong><p>${e(item.type)}</p></div><span>↗</span></a>`,
            )
            .join("")
        : empty(
            "No matching records",
            "Try another form title, question or username.",
          ),
    );
  } catch (error) {
    toast(error.message);
  }
};
document.querySelector("[data-close-dialog]").onclick = () =>
  document.querySelector("dialog").close();
document.querySelector("dialog").addEventListener("click", (event) => {
  if (event.target === event.currentTarget) {
    const r = event.currentTarget.getBoundingClientRect();
    if (
      event.clientX < r.left ||
      event.clientX > r.right ||
      event.clientY < r.top ||
      event.clientY > r.bottom
    )
      event.currentTarget.close();
  }
});
document.addEventListener("keydown", (event) => {
  if (
    event.key === "/" &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
  ) {
    event.preventDefault();
    document.querySelector("#global-search").focus();
  }
  if (event.key === "Escape") document.body.classList.remove("sidebar-open");
});

export async function createForm() {
  const dialog = modal(
    "Create a survey form",
    `<form id="create-form" class="field-stack"><label>Form title<input name="title" required maxlength="255" placeholder="e.g. University digital development survey"></label><label>Audience<select name="audience"><option value="university">University</option><option value="ministry">Ministry</option><option value="general">General</option></select></label><div class="dialog-actions"><button class="button primary" type="submit">Create draft</button></div></form>`,
  );
  document.querySelector("#create-form").onsubmit = (event) => {
    event.preventDefault();
    busy(event.submitter, async () => {
      try {
        const form = await api("/forms", {
          method: "POST",
          body: Object.fromEntries(new FormData(event.target)),
        });
        location.href = "/dashboard/forms/" + form.id;
      } catch (error) {
        errorMessage(error);
      }
    });
  };
}

async function overview() {
  describe("Your survey operations, in one place.");
  actions(
    `<button class="button" id="import-action">Import workbook</button><button class="button primary" id="create-action">＋ Create form</button>`,
  );
  const [data, forms, recent] = await Promise.all([
    api("/overview"),
    api("/forms?limit=5"),
    api("/audit?limit=5"),
  ]);
  const max = Math.max(1, ...data.trend.map((d) => d.count));
  setContent(
    `<section class="stats" aria-label="Survey statistics">${[
      ["Survey forms", data.forms, `${data.published} published versions`],
      [
        "Questions",
        data.questions,
        `${data.answer_fields} answer fields across versions`,
      ],
      ["Submissions", data.submissions, "Submitted through published forms"],
      ["Workbook records", data.source_rows, "Original answers preserved"],
    ]
      .map(
        ([label, value, note]) =>
          `<div class="stat"><p>${label}</p><strong>${value.toLocaleString()}</strong><small>${note}</small></div>`,
      )
      .join(
        "",
      )}</section><div class="overview-grid"><section class="panel"><div class="panel-head"><div><h2>Submission activity</h2><p>Daily submissions over the last 30 days</p></div>${badge("live data")}</div><div class="panel-body"><div class="chart-summary"><strong>${data.trend.reduce((s, d) => s + d.count, 0)}</strong><span class="badge">Last 30 days</span></div><div class="chart" role="img" aria-label="${e(data.trend.map((d) => `${d.date}: ${d.count}`).join("; "))}">${data.trend.map((d) => `<div class="chart-column" tabindex="0" title="${d.date}: ${d.count} submissions"><div class="chart-bar" style="height:${Math.max(1, (d.count / max) * 100)}%"></div></div>`).join("")}</div><div class="chart-axis"><span>${data.trend[0].date}</span><span>${data.trend.at(-1).date}</span></div>${data.submissions === 0 ? '<p class="editor-meta">No submissions yet. Published forms will populate this chart as responses arrive.</p>' : ""}</div></section><section class="panel"><div class="panel-head"><div><h2>Keep things moving</h2><p>Your everyday survey workflow</p></div></div><div class="panel-body">${[
      [
        "Survey forms",
        "Build, review and publish your surveys",
        "/dashboard/forms",
      ],
      [
        "Import your workbook",
        "Keep the original questions and answers",
        "/dashboard/data",
      ],
      [
        "Review submissions",
        "Explore answers and export reports",
        "/dashboard/reports",
      ],
    ]
      .map(
        ([t, d, url]) =>
          `<a class="quick-link" href="${url}"><div><strong>${t}</strong><p>${d}</p></div><span aria-hidden="true">↗</span></a>`,
      )
      .join(
        "",
      )}<p class="editor-meta">${data.active_users} active accounts · ${data.users} total accounts</p></div></section></div><section class="panel" style="margin-top:22px"><div class="panel-head"><div><h2>Your survey forms</h2><p>Drafts, published versions and archived forms</p></div><a class="button small" href="/dashboard/forms">View all forms</a></div>${formTable(forms.items)}</section><section class="panel" style="margin-top:22px"><div class="panel-head"><h2>Recent activity</h2><a href="/dashboard/audit" class="button small">View audit trail</a></div>${
      recent.items.length
        ? table(
            ["Action", "Entity", "When"],
            recent.items.map(
              (a) =>
                `<tr><td>${e(a.action.replaceAll(".", " "))}</td><td>${e(a.entity)} #${a.target_id ?? "—"}</td><td>${date(a.created_at)}</td></tr>`,
            ),
          )
        : empty(
            "No activity yet",
            "Administrator actions will appear here as you work.",
          )
    }</section>`,
  );
  document.querySelector("#create-action").onclick = createForm;
  document.querySelector("#import-action").onclick = () =>
    (location.href = "/dashboard/data");
}
function formTable(items) {
  return items.length
    ? table(
        ["Form name", "Audience", "Status", "Answer fields", ""],
        items.map((f) => {
          const v = f.versions.at(-1);
          return `<tr><td class="title"><a class="table-link" href="/dashboard/forms/${f.id}">${e(f.title)}</a><small>Version ${v?.number || 1}</small></td><td>${e(f.audience)}</td><td>${badge(f.archived ? "archived" : v?.status || "draft")}</td><td class="numeric">${v?.fields ?? 0}</td><td><a href="/dashboard/forms/${f.id}" class="button small">Open form ↗</a></td></tr>`;
        }),
      )
    : empty(
        "Your next survey starts here",
        "Create a form from scratch or import your existing DEDC workbook.",
        button("Import workbook", "/dashboard/data"),
      );
}
async function formsPage() {
  describe("Build once. Publish with confidence. Keep every version.");
  actions(
    `<a class="button" href="/dashboard/data">Import workbook</a><button class="button primary" id="create-action">＋ Create form</button>`,
  );
  const p = new URLSearchParams(location.search),
    data = await api("/forms?" + p);
  setContent(
    `<section class="panel">${searchFilter(p.get("search") || "")}${formTable(data.items)}${pagination(data.total)}</section>`,
  );
  document.querySelector("#create-action").onclick = createForm;
  bindFilters(load);
}
async function questions() {
  describe("Every question comes from a saved form version.");
  actions(button("Manage survey forms", "/dashboard/forms"));
  const p = new URLSearchParams(location.search),
    data = await api("/questions?" + p);
  setContent(
    `<section class="panel">${searchFilter(p.get("search") || "")}${
      data.items.length
        ? table(
            ["Question", "Type", "Form / version", "Status", ""],
            data.items.map(
              (q) =>
                `<tr><td class="title">${e(q.title)}<small>${e(q.key)}${q.required ? " · Required" : ""}</small></td><td>${e(q.kind.replaceAll("_", " "))}</td><td class="title">${e(q.form)}<small>Version ${q.version}</small></td><td>${badge(q.status)}</td><td><a class="button small" href="/dashboard/forms/${q.form_id}">Open builder</a></td></tr>`,
            ),
          )
        : empty(
            "No questions yet",
            "Add questions to a draft or import a workbook.",
          )
    }${pagination(data.total)}</section>`,
  );
  bindFilters(load);
}
async function reportsPage() {
  describe(
    "Filter actual submissions, review answers and export the same result set.",
  );
  const p = new URLSearchParams(location.search);
  const [data, formData, users] = await Promise.all([
    api("/reports?" + p),
    api("/forms?limit=100"),
    api("/users?limit=100"),
  ]);
  actions(
    `<a class="button" href="/api/admin/reports/export/csv?${e(p)}">Export CSV</a><a class="button" href="/api/admin/reports/export/xlsx?${e(p)}">Export Excel</a><a class="button" href="/api/admin/reports/export/pdf?${e(p)}">Export PDF</a>`,
  );
  setContent(
    `<section class="stats"><div class="stat"><p>Matching submissions</p><strong>${data.total}</strong></div><div class="stat"><p>Completed</p><strong>${data.statuses.completed || 0}</strong></div><div class="stat"><p>Approved</p><strong>${data.statuses.approved || 0}</strong></div><div class="stat"><p>Rejected</p><strong>${data.statuses.rejected || 0}</strong></div></section><section class="panel" style="margin-top:22px"><form class="filters" data-filter-form><input type="search" aria-label="Search submissions" name="search" placeholder="Search form or user…" value="${e(p.get("search") || "")}"><label>Form<select name="form_id"><option value="">All forms</option>${formData.items.map((f) => `<option value="${f.id}" ${p.get("form_id") == f.id ? "selected" : ""}>${e(f.title)}</option>`).join("")}</select></label><label>Version<select name="version_id"><option value="">All versions</option>${formData.items.flatMap((f) => f.versions.map((v) => `<option value="${v.id}" ${p.get("version_id") == v.id ? "selected" : ""}>${e(f.title)} · v${v.number}</option>`)).join("")}</select></label><label>Status<select name="status"><option value="">All statuses</option>${["completed", "pending_review", "approved", "rejected"].map((s) => `<option ${p.get("status") === s ? "selected" : ""} value="${s}">${s.replaceAll("_", " ")}</option>`).join("")}</select></label><label>User<select name="user_id"><option value="">All users</option>${users.items.map((u) => `<option value="${u.id}" ${p.get("user_id") == u.id ? "selected" : ""}>${e(u.username)}</option>`).join("")}</select></label><label>From<input type="date" name="start" value="${e(p.get("start") || "")}"></label><label>To<input type="date" name="end" value="${e(p.get("end") || "")}"></label><label>Question key<input name="question" placeholder="e.g. q1_present" value="${e(p.get("question") || "")}"></label><label>Match<select name="operator">${["equals", "contains", "greater_than", "less_than"].map((op) => `<option value="${op}" ${p.get("operator") === op ? "selected" : ""}>${op.replaceAll("_", " ")}</option>`).join("")}</select></label><label>Answer<input name="answer" value="${e(p.get("answer") || "")}"></label><button class="button" type="submit">Apply filters</button><a class="button small" href="${location.pathname}">Clear</a></form>${
      data.items.length
        ? table(
            [
              "",
              "Submission",
              "Form",
              "Submitted by",
              "Status",
              "Received",
              "",
            ],
            data.items.map(
              (r) =>
                `<tr><td><input type="checkbox" data-select-submission="${r.id}" aria-label="Select submission ${r.id}"></td><td>#${r.id}</td><td class="title">${e(r.form)}<small>Version ${r.version} · ${e(r.reporting_start || "—")} → ${e(r.reporting_end || "—")}</small></td><td>${e(r.username)}</td><td>${badge(r.status)}</td><td>${date(r.created_at)}</td><td><button class="button small" data-view-submission="${r.id}">View answers</button></td></tr>`,
            ),
          )
        : empty(
            "No submissions match",
            "Try another date range, clear your filters, or collect responses through a published form.",
            button("View workbook answers", "/dashboard/data?tab=answers"),
          )
    }${pagination(data.total)}${data.items.length ? '<div class="filters"><span>Review selected</span><button class="button small" data-review="approved">Approve</button><button class="button small danger" data-review="rejected">Reject</button><button class="button small" data-review="pending_review">Mark pending</button></div>' : ""}</section>`,
  );
  const analytics = data.analytics;
  const peak = Math.max(1, ...analytics.trend.map((day) => day.count));
  document.querySelector("#content").insertAdjacentHTML(
    "beforeend",
    `<div class="overview-grid"><section class="panel"><div class="panel-head"><div><h2>Filtered submission trend</h2><p>${analytics.completion_percent}% completed · Average completion time: ${analytics.average_seconds === null ? "—" : analytics.average_seconds + " seconds"}</p></div></div><div class="panel-body">${analytics.trend.length ? `<div class="chart" role="img" aria-label="${e(analytics.trend.map((day) => day.date + ": " + day.count).join("; "))}">${analytics.trend.map((day) => `<div class="chart-column" tabindex="0" title="${day.date}: ${day.count}"><div class="chart-bar" style="height:${Math.max(1, (day.count / peak) * 100)}%"></div></div>`).join("")}</div>` : empty("No activity in this selection", "Change the filters to include submitted responses.")}</div></section><section class="panel"><div class="panel-head"><h2>Respondent activity</h2></div>${
      analytics.by_user.length
        ? table(
            ["User", "Submissions"],
            analytics.by_user.map(
              (row) =>
                `<tr><td>${e(row.username)}</td><td class="numeric">${row.count}</td></tr>`,
            ),
          )
        : empty(
            "No respondent activity",
            "Submitted responses will appear here.",
          )
    }</section></div>${
      analytics.question_distribution.length
        ? `<section class="panel" style="margin-top:22px"><div class="panel-head"><h2>Answer distribution: ${e(p.get("question"))}</h2></div>${table(
            ["Answer", "Responses"],
            analytics.question_distribution.map(
              (item) =>
                `<tr><td>${e(typeof item.answer === "object" ? JSON.stringify(item.answer) : item.answer)}</td><td class="numeric">${item.count}</td></tr>`,
            ),
          )}</section>`
        : ""
    }`,
  );
  bindFilters(load);
  document.querySelectorAll("[data-view-submission]").forEach(
    (b) =>
      (b.onclick = () =>
        busy(b, async () => {
          try {
            const detail = await api(
              "/submissions/" + b.dataset.viewSubmission,
            );
            modal(
              "Submission #" + detail.id,
              `<p class="editor-meta">${e(detail.form)} · Version ${detail.version} · ${e(detail.username)}</p>${detail.sections.map((s) => `<section class="stack"><h3>${e(s.title)}</h3>${s.answers.map((a) => `<div class="notice"><strong>${e(a.title)}</strong><p class="source-text">${["file", "image"].includes(a.kind) && a.value?.file_id ? `<a class="table-link" href="/api/files/${Number(a.value.file_id)}">Download attachment ↗</a>` : e(typeof a.value === "object" ? JSON.stringify(a.value) : (a.value ?? "—"))}</p></div>`).join("")}</section>`).join("")}`,
            );
          } catch (error) {
            toast(error.message);
          }
        })),
  );
  document.querySelectorAll("[data-review]").forEach(
    (b) =>
      (b.onclick = () =>
        busy(b, async () => {
          const ids = [
            ...document.querySelectorAll("[data-select-submission]:checked"),
          ].map((c) => Number(c.dataset.selectSubmission));
          if (!ids.length) return toast("Select at least one submission.");
          try {
            await api("/submissions/review", {
              method: "POST",
              body: { ids, status: b.dataset.review },
            });
            toast("Submission review saved.");
            load();
          } catch (error) {
            toast(error.message);
          }
        })),
  );
}
async function usersPage() {
  describe("Manage real accounts, roles and administrator access.");
  const p = new URLSearchParams(location.search),
    data = await api("/users?" + p);
  actions(
    `<a class="button" href="/api/admin/users/export/csv?${e(p)}">Export users</a><button class="button" id="add-role">Add role</button><button class="button primary" id="add-user">＋ Add user</button>`,
  );
  setContent(
    `<section class="panel">${searchFilter(p.get("search") || "")}${table(
      ["User", "Role", "Status", "Created", ""],
      data.items.map(
        (u) =>
          `<tr><td><a class="table-link" href="/dashboard/reports?user_id=${u.id}">${e(u.username)}</a><small>User #${u.id} · View submissions</small></td><td>${e(data.roles.find((r) => r.id === u.role_id)?.name || u.role_id)}</td><td>${badge(u.is_active ? "active" : "disabled")}</td><td>${date(u.created_at)}</td><td><button class="button small" data-edit-user="${u.id}">Edit user</button></td></tr>`,
      ),
    )}${pagination(data.total)}</section>`,
  );
  bindFilters(load);
  const edit = (u) => {
    const dialog = modal(
      u ? "Edit user" : "Add user",
      `<form id="user-form" class="field-stack"><label>Username<input name="username" required maxlength="100" autocomplete="off" value="${e(u?.username || "")}"></label><label>Role<select name="role_id">${data.roles.map((r) => `<option value="${r.id}" ${u?.role_id === r.id ? "selected" : ""}>${e(r.name)}</option>`).join("")}</select></label><label>${u ? "New password (leave blank to keep current password)" : "Password"}<input type="password" name="password" minlength="8" autocomplete="new-password" ${u ? "" : "required"}></label><label class="check-label"><input type="checkbox" name="is_active" ${u?.is_active !== false ? "checked" : ""}>Account active</label><div class="dialog-actions"><button class="button primary" type="submit">Save user</button></div></form>`,
    );
    document.querySelector("#user-form").onsubmit = (event) => {
      event.preventDefault();
      busy(event.submitter, async () => {
        const values = Object.fromEntries(new FormData(event.target));
        values.role_id = Number(values.role_id);
        values.is_active = event.target.is_active.checked;
        if (!values.password) delete values.password;
        try {
          await api("/users" + (u ? "/" + u.id : ""), {
            method: u ? "PUT" : "POST",
            body: values,
          });
          dialog.close();
          toast("User saved.");
          load();
        } catch (error) {
          errorMessage(error);
        }
      });
    };
  };
  document.querySelector("#add-role").onclick = () => {
    const dialog = modal(
      "Add respondent role",
      `<form id="role-form" class="field-stack"><label>Role name<input name="name" required maxlength="100" placeholder="e.g. Enumerator"></label><p class="editor-meta">Only the configured administrator role grants access to administration pages. Other active roles can fill published surveys.</p><div class="dialog-actions"><button class="button primary" type="submit">Create role</button></div></form>`,
    );
    document.querySelector("#role-form").onsubmit = (event) => {
      event.preventDefault();
      busy(event.submitter, async () => {
        try {
          await api("/roles", {
            method: "POST",
            body: Object.fromEntries(new FormData(event.target)),
          });
          dialog.close();
          toast("Role created.");
          load();
        } catch (error) {
          errorMessage(error);
        }
      });
    };
  };
  document.querySelector("#add-user").onclick = () => edit(null);
  document
    .querySelectorAll("[data-edit-user]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          edit(data.items.find((u) => u.id == b.dataset.editUser))),
    );
}
async function audit() {
  describe(
    "A traceable record of administrator actions. Passwords and tokens are excluded.",
  );
  const p = new URLSearchParams(location.search),
    data = await api("/audit?" + p);
  setContent(
    `<section class="panel">${searchFilter(p.get("search") || "")}${
      data.items.length
        ? table(
            ["Action", "Actor", "Target", "Changes", "When"],
            data.items.map(
              (a) =>
                `<tr><td>${e(a.action)}</td><td>User #${a.actor_id ?? "—"}</td><td>${e(a.entity)} #${a.target_id ?? "—"}</td><td class="title">${e(JSON.stringify(a.changes))}</td><td>${date(a.created_at)}</td></tr>`,
            ),
          )
        : empty(
            "No audit events",
            "Important changes and exports will be recorded here.",
          )
    }${pagination(data.total)}</section>`,
  );
  bindFilters(load);
}
async function settings() {
  describe("Your account and workspace preferences.");
  const user = await api("/session");
  setContent(
    `<div class="overview-grid"><section class="panel"><div class="panel-head"><h2>Appearance</h2></div><div class="panel-body field-stack"><label>Workspace theme<select id="theme-setting"><option value="light">Light</option><option value="dark">Dark</option></select><small>Saved in this browser. No account credentials are stored.</small></label></div></section><section class="panel"><div class="panel-head"><h2>Your account</h2></div><div class="panel-body"><h3>${e(user.username)}</h3><p class="editor-meta">Administrator · User #${user.id}</p><a class="button" href="/dashboard/users">Manage accounts</a></div></section></div>`,
  );
  document.querySelector("#theme-setting").value =
    document.documentElement.dataset.theme;
  document.querySelector("#theme-setting").onchange = (event) => {
    document.documentElement.dataset.theme = event.target.value;
    try {
      localStorage.setItem("dedc-theme", event.target.value);
    } catch {}
    toast("Theme saved.");
  };
}
async function load() {
  try {
    await {
      overview,
      forms: formsPage,
      questions,
      submissions: reportsPage,
      reports: reportsPage,
      users: usersPage,
      audit,
      settings,
      editor: () => loadEditor(Number(document.body.dataset.formId)),
      preview: () => loadPreview(Number(document.body.dataset.formId)),
      data: loadImport,
    }[page]();
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = load;
  }
}
window.addEventListener("popstate", load);
load();
