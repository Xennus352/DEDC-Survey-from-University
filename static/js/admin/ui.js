export const escape = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );


/**
 * Safely escape a string for use in a RegExp constructor.
 * Escapes all special regex characters so the string matches literally.
 * @param {string} string - The string to escape
 * @returns {string} - The escaped string safe for RegExp
 */
export function escapeRegExp(string) {
  return String(string ?? "").replace(/[.*+?^${}()|[\\]\\]/g, "\\$&");
}

/**
 * Safely create a RegExp from a dynamic pattern string.
 * Returns null if the pattern is invalid instead of throwing.
 * @param {string} pattern - The regex pattern string
 * @param {string} flags - Optional regex flags
 * @returns {RegExp|null} - The RegExp object or null if invalid
 */
export function safeRegExp(pattern, flags) {
  try {
    return new RegExp(pattern, flags);
  } catch (_) {
    return null;
  }
}

/**
 * Test a string against a pattern safely.
 * Returns false if the pattern is invalid instead of throwing.
 * @param {string} value - The string to test
 * @param {string} pattern - The regex pattern
 * @param {string} flags - Optional regex flags
 * @returns {boolean} - Whether the pattern matches, or false if invalid
 */
export function safeTest(value, pattern, flags) {
  const re = safeRegExp(pattern, flags);
  return re ? re.test(String(value ?? "")) : false;
}

/**
 * Full match a string against a pattern safely (like regex.fullmatch in Python).
 * Returns false if the pattern is invalid instead of throwing.
 * @param {string} value - The string to test
 * @param {string} pattern - The regex pattern
 * @param {string} flags - Optional regex flags
 * @returns {boolean} - Whether the pattern fully matches, or false if invalid
 */
export function safeFullMatch(value, pattern, flags) {
  const re = safeRegExp(pattern, flags);
  return re ? re.test(String(value ?? "")) : false;
}

const LABELS = {
  draft: "မူကြမ်း",
  published: "ထုတ်ဝေထားသည်",
  archived: "မော်ကွန်းတင်ထားသည်",
  completed: "ပြီးစီးသည်",
  pending_review: "စစ်ဆေးရန် စောင့်နေသည်",
  approved: "အတည်ပြုထားသည်",
  rejected: "ပယ်ချထားသည်",
  active: "အသုံးပြုနေသည်",
  disabled: "ပိတ်ထားသည်",
  university: "တက္ကသိုလ်",
  ministry: "ဝန်ကြီးဌာန",
  general: "အထွေထွေ",
  form: "စစ်တမ်း",
  forms: "စစ်တမ်းများ",
  question: "မေးခွန်း",
  questions: "မေးခွန်းများ",
  section: "ကဏ္ဍ",
  sections: "ကဏ္ဍများ",
  submission: "တင်သွင်းမှု",
  submissions: "တင်သွင်းချက်များ",
  user: "အသုံးပြုသူ",
  users: "အသုံးပြုသူများ",
  role: "အခန်းကဏ္ဍ",
  roles: "အခန်းကဏ္ဍများ",
  department: "ဌာန",
  departments: "ဌာနများ",
  report: "အစီရင်ခံစာ",
  reports: "အစီရင်ခံစာများ",
  session: "ဝင်ရောက်မှု",
  file: "ဖိုင်",
  image: "ရုပ်ပုံ",
  workbook: "အလုပ်စာအုပ်",
  version: "ဗားရှင်း",
  versions: "ဗားရှင်းများ",
  title: "ခေါင်းစဉ်",
  name: "အမည်",
  username: "အသုံးပြုသူအမည်",
  status: "အခြေအနေ",
  audience: "ဖြေဆိုသူအုပ်စု",
  created_at: "ဖန်တီးချိန်",
  updated_at: "ပြင်ဆင်ချိန်",
  reporting_start: "အစီရင်ခံကာလ စတင်",
  reporting_end: "အစီရင်ခံကာလ ပြီးဆုံး",
  equals: "တူညီသည်",
  contains: "ပါဝင်သည်",
  greater_than: "ပိုကြီးသည်",
  less_than: "ပိုငယ်သည်",
};
export const label = (value) => {
  if (LABELS[value]) return LABELS[value];
  const text = String(value ?? "").replaceAll("_", " ").replaceAll(".", " ");
  return text ? text[0].toUpperCase() + text.slice(1) : "";
};
export const valueText = (value) => {
  if (value === null || value === undefined) return "အဖြေ မရှိပါ";
  if (value === true) return "ရှိသည်";
  if (value === false) return "မရှိပါ";
  if (value === "") return "စာသား မရှိပါ";
  if (Array.isArray(value)) return value.length ? value.map(valueText).join("; ") : "ရွေးချယ်မှု မရှိပါ";
  if (typeof value === "object") return Object.entries(value).map(([key,item]) => `${label(key)}: ${valueText(item)}`).join("\n") || "အချက်အလက် မရှိပါ";
  return String(value);
};
export const badge = (value) =>
  `<span class="badge ${escape(value)}">${escape(label(value))}</span>`;
