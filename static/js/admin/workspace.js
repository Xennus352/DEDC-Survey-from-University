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
  confirmDelete,
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
    const mod = await import("./editor.js?v=20261105-questions");
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

let page = document.body.dataset.page;
const content = document.querySelector("#content");

try {
  document.documentElement.dataset.theme =
    localStorage.getItem("dedc-theme") || "light";
} catch {}

const compactNavigation = matchMedia("(max-width:1080px)");
function updateNavigationState() {
  document.querySelector("[data-sidebar-toggle]").setAttribute("aria-expanded", String(
    compactNavigation.matches ? document.body.classList.contains("sidebar-open") : !document.body.classList.contains("sidebar-collapsed"),
  ));
}
compactNavigation.addEventListener("change", updateNavigationState);
updateNavigationState();
document.querySelector("[data-sidebar-toggle]").onclick = () => {
  document.body.classList.toggle(compactNavigation.matches ? "sidebar-open" : "sidebar-collapsed");
  updateNavigationState();
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
  if (event.target === event.currentTarget && !event.currentTarget.dataset.deleting) {
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
  if (event.key === "Escape") {
    document.body.classList.remove("sidebar-open");
    updateNavigationState();
  }
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
  try {
    const [data, forms, recent] = await Promise.all([
      api("/overview"),
      api("/forms?limit=5"),
      api("/audit?limit=5"),
    ]);
    const max = Math.max(1, ...data.trend.map((d) => d.count));
    actions(
      `<button class="button" id="import-action">Import workbook</button><button class="button primary" id="create-action">Create form</button>`,
    );
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
        )}</section><div class="overview-grid"><section class="panel"><div class="panel-head"><div><h2>Submission activity</h2><p>Daily submissions over the last 30 days</p></div><a class="table-link" href="/dashboard/reports">View reports</a></div><div class="panel-body"><div class="chart-summary"><strong>${data.trend.reduce((s, d) => s + d.count, 0)}</strong><span class="badge">Last 30 days</span></div><div class="chart" role="img" aria-label="${e(data.trend.map((d) => `${d.date}: ${d.count}`).join("; "))}">${data.trend.map((d) => `<div class="chart-column" tabindex="0" title="${d.date}: ${d.count} submissions"><div class="chart-bar" style="height:${(d.count / max) * 100}%"></div></div>`).join("")}</div><div class="chart-axis"><span>${data.trend[0].date}</span><span>${data.trend.at(-1).date}</span></div>${data.submissions === 0 ? '<p class="editor-meta">No submissions yet. Published forms will populate this chart as responses arrive.</p>' : ""}</div></section><section class="panel"><div class="panel-head"><div><h2>Workspace shortcuts</h2><p>Create, import and review surveys</p></div></div><div class="panel-body">${[
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

function formTable(items, search = "") {
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
          return `<tr><td><input type="checkbox" data-select-form="${f.id}" aria-label="Select form ${f.id}"></td><td class="title"><a class="table-link" href="/dashboard/forms/${f.id}">${e(f.title)}</a><small>Version ${v?.number || 1}</small></td><td>${e(f.audience)}</td><td>${badge(f.archived ? "archived" : v?.status || "draft")}</td><td class="numeric">${section_count}</td><td class="numeric">${total_questions}</td><td><a href="/dashboard/forms/${f.id}" class="button small">Open builder</a></td></tr>`;
        }),
      )
    : search ? empty("No matching forms", "Try another title or clear your search to see all survey forms.", button("Clear search", "/dashboard/forms")) : empty(
        "Your next survey starts here",
        "Create a form from scratch or import your existing DEDC workbook.",
        button("Import workbook", "/dashboard/data"),
      );
}

