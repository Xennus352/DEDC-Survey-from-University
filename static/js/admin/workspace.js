import { reportingYears } from "./period.js";
import { api } from "./api.js";
import {
  escape as e,
  badge,
  button,
  empty,
  date,
  dateTime,
  label,
  valueText,
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
    const mod = await import("./editor.js?v=20261108-recovery");
    loadEditor = mod.loadEditor;
    loadPreview = mod.loadPreview;
  } catch (error) {
    console.error("Failed to load editor module:", error);
    toast("တည်းဖြတ်ကိရိယာကို ဖွင့်မရပါ။ " + error.message);
    loadEditor = loadPreview = () => {
      setContent(
        `<div class="notice error" role="alert">${e(
          "စစ်တမ်း တည်းဖြတ်ကိရိယာကို ဖွင့်မရပါ။ စာမျက်နှာကို ပြန်လည်စတင်ကြည့်ပါ။"
        )}</div><button class="button" id="retry-editor">ထပ်စမ်းကြည့်ရန်</button>`
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
    toast("အလုပ်စာအုပ် တင်သွင်းကိရိယာကို ဖွင့်မရပါ။ " + error.message);
    loadImport = () => {
      setContent(
        `<div class="notice error" role="alert">${e(
          "အလုပ်စာအုပ် တင်သွင်းကိရိယာကို ဖွင့်မရပါ။ စာမျက်နှာကို ပြန်လည်စတင်ကြည့်ပါ။"
        )}</div><button class="button" id="retry-workbook">ထပ်စမ်းကြည့်ရန်</button>`
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
  const sidebar = document.querySelector("#sidebar");
  sidebar.inert = compactNavigation.matches && !document.body.classList.contains("sidebar-open");
  document.body.classList.toggle("navigation-modal", compactNavigation.matches && document.body.classList.contains("sidebar-open"));
}
compactNavigation.addEventListener("change", updateNavigationState);
updateNavigationState();
document.querySelector("[data-sidebar-toggle]").onclick = () => {
  document.body.classList.toggle(compactNavigation.matches ? "sidebar-open" : "sidebar-collapsed");
  updateNavigationState();
};
document.querySelector("[data-close-navigation]").onclick = () => {
  document.body.classList.remove("sidebar-open");
  updateNavigationState();
  document.querySelector("[data-sidebar-toggle]").focus();
};

async function searchWorkspace(query) {
  if (query.trim().length < 2) return toast("အနည်းဆုံး စာလုံးနှစ်လုံး ရိုက်ထည့်ပါ။");
  try {
    const data = await api("/search?q=" + encodeURIComponent(query));
    modal(
      "အလုပ်ခွင်တွင် ရှာဖွေရန်",
      data.items.length
        ? data.items
            .map(
              (item) =>
                `<a class="quick-link" href="${e(item.url)}"><div><strong>${e(item.title)}</strong><p>${e(label(item.type))}</p></div><span>↗</span></a>`,
            )
            .join("")
        : empty(
            "ကိုက်ညီသော မှတ်တမ်း မရှိပါ",
            "အခြား စစ်တမ်း၊ မေးခွန်း သို့မဟုတ် အသုံးပြုသူအမည်ကို စမ်းကြည့်ပါ။",
          ),
    );
  } catch (error) {
    toast(error.message);
  }
}
document.querySelector(".topbar .search").onsubmit = (event) => {
  event.preventDefault();
  searchWorkspace(document.querySelector("#global-search").value);
};
document.querySelector("[data-mobile-search]").onclick = () => {
  const dialog = modal("အလုပ်ခွင်တွင် ရှာဖွေရန်", `<form id="mobile-search-form" class="field-stack"><label>စစ်တမ်းများ၊ မေးခွန်းများနှင့် အသုံးပြုသူများကို ရှာဖွေရန်<input name="query" type="search" minlength="2" required placeholder="အနည်းဆုံး စာလုံးနှစ်လုံး ရိုက်ထည့်ပါ"></label><div class="dialog-actions"><button class="button primary" type="submit">ရှာဖွေရန်</button></div></form>`);
  const form = dialog.querySelector("form");
  form.elements.query.focus();
  form.onsubmit = (event) => {
    event.preventDefault();
    searchWorkspace(form.elements.query.value);
  };
};

document.querySelector("#workspace-dialog [data-close-dialog]").onclick = () =>
  document.querySelector("#workspace-dialog").close();

document.querySelector("#workspace-dialog").addEventListener("click", (event) => {
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
    if (matchMedia("(max-width:600px)").matches) document.querySelector("[data-mobile-search]").click();
    else document.querySelector("#global-search").focus();
  }
  if (event.key === "Escape") {
    const wasOpen = document.body.classList.contains("sidebar-open");
    document.body.classList.remove("sidebar-open");
    updateNavigationState();
    if (wasOpen) document.querySelector("[data-sidebar-toggle]").focus();
  }
  if (event.key === "Tab" && compactNavigation.matches && document.body.classList.contains("sidebar-open")) {
    const links = [...document.querySelectorAll(".sidebar a,.sidebar button")].filter(el => !el.disabled);
    const first = links[0], last = links.at(-1);
    if (event.shiftKey && (document.activeElement === first || !document.activeElement.closest(".sidebar"))) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && (document.activeElement === last || !document.activeElement.closest(".sidebar"))) {
      event.preventDefault(); first.focus();
    }
  }
});

// Global error boundary for uncaught errors
window.addEventListener("error", (event) => {
  console.error("Uncaught error:", event.error);
  // Prevent the error from breaking the entire dashboard
  if (!event.error?.message?.includes("Script error")) {
    toast("တစ်ခုခု မှားသွားပါသည်။ " + (event.error?.message || "အမှား အမျိုးအစား မသိ"));
  }
  event.preventDefault();
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("Unhandled rejection:", event.reason);
  toast("တစ်ခုခု မှားသွားပါသည်။ " + (event.reason?.message || "အမှား အမျိုးအစား မသိ"));
  event.preventDefault();
});

export async function createForm() {
  const dialog = modal(
    "စစ်တမ်း အသစ်ဖန်တီးရန်",
    `<form id="create-form" class="field-stack"><label>စစ်တမ်းခေါင်းစဉ်<input name="title" required maxlength="255" placeholder="ဥပမာ တက္ကသိုလ် ဒီဂျစ်တယ်ဖွံ့ဖြိုးရေး စစ်တမ်း"></label><label>ဖြေဆိုသူအုပ်စု<select name="audience"><option value="university">တက္ကသိုလ်</option><option value="ministry">ဝန်ကြီးဌာန</option><option value="general">အထွေထွေ</option></select></label><div class="dialog-actions"><button class="button primary" type="submit">စစ်တမ်း စတင်ဖန်တီးရန်</button></div></form>`,
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
  describe("သင့်စစ်တမ်းများ၊ တုံ့ပြန်ချက်များနှင့် လတ်တလော လုပ်ဆောင်ချက်များကို တစ်နေရာတည်းတွင် ကြည့်ရှုနိုင်ပါသည်။");
  try {
    const [data, forms, recent] = await Promise.all([
      api("/overview"), api("/forms?limit=5"), api("/audit?limit=5"),
    ]);
    const max = Math.max(1, ...data.trend.map((d) => d.count));
    const received = data.trend.reduce((sum, day) => sum + day.count, 0);
    actions(`<a class="button" href="/dashboard/data">အလုပ်စာအုပ် တင်သွင်းရန်</a><button class="button primary" id="create-action">စစ်တမ်း အသစ်ဖန်တီးရန်</button>`);
    setContent(`
      <section class="stats" aria-label="စစ်တမ်း ကိန်းဂဏန်းများ">${[
        ["စစ်တမ်းများ", data.forms, `${data.published} ထုတ်ဝေထားသည့် ဗားရှင်း`],
        ["မေးခွန်းများ", data.questions, `${data.answer_fields} အဖြေအကွက်များ`],
        ["တင်သွင်းချက်များ", data.submissions, "ထုတ်ဝေထားသည့် စစ်တမ်းများမှ ရရှိသည့် တုံ့ပြန်ချက်များ"],
        ["အလုပ်စာအုပ် မှတ်တမ်းများ", data.source_rows, "မူရင်းအဖြေများ သိမ်းဆည်းထားသည်"],
      ].map(([label,value,note]) => `<div class="stat"><p>${label}</p><strong>${value.toLocaleString()}</strong><small>${note}</small></div>`).join("")}</section>
      <div class="overview-main">
        <section class="panel"><div class="panel-head"><div><h2>တင်သွင်းမှု လှုပ်ရှားမှု</h2><p>လွန်ခဲ့သော ရက် ၃၀ အတွင်း ရရှိသော တုံ့ပြန်ချက်များ</p></div><a class="table-link" href="/dashboard/reports">အစီရင်ခံစာများ ကြည့်ရန် ↗</a></div><div class="panel-body"><div class="chart-summary"><strong>${received}</strong><span>ယခုလ တုံ့ပြန်ချက်များ</span></div><div class="chart" role="img" aria-label="${e(data.trend.map(d => `${d.date}: ${d.count}`).join('; '))}">${data.trend.map(d => `<div class="chart-column" tabindex="0" title="${d.date}: ${d.count} တင်သွင်းမှု"><div class="chart-bar" style="height:${d.count / max * 100}%"></div></div>`).join('')}</div><div class="chart-axis"><span>${data.trend[0].date}</span><span>${data.trend.at(-1).date}</span></div>${received === 0 ? '<p class="editor-meta">ထုတ်ဝေထားသော စစ်တမ်းများကို ဖြေဆိုပြီးပါက တုံ့ပြန်ချက်များ ဤနေရာတွင် ပေါ်လာပါမည်။</p>' : ''}</div></section>
        <section class="panel"><div class="panel-head"><h2>ဆက်လုပ်ဆောင်ရန်</h2></div><div class="panel-body">${[
          ['စစ်တမ်းများ','နောက်စစ်တမ်းတစ်ခု တည်ဆောက်ပြီး ထုတ်ဝေပါ','/dashboard/forms'],
          ['အလုပ်စာအုပ် တင်သွင်းရန်','ရှိပြီးသား မေးခွန်းများကို မူကြမ်းအဖြစ် ယူဆောင်လာပါ','/dashboard/data'],
          ['တုံ့ပြန်ချက်များ စစ်ဆေးရန်','အဖြေများကို စစ်ဆေးပြီး အစီရင်ခံစာများ ပြင်ဆင်ပါ','/dashboard/reports'],
        ].map(([title,description,url]) => `<a class="quick-link" href="${url}"><div><strong>${title}</strong><p>${description}</p></div><span aria-hidden="true">↗</span></a>`).join('')}<p class="editor-meta">${data.active_users} အသုံးပြုနေသော အကောင့်များ · စုစုပေါင်း ${data.users}</p></div></section>
      </div>
      <div class="overview-lower"><section class="panel"><div class="panel-head"><div><h2>သင့်စစ်တမ်းများ</h2><p>မူကြမ်းကို ဆက်လုပ်ပါ သို့မဟုတ် ထုတ်ဝေပြီး စစ်တမ်းကို ပြန်စစ်ဆေးပါ</p></div><a class="table-link" href="/dashboard/forms">အားလုံးကြည့်ရန် ↗</a></div>${formTable(forms.items)}</section><section class="panel"><div class="panel-head"><h2>လတ်တလော လုပ်ဆောင်ချက်များ</h2><a class="table-link" href="/dashboard/audit">အားလုံးကြည့်ရန် ↗</a></div>${recent.items.length ? `<ul class="activity-list">${recent.items.map(a => `<li><strong>${e(a.action_label || label(a.action))}</strong><small>${e(a.actor_name || "စနစ်")} · ${dateTime(a.created_at)}</small></li>`).join('')}</ul>` : empty('လုပ်ဆောင်ချက် မရှိသေးပါ','သင်လုပ်ဆောင်သည်နှင့်အမျှ စီမံခန့်ခွဲသူ လုပ်ဆောင်ချက်များ ဤနေရာတွင် ပေါ်လာပါမည်။')}</section></div>
    `);
    document.querySelector('#create-action').onclick = createForm;
  } catch (error) {
    setContent(`<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`);
    document.querySelector('#retry').onclick = overview;
  }
}

function formTable(items, search = "") {
  return items.length
    ? table(
        [
          `<input type="checkbox" aria-label="စစ်တမ်းအားလုံး ရွေးရန်" data-select-all="forms">`,
          "စစ်တမ်း အမည်",
          "ဖြေဆိုသူအုပ်စု",
          "အစီရင်ခံနှစ်",
          "အခြေအနေ (ဗားရှင်း)",
          "ထုတ်ဝေရန်",
          "ကဏ္ဍများ",
          "မေးခွန်းများ",
          "",
        ],
        items.map((f) => {
          const total_questions = f.versions.reduce((sum, v) => sum + (v.fields ?? 0), 0);
          const section_count = f.versions.reduce((sum, v) => sum + (v.sections?.length ?? v.section_count ?? 0), 0);

          // Create a row per version (year) with its own toggle
          const versionRows = f.versions.map((v, idx) => {
            const published = v.status === "published" && !f.archived;
            const statusLabel = published ? "ထုတ်ဝေထားသည်" : "မူကြမ်း";
            const statusClass = published ? "published" : "draft";
            const yearLabel = reportingYears(v);
            const toggle = `<button type="button" class="form-toggle form-status-toggle" role="switch" aria-checked="${published}" aria-label="${e(f.title)} (v${v.number}) — ${published ? "မူကြမ်း အဖြစ် ပြောင်းလဲရန်" : "ထုတ်ဝေရန်"}" data-form-toggle="status" data-form-id="${f.id}" data-version-id="${v.id}"><span class="toggle-track" aria-hidden="true"></span><span class="toggle-label">${statusLabel}</span></button>`;

            return `<tr${idx === 0 ? '' : ' class="sub-row"'}>
              <td>${idx === 0 ? `<input type="checkbox" data-select-form="${f.id}" aria-label="စစ်တမ်း ${f.id} ကို ရွေးရန်">` : ''}</td>
              <td class="title">
                <div class="form-identity">
                  <span class="record-mark" aria-hidden="true">▤</span>
                  <div>
                    ${idx === 0 ? `<a class="table-link" href="/dashboard/forms/${f.id}">${e(f.title)}</a>` : ''}
                    <small>ဗားရှင်း ${v.number} · ${yearLabel}</small>
                  </div>
                </div>
              </td>
              <td>${idx === 0 ? e(label(f.audience)) : ''}</td>
              <td>${yearLabel}</td>
              <td><span class="badge ${statusClass}">${statusLabel}</span></td>
              <td>${toggle}</td>
              <td class="numeric">${v.sections?.length ?? v.section_count ?? 0}</td>
              <td class="numeric">${v.fields ?? 0}</td>
              <td>${idx === 0 ? `<a href="/dashboard/forms/${f.id}" class="button small">တည်ဆောက်ရန်</a>` : ''}</td>
            </tr>`;
          }).join("");

          return versionRows;
        }),
      )
    : search ? empty("ကိုက်ညီသော စစ်တမ်း မရှိပါ", "အခြားအမည်တစ်ခု စမ်းကြည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ရှင်းလင်းပြီး စစ်တမ်းအားလုံးကို ကြည့်ပါ။", button("ရှာဖွေမှု ရှင်းလင်းရန်", "/dashboard/forms")) : empty(
        "နောက်စစ်တမ်းကို ဤနေရာမှ စတင်ပါ",
        "အစမှ စစ်တမ်း ဖန်တီးပါ သို့မဟုတ် သင့်လက်ရှိ DEDC အလုပ်စာအုပ်ကို တင်သွင်းပါ။",
        button("အလုပ်စာအုပ် တင်သွင်းရန်", "/dashboard/data"),
      );
}


async function formsPage() {
  describe("စစ်တမ်းများ ဖန်တီးခြင်း၊ စီစဉ်ခြင်းနှင့် ထုတ်ဝေခြင်း။ ဗားရှင်းတိုင်းကို သင်ထိန်းချုပ်နိုင်ပါသည်။");
  try {
    const p = new URLSearchParams(location.search),
      data = await api("/forms?" + p);
    actions(
      `<a class="button" href="/dashboard/data">အလုပ်စာအုပ် တင်သွင်းရန်</a><button class="button primary" id="create-action">စစ်တမ်း အသစ်ဖန်တီးရန်</button>`,
    );
    setContent(
      `<div class="collection-intro"><div><h2>စစ်တမ်း စာကြည့်တိုက်</h2><p>မူကြမ်းများ၊ ထုတ်ဝေထားသည့် စစ်တမ်းများနှင့် မော်ကွန်းတင်ထားသည့် စစ်တမ်းများ</p></div><span class="collection-count">စစ်တမ်း ${data.total} ခု</span></div><section class="panel">${searchFilter(p.get("search") || "")}${formTable(data.items, p.get("search"))}${pagination(data.total)}</section>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
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
        btn.textContent = `ရွေးထားသော ${selected.length} ခုကို ဖျက်ရန်`;
        document.querySelector("#page-actions").appendChild(btn);
      } else {
        btn.textContent = `ရွေးထားသော ${selected.length} ခုကို ဖျက်ရန်`;
      }
      btn.onclick = () => bulkDeleteForms(selected);
    } else if (btn) {
      btn.remove();
    }
  }
}

function bulkDeleteForms(ids) {
  confirmDelete(
    `ရွေးထားသော စစ်တမ်း ${ids.length} ခုကို ဖျက်မလား။`,
    "ရွေးထားသော စစ်တမ်းများနှင့် ၎င်းတို့၏ မေးခွန်းများကို အပြီးအပိုင် ဖျက်ပစ်ပါမည်။ ပြန်လည်ရယူ၍ မရနိုင်ပါ။ တင်သွင်းချက်များ သို့မဟုတ် သိမ်းဆည်းထားသော အလုပ်စာအုပ် အချက်အလက်များ ရှိနေသော စစ်တမ်းများကို မဖျက်ဘဲ မော်ကွန်းတင်ထားသင့်ပါသည်။",
    `စစ်တမ်း ${ids.length} ခု ဖျက်ရန်`,
    async () => {
      await api("/forms/bulk-delete", { method: "POST", body: { ids } });
      toast(`စစ်တမ်း ${ids.length} ခု ဖျက်ပြီးပါပြီ။`);
      await load();
    },
  );
}


async function departments() {
  describe("စစ်တမ်းများတွင် ပါဝင်သည့် ဝန်ကြီးဌာနများနှင့် တက္ကသိုလ်များ။");
  try {
    const params = new URLSearchParams(location.search);
    const data = await api("/departments?" + params);
    const type = params.get("type") || "";
    const rows = data.items, total = data.total;
    const filtered = !!params.get("search") || !!type;
    actions('<button class="button primary" id="add-org">ဌာန ထည့်ရန်</button>');
    setContent(`<div class="organization-grid single-column"><section class="panel directory-panel">
      <div class="panel-head"><div><h2>ဌာန လမ်းညွှန် <span class="inline-count">${total}</span></h2><p>စစ်တမ်းများတွင် ပါဝင်သည့် အဖွဲ့အစည်းများကို တစ်နေရာတည်းတွင် စီမံပါ</p></div></div>
      <div class="directory-summary"><span><strong>${data.counts.university || 0}</strong> တက္ကသိုလ်</span><span><strong>${data.counts.ministry || 0}</strong> ဝန်ကြီးဌာန</span></div><form class="filters" data-filter-form><input type="search" name="search" aria-label="အဖွဲ့အစည်းများ ရှာဖွေရန်" placeholder="ဌာနများ ရှာဖွေရန်…" value="${e(params.get("search") || "")}"><label><span id="directory-type-label">အမျိုးအစား</span><select name="type" aria-labelledby="directory-type-label"><option value="">အမျိုးအစားအားလုံး</option><option value="university" ${type === "university" ? "selected" : ""}>တက္ကသိုလ်</option><option value="ministry" ${type === "ministry" ? "selected" : ""}>ဝန်ကြီးဌာန</option></select></label><button class="button" type="submit">ရှာဖွေရန်</button>${filtered ? '<a class="button text-button" href="/dashboard/departments">စစ်ထုတ်မှု ရှင်းလင်းရန်</a>' : ""}</form>
      ${rows.length ? table(["အမည်", "အဖွဲ့အစည်း", "ကဏ္ဍ", "လုပ်ဆောင်ချက်များ"], rows.map((org) => `<tr><td class="title">${e(org.name)}</td><td>${org.organization === "university" ? "တက္ကသိုလ်" : "ဝန်ကြီးဌာန"}</td><td>${org.organization === "university" ? e(org.type || "မသတ်မှတ်ထားပါ") : "—"}</td><td><div class="row-actions"><button class="button small" data-edit-org="${org.id}" data-org-type="${org.organization}">ပြင်ဆင်ရန်</button><button class="button small danger" data-delete-org="${org.id}" data-org-type="${org.organization}">ဖျက်ရန်</button></div></td></tr>`)) : empty(filtered ? "ကိုက်ညီသော ဌာန မရှိပါ" : "ဌာန မထည့်ရသေးပါ", filtered ? "အခြားအမည်တစ်ခု စမ်းကြည့်ပါ သို့မဟုတ် စစ်ထုတ်မှုများ ရှင်းလင်းပြီး ဌာနအားလုံးကို ကြည့်ပါ။" : "စစ်တမ်းများတွင် ပါဝင်သည့် တက္ကသိုလ် သို့မဟုတ် ဝန်ကြီးဌာနကို ထည့်ပါ။", filtered ? button("စစ်ထုတ်မှု ရှင်းလင်းရန်", "/dashboard/departments") : '<button class="button" data-add-department>ပထမဆုံး ဌာန ထည့်ရန်</button>')}
      ${pagination(total)}
    </section></div>`);
    document.querySelector("#add-org").onclick = () => openAddOrgDialog();
    document.querySelector("[data-add-department]")?.addEventListener("click", () => openAddOrgDialog());
    document.querySelectorAll("[data-edit-org]").forEach((button) => button.onclick = () => {
      openAddOrgDialog(button.dataset.orgType, rows.find((org) => org.organization === button.dataset.orgType && org.id === Number(button.dataset.editOrg)));
    });
    document.querySelectorAll("[data-delete-org]").forEach((button) => button.onclick = () => deleteOrg(button.dataset.orgType, Number(button.dataset.deleteOrg), button));
    bindFilters(load);
  } catch (error) {
    setContent(`<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`);
    document.querySelector("#retry").onclick = departments;
  }
}

function openAddOrgDialog(orgType = "", org = null) {
  const isEdit = !!org;
  const dialog = modal(isEdit ? "ဌာန ပြင်ဆင်ရန်" : "ဌာန ထည့်ရန်", `
    <form id="org-select-form" class="field-stack">
      <label><span id="org-type-label">အမျိုးအစား</span><select name="org_type" aria-labelledby="org-type-label" required ${isEdit ? "disabled" : ""}><option value="">အမျိုးအစား ရွေးပါ</option><option value="university" ${orgType === "university" ? "selected" : ""}>တက္ကသိုလ်</option><option value="ministry" ${orgType === "ministry" ? "selected" : ""}>ဝန်ကြီးဌာန</option></select></label>
      <label><span id="org-name-label">အမည်</span><input name="name" aria-labelledby="org-name-label" required maxlength="255" autocomplete="organization" placeholder="တက္ကသိုလ် သို့မဟုတ် ဝန်ကြီးဌာနအမည် ထည့်ပါ" value="${e(org?.name || "")}"></label>
      <details id="org-university-details" ${isEdit && orgType === "university" && org.type !== "Unspecified" ? "open" : ""} hidden><summary>တက္ကသိုလ် အသေးစိတ်</summary><label><span id="org-category-label">ကဏ္ဍ (ရွေးချယ်နိုင်)</span><input name="uni_type" aria-labelledby="org-category-label" maxlength="100" placeholder="ဥပမာ အစိုးရ သို့မဟုတ် ပုဂ္ဂလိက" value="${e(org?.type === "Unspecified" ? "" : org?.type || "")}"></label></details>
      <div class="dialog-actions"><button class="button" type="button" data-cancel-org>မလုပ်တော့ပါ</button><button class="button primary" type="submit">${isEdit ? "သိမ်းဆည်းရန်" : "ဖန်တီးရန်"}</button></div>
    </form>`);
  dialog.dataset.variant = "organization";
  const form = dialog.querySelector("#org-select-form");
  const type = form.elements.org_type;
  const name = form.elements.name;
  function updateFields() {
    const chosen = type.value;
    dialog.querySelector("#org-name-label").textContent = chosen === "university" ? "တက္ကသိုလ်အမည်" : chosen === "ministry" ? "ဝန်ကြီးဌာနအမည်" : "အမည်";
    name.placeholder = chosen === "university" ? "တက္ကသိုလ်အမည် ထည့်ပါ" : chosen === "ministry" ? "ဝန်ကြီးဌာနအမည် ထည့်ပါ" : "တက္ကသိုလ် သို့မဟုတ် ဝန်ကြီးဌာနအမည် ထည့်ပါ";
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
    name.setCustomValidity(title ? "" : "ဌာနအမည် ထည့်ပါ။");
    if (!form.reportValidity()) return;
    busy(event.submitter, async () => {
      try {
        const university = type.value === "university";
        const path = university ? "/universities" : "/ministries";
        const body = { name: title, ...(university ? { type: form.elements.uni_type.value.trim() || "Unspecified" } : {}) };
        await api(path + (isEdit ? "/" + org.id : ""), { method: isEdit ? "PUT" : "POST", body });
        dialog.close();
        toast(`${university ? "တက္ကသိုလ်" : "ဝန်ကြီးဌာန"} ${isEdit ? "ပြင်ဆင်ပြီးပါပြီ" : "ဖန်တီးပြီးပါပြီ"}။`);
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
    `ဌာန ${isMinistry ? "ဝန်ကြီးဌာန" : "တက္ကသိုလ်"}ကို ဖျက်မလား။`,
    `“${name}” ကို အပြီးအပိုင် ဖျက်ပစ်ပါမည်။ ပြန်လည်ရယူ၍ မရနိုင်ပါ။`,
    (isMinistry ? "ဝန်ကြီးဌာန" : "တက္ကသိုလ်") + " ဖျက်ရန်",
    async () => {
      await api(`/${isMinistry ? "ministries" : "universities"}/${id}`, { method: "DELETE" });
      toast(`${isMinistry ? "ဝန်ကြီးဌာန" : "တက္ကသိုလ်"} ဖျက်ပြီးပါပြီ။`);
      await load();
    },
  );
}

function reportFilters(p, formData, users) {
  const advanced = ["version_id", "user_id", "start", "end", "question", "operator"].some((key) => p.get(key));
  return `<form class="filters report-filters" data-filter-form>
    <input type="search" aria-label="တင်သွင်းချက်များ ရှာဖွေရန်" name="search" placeholder="စစ်တမ်း သို့မဟုတ် အသုံးပြုသူ ရှာဖွေရန်…" value="${e(p.get("search") || "")}">
    <label>စစ်တမ်း<select name="form_id"><option value="">စစ်တမ်းအားလုံး</option>${formData.items.map((form) => `<option value="${form.id}" ${p.get("form_id") == form.id ? "selected" : ""}>${e(form.title)}</option>`).join("")}</select></label>
    <label>အခြေအနေ<select name="status"><option value="">အခြေအနေအားလုံး</option>${["completed", "pending_review", "approved", "rejected"].map((status) => `<option value="${status}" ${p.get("status") === status ? "selected" : ""}>${label(status)}</option>`).join("")}</select></label>
    <button class="button" type="submit">စစ်ထုတ်ရန်</button>
    ${location.search ? '<a class="button" href="/dashboard/reports">စစ်ထုတ်မှု ရှင်းလင်းရန်</a>' : ""}
    <details class="report-more-filters" ${advanced ? "open" : ""}><summary>နောက်ထပ် စစ်ထုတ်မှုများ</summary><div class="advanced-filters">
      <label>ဗားရှင်း<select name="version_id"><option value="">ဗားရှင်းအားလုံး</option>${formData.items.flatMap((form) => form.versions.map((version) => `<option value="${version.id}" ${p.get("version_id") == version.id ? "selected" : ""}>${e(form.title)} · v${version.number}</option>`)).join("")}</select></label>
      <label>အသုံးပြုသူ<select name="user_id"><option value="">အသုံးပြုသူအားလုံး</option>${users.items.map((user) => `<option value="${user.id}" ${p.get("user_id") == user.id ? "selected" : ""}>${e(user.username)}</option>`).join("")}</select></label>
      <label>မှ<input type="date" name="start" value="${e(p.get("start") || "")}"></label>
      <label>ထိ<input type="date" name="end" value="${e(p.get("end") || "")}"></label>
      <label>မေးခွန်း ကုဒ်<input name="question" placeholder="ဥပမာ q1_present" value="${e(p.get("question") || "")}"></label>
      <label>ကိုက်ညီပုံ<select name="operator"><option value="">ပုံသေ (တူညီသည်)</option>${["equals", "contains", "greater_than", "less_than"].map((operator) => `<option value="${operator}" ${p.get("operator") === operator ? "selected" : ""}>${label(operator)}</option>`).join("")}</select></label>
    </div></details>
  </form>`;
}

async function reportsPage() {
  describe(
    "တင်သွင်းချက်များကို စစ်ထုတ်ပါ၊ အဖြေများကို စစ်ဆေးပါ၊ ရလဒ်များကို တင်ပို့ပါ။",
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
      `<details class="export-menu"><summary class="button">အစီရင်ခံစာ တင်ပို့ရန်</summary><div><a href="/api/admin/reports/export/csv?${e(p)}">CSV ဒေါင်းလုဒ်</a><a href="/api/admin/reports/export/xlsx?${e(p)}">Excel ဒေါင်းလုဒ်</a><a href="/api/admin/reports/export/pdf?${e(p)}">PDF ဒေါင်းလုဒ်</a></div></details>`,
    );
    setContent(
      `<section class="stats"><div class="stat"><p>ကိုက်ညီသော တင်သွင်းချက်များ</p><strong>${data.total}</strong></div><div class="stat"><p>ပြီးစီး</p><strong>${data.statuses.completed || 0}</strong></div><div class="stat"><p>အတည်ပြုထားသည်</p><strong>${data.statuses.approved || 0}</strong></div><div class="stat"><p>ပယ်ချထားသည်</p><strong>${data.statuses.rejected || 0}</strong></div></section><section class="panel report-results">${reportFilters(p, formData, users)}${data.items.length
        ? table(
            [
              "",
              "တင်သွင်းမှု",
              "စစ်တမ်း",
              "တင်သွင်းသူ",
              "အခြေအနေ",
              "ရရှိချိန်",
              "",
            ],
            data.items.map(
              (r) =>
                `<tr><td><input type="checkbox" data-select-submission="${r.id}" aria-label="တင်သွင်းမှု ${r.id} ကို ရွေးရန်"></td><td>#${r.id}</td><td class="title">${e(r.form)}<small>ဗားရှင်း ${r.version} · ${date(r.reporting_start)} → ${date(r.reporting_end)}</small></td><td>${e(r.username)}</td><td>${badge(r.status)}</td><td>${date(r.created_at)}</td><td><button class="button small" data-view-submission="${r.id}">အဖြေများ ကြည့်ရန်</button></td></tr>`,
            ),
          )
        : empty(
            "ကိုက်ညီသော တင်သွင်းချက် မရှိပါ",
            "အခြားရက်စွဲအပိုင်းအခြား စမ်းကြည့်ပါ၊ စစ်ထုတ်မှုများ ရှင်းလင်းပါ၊ သို့မဟုတ် ထုတ်ဝေထားသော စစ်တမ်းမှတစ်ဆင့် တုံ့ပြန်ချက်များ စုဆောင်းပါ။",
            button("အလုပ်စာအုပ် အဖြေများ ကြည့်ရန်", "/dashboard/data?tab=answers"),
          )
      }${pagination(data.total)}${data.items.length ? '<div class="filters"><span>ရွေးထားသည်များကို စစ်ဆေးရန်</span><button class="button small" data-review="approved">အတည်ပြုရန်</button><button class="button small danger" data-review="rejected">ပယ်ချရန်</button><button class="button small" data-review="pending_review">စစ်ဆေးရန် စောင့်ဆိုင်းအဖြစ် မှတ်ရန်</button></div>' : ""}</section>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry").onclick = reportsPage;
    return;
  }
  const analytics = data.analytics;
  const peak = Math.max(1, ...analytics.trend.map((day) => day.count));
  document.querySelector("#content").insertAdjacentHTML(
    "beforeend",
    `<div class="overview-grid report-insights"><section class="panel"><div class="panel-head"><div><h2>စစ်ထုတ်ထားသည့် တင်သွင်းမှု လမ်းကြောင်း</h2><p>${analytics.completion_percent}% ပြီးစီး · ပျမ်းမျှ ပြီးစီးချိန် · ${analytics.average_seconds === null ? "—" : analytics.average_seconds + " စက္ကန့်"}</p></div></div><div class="panel-body">${analytics.trend.length ? `<div class="chart" role="img" aria-label="${e(analytics.trend.map((day) => day.date + ": " + day.count).join("; "))}">${analytics.trend.map((day) => `<div class="chart-column" tabindex="0" title="${day.date}: ${day.count}"><div class="chart-bar" style="height:${Math.max(1, (day.count / peak) * 100)}%"></div></div>`).join("")}</div>` : empty("ဤရွေးချယ်မှုအတွက် လုပ်ဆောင်ချက် မရှိပါ", "တင်သွင်းထားသော တုံ့ပြန်ချက်များ ပါဝင်ရန် စစ်ထုတ်မှုများကို ပြောင်းပါ။")}</div></section><section class="panel"><div class="panel-head"><h2>ဖြေဆိုသူများ၏ လုပ်ဆောင်ချက်</h2></div>${
      analytics.by_user.length
        ? table(
            ["အသုံးပြုသူ", "တင်သွင်းမှုများ"],
            analytics.by_user.map(
              (row) =>
                `<tr><td>${e(row.username)}</td><td class="numeric">${row.count}</td></tr>`,
            ),
          )
        : empty(
            "ဖြေဆိုသူ လုပ်ဆောင်ချက် မရှိပါ",
            "တင်သွင်းထားသော တုံ့ပြန်ချက်များ ဤနေရာတွင် ပေါ်လာပါမည်။",
          )
    }</section></div>${
      analytics.question_distribution.length
        ? `<section class="panel" style="margin-top:22px"><div class="panel-head"><h2>အဖြေ ဖြန့်ဝေမှု · ${e(p.get("question"))}</h2></div>${table(
            ["အဖြေ", "တုံ့ပြန်ချက်များ"],
            analytics.question_distribution.map(
              (item) =>
                `<tr><td>${e(item.display_value ?? valueText(item.answer))}</td><td class="numeric">${item.count}</td></tr>`,
            ),
          )}</section>`
        : ""
    }`,
  );
  const results = document.querySelector('.report-results');
  const filters = results.querySelector('.report-filters');
  const filterPanel = document.createElement('section');
  filterPanel.className = 'panel report-filter-panel';
  filterPanel.setAttribute('aria-label', 'အစီရင်ခံစာ စစ်ထုတ်မှုများ');
  filterPanel.append(filters);
  document.querySelector('#content').prepend(filterPanel);
  results.before(document.querySelector('.report-insights'));
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
              "တင်သွင်းမှု #" + detail.id,
              `<p class="editor-meta">${e(detail.form)} · ဗားရှင်း ${detail.version} · ${e(detail.username)}</p>${detail.sections.map((s) => `<section class="stack"><h3>${e(s.title)}</h3>${s.answers.map((a) => `<div class="notice"><strong>${e(a.title)}</strong><p class="source-text">${["file", "image"].includes(a.kind) && a.value?.file_id ? `<a class="table-link" href="/api/files/${Number(a.value.file_id)}">${e(a.display_value || "ပူးတွဲဖိုင် ဒေါင်းလုဒ်လုပ်ရန်")} ↗</a>` : e(a.display_value ?? valueText(a.value))}</p></div>`).join("")}</section>`).join("")}`,
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
          if (!ids.length) return toast("အနည်းဆုံး တင်သွင်းမှုတစ်ခု ရွေးပါ။");
          try {
            await api("/submissions/review", {
              method: "POST",
              body: { ids, status: b.dataset.review },
            });
            toast("စစ်ဆေးမှု ရလဒ် သိမ်းဆည်းပြီးပါပြီ။");
            load();
          } catch (error) {
            toast(error.message);
          }
        })),
  );
}