export const button = (text, href, primary = false) =>
  `<a class="button ${primary ? "primary" : ""}" href="${escape(href)}">${text}</a>`;
export const empty = (title, description, action = "") =>
  `<div class="empty"><h2>${escape(title)}</h2><p>${escape(description)}</p>${action}</div>`;
function formatDate(value, withTime = false) {
  if (!value) return "—";
  const dayOnly = /^\d{4}-\d{2}-\d{2}$/.test(value);
  const zoned = /(?:Z|[+-]\d{2}:\d{2})$/i.test(value);
  const parsed = new Date(dayOnly ? value + "T00:00:00Z" : zoned ? value : value + "Z");
  if (Number.isNaN(parsed.getTime())) return "ရက်စွဲ မသိ";
  return parsed.toLocaleString(undefined, {
    year: "numeric", month: "short", day: "numeric",
    ...(dayOnly ? { timeZone: "UTC" } : {}),
    ...(withTime && !dayOnly ? { hour: "2-digit", minute: "2-digit" } : {}),
  });
}
export const date = (value) => formatDate(value);
export const dateTime = (value) => formatDate(value, true);
export const table = (headers, rows) =>
  `<div class="table-wrap" tabindex="0" role="region" aria-label="ဘေးတိုက် လှိမ့်ကြည့်နိုင်သော အချက်အလက်ဇယား"><table><thead><tr>${headers.map((h) => `<th scope="col">${h || '<span class="sr-only">လုပ်ဆောင်ချက်များ</span>'}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
export function setContent(html) {
  const content = document.querySelector("#content");
  content.innerHTML = html;
}
export function describe(text) {
  document.querySelector("#page-description").textContent = text;
}
export function actions(html) {
  document.querySelector("#page-actions").innerHTML = html;
}
export function toast(text) {
  const node = document.querySelector(".toast");
  node.textContent = text;
  node.hidden = false;
  clearTimeout(node.timer);
  node.timer = setTimeout(() => (node.hidden = true), 4500);
}
export function modal(title, html) {
  const dialog = document.querySelector("#workspace-dialog");
  delete dialog.dataset.variant;
  document.querySelector("#dialog-title").textContent = title;
  document.querySelector("#dialog-content").innerHTML = html;
  dialog.showModal();
  return dialog;
}
export function confirmDelete(title, description, label, task) {
  const dialog = modal(title, `<p id="delete-description">${escape(description)}</p><div class="dialog-actions"><button class="button" type="button" data-cancel-delete autofocus>မလုပ်တော့ပါ</button><button class="button danger" type="button" data-confirm-delete>${escape(label)}</button></div>`);
  dialog.setAttribute("aria-describedby", "delete-description");
  const cleanup = () => dialog.removeAttribute("aria-describedby");
  dialog.addEventListener("close", cleanup, { once: true });
  dialog.querySelector("[data-cancel-delete]").onclick = () => dialog.close();
  dialog.querySelector("[data-cancel-delete]").focus();
  dialog.querySelector("[data-confirm-delete]").onclick = (event) => busy(event.currentTarget, async () => {
    const preventClose = (event) => event.preventDefault();
    const closeButton = dialog.querySelector("[data-close-dialog]");
    closeButton.disabled = true;
    dialog.dataset.deleting = "true";
    dialog.addEventListener("cancel", preventClose);
    try {
      await task();
      dialog.close();
    } catch (error) {
      errorMessage(error);
    } finally {
      closeButton.disabled = false;
      delete dialog.dataset.deleting;
      dialog.removeEventListener("cancel", preventClose);
    }
  });
  return dialog;
}

