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

// Dynamic imports with error boundaries
let loadEditor, loadPreview, loadImport;

async function loadEditorModule() {
  try {
    const mod = await import("./editor.js?v=20261103");
    loadEditor = mod.loadEditor;
    loadPreview = mod.loadPreview;
  } catch (error) {
    console.error("Failed to load editor module:", error);
    toast("Editor unavailable: " + error.message);
    loadEditor = loadPreview = () => {
      setContent(
        `<div class="notice error" role="alert">${e(
          "The form editor could not be loaded. Please refresh the page."
        )}</div><button class="button" id="retry-editor">Retry</button>`
      );
      document.querySelector("#retry-editor").onclick = () => location.reload();
    };
  }
}

async function loadWorkbookModule() {
  try {
    const mod = await import("./workbook.js");
    loadImport = mod.loadImport;
  } catch (error) {
    console.error("Failed to load workbook module:", error);
    toast("Workbook import unavailable: " + error.message);
    loadImport = () => {
      setContent(
        `<div class="notice error" role="alert">${e(
          "The workbook importer could not be loaded. Please refresh the page."
        )}</div><button class="button" id="retry-workbook">Retry</button>`
      );
      document.querySelector("#retry-workbook").onclick = () => location.reload();
    };
  }
}

// Initialize modules
await Promise.all([loadEditorModule(), loadWorkbookModule()]);

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

// Global error boundary for uncaught errors
window.addEventListener("error", (event) => {
  console.error("Uncaught error:", event.error);
  // Prevent the error from breaking the entire dashboard
  if (!event.error?.message?.includes("Script error")) {
    toast("An error occurred: " + (event.error?.message || "Unknown error"));
  }
  event.preventDefault();
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled rejection:", event.reason);
  toast("An error occurred: " + (event.reason?.message || "Unknown error"));
  event.preventDefault();
});