async function formsPage() {
  describe("Build once. Publish with confidence. Keep every version.");
  try {
    const p = new URLSearchParams(location.search),
      data = await api("/forms?" + p);
    actions(
      `<a class="button" href="/dashboard/data">Import workbook</a><button class="button primary" id="create-action">Create form</button>`,
    );
    setContent(
      `<section class="panel">${searchFilter(p.get("search") || "")}${formTable(data.items, p.get("search"))}${pagination(data.total)}</section>`,
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
        document.querySelector("#page-actions").appendChild(btn);
      } else {
        btn.textContent = `Delete ${selected.length} selected`;
      }
      btn.onclick = () => bulkDeleteForms(selected);
    } else if (btn) {
      btn.remove();
    }
  }
}

function bulkDeleteForms(ids) {
  confirmDelete(
    `Delete ${ids.length} selected form${ids.length === 1 ? "" : "s"}?`,
    "The selected forms and their questions will be permanently deleted. This action cannot be undone. Forms with submissions or preserved workbook observations must be archived instead.",
    `Delete ${ids.length} form${ids.length === 1 ? "" : "s"}`,
    async () => {
      await api("/forms/bulk-delete", { method: "POST", body: { ids } });
      toast(`${ids.length} form(s) deleted.`);
      await load();
    },
  );
}


async function departments() {
  describe("Ministries and universities participating in your surveys.");
  try {
    const params = new URLSearchParams(location.search);
    const [ministries, universities] = await Promise.all([
      api("/ministries?" + params), api("/universities?" + params),
    ]);
    const type = params.get("type") || "";
    const rows = [
      ...(type !== "university" ? ministries.items.map((org) => ({ ...org, organization: "ministry" })) : []),
      ...(type !== "ministry" ? universities.items.map((org) => ({ ...org, organization: "university" })) : []),
    ].sort((left, right) => left.name.localeCompare(right.name));
    const total = (type !== "university" ? ministries.total : 0) + (type !== "ministry" ? universities.total : 0);
    const filtered = !!params.get("search") || !!type;
    actions('<button class="button primary" id="add-org">Add department</button>');
    setContent(`<div class="organization-grid single-column"><section class="panel directory-panel">
      <div class="panel-head"><div><h2>Department directory <span class="inline-count">${total}</span></h2><p>${ministries.total} ${ministries.total === 1 ? "ministry" : "ministries"} · ${universities.total} ${universities.total === 1 ? "university" : "universities"}</p></div></div>
      <form class="filters" data-filter-form><input type="search" name="search" aria-label="Search organizations" placeholder="Search departments…" value="${e(params.get("search") || "")}"><label><span id="directory-type-label">Type</span><select name="type" aria-labelledby="directory-type-label"><option value="">All types</option><option value="university" ${type === "university" ? "selected" : ""}>University</option><option value="ministry" ${type === "ministry" ? "selected" : ""}>Ministry</option></select></label><button class="button" type="submit">Search</button>${filtered ? '<a class="button text-button" href="/dashboard/departments">Clear filters</a>' : ""}</form>
      ${rows.length ? table(["Name", "Organization", "Category", "Actions"], rows.map((org) => `<tr><td class="title">${e(org.name)}</td><td>${org.organization === "university" ? "University" : "Ministry"}</td><td>${org.organization === "university" ? e(org.type || "Unspecified") : "—"}</td><td><div class="row-actions"><button class="button small" data-edit-org="${org.id}" data-org-type="${org.organization}">Edit</button><button class="button small danger" data-delete-org="${org.id}" data-org-type="${org.organization}">Delete</button></div></td></tr>`)) : empty(filtered ? "No matching departments" : "No departments added yet", filtered ? "Try a different name or clear the filters to see all departments." : "Add a university or ministry to organize the participants in your surveys.", filtered ? button("Clear filters", "/dashboard/departments") : '<button class="button" data-add-department>Add your first department</button>')}
      ${rows.length && total > rows.length ? `<p class="directory-note">Showing ${rows.length} of ${total} departments. Search by name to narrow the list.</p>` : ""}
    </section></div>`);
    document.querySelector("#add-org").onclick = () => openAddOrgDialog();
    document.querySelector("[data-add-department]")?.addEventListener("click", () => openAddOrgDialog());
    document.querySelectorAll("[data-edit-org]").forEach((button) => button.onclick = () => {
      const data = button.dataset.orgType === "ministry" ? ministries : universities;
      openAddOrgDialog(button.dataset.orgType, data.items.find((org) => org.id === Number(button.dataset.editOrg)));
    });
    document.querySelectorAll("[data-delete-org]").forEach((button) => button.onclick = () => deleteOrg(button.dataset.orgType, Number(button.dataset.deleteOrg), button));
    bindFilters(load);
  } catch (error) {
    setContent(`<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">Retry</button>`);
    document.querySelector("#retry").onclick = departments;
  }
}

