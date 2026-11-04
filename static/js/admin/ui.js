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

export const badge = (value) =>
  `<span class="badge ${escape(value)}">${escape(String(value).replaceAll("_", " "))}</span>`;
export const button = (label, href, primary = false) =>
  `<a class="button ${primary ? "primary" : ""}" href="${escape(href)}">${label}</a>`;
export const empty = (title, description, action = "") =>
  `<div class="empty"><div class="empty-symbol" aria-hidden="true">＋</div><h2>${escape(title)}</h2><p>${escape(description)}</p>${action}</div>`;
export const date = (value) =>
  value
    ? new Date(value + "Z").toLocaleDateString(undefined, {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : "—";
export const table = (headers, rows) =>
  `<div class="table-wrap"><table><thead><tr>${headers.map((h) => `<th scope="col">${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
export function setContent(html) {
  const content = document.querySelector("#content");
  content.innerHTML = html;
  content.classList.remove("fade-in");
  requestAnimationFrame(() => content.classList.add("fade-in"));
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
  document.querySelector("#dialog-title").textContent = title;
  document.querySelector("#dialog-content").innerHTML = html;
  dialog.showModal();
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
  const p = Number(new URLSearchParams(location.search).get("page") || 1),
    count = Math.max(1, Math.ceil(total / 25));
  return `<div class="pagination"><span>${total.toLocaleString()} records · Page ${p} of ${count}</span><div class="actions"><button class="button small" data-pagination="${p - 1}" ${p <= 1 ? "disabled" : ""}>Previous</button><button class="button small" data-pagination="${p + 1}" ${p >= count ? "disabled" : ""}>Next</button></div></div>`;
}
export function bindFilters(reload) {
  document.querySelectorAll("[data-pagination]").forEach(
    (b) =>
      (b.onclick = () => {
        const p = new URLSearchParams(location.search);
        p.set("page", b.dataset.pagination);
        history.pushState({}, "", `${location.pathname}?${p}`);
        reload();
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
  `<form class="filters" data-filter-form><input type="search" aria-label="Search records" name="search" placeholder="Search records…" value="${escape(value)}"><button class="button small" type="submit">Search</button></form>`;