async function usersPage() {
  let data;
  describe("အကောင့်များ၊ အခန်းကဏ္ဍများနှင့် အသုံးပြုခွင့်များကို စီမံပါ။");
  try {
    const p = new URLSearchParams(location.search);
    data = await api("/users?" + p);
    actions(
      `<a class="button" href="/api/admin/users/export/csv?${e(p)}">အသုံးပြုသူများ တင်ပို့ရန်</a><button class="button" id="add-role">အခန်းကဏ္ဍ ထည့်ရန်</button><button class="button primary" id="add-user">အသုံးပြုသူ ထည့်ရန်</button>`,
    );
    setContent(
      `<section class="panel"><div class="user-summary"><span><strong>${data.total}</strong> အကောင့်များ</span><span><strong>${data.roles.length}</strong> အခန်းကဏ္ဍများ</span><span>အသုံးပြုခွင့်နှင့် အကောင့်အခြေအနေကို စီမံပါ</span></div>${searchFilter(p.get("search") || "")}${data.items.length ? table(
        ["အသုံးပြုသူ", "အခန်းကဏ္ဍ", "အခြေအနေ", "ဖန်တီးချိန်", ""],
        data.items.map(
          (u) =>
            `<tr><td><div class="user-identity"><span class="avatar" aria-hidden="true">${e(u.username.slice(0,1).toUpperCase())}</span><div><a class="table-link" href="/dashboard/reports?user_id=${u.id}">${e(u.username)}</a><small>အသုံးပြုသူ #${u.id} · တင်သွင်းချက်များ ကြည့်ရန်</small></div></div></td><td>${e(data.roles.find((r) => r.id === u.role_id)?.name || u.role_id)}</td><td>${badge(u.is_active ? "active" : "disabled")}</td><td>${date(u.created_at)}</td><td><button class="button small" data-edit-user="${u.id}">အသုံးပြုသူ ပြင်ဆင်ရန်</button></td></tr>`,
        ),
      ) : empty("ကိုက်ညီသော အသုံးပြုသူ မရှိပါ", "အခြားအသုံးပြုသူအမည် စမ်းကြည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ရှင်းလင်းပြီး အကောင့်အားလုံးကို ကြည့်ပါ။", button("ရှာဖွေမှု ရှင်းလင်းရန်", "/dashboard/users"))}${pagination(data.total)}</section>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry").onclick = usersPage;
    return;
  }
  bindFilters(load);
  const edit = (u) => {
    const dialog = modal(
      u ? "အသုံးပြုသူ ပြင်ဆင်ရန်" : "အသုံးပြုသူ ထည့်ရန်",
      `<form id="user-form" class="field-stack"><label>အသုံးပြုသူအမည်<input name="username" required maxlength="100" autocomplete="off" value="${e(u?.username || "")}"></label><label><span id="user-role-label">အခန်းကဏ္ဍ</span><select name="role_id" aria-labelledby="user-role-label">${data.roles.map((r) => `<option value="${r.id}" ${u?.role_id === r.id ? "selected" : ""}>${e(r.name)}</option>`).join("")}</select></label><label>${u ? "စကားဝှက်အသစ် (မပြောင်းလိုပါက ဗလာထားပါ)" : "စကားဝှက်"}<input type="password" name="password" minlength="8" autocomplete="new-password" ${u ? "" : "required"}></label><label class="check-label"><input type="checkbox" name="is_active" ${u?.is_active !== false ? "checked" : ""}>အကောင့် အသုံးပြုနိုင်သည်</label><div class="dialog-actions"><button class="button primary" type="submit">အသုံးပြုသူ သိမ်းဆည်းရန်</button></div></form>`,
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
          toast("အသုံးပြုသူ သိမ်းဆည်းပြီးပါပြီ။");
          load();
        } catch (error) {
          errorMessage(error);
        }
      });
    };
  };
  document.querySelector("#add-role").onclick = () => {
    const dialog = modal(
      "ဖြေဆိုသူ အခန်းကဏ္ဍ ထည့်ရန်",
      `<form id="role-form" class="field-stack"><label>အခန်းကဏ္ဍအမည်<input name="name" required maxlength="100" placeholder="ဥပမာ ကွင်းဆင်းစစ်တမ်းကောက်သူ"></label><p class="editor-meta">စီမံခန့်ခွဲသူ အခန်းကဏ္ဍကိုသာ စီမံခန့်ခွဲရေး စာမျက်နှာများသို့ ဝင်ခွင့်ပြုပါသည်။ အခြား အခန်းကဏ္ဍများက ထုတ်ဝေထားသော စစ်တမ်းများကို ဖြေဆိုနိုင်ပါသည်။</p><div class="dialog-actions"><button class="button primary" type="submit">အခန်းကဏ္ဍ ဖန်တီးရန်</button></div></form>`,
    );
    document.querySelector("#role-form").onsubmit = (event) => {
      event.preventDefault();
      busy(event.submitter, async () => {
        try {
          await api("/roles", {
            method: "POST",
            body: Object.fromEntries(new FormData(event.target)),
          });
          await load();
          dialog.close();
          toast("အခန်းကဏ္ဍ ဖန်တီးပြီးပါပြီ။");
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
    "စီမံခန့်ခွဲသူ လုပ်ဆောင်ချက်များကို ခြေရာခံနိုင်သည့် မှတ်တမ်း။ စကားဝှက်နှင့် တိုကင်များ မပါဝင်ပါ။",
  );
  try {
    const p = new URLSearchParams(location.search),
      data = await api("/audit?" + p);
    setContent(
      `<div class="collection-intro"><div><h2>လုပ်ဆောင်ချက် မှတ်တမ်း</h2><p>စစ်တမ်းများနှင့် စနစ်အတွင်း ပြောင်းလဲမှုများကို အချိန်စဉ်လိုက် မှတ်တမ်းတင်ထားသည်။</p></div><span class="collection-count">မှတ်တမ်း ${data.total} ခု</span></div><section class="panel">${searchFilter(p.get("search") || "")}${
        data.items.length
          ? table(
              ["လုပ်ဆောင်ချက်", "လုပ်ဆောင်သူ", "ပစ်မှတ်", "ပြောင်းလဲမှုများ", "အချိန်"],
              data.items.map(
                (a) =>
                  `<tr><td>${e(a.action_label || label(a.action))}</td><td>${e(a.actor_name || "စနစ်")}</td><td>${e(label(a.entity))}${a.target_id == null ? "" : " #" + a.target_id}</td><td class="title"><details class="audit-changes"><summary>အသေးစိတ် ကြည့်ရန်</summary><dl class="audit-summary">${Object.entries(a.changes).map(([key,value]) => `<dt>${e(label(key))}</dt><dd>${e(valueText(value))}</dd>`).join("") || "<dt>နောက်ထပ် အသေးစိတ် မရှိပါ</dt>"}</dl><details><summary>နည်းပညာဆိုင်ရာ အသေးစိတ်</summary><pre>${e(JSON.stringify(a.changes, null, 2))}</pre></details></details></td><td>${dateTime(a.created_at)}</td></tr>`,
              ),
            )
          : empty(
              "မှတ်တမ်း မရှိသေးပါ",
              "အရေးကြီးသော ပြောင်းလဲမှုများနှင့် တင်ပို့မှုများကို ဤနေရာတွင် မှတ်တမ်းတင်ပါမည်။",
            )
      }${pagination(data.total)}</section>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry").onclick = audit;
    return;
  }
  bindFilters(load);
}

async function settings() {
  describe("သင့်အကောင့်နှင့် အလုပ်ခွင် ဆက်တင်များ။");
  try {
    const user = await api("/session");
    setContent(
      `<div class="settings-layout"><nav class="settings-index" aria-label="ဆက်တင် ကဏ္ဍများ"><a href="#appearance">အသွင်အပြင်</a><a href="#account">သင့်အကောင့်</a></nav><div class="settings-sections"><section class="settings-row" id="appearance"><div class="settings-copy"><h2>အသွင်အပြင်</h2><p>ဤစက်ပစ္စည်းပေါ်တွင် အလုပ်ခွင် မည်သို့ပေါ်မည်ကို ရွေးပါ။</p></div><div class="settings-control"><label><span id="theme-setting-label">အလုပ်ခွင် အပြင်အဆင်</span><select id="theme-setting" aria-labelledby="theme-setting-label"><option value="light">အလင်း</option><option value="dark">အမှောင်</option></select></label><p class="field-hint">ရွေးချယ်မှုကို ဤဘရောက်ဇာတွင် သိမ်းဆည်းထားပါသည်။</p></div></section><section class="settings-row" id="account"><div class="settings-copy"><h2>သင့်အကောင့်</h2><p>သင့် စီမံခန့်ခွဲသူ ပရိုဖိုင်နှင့် အသုံးပြုခွင့်။</p></div><div class="settings-control"><div class="account-summary"><span class="avatar" aria-hidden="true">${e(user.username.slice(0,1).toUpperCase())}</span><div><h3>${e(user.username)}</h3><p class="field-hint">စီမံခန့်ခွဲသူ · အသုံးပြုသူ #${user.id}</p></div></div><a class="button" href="/dashboard/users">အကောင့်များ စီမံရန်</a></div></section></div></div>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry").onclick = settings;
    return;
  }
  const settingLinks = [...document.querySelectorAll('.settings-index a')];
  function selectSetting(hash) {
    settingLinks.forEach(link => {
      if (link.hash === hash) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }
  selectSetting(location.hash || '#appearance');
  settingLinks.forEach(link => link.onclick = () => selectSetting(link.hash));
  document.querySelector("#theme-setting").value =
    document.documentElement.dataset.theme;
  document.querySelector("#theme-setting").onchange = (event) => {
    document.documentElement.dataset.theme = event.target.value;
    try {
      localStorage.setItem("dedc-theme", event.target.value);
    } catch {}
    toast("အပြင်အဆင် သိမ်းဆည်းပြီးပါပြီ။");
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
        `${pageName} ကို ဖွင့်မရပါ · ${error.message}`
      )}</div><button class="button" id="retry-page">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry-page").onclick = () => safeLoad(pageFn, pageName);
  }
}

async function load() {
  const pages = {
    overview: () => safeLoad(overview, "အကျဉ်းချုပ်"),
    "survey-builder": () => describe("စစ်တမ်းခုနှစ်များ၊ ခေါင်းစဉ်များနှင့် မေးခွန်းများကို စီမံပါ။"),
    forms: () => safeLoad(formsPage, "စစ်တမ်းများ"),
    departments: () => safeLoad(departments, "ဌာနများ"),
    submissions: () => safeLoad(reportsPage, "အစီရင်ခံစာများ"),
    reports: () => safeLoad(reportsPage, "အစီရင်ခံစာများ"),
    users: () => safeLoad(usersPage, "အသုံးပြုသူများ"),
    audit: () => safeLoad(audit, "လုပ်ဆောင်ချက် မှတ်တမ်း"),
    settings: () => safeLoad(settings, "ဆက်တင်များ"),
    editor: () =>
      safeLoad(
        () => loadEditor(Number(document.body.dataset.formId)),
        "တည်းဖြတ်ကိရိယာ",
      ),
    preview: () =>
      safeLoad(
        () => loadPreview(Number(document.body.dataset.formId)),
        "အစမ်းကြည့်ရှုမှု",
      ),
    data: () => safeLoad(loadImport, "ဒေတာ တင်သွင်းခြင်း"),
  };

  const pageFn = pages[page];
  if (pageFn) {
    await pageFn();
  } else {
    setContent(
      `<div class="notice error" role="alert">${e(
        `စာမျက်နှာ မတွေ့ပါ · ${page}`
      )}</div><button class="button" id="retry-page">အကျဉ်းချုပ်သို့ သွားရန်</button>`,
    );
    document.querySelector("#retry-page").onclick = () => (location.href = "/dashboard");
  }
}

const workspacePages = {
  "/dashboard": ["overview", "အကျဉ်းချုပ်"],
  "/dashboard/forms": ["forms", "စစ်တမ်းများ"],
  "/dashboard/survey-builder": ["survey-builder", "စစ်တမ်း ဖန်တီးခြင်း"],
  "/dashboard/departments": ["departments", "ဌာနများ"],
  "/dashboard/reports": ["reports", "အစီရင်ခံစာများနှင့် ခွဲခြမ်းစိတ်ဖြာမှု"],
  "/dashboard/users": ["users", "အသုံးပြုသူများနှင့် စစ်တမ်းကောက်သူများ"],
  "/dashboard/data": ["data", "ဒေတာ စီမံခန့်ခွဲမှု"],
  "/dashboard/audit": ["audit", "လုပ်ဆောင်ချက် မှတ်တမ်း"],
  "/dashboard/settings": ["settings", "ဆက်တင်များ"],
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
    const heading = document.querySelector("h1");
    heading.tabIndex = -1;
    heading.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }
}
document.addEventListener("click", (event) => {
  const link = event.target.closest("a[href]");
  if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || link.target || link.hasAttribute("download")) return;
  const url = new URL(link.href);
  if (url.pathname === "/dashboard/survey-builder" || location.pathname === "/dashboard/survey-builder") return;
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

// Single toggle for form version status: 0 = draft (မူကြမ်း), 1 = published (ထုတ်ဝေထား�那些)
document.addEventListener("click", async (event) => {
  const control = event.target.closest("[data-form-toggle='status']");
  if (!control || control.disabled) return;
  const row = control.closest("tr");
  const rowControls = row ? row.querySelectorAll("[data-form-toggle='status']") : [control];
  rowControls.forEach(button => { button.disabled = true; });
  const formId = control.dataset.formId;
  const versionId = control.dataset.versionId;
  const isPublished = control.getAttribute("aria-checked") === "true";
  try {
    if (isPublished) {
      // Currently published -> unpublish (set to draft)
      await api(`/forms/${formId}/archive`, { method: "POST", body: { archived: true } });
    } else {
      // Currently draft -> publish this version
      const form = await api(`/forms/${formId}`);
      if (form.archived) {
        // First unarchive if archived
        await api(`/forms/${formId}/archive`, { method: "POST", body: { archived: false } });
      }
      const version = form.versions.find(v => v.id == versionId);
      if (version?.status !== "published") {
        await api(`/forms/${formId}/versions/${versionId}/publish`, { method: "POST", body: { revision: version?.revision || 1 } });
      }
    }
    toast("စစ်တမ်း အခြေအနေ ပြောင်းလဲပြီးပါပြီ။");
    await load();
  } catch (error) {
    toast(error.message);
  } finally {
    rowControls.forEach(button => { button.disabled = false; });
  }
});