function openAddOrgDialog(orgType = "", org = null) {
  const isEdit = !!org;
  const dialog = modal(isEdit ? "Edit department" : "Add department", `
    <form id="org-select-form" class="field-stack">
      <label><span id="org-type-label">Type</span><select name="org_type" aria-labelledby="org-type-label" required ${isEdit ? "disabled" : ""}><option value="">Choose type</option><option value="university" ${orgType === "university" ? "selected" : ""}>University</option><option value="ministry" ${orgType === "ministry" ? "selected" : ""}>Ministry</option></select></label>
      <label><span id="org-name-label">Name</span><input name="name" aria-labelledby="org-name-label" required maxlength="255" autocomplete="organization" placeholder="Enter university or ministry name" value="${e(org?.name || "")}"></label>
      <details id="org-university-details" ${isEdit && orgType === "university" && org.type !== "Unspecified" ? "open" : ""} hidden><summary>University details</summary><label><span id="org-category-label">Category (optional)</span><input name="uni_type" aria-labelledby="org-category-label" maxlength="100" placeholder="e.g. Public or Private" value="${e(org?.type === "Unspecified" ? "" : org?.type || "")}"></label></details>
      <div class="dialog-actions"><button class="button" type="button" data-cancel-org>Cancel</button><button class="button primary" type="submit">${isEdit ? "Save" : "Create"}</button></div>
    </form>`);
  dialog.dataset.variant = "organization";
  const form = dialog.querySelector("#org-select-form");
  const type = form.elements.org_type;
  const name = form.elements.name;
  function updateFields() {
    const chosen = type.value;
    dialog.querySelector("#org-name-label").textContent = chosen === "university" ? "University name" : chosen === "ministry" ? "Ministry name" : "Name";
    name.placeholder = chosen === "university" ? "Enter university name" : chosen === "ministry" ? "Enter ministry name" : "Enter university or ministry name";
    dialog.querySelector("#org-university-details").hidden = chosen !== "university";
  }
  type.onchange = updateFields;
  updateFields();
  form.querySelector("[data-cancel-org]").onclick = () => dialog.close();
  if (!isEdit) type.focus();
  else name.focus();
  form.onsubmit = (event) => {
    event.preventDefault();
    const title = name.value.trim();
    name.setCustomValidity(title ? "" : "Enter a department name.");
    if (!form.reportValidity()) return;
    busy(event.submitter, async () => {
      try {
        const university = type.value === "university";
        const path = university ? "/universities" : "/ministries";
        const body = { name: title, ...(university ? { type: form.elements.uni_type.value.trim() || "Unspecified" } : {}) };
        await api(path + (isEdit ? "/" + org.id : ""), { method: isEdit ? "PUT" : "POST", body });
        dialog.close();
        toast(`${university ? "University" : "Ministry"} ${isEdit ? "updated" : "created"}.`);
        await load();
      } catch (error) {
        errorMessage(error);
      }
    });
  };
  name.oninput = () => name.setCustomValidity("");
}

function deleteOrg(orgType, id, btn) {
  const isMinistry = orgType === "ministry";
  const name = btn.closest("tr").querySelector(".title").textContent;
  confirmDelete(
    `Delete ${isMinistry ? "ministry" : "university"}?`,
    `“${name}” will be permanently deleted. This action cannot be undone.`,
    "Delete " + (isMinistry ? "ministry" : "university"),
    async () => {
      await api(`/${isMinistry ? "ministries" : "universities"}/${id}`, { method: "DELETE" });
      toast(`${isMinistry ? "Ministry" : "University"} deleted.`);
      await load();
    },
  );
}