export function errorMessage(error) {
  const content = document.querySelector("#dialog-content");
  let message = content.querySelector("[data-form-error]");
  if (!message) {
    message = document.createElement("p");
    message.className = "notice error";
    message.setAttribute("role", "alert");
    message.tabIndex = -1;
    content.prepend(message);
  }
  message.textContent = error.message;
  message.focus();
}
export async function busy(button, task) {
  button.disabled = true;
  button.setAttribute("aria-busy", "true");
  try {
    return await task();
  } finally {
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }
}
export function pagination(total, reload) {
  const params = new URLSearchParams(location.search);
  const p = Number(params.get("page") || 1),
    size = Number(params.get("limit") || 25),
    count = Math.max(1, Math.ceil(total / size));
  const first = Math.max(1, Math.min(p - 2, count - 4));
  const last = Math.min(count, first + 4);
  const pages = Array.from({ length: last - first + 1 }, (_, index) => first + index)
    .map((page) =>
      page === p
        ? `<span class="pagination__page is-current" aria-current="page">${page}</span>`
        : `<button class="pagination__page" type="button" data-pagination="${page}" aria-label="စာမျက်နှာ ${page} သို့ သွားရန်">${page}</button>`,
    )
    .join("");
  return `<nav class="pagination" aria-label="စာမျက်နှာ ရွေးချယ်မှု">
    <span class="pagination__summary"><strong>${total.toLocaleString()}</strong> မှတ်တမ်း · စာမျက်နှာ <strong>${p}</strong> / ${count}</span>
    <div class="pagination__controls">
      <button class="button small pagination__step" type="button" data-pagination="${p - 1}" ${p <= 1 ? "disabled" : ""}>← ယခင်</button>
      <div class="pagination__pages">${pages}</div>
      <button class="button small pagination__step" type="button" data-pagination="${p + 1}" ${p >= count ? "disabled" : ""}>နောက်သို့ →</button>
    </div>
  </nav>`;
}
export function bindFilters(reload) {
  document.querySelectorAll("[data-pagination]").forEach(
    (b) =>
      (b.onclick = async () => {
        const p = new URLSearchParams(location.search);
        p.set("page", b.dataset.pagination);
        history.pushState({}, "", `${location.pathname}?${p}`);
        await reload();
        // New pages start at the results, rather than leaving the user at
        // the bottom of the previous page with focus on a removed button.
        const results = document.querySelector("#content .table-wrap") || document.querySelector("#content");
        results.tabIndex = 0;
        results.focus({ preventScroll: true });
        window.scrollTo({ top: 0 });
      }),
  );
  document.querySelectorAll("[data-filter-form]").forEach(
    (form) =>
      (form.onsubmit = (event) => {
        event.preventDefault();
        const p = new URLSearchParams(new FormData(form));
        for (const [key, value] of [...p]) if (!value) p.delete(key);
        history.pushState({}, "", `${location.pathname}?${p}`);
        reload();
      }),
  );
}
export const searchFilter = (value) =>
  `<form class="filters" data-filter-form><input type="search" aria-label="မှတ်တမ်းများ ရှာဖွေရန်" name="search" placeholder="မှတ်တမ်းများ ရှာဖွေရန်…" value="${escape(value)}"><button class="button small" type="submit">ရှာဖွေရန်</button></form>`;
