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
    `<a class="button" href="/dashboard/data">Import workbook</a><a class="button" href="/dashboard/data?tab=answers">View source answers</a><a class="button" href="/api/admin/workbook/export/excel">Original format: questions</a><a class="button" href="/api/admin/workbook/export/excel?answers=true">Original format: questions & answers</a>`,
  );
  const params = new URLSearchParams(location.search);
  if (params.get("tab") === "answers") return sourceAnswers(params);
  setContent(
    `<section class="panel"><div class="panel-head"><div><h2>Import an Excel workbook</h2><p>Draft-only import · Original wording and source answers preserved</p></div></div><div class="panel-body"><form id="upload-form"><div class="import-drop"><h2>Start with your existing survey</h2><p>DEDC six-column format · .xlsx files up to 10 MB</p><label class="sr-only" for="workbook-file">Excel workbook</label><input type="file" id="workbook-file" name="file" accept=".xlsx" required></div><button class="button primary" type="submit">Read workbook</button></form><div id="import-preview"></div></div></section>`,
  );
  let file, preview;
  document.querySelector("#upload-form").onsubmit = (event) => {
    event.preventDefault();
    busy(event.submitter, async () => {
      try {
        file = document.querySelector("#workbook-file").files[0];
        const body = new FormData();
        body.set("file", file);
        preview = await api("/imports/preview", { method: "POST", body });
        showPreview(0);
      } catch (error) {
        toast(error.message);
      }
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
async function sourceAnswers(params) {
  const data = await api("/source-answers?" + params);
  setContent(
    `<section class="panel"><div class="panel-head"><div><h2>Original workbook answers</h2><p>Verbatim observations, separate from newly collected submissions.</p></div><div class="actions"><a class="button small" href="/api/admin/source-answers/export/csv?${e(params)}">Export CSV</a><a class="button small" href="/api/admin/source-answers/export/xlsx?${e(params)}">Export Excel</a><a class="button small" href="/api/admin/source-answers/export/pdf?${e(params)}">Export PDF</a></div></div><form class="filters" data-filter-form><input type="hidden" name="tab" value="answers"><input type="search" name="search" aria-label="Search workbook questions" placeholder="Search original questions…" value="${e(params.get("search") || "")}"><select name="import_id" aria-label="Worksheet"><option value="">All worksheets</option>${data.imports.map((i) => `<option value="${i.id}" ${params.get("import_id") == i.id ? "selected" : ""}>${e(i.worksheet)}</option>`).join("")}</select><button class="button small" type="submit">Apply filters</button></form>${
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
