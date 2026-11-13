import { reportingYears } from "./period.js";
import { api } from "./api.js";
import { renderYearlyBars } from "./trend.js?v=20261113-overview18";
const arrowIcon = '<svg class="inline-arrow" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 17 17 5M8 5h9v9"/></svg>';
const closeIcon = '<svg class="inline-close" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 5 19 19M19 5 5 19"/></svg>';
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
} from "./ui.js?v=20261113-settings2";

// Dynamic imports with error boundaries
let loadEditor, loadPreview;

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

// Initialize modules
await loadEditorModule();

let page = document.body.dataset.page;
const content = document.querySelector("#content");

const topbarDate = document.querySelector("#topbar-date");
if (topbarDate) {
  const today = new Date();
  topbarDate.dateTime = today.toISOString().slice(0, 10);
  topbarDate.textContent = new Intl.DateTimeFormat("my-MM", { dateStyle: "medium" }).format(today);
}
function applyTheme(theme) {
  const next = theme === "dark" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  try { localStorage.setItem("dedc-theme", next); } catch {}
  document.querySelectorAll('input[name="theme-setting"]').forEach((input) => {
    input.checked = input.value === next;
  });
  const current = document.querySelector("#theme-current-label");
  if (current) current.textContent = next === "dark" ? "အမှောင်" : "အလင်း";
  const status = document.querySelector("#theme-status");
  if (status) status.textContent = `${next === "dark" ? "အမှောင်" : "အလင်း"} အပြင်အဆင်ကို ဤဘရောက်ဇာတွင် သိမ်းဆည်းထားပါသည်။`;
}
document.querySelector("[data-theme-toggle]")?.addEventListener("click", () => {
  applyTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark");
});

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
                `<a class="quick-link" href="${e(item.url)}"><div><strong>${e(item.title)}</strong><p>${e(label(item.type))}</p></div><span>${arrowIcon}</span></a>`,
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
const mobileSearch = document.querySelector("[data-mobile-search]");
if (mobileSearch) {
  mobileSearch.onclick = () => {
    const dialog = modal("အလုပ်ခွင်တွင် ရှာဖွေရန်", `<form id="mobile-search-form" class="field-stack"><label>စစ်တမ်းများ၊ မေးခွန်းများနှင့် အသုံးပြုသူများကို ရှာဖွေရန်<input name="query" type="search" minlength="2" required placeholder="အနည်းဆုံး စာလုံးနှစ်လုံး ရိုက်ထည့်ပါ"></label><div class="dialog-actions"><button class="button primary" type="submit">ရှာဖွေရန်</button></div></form>`);
    const form = dialog.querySelector("form");
    form.elements.query.focus();
    form.onsubmit = (event) => {
      event.preventDefault();
      dialog.close();
      searchWorkspace(form.elements.query.value);
    };
  };
}

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
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    mobileSearch?.click();
  }
  if (
    event.key === "/" &&
    !["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName)
  ) {
    event.preventDefault();
    mobileSearch?.click();
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

let surveyWizard = null;

function monthName(month) {
  return new Intl.DateTimeFormat("en", { month: "long" }).format(
    new Date(2000, month - 1, 1),
  );
}

function surveyAudienceLabel(orgType) {
  return label(orgType);
}

function getDefaultYearMonth() {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

const SURVEY_MONTH_NAMES = ["", "ဇန်နဝါရီ", "ဖေဖော်ဝါရီ", "မတ်", "ဧပြီ", "မေ", "ဇွန်", "ဇူလိုင်", "ဩဂုတ်", "စက်တင်ဘာ", "အောက်တိုဘာ", "နိုဝင်ဘာ", "ဒီဇင်ဘာ"];
const SURVEY_WIZARD_STEPS = ["အမျိုးအစား", "ခုနှစ်", "မေးခွန်းများ"];
const QUESTION_LABEL = "မေးခွန်း";
const WIZARD_CHECK_ICON = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12l5 5 9-9"/></svg>';

function wizardStepsHTML(active) {
  const items = SURVEY_WIZARD_STEPS.map((text, index) => {
    const step = index + 1;
    const state = step < active ? " is-done" : step === active ? " is-active" : "";
    return `<li class="wizard-steps__item${state}"${step === active ? ' aria-current="step"' : ""}><span class="wizard-steps__dot">${step < active ? WIZARD_CHECK_ICON : step}</span><span class="wizard-steps__label">${text}</span></li>`;
  });
  return `<ol class="wizard-steps">${items.join('<li class="wizard-steps__sep" aria-hidden="true"></li>')}</ol>`;
}

export async function createForm() {
  const defaults = getDefaultYearMonth();
  surveyWizard = {
    orgType: null,
    startYear: defaults.year,
    startMonth: defaults.month,
    endYear: defaults.year,
    endMonth: defaults.month,
    status: 1,
  };
  const dialog = modal("စစ်တမ်း အသစ်ဖန်တီးရန်", "");
  dialog.dataset.variant = "survey-wizard";
  renderSurveyAudienceStep(dialog);
}

function renderSurveyAudienceStep(dialog) {
  document.querySelector("#dialog-title").textContent = "စစ်တမ်း အသစ်ဖန်တီးရန်";
  const content = dialog.querySelector("#dialog-content");
  content.innerHTML = `
    ${wizardStepsHTML(1)}
    <div class="survey-wizard">
      <p class="dialog-intro">မည်သည့် ဖြေဆိုသူအုပ်စုအတွက် စစ်တမ်း ဖန်တီးမည်ကို ရွေးပါ။</p>
      <div class="survey-audience-grid">
        <button class="survey-audience-card" type="button" data-audience="university">
          <span class="survey-audience-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 9l9-5 9 5-9 5-9-5z"/><path d="M7 11v5c0 1 2.2 3 5 3s5-2 5-3v-5"/><path d="M21 9v5"/></svg></span>
          <strong>တက္ကသိုလ်</strong>
          <span>တက္ကသိုလ်များအတွက် စစ်တမ်း မေးခွန်းများ ဖန်တီးပါ</span>
        </button>
        <button class="survey-audience-card" type="button" data-audience="ministry">
          <span class="survey-audience-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-4h6v4M9 11h.01M15 11h.01"/></svg></span>
          <strong>ဝန်ကြီးဌာန</strong>
          <span>ဝန်ကြီးဌာနများအတွက် စစ်တမ်း မေးခွန်းများ ဖန်တီးပါ</span>
        </button>
      </div>
    </div>`;
  content.querySelectorAll("[data-audience]").forEach((button) => {
    button.onclick = () => {
      surveyWizard.orgType = button.dataset.audience;
      renderSurveyYearStep(dialog);
    };
  });
}

async function renderSurveyYearStep(dialog) {
  document.querySelector("#dialog-title").textContent = "ခုနှစ် ရွေးချယ်ရန်";
  const content = dialog.querySelector("#dialog-content");
  const monthOptions = (selected) => SURVEY_MONTH_NAMES
    .map((name, month) => (month ? `<option value="${month}"${month === selected ? " selected" : ""}>${name}</option>` : ""))
    .join("");
  content.innerHTML = `
    ${wizardStepsHTML(2)}
    <div class="survey-wizard">
      <div class="survey-wizard-summary"><span>အမျိုးအစား <strong>${e(surveyAudienceLabel(surveyWizard.orgType))}</strong></span></div>
      <p class="dialog-intro">စစ်တမ်း စတင်ရက် မှ ပြီးဆုံးရက် အထိ ရွေးပါ။</p>
      <div class="wizard-range">
        <div class="wizard-range__end">
          <span class="wizard-range__tag">စတင်ရက်</span>
          <div class="wizard-range__fields">
            <label class="wizard-field"><span>လ</span><select name="start-month">${monthOptions(surveyWizard.startMonth)}</select></label>
            <label class="wizard-field"><span>ခုနှစ်</span><input type="number" name="start-year" min="1900" max="2100" value="${surveyWizard.startYear}" inputmode="numeric" required></label>
          </div>
        </div>
        <span class="wizard-range__arrow" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></span>
        <div class="wizard-range__end">
          <span class="wizard-range__tag">ပြီးဆုံးရက်</span>
          <div class="wizard-range__fields">
            <label class="wizard-field"><span>လ</span><select name="end-month">${monthOptions(surveyWizard.endMonth)}</select></label>
            <label class="wizard-field"><span>ခုနှစ်</span><input type="number" name="end-year" min="1900" max="2100" value="${surveyWizard.endYear}" inputmode="numeric" required></label>
          </div>
        </div>
      </div>
      <label class="wizard-switch">
        <span class="sf-toggle"><input type="checkbox" name="publish" ${surveyWizard.status === 1 ? "checked" : ""}><span class="sf-toggle__track" aria-hidden="true"></span></span>
        <span class="wizard-switch__text"><strong>ချက်ချင်း ထုတ်ဝေရန်</strong></span>
      </label>
      <div class="survey-wizard-actions">
        <button class="button" type="button" data-back>နောက်သို့</button>
        <div class="right"><button class="button primary" type="button" data-next>ဆက်လုပ်ရန်</button></div>
      </div>
    </div>`;

  const startYear = content.querySelector('[name="start-year"]');
  const startMonth = content.querySelector('[name="start-month"]');
  const endYear = content.querySelector('[name="end-year"]');
  const endMonth = content.querySelector('[name="end-month"]');
  const publish = content.querySelector('input[name="publish"]');

  [startYear, startMonth, endYear, endMonth].forEach((field) => {
    field.oninput = () => field.setCustomValidity("");
    field.onchange = () => field.setCustomValidity("");
  });

  content.querySelector("[data-back]").onclick = () => renderSurveyAudienceStep(dialog);

  content.querySelector("[data-next]").onclick = () => {
    const sy = Number(startYear.value);
    const sm = Number(startMonth.value);
    const ey = Number(endYear.value);
    const em = Number(endMonth.value);

    if (!Number.isInteger(sy) || sy < 1900 || sy > 2100) {
      startYear.setCustomValidity("စတင်မှုခုနှစ်ကို 1900 မှ 2100 အတွင်း ထည့်ပါ။");
      startYear.reportValidity();
      return;
    }
    if (!Number.isInteger(sm) || sm < 1 || sm > 12) {
      startMonth.setCustomValidity("စတင်မှုလကို 1 မှ 12 အတွင်း ထည့်ပါ။");
      startMonth.reportValidity();
      return;
    }
    if (!Number.isInteger(ey) || ey < 1900 || ey > 2100) {
      endYear.setCustomValidity("ပြီးဆုံးခုနှစ်ကို 1900 မှ 2100 အတွင်း ထည့်ပါ။");
      endYear.reportValidity();
      return;
    }
    if (!Number.isInteger(em) || em < 1 || em > 12) {
      endMonth.setCustomValidity("ပြီးဆုံးလကို 1 မှ 12 အတွင်း ထည့်ပါ။");
      endMonth.reportValidity();
      return;
    }

    const start = sy * 100 + sm;
    const end = ey * 100 + em;
    if (start > end) {
      endYear.setCustomValidity("စတင်မှု ရက်စွဲသည် ပြီးဆုံး ရက်စွဲမှာ မဖြုတ်နိုင်ပါ။");
      endYear.reportValidity();
      return;
    }

    surveyWizard.startYear = sy;
    surveyWizard.startMonth = sm;
    surveyWizard.endYear = ey;
    surveyWizard.endMonth = em;
    surveyWizard.status = publish.checked ? 1 : 0;
    renderSurveyQuestionsStep(dialog);
  };
}

function surveyQuestionTemplate(index) {
  return `<div class="survey-question-row" data-survey-question>
    <span class="survey-question-num" aria-hidden="true"><span data-question-number>${index + 1}</span></span>
    <textarea data-question required maxlength="10000" rows="2" placeholder="မေးခွန်း စာသား ထည့်ပါ" aria-label="မေးခွန်း ${index + 1}"></textarea>
    <button class="icon-button" type="button" data-remove-question aria-label="မေးခွန်း ဖယ်ရှားရန်" title="မေးခွန်း ဖယ်ရှားရန်">${closeIcon}</button>
  </div>`;
}

function surveyGroupTemplate(index) {
  return `<fieldset class="survey-question-group" data-survey-group>
    <legend><span class="wizard-chip" data-group-number>${index + 1}</span>မေးခွန်း ခေါင်းစဉ်</legend>
    <label class="wizard-field"><span>ခေါင်းစဉ်</span><input type="text" data-group-title required maxlength="10000" placeholder="ဥပမာ ဒီဂျစ်တယ် အခြေခံအဆောက်အအုံ"></label>
    <div class="survey-group-questions" data-group-questions>${surveyQuestionTemplate(0)}</div>
    <div class="survey-group-actions">
      <button class="button small" type="button" data-add-question>+ မေးခွန်း ထပ်ထည့်ရန်</button>
      <button class="button small danger" type="button" data-remove-group>ခေါင်းစဉ် ဖယ်ရှားရန်</button>
    </div>
  </fieldset>`;
}

function renumberSurveyGroups(list) {
  [...list.querySelectorAll("[data-survey-group]")].forEach((group, groupIndex) => {
    group.querySelector("[data-group-number]").textContent = groupIndex + 1;
    [...group.querySelectorAll("[data-survey-question]")].forEach((row, questionIndex) => {
      row.querySelector("[data-question-number]").textContent = questionIndex + 1;
      row.querySelector("[data-question]").setAttribute("aria-label", `${QUESTION_LABEL} ${questionIndex + 1}`);
    });
  });
}

function collectSurveyGroups(form) {
  return [...form.querySelectorAll("[data-survey-group]")]
    .map((group) => {
      const title = group.querySelector("[data-group-title]").value.trim();
      const description = group.querySelector("[data-group-description]")?.value.trim();
      const questions = [...group.querySelectorAll("[data-question]")]
        .map((field) => field.value.trim())
        .filter(Boolean);
      return { title, description: description || null, questions };
    })
    .filter((group) => group.title && group.questions.length);
}

function renderSurveyQuestionsStep(dialog) {
  document.querySelector("#dialog-title").textContent = "မေးခွန်းများ ထည့်သွင်းရန်";
  const content = dialog.querySelector("#dialog-content");
  content.innerHTML = `
    ${wizardStepsHTML(3)}
    <form id="survey-wizard-form" class="survey-wizard" novalidate>
      <div class="survey-wizard-summary">
        <span>အမျိုးအစား <strong>${e(surveyAudienceLabel(surveyWizard.orgType))}</strong></span>
        <span>ခုနှစ် <strong>${e(surveyWizard.startYear + "/" + surveyWizard.startMonth + " မှ " + surveyWizard.endYear + "/" + surveyWizard.endMonth + " အထိ")}</strong></span>
      </div>
      <p class="dialog-intro">မေးခွန်း ခေါင်းစဉ်တစ်ခုနှင့် ယင်းအောက်ရှိ မေးခွန်းများကို ထည့်ပါ။ ခေါင်းစဉ်တစ်ခုတွင် မေးခွန်း မည်မျှပါဝင်သည်ကို သင်ကိုယ်တိုင် သတ်မှတ်နိုင်ပါသည်။</p>
      <div class="survey-group-list" data-group-list>${surveyGroupTemplate(0)}</div>
      <button class="wizard-add-group" type="button" data-add-group>+ မေးခွန်း ခေါင်းစဉ် ထပ်ထည့်ရန်</button>
      <div class="survey-wizard-actions">
        <button class="button" type="button" data-back>နောက်သို့</button>
        <div class="right"><button class="button primary" type="submit">စစ်တမ်း ဖန်တီးရန်</button></div>
      </div>
    </form>`;
  const form = content.querySelector("#survey-wizard-form");
  const list = content.querySelector("[data-group-list]");
  const bindQuestion = (row) => {
    const field = row.querySelector("[data-question]");
    field.oninput = () => field.setCustomValidity("");
    row.querySelector("[data-remove-question]").onclick = () => {
      const group = row.closest("[data-survey-group]");
      const questions = group.querySelectorAll("[data-survey-question]");
      if (questions.length === 1) {
        toast("အနည်းဆုံး မေးခွန်း တစ်ခု လိုအပ်ပါသည်။");
        return;
      }
      row.remove();
      renumberSurveyGroups(list);
    };
  };
  const bindGroup = (group) => {
    group.querySelectorAll("input,textarea").forEach((field) => {
      field.oninput = () => field.setCustomValidity("");
    });
    group.querySelectorAll("[data-survey-question]").forEach(bindQuestion);
    group.querySelector("[data-add-question]").onclick = () => {
      const container = group.querySelector("[data-group-questions]");
      container.insertAdjacentHTML(
        "beforeend",
        surveyQuestionTemplate(container.children.length),
      );
      const row = container.lastElementChild;
      bindQuestion(row);
      renumberSurveyGroups(list);
      row.querySelector("[data-question]").focus();
    };
    group.querySelector("[data-remove-group]").onclick = () => {
      if (list.children.length === 1) {
        toast("အနည်းဆုံး ခေါင်းစဉ် တစ်ခု လိုအပ်ပါသည်။");
        return;
      }
      group.remove();
      renumberSurveyGroups(list);
    };
  };
  list.querySelectorAll("[data-survey-group]").forEach(bindGroup);
  content.querySelector("[data-add-group]").onclick = () => {
    list.insertAdjacentHTML("beforeend", surveyGroupTemplate(list.children.length));
    bindGroup(list.lastElementChild);
    renumberSurveyGroups(list);
    list.lastElementChild.querySelector("[data-group-title]").focus();
  };
  content.querySelector("[data-back]").onclick = () => renderSurveyYearStep(dialog);
  form.onsubmit = (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const groups = collectSurveyGroups(form);
    if (!groups.length) {
      errorMessage(new Error("ခေါင်းစဉ်နှင့် မေးခွန်း အနည်းဆုံး တစ်ခု ထည့်ပါ။"));
      return;
    }
    const submitButton =
      event.submitter || form.querySelector('button[type="submit"]');
    busy(submitButton, async () => {
      try {
        const body = {
          org_type: surveyWizard.orgType,
          start_year: surveyWizard.startYear,
          start_month: surveyWizard.startMonth,
          end_year: surveyWizard.endYear,
          end_month: surveyWizard.endMonth,
          status: surveyWizard.status,
          groups,
        };
        await api("/survey/forms/create", { method: "POST", body });
        dialog.close();
        toast(
          `${surveyAudienceLabel(surveyWizard.orgType)} စစ်တမ်းကို ${surveyWizard.startYear + "/" + surveyWizard.startMonth + " မှ " + surveyWizard.endYear + "/" + surveyWizard.endMonth + " အထိ"} အတွက် ဖန်တီးပြီးပါပြီ။`,
        );
        if (location.pathname === "/dashboard/forms") await formsPage();
        else location.href = "/dashboard/forms";
      } catch (error) {
        errorMessage(error);
      }
    });
  };
}

// ============================================================
// Edit modal: question titles of one survey year (edit icon)
// ============================================================

let surveyEdit = null;

async function editSurveyYear(form) {
  if (!form) return;
  let data;
  try {
    data = await api(`/survey/builder/groups/${form.org_type}/${form.year_id}`);
  } catch (error) {
    toast(error.message);
    return;
  }
  surveyEdit = { form, groups: data.groups || [] };
  const dialog = modal("မေးခွန်း ခေါင်းစဉ်များ ပြင်ဆင်ရန်", "");
  dialog.dataset.variant = "survey-edit";
  renderSurveyGroupsList(dialog);
}

function renderSurveyGroupsList(dialog) {
  const { form, groups } = surveyEdit;
  document.querySelector("#dialog-title").textContent = "မေးခွန်း ခေါင်းစဉ်များ ပြင်ဆင်ရန်";
  const content = dialog.querySelector("#dialog-content");
  const rows = groups
    .map((group, index) => {
      const titleText = group.qTDetail || "ခေါင်းစဉ် မရွေးထားသော မေးခွန်းများ";
      return `<li class="survey-edit-group${group.qTID == null ? " is-untitled" : ""}">
        <span class="wizard-chip" aria-hidden="true">${index + 1}</span>
        <div class="survey-edit-group__body">
          <strong>${e(titleText)}</strong>
          <small>${QUESTION_LABEL} ${group.questions.length} ခု</small>
        </div>
        ${group.qTID == null
          ? ""
          : `<div class="survey-edit-group__actions">
          <button class="button small" type="button" data-edit-group="${group.qTID}">ပြင်ဆင်ရန်</button>
          <button class="button small danger" type="button" data-delete-group="${group.qTID}">ဖျက်ရန်</button>
        </div>`}
      </li>`;
    })
    .join("");
  content.innerHTML = `
    <div class="survey-wizard">
      <div class="survey-wizard-summary">
        <span>အမျိုးအစား <strong>${e(surveyOrgLabel(form.org_type))}</strong></span>
        <span>ခုနှစ် <strong>${e(formatYearRange(form))}</strong></span>
      </div>
      ${groups.length
        ? `<p class="dialog-intro">မေးခွန်း ခေါင်းစဉ်ကို ရွေးပါ။</p>
      <ul class="survey-edit-list">${rows}</ul>`
        : `<p class="dialog-intro">ဤစစ်တမ်းတွင် မေးခွန်း များ မရှိသေးပါ။</p>`}
    </div>`;
  content.querySelectorAll("[data-edit-group]").forEach(
    (button) =>
      (button.onclick = () => {
        const group = groups.find((g) => String(g.qTID) === button.dataset.editGroup);
        if (group) renderSurveyGroupEditor(dialog, group);
      }),
  );
  content.querySelectorAll("[data-delete-group]").forEach(
    (button) =>
      (button.onclick = () => {
        const group = groups.find((g) => String(g.qTID) === button.dataset.deleteGroup);
        if (group) renderSurveyGroupDelete(dialog, group);
      }),
  );
}

function surveyEditQuestionTemplate(index, question) {
  const idAttr = question ? ` data-question-id="${question.id}"` : "";
  const value = question ? e(question.detail) : "";
  return `<div class="survey-question-row" data-edit-question${idAttr}>
    <span class="survey-question-num" aria-hidden="true">${index + 1}</span>
    <textarea data-question required maxlength="10000" rows="2" placeholder="မေးခွန်း စာသား ထည့်ပါ" aria-label="${QUESTION_LABEL} ${index + 1}">${value}</textarea>
    <button class="icon-button" type="button" data-remove-question aria-label="မေးခွန်း ဖယ်ရှားရန်" title="မေးခွန်း ဖယ်ရှားရန်">${closeIcon}</button>
  </div>`;
}

function renderSurveyGroupEditor(dialog, group) {
  const { form } = surveyEdit;
  document.querySelector("#dialog-title").textContent = "ခေါင်းစဉ် ပြင်ဆင်ရန်";
  const content = dialog.querySelector("#dialog-content");
  content.innerHTML = `
    <form id="survey-edit-form" class="survey-wizard" novalidate>
      <div class="survey-wizard-summary">
        <span>အမျိုးအစား <strong>${e(surveyOrgLabel(form.org_type))}</strong></span>
        <span>ခုနှစ် <strong>${e(formatYearRange(form))}</strong></span>
      </div>
      <label class="wizard-field"><span>ခေါင်းစဉ်</span><input type="text" data-edit-title required maxlength="10000" value="${e(group.qTDetail || "")}"></label>
      <div class="survey-group-questions" data-edit-questions>
        ${group.questions.map((question, index) => surveyEditQuestionTemplate(index, question)).join("")}
      </div>
      <div class="survey-group-actions">
        <button class="button small" type="button" data-add-question>+ မေးခွန်း ထပ်ထည့်ရန်</button>
      </div>
      <div class="survey-wizard-actions">
        <button class="button" type="button" data-back>နောက်သို့</button>
        <div class="right"><button class="button primary" type="submit">သိမ်းဆည်းရန်</button></div>
      </div>
    </form>`;
  const editForm = content.querySelector("#survey-edit-form");
  const list = content.querySelector("[data-edit-questions]");
  const titleInput = content.querySelector("[data-edit-title]");
  titleInput.oninput = () => titleInput.setCustomValidity("");
  const renumberQuestions = () => {
    list.querySelectorAll("[data-edit-question]").forEach((row, index) => {
      row.querySelector(".survey-question-num").textContent = index + 1;
      row.querySelector("[data-question]").setAttribute("aria-label", `${QUESTION_LABEL} ${index + 1}`);
    });
  };
  const bindRow = (row) => {
    const field = row.querySelector("[data-question]");
    field.oninput = () => field.setCustomValidity("");
    row.querySelector("[data-remove-question]").onclick = () => {
      if (list.querySelectorAll("[data-edit-question]").length === 1) {
        toast("အနည်းဆုံး မေးခွန်း တစ်ခု လိုအပ်ပါသည်။");
        return;
      }
      row.remove();
      renumberQuestions();
    };
  };
  list.querySelectorAll("[data-edit-question]").forEach(bindRow);
  content.querySelector("[data-add-question]").onclick = () => {
    list.insertAdjacentHTML("beforeend", surveyEditQuestionTemplate(list.children.length, null));
    const row = list.lastElementChild;
    bindRow(row);
    renumberQuestions();
    row.querySelector("[data-question]").focus();
  };
  content.querySelector("[data-back]").onclick = () => renderSurveyGroupsList(dialog);
  editForm.onsubmit = (event) => {
    event.preventDefault();
    if (!editForm.reportValidity()) return;
    const title = titleInput.value.trim();
    const questions = [...list.querySelectorAll("[data-edit-question]")].map((row) => {
      const item = { detail: row.querySelector("[data-question]").value.trim() };
      if (row.dataset.questionId) item.id = Number(row.dataset.questionId);
      return item;
    });
    const submitButton = event.submitter || editForm.querySelector('button[type="submit"]');
    busy(submitButton, async () => {
      try {
        const updated = await api(
          `/survey/builder/groups/${form.org_type}/${form.year_id}/${group.qTID}`,
          { method: "PUT", body: { title, questions } },
        );
        group.qTID = updated.qTID;
        group.qTDetail = updated.qTDetail;
        group.questions = updated.questions;
        toast("ခေါင်းစဉ်နှင့် မေးခွန်းများ သိမ်းဆည်းပြီးပါပြီ။");
        renderSurveyGroupsList(dialog);
      } catch (error) {
        errorMessage(error);
      }
    });
  };
}

function renderSurveyGroupDelete(dialog, group) {
  const { form } = surveyEdit;
  document.querySelector("#dialog-title").textContent = "ခေါင်းစဉ်ကို ဖျက်မလား။";
  const content = dialog.querySelector("#dialog-content");
  content.innerHTML = `
    <p id="delete-group-description">“${e(group.qTDetail || "ခေါင်းစဉ် မရွေးထားသော မေးခွန်းများ")}” ၎င်းအောက်ရှိ မေးခွန်းများ အားလုံးကို အပြီးအပိုင် ဖျက်ပစ်ပါမည်။ ပြန်လည်ရယူ၍ မရနိုင်ပါ။</p>
    <div class="dialog-actions">
      <button class="button" type="button" data-cancel-group>မလုပ်တော့ပါ</button>
      <button class="button danger" type="button" data-confirm-group>ခေါင်းစဉ် ဖျက်ရန်</button>
    </div>`;
  dialog.setAttribute("aria-describedby", "delete-group-description");
  const cleanup = () => dialog.removeAttribute("aria-describedby");
  const cancelButton = content.querySelector("[data-cancel-group]");
  const confirmButton = content.querySelector("[data-confirm-group]");
  cancelButton.onclick = () => {
    cleanup();
    renderSurveyGroupsList(dialog);
  };
  cancelButton.focus();
  confirmButton.onclick = () =>
    busy(confirmButton, async () => {
      const preventClose = (event) => event.preventDefault();
      const closeButton = dialog.querySelector("[data-close-dialog]");
      closeButton.disabled = true;
      dialog.dataset.deleting = "true";
      dialog.addEventListener("cancel", preventClose);
      try {
        await api(`/survey/builder/groups/${form.org_type}/${form.year_id}/${group.qTID}`, { method: "DELETE" });
        surveyEdit.groups = surveyEdit.groups.filter((g) => g !== group);
        cleanup();
        toast("ခေါင်းစဉ်နှင့် မေးခွန်းများ ဖျက်ပြီးပါပြီ။");
        renderSurveyGroupsList(dialog);
        if (location.pathname === "/dashboard/forms") await formsPage();
      } catch (error) {
        errorMessage(error);
      } finally {
        closeButton.disabled = false;
        delete dialog.dataset.deleting;
        dialog.removeEventListener("cancel", preventClose);
      }
    });
}

async function overview() {
  describe("မေးခွန်းများ၊ အဖွဲ့အစည်းများနှင့် စစ်တမ်းများ၏ လက်ရှိအခြေအနေ");
  document.querySelector(".page-heading h1").textContent = "လုပ်ငန်းအကျဉ်းချုပ်";
  document.querySelector("#page-description").append(" · " + new Intl.DateTimeFormat("my-MM", { dateStyle: "long" }).format(new Date()));
  try {
    const data = await api("/overview");
    const yearly = data.completed_by_year;
    const seriesTotal = (items) => items.reduce(
      (sum, item) => sum + item.values.reduce((count, value) => count + value, 0), 0,
    );
    const universityCompleted = seriesTotal(yearly.university.series);
    const ministryCompleted = seriesTotal(yearly.ministry.series);
    const completedTotal = universityCompleted + ministryCompleted;
    const formStatus = data.form_status;
    const statusTotal = formStatus.published + formStatus.draft;
    const publishedShare = statusTotal ? (formStatus.published / statusTotal) * 100 : 0;
    actions(`<a class="button" href="/dashboard/reports">အစီရင်ခံစာ ထုတ်ယူရန်</a><button class="button primary" id="create-action">စစ်တမ်း အသစ်ဖန်တီးရန်</button>`);
    const directory = data.directory_stats;
    const metricCards = [
      ["University မေးခွန်း", directory.university_questions, "ထုတ်ဝေထားသော စစ်တမ်း", "/dashboard/forms?org_type=university", SURVEY_ICONS.questions],
      ["Ministry မေးခွန်း", directory.ministry_questions, "ထုတ်ဝေထားသော စစ်တမ်း", "/dashboard/forms?org_type=ministry", SURVEY_ICONS.questions],
      ["University အရေအတွက်", directory.universities, "အဖွဲ့အစည်း", "/dashboard/departments", SURVEY_ICONS.building],
      ["Ministry အရေအတွက်", directory.ministries, "အဖွဲ့အစည်း", "/dashboard/ministries", SURVEY_ICONS.landmark],
    ].map(([label, value, kind, href, icon]) => `<a class="sf-kpi overview-metric" href="${href}"><span class="sf-kpi__icon" aria-hidden="true">${icon}</span><span class="sf-kpi__body"><strong>${value.toLocaleString()}</strong><span class="sf-kpi__label">${label}</span><small class="sf-kpi__hint">${kind}</small></span></a>`).join("");
    const shortcutLinks = [
      ["စစ်တမ်းများ", "/dashboard/forms"],
      ["အစီရင်ခံစာများ", "/dashboard/reports"],
      ["တက္ကသိုလ်များ", "/dashboard/departments"],
      ["ဝန်ကြီးဌာနများ", "/dashboard/ministries"],
    ].map(([title, url]) => `<a class="overview-shortcut" href="${url}">${title}<span aria-hidden="true">${arrowIcon}</span></a>`).join("");
    setContent(`
      <section class="overview-metrics" aria-labelledby="overview-metrics-title"><div class="overview-section-head"><h2 id="overview-metrics-title">စစ်တမ်း အချက်အလက်</h2><p>ထုတ်ဝေထားသော မေးခွန်းများ · အဖွဲ့အစည်း စုစုပေါင်း</p></div><div class="stats">${metricCards}</div></section>
      <nav class="overview-shortcuts" aria-label="အမြန်သွားရန်"><strong>ဆက်လုပ်ဆောင်ရန်</strong>${shortcutLinks}</nav>
      <div class="overview-main">
        <section class="panel trend-panel"><div class="panel-head"><div><h2>တင်သွင်းမှု လှုပ်ရှားမှု</h2><p>တင်သွင်းသည့် နှစ်အလိုက် ဖြေဆိုပြီး မေးခွန်းများ</p></div><a class="table-link" href="/dashboard/reports">အစီရင်ခံစာများ ${arrowIcon}</a></div><div class="panel-body"><div class="chart-summary"><strong>${completedTotal.toLocaleString()}</strong><span>ဖြေဆိုပြီး မေးခွန်း စုစုပေါင်း</span></div><div class="answer-chart-grid"><article class="answer-chart-card"><div class="answer-chart-card__head"><h3><i class="answer-dot answer-dot--university" aria-hidden="true"></i>University</h3><strong>${universityCompleted.toLocaleString()}</strong></div><div id="overview-trend-university" class="overview-trend"></div></article><article class="answer-chart-card"><div class="answer-chart-card__head"><h3><i class="answer-dot answer-dot--ministry" aria-hidden="true"></i>Ministry</h3><strong>${ministryCompleted.toLocaleString()}</strong></div><div id="overview-trend-ministry" class="overview-trend"></div></article></div></div></section>
        <section class="panel status-panel"><div class="panel-head"><div><h2>စစ်တမ်း အခြေအနေ</h2><p>မူကြမ်းနှင့် ထုတ်ဝေထားသော စစ်တမ်းများ</p></div><a class="table-link" href="/dashboard/forms">စစ်တမ်းများ ${arrowIcon}</a></div><div class="panel-body"><div class="status-chart-layout"><div class="status-pie ${statusTotal ? '' : 'status-pie--empty'}" style="--published-share:${publishedShare}%" role="img" aria-label="ထုတ်ဝေထားသည် ${formStatus.published} ခု၊ မူကြမ်း ${formStatus.draft} ခု"></div><div class="status-details"><div class="status-total"><strong>${statusTotal.toLocaleString()}</strong><span>လက်ရှိ စစ်တမ်းများ</span></div><ul class="status-legend"><li><span><i class="status-dot status-dot--published"></i>ထုတ်ဝေထားသည်</span><strong>${formStatus.published.toLocaleString()}</strong></li><li><span><i class="status-dot status-dot--draft"></i>မူကြမ်း</span><strong>${formStatus.draft.toLocaleString()}</strong></li></ul></div></div></div></section>
      </div>
    `);
    document.querySelector('#create-action').onclick = createForm;
    for (const audience of ["university", "ministry"]) {
      renderYearlyBars(
        document.querySelector(`#overview-trend-${audience}`),
        yearly.years,
        yearly[audience].series,
        audience === "university" ? "University" : "Ministry",
      );
    }
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
        "စစ်တမ်းအသစ် ဖန်တီးရန် စတင်ပါ။",
        button("စစ်တမ်း အသစ်ဖန်တီးရန်", "/dashboard/forms"),
      );
}
// ============================================================
// Forms page — DEDC survey board (native `year` surveys)
// ============================================================

const SURVEY_ORG_META = {
  university: {
    label: "တက္ကသိုလ်",
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 9l9-5 9 5-9 5-9-5z"/><path d="M7 11v5c0 1 2.2 3 5 3s5-2 5-3v-5"/><path d="M21 9v5"/></svg>',
  },
  ministry: {
    label: "ဝန်ကြီးဌာန",
    icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-4h6v4M9 11h.01M15 11h.01"/></svg>',
  },
};

const SURVEY_ICONS = {
  forms: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 8h6M9 12h6M9 16h3"/></svg>',
  titles: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16M4 5v13a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1V5"/><path d="M8 10h8M8 14h5"/></svg>',
  questions: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 4h16v13H9l-5 4zM9 8a3 3 0 0 1 6 0c0 2-3 2-3 4m0 2h.01"/></svg>',
  period: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/></svg>',
  eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>',
  edit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>',
  trash: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>',
  building: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21h18M5 21V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v16M8 7h2M8 11h2M8 15h2M16 9h2a2 2 0 0 1 2 2v10"/></svg>',
  landmark: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 21h18M4 9h16M6 9V6l6-3 6 3v3M7 9v9M12 9v9M17 9v9"/></svg>',
};

const REPORT_ICONS = {
  years: SURVEY_ICONS.period,
  universities: SURVEY_ICONS.building,
  reports: SURVEY_ICONS.forms,
  completion:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="m8 12 2.6 2.6L16.5 9"/></svg>',
  clock:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
  trend:
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 18V6M4 18h16"/><path d="m7 14 4-4 3 2 4-5"/></svg>',
};

function surveyOrgLabel(orgType) {
  return SURVEY_ORG_META[orgType]?.label || label(orgType);
}

function formatYearRange(form) {
  // Format: "2026 March to 2027 November" in Myanmar numerals
  const monthNames = SURVEY_MONTH_NAMES;
  const startYear = form.year_from;
  const startMonth = form.month_from;
  const endYear = form.year_to;
  const endMonth = form.month_to;
  if (startYear && endYear && startMonth && endMonth) {
    return `${startYear} ${monthNames[startMonth]} မှ ${endYear} ${monthNames[endMonth]} အထိ`;
  } else if (form.year_label) {
    return form.year_label;
  }
  return "";
}

function surveyKpiCard({ icon, value, title, hint, tone }) {
  return `<div class="sf-kpi sf-kpi--${tone}">
    <span class="sf-kpi__icon" aria-hidden="true">${icon}</span>
    <div class="sf-kpi__body">
      <strong>${value}</strong>
      <span class="sf-kpi__label">${title}</span>
      <small class="sf-kpi__hint">${hint}</small>
    </div>
  </div>`;
}

function surveyOrgPill(orgType) {
  const meta = SURVEY_ORG_META[orgType] || { label: surveyOrgLabel(orgType), icon: "" };
  return `<span class="sf-org sf-org--${e(orgType)}">${meta.icon}<span>${e(meta.label)}</span></span>`;
}

function surveyToggle(form) {
  const published = form.year_status === 1 || form.is_active;
  return `<label class="sf-toggle">
    <input type="checkbox" data-toggle-status data-year-id="${form.year_id}" data-org-type="${e(form.org_type)}" ${published ? "checked" : ""} aria-label="${e(surveyOrgLabel(form.org_type))} စစ်တမ်း ထုတ်ဝေမှု">
    <span class="sf-toggle__track" aria-hidden="true"></span>
  </label>`;
}

function surveyStatusBadge(form) {
  const published = form.year_status === 1 || form.is_active;
  return `<span class="sf-status ${published ? "sf-status--published" : "sf-status--draft"}">
    <span class="sf-status__dot" aria-hidden="true"></span>${published ? "ထုတ်ဝေထားသည်" : "မူကြမ်း"}
  </span>`;
}

function surveyRow(form) {
  const yearRange = formatYearRange(form);
  const titleCount = form.question_title_count ?? 0;
  const questionCount = form.question_count ?? 0;
  return `<tr class="sf-row sf-row--${e(form.org_type)}">
    <td class="sf-cell-period">
      <span class="sf-period-icon" aria-hidden="true">${SURVEY_ICONS.period}</span>
      <div class="sf-period">
        <strong>${e(yearRange || "ကာလ မသတ်မှတ်ထားပါ")}</strong>
      </div>
    </td>
    <td>${surveyOrgPill(form.org_type)}</td>
    <td class="numeric"><span class="sf-count sf-count--titles" title="ကွဲပြားသော မေးခွန်းခေါင်းစဉ် အရေအတွက်">${titleCount}</span></td>
    <td class="numeric"><span class="sf-count sf-count--questions">${questionCount}</span></td>
    <td class="sf-cell-status">
      <div class="sf-status-group">
        ${surveyToggle(form)}
        ${surveyStatusBadge(form)}
      </div>
    </td>
    <td class="sf-cell-actions">
      <div class="sf-actions">
        <button type="button" class="icon-button" data-detail-year="${form.year_id}" data-org-type="${e(form.org_type)}" title="အသေးစိတ် ကြည့်ရန်" aria-label="${e(yearRange)} — အသေးစိတ် ကြည့်ရန်">${SURVEY_ICONS.eye}</button>
        <button type="button" class="icon-button" data-edit-year="${form.year_id}" data-org-type="${e(form.org_type)}" title="မေးခွန်း ခေါင်းစဉ်များ ပြင်ဆင်ရန်" aria-label="${e(yearRange)} — မေးခွန်း ခေါင်းစဉ်များ ပြင်ဆင်ရန်">${SURVEY_ICONS.edit}</button>
        <button type="button" class="icon-button danger" data-delete-year="${form.year_id}" data-org-type="${e(form.org_type)}" title="ဖျက်ရန်" aria-label="${e(yearRange)} — ဖျက်ရန်">${SURVEY_ICONS.trash}</button>
      </div>
    </td>
  </tr>`;
}

function surveyBoard(surveys, orgFilter, search) {
  const rows = orgFilter
    ? surveys.filter((form) => form.org_type === orgFilter)
    : surveys;
  const params = new URLSearchParams(location.search);
  const pageSize = Math.max(1, Number(params.get("limit") || 25));
  const page = Math.max(1, Number(params.get("page") || 1) || 1);
  const pageRows = rows.slice((page - 1) * pageSize, page * pageSize);
  const counts = {
    all: surveys.length,
    university: surveys.filter((form) => form.org_type === "university").length,
    ministry: surveys.filter((form) => form.org_type === "ministry").length,
  };
  const totalQuestions = surveys.reduce((sum, form) => sum + (form.question_count || 0), 0);
  const totalTitles = surveys.reduce((sum, form) => sum + (form.question_title_count || 0), 0);

  const segments = [
    { value: "", label: "အားလုံး", count: counts.all, dot: false },
    { value: "university", label: "တက္ကသိုလ်", count: counts.university, dot: "university" },
    { value: "ministry", label: "ဝန်ကြီးဌာန", count: counts.ministry, dot: "ministry" },
  ];

  return `
  <section class="sf-stage" aria-label="DEDC စစ်တမ်းများ">
    <div class="sf-kpis">
      ${surveyKpiCard({ icon: SURVEY_ICONS.forms, value: counts.all.toLocaleString(), title: "စစ်တမ်း စုစုပေါင်း", hint: `${counts.university} တက္ကသိုလ် · ${counts.ministry} ဝန်ကြီးဌာန`, tone: "total" })}
      ${surveyKpiCard({ icon: SURVEY_ICONS.titles, value: totalTitles.toLocaleString(), title: "မေးခွန်း ခေါင်းစဉ်များ", hint: "ကွဲပြားသော ခေါင်းစဉ် အရေအတွက်", tone: "titles" })}
      ${surveyKpiCard({ icon: SURVEY_ICONS.questions, value: totalQuestions.toLocaleString(), title: "မေးခွန်း စုစုပေါင်း", hint: "စစ်တမ်းများတွင် ပါဝင်သည့် မေးခွန်းများ", tone: "questions" })}
      ${surveyKpiCard({ icon: SURVEY_ICONS.edit, value: (counts.all ? Math.round((surveys.filter((form) => (form.year_status === 1 || form.is_active)).length / counts.all) * 100) : 0) + "%", title: "ထုတ်ဝေထားသည်", hint: "ဖြေဆိုသူများ ဝင်ရောက်နိုင်သည်", tone: "published" })}
    </div>
    <section class="sf-board" aria-label="စစ်တမ်း စာရင်း">
      <div class="sf-toolbar">
        <div class="sf-segmented" role="group" aria-label="ဖြေဆိုသူ အုပ်စု အားဖြင့် စစ်ထုတ်ရန်">
          ${segments.map((segment) => `
          <button type="button" class="sf-seg ${orgFilter === segment.value ? "is-active" : ""}" data-org-filter="${segment.value}" aria-pressed="${orgFilter === segment.value}">
            ${segment.dot ? `<span class="sf-seg__dot sf-seg__dot--${segment.dot}" aria-hidden="true"></span>` : ""}
            <span>${segment.label}</span><span class="sf-seg__count">${segment.count}</span>
          </button>`).join("")}
        </div>
        <p class="sf-toolbar__summary">${rows.length ? `စစ်တမ်း <strong>${rows.length}</strong> ခု ပြသနေသည်${orgFilter ? ` · ${surveyOrgLabel(orgFilter)}` : ""}` : ""}</p>
        <form class="sf-search" data-filter-form role="search">
          <input type="hidden" name="org_type" value="${e(orgFilter)}">
          ${SURVEY_ICONS.search}<input type="search" name="search" placeholder="ကာလ သို့မဟုတ် အမျိုးအစား ရှာဖွေရန်…" value="${e(search)}" aria-label="စစ်တမ်းများ ရှာဖွေရန်">
          <button class="button small" type="submit">ရှာဖွေရန်</button>

        </form>
      </div>
      ${rows.length
        ? `<div class="table-wrap sf-table-wrap" tabindex="0" role="region" aria-label="ဘေးတိုက် လှိမ့်ကြည့်နိုင်သော စစ်တမ်း စာရင်း"><table class="sf-table">
          <thead><tr>
            <th scope="col">စစ်တမ်းကာလ</th>
            <th scope="col">အမျိုးအစား</th>
            <th scope="col" class="numeric"><span class="sf-th-hint">ခေါင်းစဉ်များ</span><small>ကွဲပြားသော ခေါင်းစဉ်</small></th>
            <th scope="col" class="numeric"><span class="sf-th-hint">မေးခွန်းများ</span><small>စုစုပေါင်း မေးခွန်း</small></th>
            <th scope="col">အခြေအနေ / ထုတ်ဝေမှု</th>
            <th scope="col">လုပ်ဆောင်ချက်များ</th>
          </tr></thead>
          <tbody>${pageRows.map(surveyRow).join("")}</tbody>
        </table></div>
        <footer class="sf-board__footer">
          <span>${pageRows.length.toLocaleString()} / ${rows.length.toLocaleString()} စစ်တမ်း ပြသနေသည်</span>
          <div class="sf-legend" aria-hidden="true">
            <span class="sf-legend__item"><i class="sf-legend__dot sf-legend__dot--university"></i>တက္ကသိုလ်</span>
            <span class="sf-legend__item"><i class="sf-legend__dot sf-legend__dot--ministry"></i>ဝန်ကြီးဌာန</span>
          </div>
        </footer>
        ${pagination(rows.length)}`
        : `<div class="sf-empty">${empty(
            search || orgFilter ? "ကိုက်ညီသော စစ်တမ်း မရှိပါ" : "နောက်စစ်တမ်းကို ဤနေရာမှ စတင်ပါ",
            search || orgFilter
              ? "အခြားကာလတစ်ခု စမ်းကြည့်ပါ သို့မဟုတ် စစ်ထုတ်မှုများကို ရှင်းလင်းပြီး စစ်တမ်းအားလုံးကို ကြည့်ပါ။"
              : "စစ်တမ်းအသစ် ဖန်တီးရန် စတင်ပါ။",
            search || orgFilter ? button("စစ်ထုတ်မှု ရှင်းလင်းရန်", "/dashboard/forms") : button("စစ်တမ်း အသစ်ဖန်တီးရန်", "/dashboard/forms"),
          )}</div>`}
    </section>
  </section>`;
}

function findSurvey(yearId, orgType) {
  return surveyBoardData.find(
    (form) => form.year_id == yearId && form.org_type === orgType,
  );
}

async function showSurveyDetail(form) {
  if (!form) return;
  try {
    const questions = await api(
      `/survey/questions/${form.org_type}/by-year/${form.year_id}`,
    );
    const groups = [];
    const index = new Map();
    for (const question of questions) {
      const key = question.qTDetail || "ခေါင်းစဉ် မရွေးထားသော မေးခွန်းများ";
      if (!index.has(key)) {
        const group = { title: key, description: question.title_description, questions: [] };
        index.set(key, group);
        groups.push(group);
      }
      index.get(key).questions.push(question.uQDetail || question.mQDetail || "—");
    }
    modal(
      "စစ်တမ်း အသေးစိတ်",
      `<div class="sf-detail">
        <div class="sf-detail__meta">
          ${surveyOrgPill(form.org_type)}
          <span class="sf-detail__period">${SURVEY_ICONS.period}<span>${e(formatYearRange(form))}</span></span>
        </div>
        <p class="sf-detail__summary">ခေါင်းစဉ် <strong>${groups.length}</strong> ခု · မေးခွန်း <strong>${questions.length}</strong> ခု ပါဝင်သည်။</p>
        ${groups.length
          ? groups
              .map(
                (group) => `<section class="sf-detail__group">
                  <h3><span>${e(group.title)}</span><span class="sf-detail__count">${group.questions.length}</span></h3>
                  ${group.description ? `<p>${e(group.description)}</p>` : ""}
                  <ol>${group.questions.map((question) => `<li>${e(question)}</li>`).join("")}</ol>
                </section>`,
              )
              .join("")
          : `<p class="sf-detail__summary">ဤစစ်တမ်းတွင် မေးခွန်း များ မရှိသေးပါ။</p>`}
      </div>`,
    );
  } catch (error) {
    toast(error.message);
  }
}

function deleteSurveyYear(form) {
  if (!form) return;
  const yearRange = formatYearRange(form);
  confirmDelete(
    "စစ်တမ်းကို ဖျက်မလား။",
    `“${yearRange}” ${surveyOrgLabel(form.org_type)} စစ်တမ်းကာလနှင့် ၎င်းအောက်ရှိ မေးခွန်းများ အားလုံးကို အပြီးအပိုင် ဖျက်ပစ်ပါမည်။ ပြန်လည်ရယူ၍ မရနိုင်ပါ။`,
    "စစ်တမ်းကာလ ဖျက်ရန်",
    async () => {
      await api(`/survey/years/${form.year_id}`, { method: "DELETE" });
      toast("စစ်တမ်းကာလ ဖျက်ပြီးပါပြီ။");
      await load();
    },
  );
}

let surveyBoardData = [];

async function formsPage() {
  describe(
    "DEDC ဒေတာဘေ့စ်ရှိ တက္ကသိုလ်နှင့် ဝန်ကြီးဌာန စစ်တမ်းများကို ကြည့်ရှုပါ။ အုပ်စုအားဖြင့် စစ်ထုတ်ပြီး ထုတ်ဝေမှုကို ထိန်းချုပ်နိုင်ပါသည်။",
  );
  const p = new URLSearchParams(location.search);
  const orgFilter = ["university", "ministry"].includes(p.get("org_type"))
    ? p.get("org_type")
    : "";
  const search = (p.get("search") || "").trim();
  let surveys = [];
  try {
    const params = new URLSearchParams({ limit: "100" });
    if (search) params.set("search", search);
    surveys = await api("/survey/forms?" + params);
  } catch (error) {
    console.error("Could not load native DEDC surveys:", error);
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry").onclick = formsPage;
    return;
  }
  surveyBoardData = surveys;
  actions(
    `<button class="button primary" id="create-action">စစ်တမ်း အသစ်ဖန်တီးရန်</button>`,
  );
  setContent(surveyBoard(surveys, orgFilter, search));
  document.querySelector("#create-action").onclick = createForm;
  bindFilters(load);

  // Segmented audience filter (all / university / ministry)
  document.querySelectorAll("[data-org-filter]").forEach((button) => {
    button.onclick = () => {
      const value = button.dataset.orgFilter;
      const params = new URLSearchParams(location.search);
      params.delete("page");
      if (value) params.set("org_type", value);
      else params.delete("org_type");
      const query = params.toString();
      history.pushState({}, "", location.pathname + (query ? "?" + query : ""));
      load();
    };
  });

  // Publish toggle for a survey year
  document.querySelectorAll("[data-toggle-status]").forEach((control) => {
    control.addEventListener("change", async () => {
      const yearId = control.dataset.yearId;
      const form = findSurvey(yearId, control.dataset.orgType);
      const published = control.checked;
      try {
        await api(`/survey/years/${yearId}`, {
          method: "PUT",
          body: {
            year_from: form?.month_from || 1,
            year_to: form?.year_to || new Date().getFullYear(),
            status: published ? 1 : 0,
          },
        });
        const badge = control.closest("tr")?.querySelector(".sf-status");
        if (badge) {
          badge.className = `sf-status ${published ? "sf-status--published" : "sf-status--draft"}`;
          badge.innerHTML = `<span class="sf-status__dot" aria-hidden="true"></span>${published ? "ထုတ်ဝေထားသည်" : "မူကြမ်း"}`;
        }
        toast(published ? "စစ်တမ်းကို ထုတ်ဝေပြီးပါပြီ။" : "စစ်တမ်းကို မူကြမ်း အဖြစ် ပြောင်းလဲပြီးပါပြီ။");
      } catch (error) {
        control.checked = !published;
        toast(error.message);
      }
    });
  });

  // Row actions
  document.querySelectorAll("[data-edit-year]").forEach(
    (button) =>
      (button.onclick = () =>
        editSurveyYear(
          findSurvey(button.dataset.editYear, button.dataset.orgType),
        )),
  );
  document.querySelectorAll("[data-detail-year]").forEach(
    (button) =>
      (button.onclick = () =>
        showSurveyDetail(
          findSurvey(button.dataset.detailYear, button.dataset.orgType),
        )),
  );
  document.querySelectorAll("[data-delete-year]").forEach(
    (button) =>
      (button.onclick = () =>
        deleteSurveyYear(
          findSurvey(button.dataset.deleteYear, button.dataset.orgType),
          button,
        )),
  );
}


async function departments() {
  describe("စနစ်တွင် သတ်မှတ်ထားသော တက္ကသိုလ်များကို စီမံခန့်ခွဲပါ။");
  try {
    const params = new URLSearchParams(location.search);
    params.set("limit", params.get("limit") || "25");
    const data = await api("/universities?" + params);
    const rows = data.items;
    const total = data.total;
    const search = params.get("search") || "";
    actions('<button class="button primary" id="add-org">တက္ကသိုလ် ထည့်ရန်</button>');
    setContent(`<section class="panel directory-page">
      <div class="panel-head">
        <div class="directory-title">
          <span class="directory-title__icon">${SURVEY_ICONS.building}</span>
          <div>
            <h2>တက္ကသိုလ် လမ်းညွှန် <span class="inline-count">${total.toLocaleString()}</span></h2>
            <p>စနစ်တွင် သတ်မှတ်ထားသော တက္ကသိုလ်များကို တစ်နေရာတည်းတွင် စီမံပါ</p>
          </div>
        </div>
      </div>
      <div class="directory-toolbar">
        <form class="directory-search" data-filter-form>
          ${SURVEY_ICONS.search}
          <input type="search" name="search" aria-label="တက္ကသိုလ်များ ရှာဖွေရန်" placeholder="တက္ကသိုလ်အမည် ရှာဖွေရန်…" value="${e(search)}">
          ${search ? '<a class="directory-search__clear" href="/dashboard/departments" aria-label="ရှာဖွေမှု ရှင်းလင်းရန်" title="ရှာဖွေမှု ရှင်းလင်းရန်">' + closeIcon + '</a>' : ""}
        </form>
        <span class="directory-count"><strong>${total.toLocaleString()}</strong> တက္ကသိုလ်</span>
      </div>
      ${rows.length
        ? table(
            ["တက္ကသိုလ်အမည်", "အမျိုးအစား", "လုပ်ဆောင်ချက်များ"],
            rows.map(
              (uni) => `<tr>
                <td class="title"><div class="uni-cell"><span class="uni-cell__mark">${SURVEY_ICONS.building}</span><div><strong>${e(uni.name)}</strong></div></div></td>
                <td><span class="uni-type">${e(uni.type || "မသတ်မှတ်ထားပါ")}</span></td>
                <td><div class="row-actions"><button class="button small" data-edit-org="${uni.id}">${SURVEY_ICONS.edit}<span>ပြင်ဆင်ရန်</span></button><button class="button small danger" data-delete-org="${uni.id}">${SURVEY_ICONS.trash}<span>ဖျက်ရန်</span></button></div></td>
              </tr>`,
            ),
          )
        : empty(
            search ? "ကိုက်ညီသော တက္ကသိုလ် မရှိပါ" : "တက္ကသိုလ် မထည့်ရသေးပါ",
            search
              ? "အခြားအမည်တစ်ခု စမ်းကြည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ရှင်းလင်းပါ။"
              : "စနစ်တွင် ပါဝင်မည့် ပထမဆုံး တက္ကသိုလ်ကို ထည့်ပါ။",
            search
              ? button("ရှာဖွေမှု ရှင်းလင်းရန်", "/dashboard/departments")
              : '<button class="button" data-add-department>ပထမဆုံး တက္ကသိုလ် ထည့်ရန်</button>',
          )}
      ${total ? pagination(total) : ""}
    </section>`);
    document.querySelector("#add-org").onclick = () => openAddOrgDialog();
    document.querySelector("[data-add-department]")?.addEventListener("click", () => openAddOrgDialog());
    document.querySelectorAll("[data-edit-org]").forEach((button) => {
      button.onclick = () => openAddOrgDialog(rows.find((uni) => uni.id === Number(button.dataset.editOrg)));
    });
    document.querySelectorAll("[data-delete-org]").forEach((button) => {
      button.onclick = () => deleteOrg(Number(button.dataset.deleteOrg), button);
    });
    bindFilters(load);
  } catch (error) {
    setContent(`<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`);
    document.querySelector("#retry").onclick = departments;
  }
}

async function ministries() {
  describe("စနစ်တွင် သတ်မှတ်ထားသော ဝန်ကြီးဌာနများကို စီမံခန့်ခွဲပါ။");
  try {
    const params = new URLSearchParams(location.search);
    params.set("limit", params.get("limit") || "25");
    const data = await api("/ministries?" + params);
    const rows = data.items;
    const total = data.total;
    const search = params.get("search") || "";
    actions('<button class="button primary" id="add-ministry">ဝန်ကြီးဌာန ထည့်ရန်</button>');
    setContent(`<section class="panel directory-page ministry-directory">
      <div class="panel-head">
        <div class="directory-title">
          <span class="directory-title__icon">${SURVEY_ICONS.landmark}</span>
          <div>
            <h2>ဝန်ကြီးဌာန လမ်းညွှန် <span class="inline-count">${total.toLocaleString()}</span></h2>
            <p>စနစ်တွင် သတ်မှတ်ထားသော ဝန်ကြီးဌာနများကို တစ်နေရာတည်းတွင် စီမံပါ</p>
          </div>
        </div>
      </div>
      <div class="directory-toolbar">
        <form class="directory-search" data-filter-form>
          ${SURVEY_ICONS.search}
          <input type="search" name="search" aria-label="ဝန်ကြီးဌာနများ ရှာဖွေရန်" placeholder="ဝန်ကြီးဌာနအမည် ရှာဖွေရန်…" value="${e(search)}">
          ${search ? '<a class="directory-search__clear" href="/dashboard/ministries" aria-label="ရှာဖွေမှု ရှင်းလင်းရန်" title="ရှာဖွေမှု ရှင်းလင်းရန်">' + closeIcon + '</a>' : ""}
        </form>
        <span class="directory-count"><strong>${total.toLocaleString()}</strong> ဝန်ကြီးဌာန</span>
      </div>
      ${rows.length
        ? table(
            ["ဝန်ကြီးဌာနအမည်", "လုပ်ဆောင်ချက်များ"],
            rows.map(
              (ministry) => `<tr>
                <td class="title"><div class="uni-cell"><span class="uni-cell__mark">${SURVEY_ICONS.landmark}</span><div><strong>${e(ministry.name)}</strong></div></div></td>
                <td><div class="row-actions"><button class="button small" data-edit-ministry="${ministry.id}">${SURVEY_ICONS.edit}<span>ပြင်ဆင်ရန်</span></button><button class="button small danger" data-delete-ministry="${ministry.id}">${SURVEY_ICONS.trash}<span>ဖျက်ရန်</span></button></div></td>
              </tr>`,
            ),
          )
        : empty(
            search ? "ကိုက်ညီသော ဝန်ကြီးဌာန မရှိပါ" : "ဝန်ကြီးဌာန မထည့်ရသေးပါ",
            search
              ? "အခြားအမည်တစ်ခု စမ်းကြည့်ပါ သို့မဟုတ် ရှာဖွေမှုကို ရှင်းလင်းပါ။"
              : "စနစ်တွင် ပါဝင်မည့် ပထမဆုံး ဝန်ကြီးဌာနကို ထည့်ပါ။",
            search
              ? button("ရှာဖွေမှု ရှင်းလင်းရန်", "/dashboard/ministries")
              : '<button class="button" data-add-ministry>ပထမဆုံး ဝန်ကြီးဌာန ထည့်ရန်</button>',
          )}
      ${total ? pagination(total) : ""}
    </section>`);
    document.querySelector("#add-ministry").onclick = () => openMinistryDialog();
    document.querySelector("[data-add-ministry]")?.addEventListener("click", () => openMinistryDialog());
    document.querySelectorAll("[data-edit-ministry]").forEach((button) => {
      button.onclick = () => openMinistryDialog(rows.find((ministry) => ministry.id === Number(button.dataset.editMinistry)));
    });
    document.querySelectorAll("[data-delete-ministry]").forEach((button) => {
      button.onclick = () => deleteMinistry(Number(button.dataset.deleteMinistry), button);
    });
    bindFilters(load);
  } catch (error) {
    setContent(`<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry-ministries">ထပ်စမ်းကြည့်ရန်</button>`);
    document.querySelector("#retry-ministries").onclick = ministries;
  }
}

function openAddOrgDialog(org = null) {
  const isEdit = !!org;
  const dialog = modal(isEdit ? "တက္ကသိုလ် ပြင်ဆင်ရန်" : "တက္ကသိုလ် ထည့်ရန်", `
    <form id="org-select-form" class="dialog-form">
      <div class="dialog-form__intro">
        <span class="dialog-icon">${SURVEY_ICONS.building}</span>
        <div>
          <strong>${isEdit ? "တက္ကသိုလ် အချက်အလက် ပြင်ဆင်ခြင်း" : "တက္ကသိုလ် အသစ် ထည့်ခြင်း"}</strong>
          <p>တက္ကသိုလ်အမည်နှင့် အမျိုးအစားကို ဖြည့်စွက်ပါ။</p>
        </div>
      </div>
      <label class="form-field"><span>တက္ကသိုလ်အမည် <em>*</em></span><input name="name" required maxlength="255" autocomplete="organization" placeholder="ဥပမာ ရန်ကုန် ကွန်ပျူတာတက္ကသိုလ်" value="${e(org?.name || "")}"></label>
      <label class="form-field"><span>တက္ကသိုလ် အမျိုးအစား <em>*</em></span><input name="uni_type" required maxlength="100" list="university-type-options" autocomplete="off" placeholder="ဥပမာ Public သို့မဟုတ် Private" value="${e(org?.type || "")}"><datalist id="university-type-options"><option value="Public"></option><option value="Private"></option><option value="Government"></option><option value="Unspecified"></option></datalist><small>ဥပမာ — Public (အစိုးရ) သို့မဟုတ် Private (ပုဂ္ဂလိက)</small></label>
      <div class="dialog-actions"><button class="button" type="button" data-cancel-org>မလုပ်တော့ပါ</button><button class="button primary" type="submit">${isEdit ? "သိမ်းဆည်းရန်" : "တက္ကသိုလ် ဖန်တီးရန်"}</button></div>
    </form>`);
  dialog.dataset.variant = "organization";
  const form = dialog.querySelector("#org-select-form");
  const name = form.elements.name;
  const type = form.elements.uni_type;
  form.querySelector("[data-cancel-org]").onclick = () => dialog.close();
  name.focus();
  form.onsubmit = (event) => {
    event.preventDefault();
    name.setCustomValidity(name.value.trim() ? "" : "တက္ကသိုလ်အမည် ထည့်ပါ။");
    type.setCustomValidity(type.value.trim() ? "" : "တက္ကသိုလ် အမျိုးအစား ထည့်ပါ။");
    if (!form.reportValidity()) return;
    busy(event.submitter || form.querySelector('button[type="submit"]'), async () => {
      try {
        await api("/universities" + (isEdit ? "/" + org.id : ""), {
          method: isEdit ? "PUT" : "POST",
          body: { name: name.value.trim(), type: type.value.trim() },
        });
        dialog.close();
        toast(`တက္ကသိုလ် ${isEdit ? "ပြင်ဆင်ပြီးပါပြီ" : "ဖန်တီးပြီးပါပြီ"}။`);
        await load();
      } catch (error) {
        errorMessage(error);
      }
    });
  };
  name.oninput = () => name.setCustomValidity("");
  type.oninput = () => type.setCustomValidity("");
}

function deleteOrg(id, btn) {
  const name = btn.closest("tr").querySelector(".uni-cell strong")?.textContent.trim() || "ဤတက္ကသိုလ်";
  confirmDelete(
    "တက္ကသိုလ်ကို ဖျက်မလား။",
    `“${name}” ကို အပြီးအပိုင် ဖျက်ပစ်ပါမည်။ ပြန်လည်ရယူ၍ မရနိုင်ပါ။`,
    "တက္ကသိုလ် ဖျက်ရန်",
    async () => {
      await api(`/universities/${id}`, { method: "DELETE" });
      toast("တက္ကသိုလ် ဖျက်ပြီးပါပြီ။");
      await load();
    },
  );
}

function openMinistryDialog(ministry = null) {
  const isEdit = !!ministry;
  const dialog = modal(isEdit ? "ဝန်ကြီးဌာန ပြင်ဆင်ရန်" : "ဝန်ကြီးဌာန ထည့်ရန်", `
    <form id="ministry-form" class="dialog-form">
      <div class="dialog-form__intro">
        <span class="dialog-icon">${SURVEY_ICONS.landmark}</span>
        <div>
          <strong>${isEdit ? "ဝန်ကြီးဌာန အချက်အလက် ပြင်ဆင်ခြင်း" : "ဝန်ကြီးဌာန အသစ် ထည့်ခြင်း"}</strong>
          <p>ဝန်ကြီးဌာနအမည်ကို ဖြည့်စွက်ပါ။</p>
        </div>
      </div>
      <label class="form-field"><span>ဝန်ကြီးဌာနအမည် <em>*</em></span><input name="name" required maxlength="255" autocomplete="organization" placeholder="ဥပမာ သိပ္ပံနှင့် နည်းပညာ ဝန်ကြီးဌာန" value="${e(ministry?.name || "")}"></label>
      <div class="dialog-actions"><button class="button" type="button" data-cancel-ministry>မလုပ်တော့ပါ</button><button class="button primary" type="submit">${isEdit ? "သိမ်းဆည်းရန်" : "ဝန်ကြီးဌာန ဖန်တီးရန်"}</button></div>
    </form>`);
  dialog.dataset.variant = "organization";
  const form = dialog.querySelector("#ministry-form");
  const name = form.elements.name;
  form.querySelector("[data-cancel-ministry]").onclick = () => dialog.close();
  name.focus();
  form.onsubmit = (event) => {
    event.preventDefault();
    name.setCustomValidity(name.value.trim() ? "" : "ဝန်ကြီးဌာနအမည် ထည့်ပါ။");
    if (!form.reportValidity()) return;
    busy(event.submitter || form.querySelector('button[type="submit"]'), async () => {
      try {
        await api("/ministries" + (isEdit ? "/" + ministry.id : ""), {
          method: isEdit ? "PUT" : "POST",
          body: { name: name.value.trim() },
        });
        dialog.close();
        toast(`ဝန်ကြီးဌာန ${isEdit ? "ပြင်ဆင်ပြီးပါပြီ" : "ဖန်တီးပြီးပါပြီ"}။`);
        await load();
      } catch (error) {
        errorMessage(error);
      }
    });
  };
  name.oninput = () => name.setCustomValidity("");
}

function deleteMinistry(id, btn) {
  const name = btn.closest("tr").querySelector(".uni-cell strong")?.textContent.trim() || "ဤဝန်ကြီးဌာန";
  confirmDelete(
    "ဝန်ကြီးဌာနကို ဖျက်မလား။",
    `“${name}” ကို အပြီးအပိုင် ဖျက်ပစ်ပါမည်။ ပြန်လည်ရယူ၍ မရနိုင်ပါ။`,
    "ဝန်ကြီးဌာန ဖျက်ရန်",
    async () => {
      await api(`/ministries/${id}`, { method: "DELETE" });
      toast("ဝန်ကြီးဌာန ဖျက်ပြီးပါပြီ။");
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

const REPORT_STATUS = {
  completed: { label: "ပြီးစီး" },
  in_progress: { label: "ဆောင်ရွက်နေဆဲ" },
  not_started: { label: "မစတင်ရသေး" },
};

function reportNumber(value) {
  return Number(value || 0).toLocaleString();
}

function reportPercent(value) {
  return `${(Number(value) || 0).toLocaleString(undefined, {
    maximumFractionDigits: 1,
  })}%`;
}

function reportStatusMeta(status) {
  return REPORT_STATUS[status] || REPORT_STATUS.not_started;
}

function reportStatusBadge(status) {
  const meta = reportStatusMeta(status);
  return `<span class="rp-state rp-state--${e(status)}"><i aria-hidden="true"></i>${e(meta.label)}</span>`;
}

function reportKpiCard({ icon, value, title, hint, tone = "primary", meter = null }) {
  return `<article class="rp-kpi rp-kpi--${e(tone)}">
    <span class="rp-kpi__icon" aria-hidden="true">${icon}</span>
    <div class="rp-kpi__body">
      <p class="rp-kpi__label">${e(title)}</p>
      <strong class="rp-kpi__value">${value}</strong>
      <small class="rp-kpi__hint">${hint}</small>
    </div>
    ${
      meter === null
        ? ""
        : `<span class="rp-kpi__meter" aria-hidden="true"><span style="width:${Math.min(100, Math.max(0, Number(meter) || 0))}%"></span></span>`
    }
  </article>`;
}

function reportYearCard(year, totalUniversities) {
  const completion = Number(year.completion_percent) || 0;
  const coverage = Number(year.answer_coverage_percent) || 0;
  const lastSubmitted = year.last_submitted_at
    ? dateTime(year.last_submitted_at)
    : "တင်သွင်းမှု မရှိသေးပါ";
  return `<article class="rp-year">
    <div class="rp-year__head">
      <div class="rp-year__identity">
        <span class="rp-year__icon" aria-hidden="true">${SURVEY_ICONS.period}</span>
        <div>
          <h3>${e(year.label)}</h3>
          <p>${reportNumber(year.question_count)} မေးခွန်း · ${reportNumber(year.submitted_universities)} / ${reportNumber(totalUniversities)} တက္ကသိုလ်</p>
        </div>
      </div>
      ${reportStatusBadge(year.status)}
    </div>
    <div class="rp-meter rp-meter--lg" role="progressbar" aria-label="${e(year.label)} တက္ကသိုလ် တင်သွင်းမှု" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${completion}">
      <span style="width:${Math.min(100, completion)}%"></span>
    </div>
    <div class="rp-year__foot">
      <span class="rp-year__stat"><strong>${reportPercent(completion)}</strong><small>တင်သွင်းပြီး</small></span>
      <span class="rp-year__stat"><strong>${reportNumber(year.pending_universities)}</strong><small>ကျန်ရှိ</small></span>
      <span class="rp-year__stat"><strong>${reportPercent(coverage)}</strong><small>အဖြေ လွှမ်းခြုံမှု</small></span>
      <span class="rp-year__last">${REPORT_ICONS.clock}<span>${e(lastSubmitted)}</span></span>
    </div>
    <div class="rp-year__actions" aria-label="${e(year.label)} တက္ကသိုလ် စာရင်း">
      <button class="rp-year__action rp-year__action--answered" type="button" data-report-year="${Number(year.year_id)}" data-report-state="answered" aria-haspopup="dialog">
        <span class="rp-year__action-icon" aria-hidden="true">${REPORT_ICONS.completion}</span>
        <span class="rp-year__action-label">တင်သွင်းပြီး</span>
        <strong>${reportNumber(year.submitted_universities)}</strong>
      </button>
      <button class="rp-year__action rp-year__action--pending" type="button" data-report-year="${Number(year.year_id)}" data-report-state="pending" aria-haspopup="dialog">
        <span class="rp-year__action-icon" aria-hidden="true">${REPORT_ICONS.clock}</span>
        <span class="rp-year__action-label">မတင်သွင်းရသေး</span>
        <strong>${reportNumber(year.pending_universities)}</strong>
      </button>
    </div>
  </article>`;
}

function reportRecentCard(report) {
  const completion = Number(report.completion_percent) || 0;
  return `<article class="rp-recent">
    <div class="rp-recent__top">
      <span class="rp-org-mark" aria-hidden="true">${e(String(report.university || "?").slice(0, 1).toUpperCase())}</span>
      <div class="rp-recent__identity">
        <strong>${e(report.university)}</strong>
        <small>${e(report.university_type || "တက္ကသိုလ်")}</small>
      </div>
      ${reportStatusBadge(report.status)}
    </div>
    <div class="rp-recent__row">
      <span class="rp-period">${SURVEY_ICONS.period}${e(report.year_label)}</span>
      <span>${reportNumber(report.answered_questions)} / ${reportNumber(report.question_count)} မေးခွန်း</span>
      <time>${e(dateTime(report.submitted_at))}</time>
    </div>
    <div class="rp-meter rp-meter--sm" aria-hidden="true">
      <span style="width:${Math.min(100, completion)}%"></span>
    </div>
  </article>`;
}

function reportUniversityModal(data) {
  const answered = data.state === "answered";
  const title = `${data.year_label} · ${answered ? "တင်သွင်းပြီး တက္ကသိုလ်များ" : "မတင်သွင်းရသေး တက္ကသိုလ်များ"}`;
  const intro = answered
    ? `${reportNumber(data.total)} တက္ကသိုလ်က ${reportNumber(data.question_count)} မေးခွန်းအတွက် အဖြေ တင်သွင်းထားပါသည်။`
    : `${reportNumber(data.total)} တက္ကသိုလ်က ဤစစ်တမ်းကာလအတွက် အဖြေ မတင်သွင်းရသေးပါ။`;
  let body;
  if (!data.universities.length) {
    body = `<div class="rp-roster-empty"><span aria-hidden="true">${answered ? REPORT_ICONS.completion : REPORT_ICONS.clock}</span><p>${answered ? "တင်သွင်းထားသော တက္ကသိုလ် မရှိသေးပါ။" : "တင်သွင်းရန် ကျန်ရှိသော တက္ကသိုလ် မရှိပါ။"}</p></div>`;
  } else if (answered) {
    body = `<div class="rp-roster">${table(
      ["တက္ကသိုလ်", "ဖြေဆိုပြီး", "အခြေအနေ", "နောက်ဆုံး တင်သွင်းချိန်"],
      data.universities.map(
        (row) =>
          `<tr><td class="title"><strong>${e(row.university)}</strong><small>${e(row.university_type || "တက္ကသိုလ်")}</small></td><td class="numeric">${reportNumber(row.answered_questions)} / ${reportNumber(row.question_count)}</td><td>${reportStatusBadge(row.status)}</td><td>${e(dateTime(row.last_submitted_at))}</td></tr>`,
      ),
    )}</div>`;
  } else {
    body = `<div class="rp-roster">${table(
      ["တက္ကသိုလ်", "အမျိုးအစား", "အခြေအနေ"],
      data.universities.map(
        (row) =>
          `<tr><td class="title"><strong>${e(row.university)}</strong></td><td>${e(row.university_type || "—")}</td><td>${reportStatusBadge(row.status)}</td></tr>`,
      ),
    )}</div>`;
  }
  modal(title, `<p class="dialog-intro">${e(intro)}</p>${body}`);
}

function reportLegacySection(p, data, formData, users) {
  const analytics = data.analytics;
  const peak = Math.max(1, ...analytics.trend.map((day) => day.count));
  return `<details class="rp-more" ${location.search ? "open" : ""}>
    <summary class="rp-more__summary">
      <span class="rp-more__identity">
        <span class="rp-more__icon" aria-hidden="true">${SURVEY_ICONS.forms}</span>
        <span>
          <strong>အသေးစိတ် တင်သွင်းမှု မှတ်တမ်းများ</strong>
          <small>ဖောင် တင်သွင်းချက်များကို စစ်ထုတ်၊ စစ်ဆေးပြီး တင်ပို့ပါ။</small>
        </span>
      </span>
      <span class="rp-more__aside">
        <span class="rp-more__count">${reportNumber(data.total)} မှတ်တမ်း</span>
        <span class="rp-more__chevron" aria-hidden="true">⌄</span>
      </span>
    </summary>
    <div class="rp-more__body">
      <div class="rp-more__toolbar">
        <span>
          <strong>အစီရင်ခံစာ တင်ပို့ရန်</strong>
          <small>လက်ရှိ စစ်ထုတ်မှုအတိုင်း ဒေါင်းလုဒ်လုပ်ပါ။</small>
        </span>
        <details class="export-menu"><summary class="button">ဖိုင် ရွေးရန်</summary><div><a href="/api/admin/reports/export/csv?${e(p)}">CSV ဒေါင်းလုဒ်</a><a href="/api/admin/reports/export/xlsx?${e(p)}">Excel ဒေါင်းလုဒ်</a><a href="/api/admin/reports/export/pdf?${e(p)}">PDF ဒေါင်းလုဒ်</a></div></details>
      </div>
      ${reportFilters(p, formData, users)}
      ${
        data.items.length
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
              button("စစ်တမ်းများ ကြည့်ရန်", "/dashboard/forms"),
            )
      }
      ${pagination(data.total)}
      ${
        data.items.length
          ? '<div class="filters rp-review-bar"><span>ရွေးထားသည်များကို စစ်ဆေးရန်</span><button class="button small" data-review="approved">အတည်ပြုရန်</button><button class="button small danger" data-review="rejected">ပယ်ချရန်</button><button class="button small" data-review="pending_review">စစ်ဆေးရန် စောင့်ဆိုင်းအဖြစ် မှတ်ရန်</button></div>'
          : ""
      }
      <div class="overview-grid report-insights rp-insights">
        <section class="panel">
          <div class="panel-head"><div><h2>စစ်ထုတ်ထားသည့် တင်သွင်းမှု လမ်းကြောင်း</h2><p>${analytics.completion_percent}% ပြီးစီး · ပျမ်းမျှ ပြီးစီးချိန် · ${analytics.average_seconds === null ? "—" : analytics.average_seconds + " စက္ကန့်"}</p></div></div>
          <div class="panel-body">${
            analytics.trend.length
              ? `<div class="chart" role="img" aria-label="${e(analytics.trend.map((day) => day.date + ": " + day.count).join("; "))}">${analytics.trend.map((day) => `<div class="chart-column" tabindex="0" title="${day.date}: ${day.count}"><div class="chart-bar" style="height:${Math.max(1, (day.count / peak) * 100)}%"></div></div>`).join("")}</div>`
              : empty(
                  "ဤရွေးချယ်မှုအတွက် လုပ်ဆောင်ချက် မရှိပါ",
                  "တင်သွင်းထားသော တုံ့ပြန်ချက်များ ပါဝင်ရန် စစ်ထုတ်မှုများကို ပြောင်းပါ။",
                )
          }</div>
        </section>
        <section class="panel">
          <div class="panel-head"><h2>ဖြေဆိုသူများ၏ လုပ်ဆောင်ချက်</h2></div>
          ${
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
          }
        </section>
      </div>
      ${
        analytics.question_distribution.length
          ? `<section class="panel rp-question-distribution"><div class="panel-head"><h2>အဖြေ ဖြန့်ဝေမှု · ${e(p.get("question"))}</h2></div>${table(
              ["အဖြေ", "တုံ့ပြန်ချက်များ"],
              analytics.question_distribution.map(
                (item) =>
                  `<tr><td>${e(item.display_value ?? valueText(item.answer))}</td><td class="numeric">${item.count}</td></tr>`,
              ),
            )}</section>`
          : ""
      }
    </div>
  </details>`;
}

async function reportsPage() {
  describe("");
  actions("");
  const p = new URLSearchParams(location.search);
  let activity = null;
  let data, formData, users;
  let activityError = null;
  let legacyError = null;
  const [activityResult, legacyResult] = await Promise.allSettled([
    api("/reports/university"),
    Promise.all([
      api("/reports?" + p),
      api("/forms?limit=100"),
      api("/users?limit=100"),
    ]),
  ]);
  if (activityResult.status === "fulfilled") activity = activityResult.value;
  else activityError = activityResult.reason;
  if (legacyResult.status === "fulfilled") {
    [data, formData, users] = legacyResult.value;
  } else {
    legacyError = legacyResult.reason;
  }

  if (!activity && !data) {
    const message =
      (activityError && activityError.message) ||
      (legacyError && legacyError.message) ||
      "အစီရင်ခံစာ အချက်အလက်များကို ဖွင့်မရပါ။";
    setContent(
      `<div class="notice error" role="alert">${e(message)}</div><button class="button" id="retry-reports" type="button">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry-reports").onclick = reportsPage;
    return;
  }

  const totals = activity?.totals || {
    universities: 0,
    active_years: 0,
    questions: 0,
    reports_expected: 0,
    reports_submitted: 0,
    reports_pending: 0,
    participating_universities: 0,
    completion_percent: 0,
    answer_coverage_percent: 0,
    answers: 0,
    last_submitted_at: null,
  };
  const activeYears = activity?.active_years || [];
  const recentReports = activity?.recent_reports || [];
  const activityPanel = activity
    ? `<div class="rp-kpis">
        ${reportKpiCard({
          icon: REPORT_ICONS.years,
          value: reportNumber(totals.active_years),
          title: "လက်ရှိ စစ်တမ်းကာလ",
          hint: "သက်ဝင်နေသော စစ်တမ်းကာလများ",
          tone: "years",
        })}
        ${reportKpiCard({
          icon: REPORT_ICONS.universities,
          value: reportNumber(totals.participating_universities),
          title: "ပါဝင်တင်သွင်းသည့် တက္ကသိုလ်",
          hint: `<strong>${reportNumber(totals.universities)}</strong> တက္ကသိုလ်အနက်`,
          tone: "universities",
        })}
        ${reportKpiCard({
          icon: REPORT_ICONS.reports,
          value: reportNumber(totals.reports_submitted),
          title: "တင်သွင်းပြီး အစီရင်ခံစာ",
          hint: `<strong>${reportNumber(totals.reports_pending)}</strong> ခု ကျန်ရှိ`,
          tone: "reports",
        })}
        ${reportKpiCard({
          icon: REPORT_ICONS.completion,
          value: reportPercent(totals.completion_percent),
          title: "တင်သွင်းမှု ပြီးစီးနှုန်း",
          hint: `အဖြေ လွှမ်းခြုံမှု <strong>${reportPercent(totals.answer_coverage_percent)}</strong>`,
          tone: "completion",
          meter: totals.completion_percent,
        })}
      </div>
      <div class="rp-grid">
        <section class="rp-panel rp-panel--years">
          <header class="rp-panel__head">
            <div><h2>လက်ရှိ စစ်တမ်းကာလများ</h2><p>သက်ဝင်နေသော နှစ်များနှင့် တက္ကသိုလ် တင်သွင်းမှု တိုးတက်မှု</p></div>
            <span class="rp-count">${reportNumber(activeYears.length)} ကာလ</span>
          </header>
          ${
            activeYears.length
              ? `<div class="rp-year-list">${activeYears.map((year) => reportYearCard(year, totals.universities)).join("")}</div>`
              : `<div class="rp-empty rp-empty--compact"><span class="rp-empty__icon" aria-hidden="true">${REPORT_ICONS.years}</span><h3>လက်ရှိ စစ်တမ်းကာလ မရှိပါ</h3><p>စစ်တမ်းကာလတစ်ခုကို ထုတ်ဝေပြီးပါက ၎င်း၏ တက္ကသိုလ် တင်သွင်းမှု အခြေအနေ ဤနေရာတွင် ပေါ်လာပါမည်။</p><a class="button" href="/dashboard/forms">စစ်တမ်းများ ကြည့်ရန်</a></div>`
          }
        </section>
        <section class="rp-panel rp-panel--recent">
          <header class="rp-panel__head">
            <div><h2>မကြာသေးမီ တင်သွင်းမှုများ</h2><p>လက်ရှိ စစ်တမ်းကာလများအတွင်း နောက်ဆုံး တင်သွင်းခဲ့သည့် တက္ကသိုလ်များ</p></div>
            <span class="rp-count">${reportNumber(recentReports.length)} ခု</span>
          </header>
          ${
            recentReports.length
              ? `<div class="rp-recent-list">${recentReports.map(reportRecentCard).join("")}</div>`
              : `<div class="rp-empty rp-empty--compact"><span class="rp-empty__icon" aria-hidden="true">${REPORT_ICONS.reports}</span><h3>တင်သွင်းမှု မရှိသေးပါ</h3><p>တက္ကသိုလ်များ တင်သွင်းပြီးပါက နောက်ဆုံး အစီရင်ခံစာများ ဤနေရာတွင် ပေါ်လာပါမည်။</p></div>`
          }
        </section>
      </div>`
    : `<div class="notice error" role="alert">${e(activityError?.message || "တက္ကသိုလ် အစီရင်ခံစာ အချက်အလက်များကို ဖွင့်မရပါ။")}</div><button class="button" id="retry-activity" type="button">တက္ကသိုလ် အစီရင်ခံစာများ ထပ်စမ်းကြည့်ရန်</button>`;

  setContent(
    `<section class="rp-stage">
      <div class="rp-intro">
        <div>
          <span class="rp-eyebrow"><i aria-hidden="true"></i>တက္ကသိုလ် စစ်တမ်း လုပ်ငန်းစဉ်</span>
          <h2>လက်ရှိ စစ်တမ်းကာလများ၏ တင်သွင်းမှု အခြေအနေ</h2>
          <p>သက်ဝင်နေသော စစ်တမ်းကာလများတွင် တက္ကသိုလ်များ၏ တင်သွင်းမှုကို တစ်နေရာတည်းမှ စောင့်ကြည့်ပါ။</p>
          <div class="rp-intro__facts">
            <span><strong>${reportNumber(totals.questions)}</strong> မေးခွန်း</span>
            <span><strong>${reportNumber(totals.answers)}</strong> အဖြေ</span>
            <span><strong>${reportNumber(totals.reports_expected)}</strong> မျှော်မှန်း အစီရင်ခံစာ</span>
          </div>
        </div>
        <div class="rp-intro__status">
          <span class="rp-live"><i aria-hidden="true"></i>လက်ရှိ အခြေအနေ</span>
          <small>${totals.last_submitted_at ? `နောက်ဆုံး တင်သွင်းချိန်<br><strong>${e(dateTime(totals.last_submitted_at))}</strong>` : "တင်သွင်းမှု မရှိသေးပါ"}</small>
        </div>
      </div>
      ${activityPanel}
      ${
        data
          ? reportLegacySection(p, data, formData, users)
          : `<div class="notice error" role="alert">${e(legacyError?.message || "အသေးစိတ် တင်သွင်းမှု မှတ်တမ်းများကို ဖွင့်မရပါ။")}</div><button class="button" id="retry-legacy" type="button">အသေးစိတ် မှတ်တမ်းများ ထပ်စမ်းကြည့်ရန်</button>`
      }
    </section>`,
  );

  const bindRefresh = (selector) => {
    const node = document.querySelector(selector);
    if (node) node.onclick = () => busy(node, reportsPage);
  };
  bindRefresh("#retry-activity");
  bindRefresh("#retry-legacy");
  document.querySelectorAll("[data-report-state]").forEach((button) => {
    button.onclick = () =>
      busy(button, async () => {
        try {
          const report = await api(
            `/reports/university/${Number(button.dataset.reportYear)}/universities?state=${encodeURIComponent(button.dataset.reportState)}`,
          );
          reportUniversityModal(report);
        } catch (error) {
          toast(error.message);
        }
      });
  });

  if (data) {
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
                `<p class="editor-meta">${e(detail.form)} · ဗားရှင်း ${detail.version} · ${e(detail.username)}</p>${detail.sections.map((s) => `<section class="stack"><h3>${e(s.title)}</h3>${s.answers.map((a) => `<div class="notice"><strong>${e(a.title)}</strong><p class="source-text">${["file", "image"].includes(a.kind) && a.value?.file_id ? `<a class="table-link" href="/api/files/${Number(a.value.file_id)}">${e(a.display_value || "ပူးတွဲဖိုင် ဒေါင်းလုဒ်လုပ်ရန်")} ${arrowIcon}</a>` : e(a.display_value ?? valueText(a.value))}</p></div>`).join("")}</section>`).join("")}`,
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
}

function themeOption(value, name, description) {
  return `<label class="settings-theme-option">
    <input class="sr-only" type="radio" name="theme-setting" value="${value}">
    <span class="settings-theme-preview settings-theme-preview--${value}" aria-hidden="true">
      <span class="settings-theme-preview__rail"><span class="settings-theme-preview__mark"></span><span class="settings-theme-preview__nav"></span><span class="settings-theme-preview__nav"></span><span class="settings-theme-preview__nav"></span></span>
      <span class="settings-theme-preview__workspace"><span class="settings-theme-preview__topbar"></span><span class="settings-theme-preview__heading"></span><span class="settings-theme-preview__surface"><span></span><span></span><span></span></span></span>
    </span>
    <span class="settings-theme-option__copy"><span><strong>${name}</strong><small>${description}</small></span><span class="settings-theme-option__check" aria-hidden="true"></span></span>
  </label>`;
}

async function settings() {
  describe("သင့်အကောင့်ကို ကာကွယ်ပြီး စီမံခန့်ခွဲသူများ၏ အသုံးပြုခွင့်ကို စီမံပါ။");
  const params = new URLSearchParams(location.search);
  const pageSize = Number(params.get("limit") || 10);
  params.set("limit", String(pageSize));
  let user, directory;
  try {
    [user, directory] = await Promise.all([
      api("/session"), api("/administrators?" + params),
    ]);
    const pageNumber = Number(params.get("page") || 1);
    const lastPage = Math.max(1, Math.ceil(directory.total / pageSize));
    if (pageNumber > lastPage) {
      params.set("page", String(lastPage));
      history.replaceState({}, "", `${location.pathname}?${params}${location.hash}`);
      return settings();
    }
    const rows = directory.items.map((account) =>
      `<tr><td><div class="user-identity"><span class="avatar" aria-hidden="true">${e(account.username.slice(0, 1).toUpperCase())}</span><div><strong>${e(account.username)}</strong><small>#${account.id}${account.id === user.id ? " · သင်" : ""}</small></div></div></td><td>${badge(account.is_active ? "active" : "disabled")}</td><td>${date(account.created_at)}</td><td><div class="row-actions"><button class="button small" type="button" data-edit-admin="${account.id}">ပြင်ဆင်ရန်</button>${account.id === user.id ? "" : `<button class="button small danger" type="button" data-delete-admin="${account.id}">ဖျက်ရန်</button>`}</div></td></tr>`,
    );
    const mobileRows = directory.items.map((account) =>
      `<li class="settings-mobile-item"><div class="settings-mobile-item__top"><div class="user-identity"><span class="avatar" aria-hidden="true">${e(account.username.slice(0, 1).toUpperCase())}</span><div><strong>${e(account.username)}</strong><small>#${account.id}${account.id === user.id ? " · သင်" : ""}</small></div></div>${badge(account.is_active ? "active" : "disabled")}</div><div class="settings-mobile-item__foot"><span>${date(account.created_at)}</span><div class="row-actions"><button class="button small" type="button" data-edit-admin="${account.id}">ပြင်ဆင်ရန်</button>${account.id === user.id ? "" : `<button class="button small danger" type="button" data-delete-admin="${account.id}">ဖျက်ရန်</button>`}</div></div></li>`,
    );
    setContent(
      `<div class="settings-layout"><div class="settings-index" role="tablist" aria-label="ဆက်တင် ကဏ္ဍများ"><button id="settings-tab-account" type="button" role="tab" aria-controls="account" data-settings-tab="account">သင့်အကောင့်</button><button id="settings-tab-administrators" type="button" role="tab" aria-controls="administrators" data-settings-tab="administrators">စီမံခန့်ခွဲသူများ</button><button id="settings-tab-appearance" type="button" role="tab" aria-controls="appearance" data-settings-tab="appearance">အသွင်အပြင်</button></div><div class="settings-sections">
        <section class="settings-row" id="account" role="tabpanel" aria-labelledby="settings-tab-account" tabindex="-1"><div class="settings-copy"><h2 id="account-title">သင့်အကောင့်</h2><p>သင့်စကားဝှက်ကို အချိန်မရွေး ပြောင်းလဲနိုင်ပါသည်။</p></div><div class="settings-control"><div class="account-summary"><span class="avatar" aria-hidden="true">${e(user.username.slice(0, 1).toUpperCase())}</span><div><h3>${e(user.username)}</h3><p class="field-hint">စီမံခန့်ခွဲသူ · #${user.id}</p></div></div><form id="password-form" class="settings-form"><label>လက်ရှိ စကားဝှက်<input name="current_password" type="password" required autocomplete="current-password"></label><label>စကားဝှက်အသစ်<input name="new_password" type="password" required minlength="8" maxlength="1024" autocomplete="new-password"><small>အနည်းဆုံး ၈ လုံး အသုံးပြုပါ။</small></label><label>စကားဝှက်အသစ် ထပ်ရိုက်ပါ<input name="confirm_password" type="password" required minlength="8" maxlength="1024" autocomplete="new-password"></label><p class="settings-feedback" id="password-feedback" role="status" aria-live="polite"></p><button class="button primary" type="submit">စကားဝှက် ပြောင်းရန်</button></form></div></section>
        <section class="settings-row settings-row--wide" id="administrators" role="tabpanel" aria-labelledby="settings-tab-administrators" tabindex="-1"><div class="settings-copy settings-copy--action"><div><h2 id="admins-title">စီမံခန့်ခွဲသူများ</h2><p>အကောင့်အသစ် ထည့်ရန်၊ ပြင်ဆင်ရန်၊ အသုံးပြုခွင့် ပိတ်ရန် သို့မဟုတ် ဖျက်ရန်။</p></div><button class="button primary" id="add-administrator" type="button">စီမံခန့်ခွဲသူ ထည့်ရန်</button></div><form class="filters settings-search" data-filter-form><label class="sr-only" for="admin-search">စီမံခန့်ခွဲသူ ရှာဖွေရန်</label><input id="admin-search" type="search" name="search" placeholder="အမည်ဖြင့် ရှာဖွေရန်…" value="${e(params.get("search") || "")}"><button class="button" type="submit">ရှာဖွေရန်</button><span class="settings-count">${directory.total} ယောက်</span></form>${rows.length ? table(["အကောင့်", "အခြေအနေ", "ဖန်တီးချိန်", ""], rows) + `<ul class="settings-mobile-list">${mobileRows.join("")}</ul>` : empty("စီမံခန့်ခွဲသူ မတွေ့ပါ", params.get("search") ? "ရှာဖွေမှုကို ရှင်းလင်းပြီး ထပ်စမ်းကြည့်ပါ။" : "စီမံခန့်ခွဲသူအသစ် ထည့်နိုင်ပါသည်။", params.get("search") ? button("ရှာဖွေမှု ရှင်းရန်", "/dashboard/settings#administrators") : "")}${pagination(directory.total, pageSize)}</section>
        <section class="settings-row settings-row--appearance" id="appearance" role="tabpanel" aria-labelledby="settings-tab-appearance" tabindex="-1"><div class="settings-appearance-head"><div><h2 id="appearance-title">အသွင်အပြင်</h2><p>အလုပ်ခွင်အတွက် သင့်မျက်စိနှင့် သင့်တော်သော အရောင်ကို ရွေးပါ။</p></div><p class="settings-appearance-current">လက်ရှိရွေးချယ်မှု <strong id="theme-current-label"></strong></p></div><fieldset class="settings-theme-fieldset"><legend class="sr-only">အလုပ်ခွင် အပြင်အဆင်</legend><div class="settings-theme-choice-group"><p>အလုပ်ခွင် အပြင်အဆင်</p><div class="settings-theme-options">${themeOption("light", "အလင်း", "နေ့ခင်းဘက် အသုံးပြုရန်")}${themeOption("dark", "အမှောင်", "အလင်းနည်းသော နေရာတွင် အသုံးပြုရန်")}</div></div></fieldset><p class="settings-appearance-status" id="theme-status" role="status" aria-live="polite"></p></section>
      </div></div>`,
    );
  } catch (error) {
    setContent(
      `<div class="notice error" role="alert">${e(error.message)}</div><button class="button" id="retry">ထပ်စမ်းကြည့်ရန်</button>`,
    );
    document.querySelector("#retry").onclick = settings;
    return;
  }
  const settingTabs = [...document.querySelectorAll('[data-settings-tab]')];
  function selectSetting(id, updateUrl = false) {
    const selected = settingTabs.some((tab) => tab.dataset.settingsTab === id) ? id : 'account';
    settingTabs.forEach((tab) => {
      const active = tab.dataset.settingsTab === selected;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      document.getElementById(tab.dataset.settingsTab).hidden = !active;
    });
    if (updateUrl) history.replaceState({}, '', `${location.pathname}${location.search}#${selected}`);
  }
  selectSetting(location.hash.slice(1));
  settingTabs.forEach((tab, index) => {
    tab.onclick = () => selectSetting(tab.dataset.settingsTab, true);
    tab.onkeydown = (event) => {
      const next = event.key === 'ArrowRight' ? index + 1 : event.key === 'ArrowLeft' ? index - 1 : event.key === 'Home' ? 0 : event.key === 'End' ? settingTabs.length - 1 : null;
      if (next === null) return;
      event.preventDefault();
      const target = settingTabs[(next + settingTabs.length) % settingTabs.length];
      selectSetting(target.dataset.settingsTab, true);
      target.focus();
    };
  });
  document.querySelector("#password-form").onsubmit = (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const values = Object.fromEntries(new FormData(form));
    const feedback = form.querySelector("#password-feedback");
    if (values.new_password !== values.confirm_password) {
      feedback.textContent = "စကားဝှက်အသစ် နှစ်ခု မတူပါ။";
      feedback.dataset.state = "error";
      return;
    }
    busy(event.submitter, async () => {
      try {
        await api("/account/password", { method: "POST", body: {
          current_password: values.current_password, new_password: values.new_password,
        } });
        form.reset();
        feedback.textContent = "စကားဝှက် ပြောင်းပြီးပါပြီ။ အခြားစက်များမှ အကောင့်ဝင်ထားမှုများကို ပိတ်ထားပါသည်။";
        feedback.dataset.state = "success";
      } catch (error) {
        feedback.textContent = error.message;
        feedback.dataset.state = "error";
      }
    });
  };
  function editAdministrator(account) {
    const dialog = modal(account ? "စီမံခန့်ခွဲသူ ပြင်ဆင်ရန်" : "စီမံခန့်ခွဲသူ ထည့်ရန်",
      `<form id="administrator-form" class="field-stack"><label>အသုံးပြုသူအမည်<input name="username" required maxlength="100" value="${e(account?.username || "")}" autocomplete="off"></label>${account?.id === user.id ? "<p class=\"field-hint\">သင့်စကားဝှက်ကို သင့်အကောင့်ကဏ္ဍတွင် ပြောင်းပါ။</p>" : `<label>${account ? "စကားဝှက်အသစ် (မပြောင်းလိုပါက ဗလာထားပါ)" : "စကားဝှက်"}<input name="password" type="password" minlength="8" maxlength="1024" autocomplete="new-password" ${account ? "" : "required"}></label>`}${account ? `<label class="check-label"><input name="is_active" type="checkbox" ${account.is_active ? "checked" : ""} ${account.id === user.id ? "disabled" : ""}>အကောင့် အသုံးပြုနိုင်သည်</label>` : ""}<div class="dialog-actions"><button class="button primary" type="submit">${account ? "ပြောင်းလဲမှု သိမ်းရန်" : "အကောင့် ဖန်တီးရန်"}</button></div></form>`);
    dialog.querySelector("#administrator-form").onsubmit = (event) => {
      event.preventDefault();
      const form = event.currentTarget;
      busy(event.submitter, async () => {
        const values = Object.fromEntries(new FormData(form));
        values.is_active = !account || account.id === user.id ? true : form.elements.is_active.checked;
        if (!values.password) delete values.password;
        try {
          await api("/administrators" + (account ? "/" + account.id : ""), {
            method: account ? "PUT" : "POST", body: values,
          });
          await settings();
          dialog.close();
          toast("စီမံခန့်ခွဲသူ အကောင့် သိမ်းဆည်းပြီးပါပြီ။");
        } catch (error) { errorMessage(error); }
      });
    };
  }
  document.querySelector("#add-administrator").onclick = () => editAdministrator(null);
  document.querySelectorAll("[data-edit-admin]").forEach((button) => {
    button.onclick = () => editAdministrator(directory.items.find((account) => account.id === Number(button.dataset.editAdmin)));
  });
  document.querySelectorAll("[data-delete-admin]").forEach((button) => {
    button.onclick = () => {
      const account = directory.items.find((item) => item.id === Number(button.dataset.deleteAdmin));
      confirmDelete("စီမံခန့်ခွဲသူ ဖျက်ရန်", `${account.username} အကောင့်ကို ဖျက်မည်လား။ မှတ်တမ်းရှိသည့်အကောင့်ကို ဖျက်မရပါ။`, "အကောင့် ဖျက်ရန်", async () => {
        await api("/administrators/" + account.id, { method: "DELETE" });
        toast("စီမံခန့်ခွဲသူ အကောင့် ဖျက်ပြီးပါပြီ။");
        await settings();
      });
    };
  });
  document.querySelectorAll('#administrators [data-pagination]').forEach((button) => {
    button.onclick = async () => {
      const next = new URLSearchParams(location.search);
      next.set('page', button.dataset.pagination);
      next.set('limit', String(pageSize));
      history.pushState({}, '', `${location.pathname}?${next}#administrators`);
      await settings();
      document.querySelector('#administrators').focus({ preventScroll: true });
      window.scrollTo({ top: 0 });
    };
  });
  document.querySelector('#administrators .settings-search').onsubmit = async (event) => {
    event.preventDefault();
    const next = new URLSearchParams(new FormData(event.currentTarget));
    for (const [key, value] of [...next]) if (!value) next.delete(key);
    next.set('limit', String(pageSize));
    history.pushState({}, '', `${location.pathname}?${next}#administrators`);
    await settings();
    document.querySelector('#administrators').focus({ preventScroll: true });
  };
  document.querySelectorAll('input[name="theme-setting"]').forEach((input) => {
    input.checked = input.value === document.documentElement.dataset.theme;
    input.onchange = () => applyTheme(input.value);
  });
  const currentTheme = document.documentElement.dataset.theme === "dark" ? "အမှောင်" : "အလင်း";
  document.querySelector("#theme-current-label").textContent = currentTheme;
  document.querySelector("#theme-status").textContent = `${currentTheme} အပြင်အဆင်ကို ဤဘရောက်ဇာတွင် သိမ်းဆည်းထားပါသည်။`;
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
    forms: () => safeLoad(formsPage, "စစ်တမ်းများ"),
    departments: () => safeLoad(departments, "တက္ကသိုလ်များ"),
    ministries: () => safeLoad(ministries, "ဝန်ကြီးဌာနများ"),
    submissions: () => safeLoad(reportsPage, "တက္ကသိုလ် အစီရင်ခံစာများ"),
    reports: () => safeLoad(reportsPage, "တက္ကသိုလ် အစီရင်ခံစာများ"),
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
  "/dashboard/departments": ["departments", "တက္ကသိုလ်များ"],
  "/dashboard/ministries": ["ministries", "ဝန်ကြီးဌာနများ"],
  "/dashboard/reports": ["reports", "တက္ကသိုလ် အစီရင်ခံစာများ"],
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
