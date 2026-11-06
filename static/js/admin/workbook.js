import { api } from "./api.js";
import {
  escape as e,
  button,
  empty,
  table,
  setContent,
  describe,
  actions,
  toast,
  busy,
  pagination,
  bindFilters,
} from "./ui.js";
export async function loadImport() {
  describe(
    "Bring in your DEDC workbook. Review the structure and preserve the original answers.",
  );
  actions(
    `<details class="export-menu"><summary class="button">Export workbook</summary><div><a href="/api/admin/workbook/export/excel">Original format: questions</a><a href="/api/admin/workbook/export/excel?answers=true">Original format: questions & answers</a></div></details>`,
  );
  const params = new URLSearchParams(location.search);
  const tabs = `<nav class="data-tabs" aria-label="Data management"><a href="/dashboard/data" ${params.get('tab') !== 'answers' ? 'aria-current="page"' : ''}>Import workbook</a><a href="/dashboard/data?tab=answers" ${params.get('tab') === 'answers' ? 'aria-current="page"' : ''}>Source answers</a></nav>`;
  if (params.get("tab") === "answers") return sourceAnswers(params, tabs);
  setContent(
    `${tabs}<section class="panel"><div class="import-layout"><div class="import-copy"><h2>Your workbook. A new survey.</h2><p>Bring your existing DEDC questions into the workspace, then review the structure before creating a draft.</p><ul class="import-notes"><li>Original wording preserved</li><li>Source answers kept separately</li><li>Nothing published automatically</li></ul></div><form id="upload-form"><div class="import-drop" id="workbook-drop"><svg class="import-upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></svg><h2>Drag your workbook here</h2><p id="workbook-help">DEDC six-column format · One .xlsx file, up to 10 MB</p><input type="file" id="workbook-file" name="file" accept=".xlsx" aria-label="Excel workbook" aria-describedby="workbook-help" hidden><button class="button" type="button" id="choose-workbook">Choose workbook</button><div class="import-file" id="workbook-selection" hidden><div><strong id="workbook-name"></strong><span id="workbook-size"></span></div><button class="button small" type="button" id="remove-workbook" aria-label="Remove selected workbook">Remove</button></div><p class="import-status" id="workbook-status" role="status" aria-live="polite"></p></div><button class="button primary" id="read-workbook" type="submit" disabled>Read workbook</button></form></div><div id="import-preview"></div></section>`,
  );
  let selectedFile, file, preview, reading = false;
  const input = document.querySelector("#workbook-file"),
    drop = document.querySelector("#workbook-drop"),
    choose = document.querySelector("#choose-workbook"),
    read = document.querySelector("#read-workbook"),
    selection = document.querySelector("#workbook-selection"),
    status = document.querySelector("#workbook-status");
  choose.onclick = () => input.click();
  function selectFile(files) {
    if (!files.length) return;
    const candidate = files[0];
    let error = "";
    if (files.length !== 1) error = "Choose one workbook at a time.";
    else if (!/\.xlsx$/i.test(candidate.name)) error = "Choose an Excel workbook (.xlsx).";
    else if (candidate.size > 10 * 1024 * 1024) error = "Workbook exceeds 10 MB. Choose a smaller file.";
    else if (!candidate.size) error = "This file is empty. Choose a workbook with content.";
    status.textContent = error;
    drop.classList.toggle("has-error", Boolean(error));
    if (error) return;
    selectedFile = candidate;
    selection.hidden = false;
    document.querySelector("#workbook-name").textContent = candidate.name;
    document.querySelector("#workbook-size").textContent = candidate.size < 1024 * 1024
      ? `${Math.max(1, Math.ceil(candidate.size / 1024))} KB · Ready to read`
      : `${(candidate.size / (1024 * 1024)).toFixed(1)} MB · Ready to read`;
    choose.textContent = "Change workbook";
    read.disabled = reading;
    preview = null;
    document.querySelector("#import-preview").replaceChildren();
    status.textContent = "Workbook selected. Select Read workbook to review it.";
  }
  input.onchange = () => {
    selectFile(input.files);
    input.value = ""; // Allow choosing the same file again after removing it.
  };
  document.querySelector("#remove-workbook").onclick = () => {
    selectedFile = null;
    preview = null;
    selection.hidden = true;
    read.disabled = true;
    choose.textContent = "Choose workbook";
    status.textContent = "Workbook removed.";
    drop.classList.remove("has-error");
    document.querySelector("#import-preview").replaceChildren();
    choose.focus();
  };
  let dragDepth = 0;
  drop.addEventListener("dragenter", (event) => {
    event.preventDefault();
    dragDepth++;
    drop.classList.add("is-dragging");
  });
  drop.addEventListener("dragover", (event) => {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  });
  drop.addEventListener("dragleave", (event) => {
    event.preventDefault();
    dragDepth = Math.max(0, dragDepth - 1);
    if (!dragDepth) drop.classList.remove("is-dragging");
  });
  drop.addEventListener("drop", (event) => {
    event.preventDefault();
    dragDepth = 0;
    drop.classList.remove("is-dragging");
    selectFile(event.dataTransfer?.files || []);
  });
  document.querySelector("#upload-form").onsubmit = (event) => {
    event.preventDefault();
    if (!selectedFile || reading) return;
    const workbook = selectedFile;
    reading = true;
    busy(read, async () => {
      try {
        const body = new FormData();
        body.set("file", workbook);
        const result = await api("/imports/preview", { method: "POST", body });
        if (selectedFile !== workbook) return;
        file = workbook;
        preview = result;
        showPreview(0);
      } catch (error) {
        toast(error.message);
      }
    }).finally(() => {
      reading = false;
      read.disabled = !selectedFile;
    });
  };
  function showPreview(index) {
    const sheet = preview.sheets[index],
      target = document.querySelector("#import-preview");
    target.innerHTML = `<hr style="border:0;border-top:1px solid var(--border);margin:28px 0"><label>Worksheet<select id="worksheet">${preview.sheets.map((s, i) => `<option value="${i}" ${i === index ? "selected" : ""}>${e(s.worksheet)}</option>`).join("")}</select></label>${
      sheet.error
        ? `<p class="notice error">${e(sheet.error)}</p>`
        : `<div class="source-summary" style="margin-top:20px"><div><strong>${sheet.question_rows}</strong><span>Original question rows</span></div><div><strong>${sheet.definition.sections.length}</strong><span>Sections</span></div><div><strong>${sheet.field_count}</strong><span>Editable answer fields</span></div><div><strong>${sheet.rows.length}</strong><span>Historical answer rows</span></div></div><div class="notice">${sheet.warnings.map((w) => `<p>${e(w)}</p>`).join("")}</div><h3>Question and answer review</h3>${table(
            [
              "#",
              "Original question",
              "Present / absent",
              "Recorded count / details",
            ],
            sheet.rows.map(
              (r) =>
                `<tr><td>${e(r.number)}</td><td class="title">${e(r.question)}<small>${e(r.source_cell)}</small></td><td>${e(r.present_text || r.absent_text || "—")}</td><td class="source-text">${e(r.quantity_text)}${r.details_text ? "<br>" + e(r.details_text) : ""}</td></tr>`,
            ),
          )}<details style="margin-top:24px"><summary>Review or correct the detected form definition</summary><p class="editor-meta">Change labels, types, required flags and options before saving. Recorded source answers remain unchanged.</p><label>Draft definition (JSON)<textarea id="import-definition" class="code-input">${e(JSON.stringify(sheet.definition, null, 2))}</textarea></label></details><div class="actions" style="margin-top:24px"><button type="button" class="button primary" id="confirm-import">Confirm & create draft</button><p class="editor-meta">Nothing will be published automatically.</p></div>`
    }`;
    document.querySelector("#worksheet").onchange = (event) =>
      showPreview(Number(event.target.value));
    const confirm = document.querySelector("#confirm-import");
    if (confirm)
      confirm.onclick = () =>
        busy(confirm, async () => {
          try {
            const definition =
              document.querySelector("#import-definition").value;
            JSON.parse(definition);
            const body = new FormData();
            body.set("file", file);
            body.set("worksheet", sheet.worksheet);
            body.set("definition", definition);
            const form = await api("/imports/confirm", {
              method: "POST",
              body,
            });
            location.href = "/dashboard/forms/" + form.id;
          } catch (error) {
            toast(error.message);
          }
        });
  }
}
async function sourceAnswers(params, tabs) {
  const data = await api("/source-answers?" + params);
  setContent(
    `${tabs}<section class="panel"><div class="panel-head"><div><h2>Original workbook answers</h2><p>Verbatim observations, separate from newly collected submissions.</p></div><div class="actions"><a class="button small" href="/api/admin/source-answers/export/csv?${e(params)}">Export CSV</a><a class="button small" href="/api/admin/source-answers/export/xlsx?${e(params)}">Export Excel</a><a class="button small" href="/api/admin/source-answers/export/pdf?${e(params)}">Export PDF</a></div></div><form class="filters" data-filter-form><input type="hidden" name="tab" value="answers"><input type="search" name="search" aria-label="Search workbook questions" placeholder="Search original questions…" value="${e(params.get("search") || "")}"><select name="import_id" aria-label="Worksheet"><option value="">All worksheets</option>${data.imports.map((i) => `<option value="${i.id}" ${params.get("import_id") == i.id ? "selected" : ""}>${e(i.worksheet)}</option>`).join("")}</select><button class="button small" type="submit">Apply filters</button></form>${
      data.items.length
        ? table(
            [
              "Period / #",
              "Original question",
              "Present",
              "Absent",
              "Recorded count",
              "Details",
            ],
            data.items.map(
              (r) =>
                `<tr><td>${e(r.worksheet)}<small>Question ${e(r.number)} · ${e(r.source_cell)}</small></td><td class="title source-text">${e(r.question)}</td><td>${e(r.present || "—")}</td><td>${e(r.absent || "—")}</td><td class="source-text">${e(r.quantity || "—")}</td><td class="source-text">${e(r.details || "—")}</td></tr>`,
            ),
          )
        : empty(
            "No source answers",
            "Import a workbook to preserve its questions and original answer cells.",
            button("Import workbook", "/dashboard/data"),
          )
    }${pagination(data.total)}</section>`,
  );
  bindFilters(loadImport);
}