function reportFilters(p, formData, users) {
  const advanced = ["version_id", "user_id", "start", "end", "question", "operator"].some((key) => p.get(key));
  return `<form class="filters report-filters" data-filter-form>
    <input type="search" aria-label="Search submissions" name="search" placeholder="Search form or user…" value="${e(p.get("search") || "")}">
    <label>Form<select name="form_id"><option value="">All forms</option>${formData.items.map((form) => `<option value="${form.id}" ${p.get("form_id") == form.id ? "selected" : ""}>${e(form.title)}</option>`).join("")}</select></label>
    <label>Status<select name="status"><option value="">All statuses</option>${["completed", "pending_review", "approved", "rejected"].map((status) => `<option value="${status}" ${p.get("status") === status ? "selected" : ""}>${status.replaceAll("_", " ")}</option>`).join("")}</select></label>
    <button class="button" type="submit">Apply filters</button>
    ${location.search ? '<a class="button" href="/dashboard/reports">Clear filters</a>' : ""}
    <details class="report-more-filters" ${advanced ? "open" : ""}><summary>More filters</summary><div class="advanced-filters">
      <label>Version<select name="version_id"><option value="">All versions</option>${formData.items.flatMap((form) => form.versions.map((version) => `<option value="${version.id}" ${p.get("version_id") == version.id ? "selected" : ""}>${e(form.title)} · v${version.number}</option>`)).join("")}</select></label>
      <label>User<select name="user_id"><option value="">All users</option>${users.items.map((user) => `<option value="${user.id}" ${p.get("user_id") == user.id ? "selected" : ""}>${e(user.username)}</option>`).join("")}</select></label>
      <label>From<input type="date" name="start" value="${e(p.get("start") || "")}"></label>
      <label>To<input type="date" name="end" value="${e(p.get("end") || "")}"></label>
      <label>Question key<input name="question" placeholder="e.g. q1_present" value="${e(p.get("question") || "")}"></label>
      <label>Match<select name="operator"><option value="">Default (equals)</option>${["equals", "contains", "greater_than", "less_than"].map((operator) => `<option value="${operator}" ${p.get("operator") === operator ? "selected" : ""}>${operator.replaceAll("_", " ")}</option>`).join("")}</select></label>
    </div></details>
  </form>`;
}