export async function createForm() {
  const dialog = modal(
    "Create a survey form",
    `<form id="create-form" class="field-stack"><label>Form title<input name="title" required maxlength="255" placeholder="e.g. University digital development survey"></label><label>Audience<select name="audience"><option value="university">University</option><option value="ministry">Ministry</option><option value="general">General</option></select></label><div class="dialog-actions"><button class="button primary" type="submit">Create draft</button></div></form>`,
  );
  document.querySelector("#create-form").onsubmit = async (event) => {
    event.preventDefault();
    busy(event.submitter, async () => {
      try {
        const form = await api("/forms", {
          method: "POST",
          body: Object.fromEntries(new FormData(event.target)),
        });
        // Navigate to the form builder page
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
  try {
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
                  `<tr><td>${e(a.action.replace(/\./g, " "))}</td><td>${e(a.entity)} #${a.target_id ?? "—"}</td><td>${date(a.created_at)}</td></tr>`,
              ),
            )
          : empty(
              "No activity yet",
              "Administrator actions will appear here as you work.",
            )
      }</section>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = overview;
    return;
  }
  document.querySelector("#create-action").onclick = createForm;
  document.querySelector("#import-action").onclick = () =>
    (location.href = "/dashboard/data");
}

function formTable(items) {
  return items.length
    ? table(
        [
          `<input type="checkbox" aria-label="Select all forms" data-select-all="forms">`,
          "Form name",
          "Audience",
          "Status",
          "Sections",
          "Questions",
          "",
        ],
        items.map((f) => {
          const v = f.versions.at(-1);
          const total_questions = v?.fields ?? 0;
          const section_count = v?.sections?.length ?? v?.section_count ?? 0;
          return `<tr><td><input type="checkbox" data-select-form="${f.id}" aria-label="Select form ${f.id}"></td><td class="title"><a class="table-link" href="/dashboard/forms/${f.id}">${e(f.title)}</a><small>Version ${v?.number || 1}</small></td><td>${e(f.audience)}</td><td>${badge(f.archived ? "archived" : v?.status || "draft")}</td><td class="numeric">${section_count}</td><td class="numeric">${total_questions}</td><td><a href="/dashboard/forms/${f.id}" class="button small">Open builder ↗</a></td></tr>`;
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
  try {
    const p = new URLSearchParams(location.search),
      data = await api("/forms?" + p);
    setContent(
      `<section class="panel">${searchFilter(p.get("search") || "")}${formTable(data.items)}${pagination(data.total)}</section>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = formsPage;
    return;
  }
  document.querySelector("#create-action").onclick = createForm;
  bindFilters(load);
  setupBulkDelete();
}

function setupBulkDelete() {
  const selectAll = document.querySelector("th input[type='checkbox'][data-select-all='forms']");
  if (!selectAll) return;

  selectAll.onchange = () => {
    document
      .querySelectorAll("td input[data-select-form]")
      .forEach((cb) => (cb.checked = selectAll.checked));
    updateBulkDeleteButton();
  };

  document
    .querySelectorAll("td input[data-select-form]")
    .forEach((cb) => (cb.onchange = updateBulkDeleteButton));

  function updateBulkDeleteButton() {
    const selected = [
      ...document.querySelectorAll("td input[data-select-form]:checked"),
    ].map((cb) => Number(cb.dataset.selectForm));
    // Update select all state
    const all = document.querySelectorAll("td input[data-select-form]");
    const checked = document.querySelectorAll("td input[data-select-form]:checked");
    if (all.length > 0) {
      selectAll.checked = all.length === checked.length;
      selectAll.indeterminate = checked.length > 0 && checked.length < all.length;
    }
    let btn = document.querySelector("#bulk-delete-forms");
    if (selected.length) {
      if (!btn) {
        btn = document.createElement("button");
        btn.id = "bulk-delete-forms";
        btn.className = "button danger small";
        btn.textContent = `Delete ${selected.length} selected`;
        btn.onclick = () => bulkDeleteForms(selected);
        document.querySelector("#page-actions").appendChild(btn);
      } else {
        btn.textContent = `Delete ${selected.length} selected`;
      }
    } else if (btn) {
      btn.remove();
    }
  }
}

async function bulkDeleteForms(ids) {
  if (
    !confirm(
      `Are you sure you want to delete ${ids.length} form(s)? This action cannot be undone.`
    )
  )
    return;
  try {
    await api("/forms/bulk-delete", {
      method: "POST",
      body: { ids },
    });
    toast(`${ids.length} form(s) deleted.`);
    load();
  } catch (error) {
    errorMessage(error);
  }
}



async function departments() {
  describe("Manage ministries and universities for survey audiences.");
  actions(
    `<button class="button primary" id="add-org">＋ Add ministry or university</button>`,
  );
  try {
    const p = new URLSearchParams(location.search);
    const [ministriesData, universitiesData] = await Promise.all([
      api("/ministries?" + p),
      api("/universities?" + p),
    ]);
    setContent(
      `<section class="panel">${searchFilter(p.get("search") || "")}<div class="filters"><label>Filter by type<select id="org-filter"><option value="all" ${p.get("type") === "all" || !p.get("type") ? "selected" : ""}>All</option><option value="ministry" ${p.get("type") === "ministry" ? "selected" : ""}>Ministry</option><option value="university" ${p.get("type") === "university" ? "selected" : ""}>University</option></select></label><button class="button small" id="apply-org-filter">Apply</button></div></section>
      ${ (p.get("type") === "all" || !p.get("type") || p.get("type") === "ministry") && ministriesData.items.length
        ? `<section class="panel" style="margin-top:22px"><h3>Ministries</h3>${table(
            ["Ministry", ""],
            ministriesData.items.map(
              (m) =>
                `<tr><td class="title">${e(m.name)}</td><td><button class="button small" data-edit-ministry='${JSON.stringify(m).replace(/'/g, "'")}'>Edit</button><button class="button small danger" data-delete-ministry="${m.id}">Delete</button></td></tr>`,
            ),
          )}</section>`
        : (p.get("type") === "ministry" && !ministriesData.items.length)
        ? `<section class="panel" style="margin-top:22px">${empty("No ministries yet", "Add ministries to organize survey audiences.")}</section>`
        : ""
      }
      ${ (p.get("type") === "all" || !p.get("type") || p.get("type") === "university") && universitiesData.items.length
        ? `<section class="panel" style="margin-top:22px"><h3>Universities</h3>${table(
            ["University", "Type", ""],
            universitiesData.items.map(
              (u) =>
                `<tr><td class="title">${e(u.name)}</td><td>${e(u.type) || "—"}</td><td><button class="button small" data-edit-university='${JSON.stringify(u).replace(/'/g, "'")}'>Edit</button><button class="button small danger" data-delete-university="${u.id}">Delete</button></td></tr>`,
            ),
          )}</section>`
        : (p.get("type") === "university" && !universitiesData.items.length)
        ? `<section class="panel" style="margin-top:22px">${empty("No universities yet", "Add universities to organize survey audiences.")}</section>`
        : ""
      }`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = departments;
    return;
  }
  document.querySelector("#add-org").onclick = () => openAddOrgDialog();
  document.querySelector("#apply-org-filter")?.addEventListener("click", () => {
    const type = document.querySelector("#org-filter")?.value || "all";
    const search = document.querySelector("input[type=search]")?.value || "";
    const url = new URL(location.href);
    if (type !== "all") url.searchParams.set("type", type); else url.searchParams.delete("type");
    if (search) url.searchParams.set("search", search); else url.searchParams.delete("search");
    location.href = url.toString();
  });
  bindFilters(load);
  document.querySelectorAll("[data-edit-ministry]").forEach((btn) => {
    btn.onclick = () => openAddOrgDialog("ministry", JSON.parse(btn.dataset.editMinistry));
  });
  document.querySelectorAll("[data-edit-university]").forEach((btn) => {
    btn.onclick = () => openAddOrgDialog("university", JSON.parse(btn.dataset.editUniversity));
  });
  document.querySelectorAll("[data-delete-ministry]").forEach((btn) => {
    btn.onclick = () => deleteOrg("ministry", Number(btn.dataset.deleteMinistry), btn);
  });
  document.querySelectorAll("[data-delete-university]").forEach((btn) => {
    btn.onclick = () => deleteOrg("university", Number(btn.dataset.deleteUniversity), btn);
  });
}

function openAddOrgDialog(orgType = null, org = null) {
  const isEdit = !!org;
  const initialType = orgType || "";
  const dialog = modal(
    isEdit ? (initialType === "ministry" ? "Edit ministry" : "Edit university") : "Add ministry or university",
    `<form id="org-select-form" class="field-stack"><input type="hidden" name="id" value="${org?.id || ""}"><label>Type<select name="org_type" required ${isEdit ? "disabled" : ""}><option value="">Choose...</option><option value="ministry" ${initialType === "ministry" ? "selected" : ""}>Ministry</option><option value="university" ${initialType === "university" ? "selected" : ""}>University</option></select></label><div id="org-details" class="field-stack" style="display:${isEdit || initialType ? "block" : "none"}"><label>Name<input name="name" required maxlength="255" value="${e(org?.name || "")}"></label><label id="uni-type-label" style="display:${initialType === "university" ? "block" : "none"}">University type<input name="uni_type" maxlength="100" placeholder="e.g. Public, Private" value="${e(org?.type || "Unspecified")}"></label></div><div class="dialog-actions"><button class="button primary" type="submit">${isEdit ? "Save" : "Create"}</button></div></form>`,
  );
  const typeSel = dialog.querySelector('select[name="org_type"]');
  const details = dialog.querySelector('#org-details');
  const uniLabel = dialog.querySelector('#uni-type-label');
  if (!isEdit) {
    typeSel.onchange = () => {
      if (typeSel.value) {
        details.style.display = 'block';
        uniLabel.style.display = typeSel.value === 'university' ? 'block' : 'none';
      } else {
        details.style.display = 'none';
      }
    };
  }
  document.querySelector("#org-select-form").onsubmit = async (event) => {
    event.preventDefault();
    busy(event.submitter, async () => {
      try {
        const values = Object.fromEntries(new FormData(event.target));
        const orgTypeVal = values.org_type || initialType;
        const id = values.id;
        if (orgTypeVal === 'ministry') {
          if (id) {
            await api('/ministries/' + id, { method: 'PUT', body: { name: values.name } });
            toast('Ministry updated.');
          } else {
            await api('/ministries', { method: 'POST', body: { name: values.name } });
            toast('Ministry created.');
          }
        } else if (orgTypeVal === 'university') {
          if (id) {
            await api('/universities/' + id, { method: 'PUT', body: { name: values.name, type: values.uni_type || 'Unspecified' } });
            toast('University updated.');
          } else {
            await api('/universities', { method: 'POST', body: { name: values.name, type: values.uni_type || 'Unspecified' } });
            toast('University created.');
          }
        }
        dialog.close();
        load();
      } catch (error) {
        errorMessage(error);
      }
    });
  };
}
async function deleteOrg(orgType, id, btn) {
  const isMinistry = orgType === "ministry";
  if (!confirm(`Are you sure you want to delete this ${isMinistry ? "ministry" : "university"}? This action cannot be undone.`)) return;
  try {
    await api(`/${isMinistry ? "ministries" : "universities"}/${id}`, { method: "DELETE" });
    toast(`${isMinistry ? "Ministry" : "University"} deleted.`);
    load();
  } catch (error) {
    errorMessage(error);
  }
}

async function reportsPage() {
  describe(
    "Filter actual submissions, review answers and export the same result set.",
  );
  let data, formData, users;
  try {
    const p = new URLSearchParams(location.search);
    [data, formData, users] = await Promise.all([
      api("/reports?" + p),
      api("/forms?limit=100"),
      api("/users?limit=100"),
    ]);
    actions(
      `<a class="button" href="/api/admin/reports/export/csv?${e(p)}">Export CSV</a><a class="button" href="/api/admin/reports/export/xlsx?${e(p)}">Export Excel</a><a class="button" href="/api/admin/reports/export/pdf?${e(p)}">Export PDF</a>`,
    );
    setContent(
      `<section class="stats"><div class="stat"><p>Matching submissions</p><strong>${data.total}</strong></div><div class="stat"><p>Completed</p><strong>${data.statuses.completed || 0}</strong></div><div class="stat"><p>Approved</p><strong>${data.statuses.approved || 0}</strong></div><div class="stat"><p>Rejected</p><strong>${data.statuses.rejected || 0}</strong></div></section><section class="panel" style="margin-top:22px"><form class="filters" data-filter-form><input type="search" aria-label="Search submissions" name="search" placeholder="Search form or user…" value="${e(p.get("search") || "")}"><label>Form<select name="form_id"><option value="">All forms</option>${formData.items.map((f) => `<option value="${f.id}" ${p.get("form_id") == f.id ? "selected" : ""}>${e(f.title)}</option>`).join("")}</select></label><label>Version<select name="version_id"><option value="">All versions</option>${formData.items.flatMap((f) => f.versions.map((v) => `<option value="${v.id}" ${p.get("version_id") == v.id ? "selected" : ""}>${e(f.title)} · v${v.number}</option>`)).join("")}</select></label><label>Status<select name="status"><option value="">All statuses</option>${["completed", "pending_review", "approved", "rejected"].map((s) => `<option ${p.get("status") === s ? "selected" : ""} value="${s}">${s.replace(/_/g, " ")}</option>`).join("")}</select></label><label>User<select name="user_id"><option value="">All users</option>${users.items.map((u) => `<option value="${u.id}" ${p.get("user_id") == u.id ? "selected" : ""}>${e(u.username)}</option>`).join("")}</select></label><label>From<input type="date" name="start" value="${e(p.get("start") || "")}"></label><label>To<input type="date" name="end" value="${e(p.get("end") || "")}"></label><label>Question key<input name="question" placeholder="e.g. q1_present" value="${e(p.get("question") || "")}"></label><label>Match<select name="operator">${["equals", "contains", "greater_than", "less_than"].map((op) => `<option value="${op}" ${p.get("operator") === op ? "selected" : ""}>${op.replace(/_/g, " ")}</option>`).join("")}</select></label><button class="button small" type="submit">Apply</button></form>${data.items.length
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
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = reportsPage;
    return;
  }
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
  try {
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
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = usersPage;
    return;
  }
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
  try {
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
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = audit;
    return;
  }
  bindFilters(load);
}

async function settings() {
  describe("Your account and workspace preferences.");
  try {
    const user = await api("/session");
    setContent(
      `<div class="overview-grid"><section class="panel"><div class="panel-head"><h2>Appearance</h2></div><div class="panel-body field-stack"><label>Workspace theme<select id="theme-setting"><option value="light">Light</option><option value="dark">Dark</option></select><small>Saved in this browser. No account credentials are stored.</small></label></div></section><section class="panel"><div class="panel-head"><h2>Your account</h2></div><div class="panel-body"><h3>${e(user.username)}</h3><p class="editor-meta">Administrator · User #${user.id}</p><a class="button" href="/dashboard/users">Manage accounts</a></div></div>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`,
    );
    document.querySelector("#retry").onclick = settings;
    return;
  }
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

// Error boundary wrapper for page loading
async function safeLoad(pageFn, pageName) {
  try {
    await pageFn();
  } catch (error) {
    console.error(`Error loading ${pageName}:`, error);
    setContent(
      `<div class="notice error" role="alert">${e(
        `Failed to load ${pageName}: ${error.message}`
      )}</div><button class="button" id="retry-page">Retry</button>`,
    );
    document.querySelector("#retry-page").onclick = () => safeLoad(pageFn, pageName);
  }
}

async function load() {
  const pages = {
    overview: () => safeLoad(overview, "overview"),
    forms: () => safeLoad(formsPage, "forms"),
    departments: () => safeLoad(departments, "departments"),
    submissions: () => safeLoad(reportsPage, "reports"),
    reports: () => safeLoad(reportsPage, "reports"),
    users: () => safeLoad(usersPage, "users"),
    audit: () => safeLoad(audit, "audit"),
    settings: () => safeLoad(settings, "settings"),
    editor: () =>
      safeLoad(
        () => loadEditor(Number(document.body.dataset.formId)),
        "editor",
      ),
    preview: () =>
      safeLoad(
        () => loadPreview(Number(document.body.dataset.formId)),
        "preview",
      ),
    data: () => safeLoad(loadImport, "data import"),
  };

  const pageFn = pages[page];
  if (pageFn) {
    await pageFn();
  } else {
    setContent(
      `<div class="notice error" role="alert">${e(
        `Unknown page: ${page}`
      )}</div><button class="button" id="retry-page">Go to Overview</button>`,
    );
    document.querySelector("#retry-page").onclick = () => (location.href = "/dashboard");
  }
}

window.addEventListener("popstate", load);
load();