async function reportsPage() {
  describe(
    "Filter actual submissions, review answers and export the same result set.",
  );
  let data, formData, users;
  const p = new URLSearchParams(location.search);
  try {
    [data, formData, users] = await Promise.all([
      api("/reports?" + p),
      api("/forms?limit=100"),
      api("/users?limit=100"),
    ]);
    actions(
      `<details class="export-menu"><summary class="button">Export report</summary><div><a href="/api/admin/reports/export/csv?${e(p)}">Export CSV</a><a href="/api/admin/reports/export/xlsx?${e(p)}">Export Excel</a><a href="/api/admin/reports/export/pdf?${e(p)}">Export PDF</a></div></details>`,
    );
    setContent(
      `<section class="stats"><div class="stat"><p>Matching submissions</p><strong>${data.total}</strong></div><div class="stat"><p>Completed</p><strong>${data.statuses.completed || 0}</strong></div><div class="stat"><p>Approved</p><strong>${data.statuses.approved || 0}</strong></div><div class="stat"><p>Rejected</p><strong>${data.statuses.rejected || 0}</strong></div></section><section class="panel" style="margin-top:22px">${reportFilters(p, formData, users)}${data.items.length
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
  let data;
  describe("Manage real accounts, roles and administrator access.");
  try {
    const p = new URLSearchParams(location.search);
    data = await api("/users?" + p);
    actions(
      `<a class="button" href="/api/admin/users/export/csv?${e(p)}">Export users</a><button class="button" id="add-role">Add role</button><button class="button primary" id="add-user">Add user</button>`,
    );
    setContent(
      `<section class="panel">${searchFilter(p.get("search") || "")}${data.items.length ? table(
        ["User", "Role", "Status", "Created", ""],
        data.items.map(
          (u) =>
            `<tr><td><a class="table-link" href="/dashboard/reports?user_id=${u.id}">${e(u.username)}</a><small>User #${u.id} · View submissions</small></td><td>${e(data.roles.find((r) => r.id === u.role_id)?.name || u.role_id)}</td><td>${badge(u.is_active ? "active" : "disabled")}</td><td>${date(u.created_at)}</td><td><button class="button small" data-edit-user="${u.id}">Edit user</button></td></tr>`,
        ),
      ) : empty("No matching users", "Try another username or clear your search to see all accounts.", button("Clear search", "/dashboard/users"))}${pagination(data.total)}</section>`,
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
                  `<tr><td>${e(a.action)}</td><td>User #${a.actor_id ?? "—"}</td><td>${e(a.entity)} #${a.target_id ?? "—"}</td><td class="title"><details class="audit-changes"><summary>View details</summary><pre>${e(JSON.stringify(a.changes, null, 2))}</pre></details></td><td>${date(a.created_at)}</td></tr>`,
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
      `<div class="settings-layout"><section class="settings-row"><div class="settings-copy"><h2>Appearance</h2><p>Choose how the workspace looks on this device.</p></div><div class="settings-control"><label><span id="theme-setting-label">Workspace theme</span><select id="theme-setting" aria-labelledby="theme-setting-label"><option value="light">Light</option><option value="dark">Dark</option></select></label><p class="field-hint">Your preference is saved in this browser.</p></div></section><section class="settings-row"><div class="settings-copy"><h2>Your account</h2><p>Your administrator profile and access.</p></div><div class="settings-control"><h3>${e(user.username)}</h3><p class="editor-meta">Administrator · User #${user.id}</p><a class="button" href="/dashboard/users">Manage accounts</a></div></section></div>`,
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

const workspacePages = {
  "/dashboard": ["overview", "Overview"],
  "/dashboard/forms": ["forms", "Survey forms"],
  "/dashboard/departments": ["departments", "Departments"],
  "/dashboard/reports": ["reports", "Reports & analytics"],
  "/dashboard/users": ["users", "Users & enumerators"],
  "/dashboard/audit": ["audit", "Audit trail"],
  "/dashboard/settings": ["settings", "Settings"],
};
let navigating = false;
let navigationTask = Promise.resolve();
function showWorkspacePage() {
  navigationTask = navigationTask.then(renderWorkspacePage);
  return navigationTask;
}
async function renderWorkspacePage() {
  const target = workspacePages[location.pathname];
  if (!target) return location.reload();
  [page] = target;
  document.body.dataset.page = page;
  document.title = `${target[1]} · DEDC`;
  document.querySelector("h1").textContent = target[1];
  document.querySelector(".breadcrumb strong").textContent = target[1];
  document.querySelectorAll(".sidebar nav a").forEach((link) => {
    if (new URL(link.href).pathname === location.pathname) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  document.body.classList.remove("sidebar-open");
  updateNavigationState();
  actions("");
  content.setAttribute("aria-busy", "true");
  content.inert = true;
  navigating = true;
  try { await load(); }
  finally {
    navigating = false;
    content.removeAttribute("aria-busy");
    content.inert = false;
  }
}
document.addEventListener("click", (event) => {
  const link = event.target.closest("a[href]");
  if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute("download")) return;
  const url = new URL(link.href);
  if (url.origin !== location.origin || !workspacePages[url.pathname] || !workspacePages[location.pathname] || url.hash) return;
  if (document.querySelector("#workspace-dialog").open) return;
  event.preventDefault();
  if (navigating || url.href === location.href) return;
  history.pushState({}, "", url);
  showWorkspacePage();
});
window.addEventListener("popstate", () => {
  if (workspacePages[location.pathname]) showWorkspacePage();
  else location.reload();
});
navigating = true;
content.setAttribute("aria-busy", "true");
content.inert = true;
navigationTask = load().finally(() => {
  navigating = false;
  content.removeAttribute("aria-busy");
  content.inert = false;
});
