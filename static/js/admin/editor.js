import { api } from "./api.js";
import {
  escape as e,
  badge,
  button,
  empty,
  setContent,
  describe,
  actions,
  toast,
  modal,
  errorMessage,
  busy,
} from "./ui.js";
import { renderSurvey } from "./renderer.js";
import { conditionEditor } from "./conditions.js";
const kinds = [
  "short_text",
  "long_text",
  "number",
  "decimal",
  "single_choice",
  "multiple_choice",
  "dropdown",
  "radio",
  "checkboxes",
  "date",
  "time",
  "datetime",
  "yes_no",
  "location",
  "information",
  "calculated",
  "repeating_group",
  "image",
  "file",
];
function definition(v) {
  return Object.fromEntries(
    [
      "title",
      "description",
      "language",
      "starts_at",
      "ends_at",
      "reporting_start",
      "reporting_end",
      "revision",
      "sections",
    ].map((k) => [k, structuredClone(v[k])]),
  );
}
let unsaved = false;
window.addEventListener("beforeunload", (event) => {
  if (unsaved) {
    event.preventDefault();
    event.returnValue = "";
  }
});
export async function loadEditor(formId) {
  const form = await api("/forms/" + formId),
    params = new URLSearchParams(location.search);
  let version =
      form.versions.find((v) => v.id == params.get("version")) ||
      form.versions.at(-1),
    draft = definition(version),
    editable = version.status === "draft" && !form.archived;
  unsaved = false;
  describe(
    `Version ${version.number} · ${version.status === "draft" ? "Edit questions and sections, then save and preview." : "This published version is immutable."}`,
  );
  const mark = () => {
    unsaved = true;
    const note = document.querySelector("#save-status");
    if (note) note.textContent = "Unsaved changes";
  };
  async function save() {
    draft.title = document.querySelector("#draft-title").value;
    draft.description = document.querySelector("#draft-description").value;
    draft.language = document.querySelector("#draft-language").value;
    draft.starts_at = document.querySelector("#draft-start").value || null;
    draft.ends_at = document.querySelector("#draft-end").value || null;
    draft.reporting_start =
      document.querySelector("#draft-report-start").value || null;
    draft.reporting_end =
      document.querySelector("#draft-report-end").value || null;
    const result = await api(`/forms/${formId}/versions/${version.id}`, {
      method: "PUT",
      body: draft,
    });
    draft.revision = result.revision;
    version.revision = result.revision;
    unsaved = false;
    document.querySelector("#save-status").textContent = "All changes saved";
    toast("Draft saved.");
  }
  function draw() {
    actions(
      `${button("Preview", `/dashboard/forms/${formId}/preview?version=${version.id}`)}<details class="export-menu"><summary class="button">Export Excel</summary><div><a href="/api/admin/forms/${formId}/export/excel?version_id=${version.id}">Questions only</a><a href="/api/admin/forms/${formId}/export/excel?version_id=${version.id}&answers=true">Questions & answers</a></div></details>${editable ? '<button class="button primary" id="save-draft">Save changes</button>' : '<button class="button primary" id="new-version">Create new draft</button>'}`,
    );
    setContent(
      `<div class="editor-layout"><div>${!editable ? '<p class="notice">This version is preserved. Create a new draft to make changes.</p>' : ""}${draft.sections.map((s, si) => `<section class="panel section-block" data-section-index="${si}"><div class="section-heading" ${editable ? `draggable="true" data-section-drag="${si}"` : ""}><span class="badge">${si + 1}</span><h2>${e(s.title)}</h2>${!s.enabled ? badge("disabled") : ""}${editable ? `<div class="actions"><button class="icon-button" data-section-up="${si}" aria-label="Move section up" ${si === 0 ? "disabled" : ""}>↑</button><button class="icon-button" data-section-down="${si}" aria-label="Move section down" ${si === draft.sections.length - 1 ? "disabled" : ""}>↓</button><button class="button small" data-edit-section="${si}">Edit</button></div>` : ""}</div>${s.questions.map((q, qi) => `<div class="question-row" data-question="${si}:${qi}" ${editable ? 'draggable="true"' : ""}><span class="question-handle" aria-hidden="true">⠿</span><div class="question-main"><strong>${e(q.title)}</strong><div class="question-meta"><span>${e(q.key)}</span><span>·</span><span>${e(q.kind.replaceAll("_", " "))}</span>${q.required ? "<span>· Required</span>" : ""}${q.conditions ? "<span>· Conditional</span>" : ""}${!q.enabled ? "<span>· Disabled</span>" : ""}</div></div>${editable ? `<div class="actions"><button class="icon-button" data-question-up="${si}:${qi}" aria-label="Move question up" ${qi === 0 ? "disabled" : ""}>↑</button><button class="icon-button" data-question-down="${si}:${qi}" aria-label="Move question down" ${qi === s.questions.length - 1 ? "disabled" : ""}>↓</button><button class="button small" data-edit-question="${si}:${qi}">Edit</button></div>` : ""}</div>`).join("")}${editable ? `<div class="section-footer"><button class="button small" data-add-question="${si}">＋ Add question</button></div>` : ""}</section>`).join("") || empty("Structure your survey", "Start with a section, then add the questions you need.")}${editable ? '<button class="button" id="add-section">＋ Add section</button>' : ""}</div><aside class="editor-sidebar stack"><section class="panel"><div class="panel-head"><h2>Form settings</h2>${badge(form.archived ? "archived" : version.status)}</div><div class="panel-body field-stack"><label>Title<input id="draft-title" value="${e(draft.title)}" maxlength="255" ${editable ? "" : "disabled"}></label><label>Description<textarea id="draft-description" ${editable ? "" : "disabled"}>${e(draft.description)}</textarea></label><label>Language<select id="draft-language" ${editable ? "" : "disabled"}>${["my", "en", "bilingual"].map((l) => `<option value="${l}" ${draft.language === l ? "selected" : ""}>${{ my: "Burmese", en: "English", bilingual: "Bilingual" }[l]}</option>`).join("")}</select></label><label>Default reporting From date<input type="date" id="draft-report-start" value="${e(draft.reporting_start || "")}" ${editable ? "" : "disabled"}></label><label>Default reporting To date<input type="date" id="draft-report-end" value="${e(draft.reporting_end || "")}" ${editable ? "" : "disabled"}></label><label>Available from (UTC)<input type="datetime-local" id="draft-start" value="${e(draft.starts_at?.slice(0, 16) || "")}" ${editable ? "" : "disabled"}></label><label>Available until (UTC)<input type="datetime-local" id="draft-end" value="${e(draft.ends_at?.slice(0, 16) || "")}" ${editable ? "" : "disabled"}></label><p class="editor-meta" id="save-status">${unsaved ? "Unsaved changes" : "All changes saved"}</p>${editable ? '<button class="button primary" id="publish-form">Publish this version</button>' : ""}</div></section><section class="panel"><div class="panel-head"><h2>Version history</h2></div><div class="panel-body">${form.versions.map((v) => `<a class="quick-link" href="?version=${v.id}"><strong>Version ${v.number}</strong>${badge(v.status)}</a>`).join("")}</div></section><section class="panel panel-body field-stack"><button class="button" id="duplicate-form">Duplicate form</button><button class="button" id="archive-form">${form.archived ? "Restore form" : "Archive form"}</button>${editable ? '<button class="button danger" id="delete-form">Delete unpublished form</button>' : ""}</section></aside></div>`,
    );
    if (editable) {
      document
        .querySelectorAll(
          ".editor-sidebar input,.editor-sidebar textarea,.editor-sidebar select",
        )
        .forEach(
          (input) =>
            (input.oninput = () => {
              syncMeta();
              mark();
            }),
        );
      document.querySelector("#save-draft").onclick = (event) =>
        busy(event.currentTarget, async () => {
          try {
            await save();
          } catch (error) {
            toast(error.message);
          }
        });
      document.querySelector("#publish-form").onclick = (event) =>
        busy(event.currentTarget, async () => {
          if (
            !confirm(
              "Publish this version? Its question definitions will become immutable.",
            )
          )
            return;
          try {
            await save();
            await api(`/forms/${formId}/versions/${version.id}/publish`, {
              method: "POST",
              body: { revision: draft.revision },
            });
            unsaved = false;
            await loadEditor(formId);
          } catch (error) {
            toast(error.message);
          }
        });
      document.querySelector("#add-section").onclick = () => editSection();
      document
        .querySelectorAll("[data-edit-section]")
        .forEach(
          (b) => (b.onclick = () => editSection(Number(b.dataset.editSection))),
        );
      document
        .querySelectorAll("[data-add-question]")
        .forEach(
          (b) =>
            (b.onclick = () => editQuestion(Number(b.dataset.addQuestion))),
        );
      document
        .querySelectorAll("[data-edit-question]")
        .forEach(
          (b) =>
            (b.onclick = () =>
              editQuestion(...b.dataset.editQuestion.split(":").map(Number))),
        );
      for (const [attribute, direction] of [
        ["sectionUp", -1],
        ["sectionDown", 1],
      ])
        document
          .querySelectorAll(`[data-section-${direction < 0 ? "up" : "down"}]`)
          .forEach(
            (b) =>
              (b.onclick = () => {
                syncMeta();
                const i = Number(b.dataset[attribute]);
                [draft.sections[i], draft.sections[i + direction]] = [
                  draft.sections[i + direction],
                  draft.sections[i],
                ];
                mark();
                draw();
              }),
          );
      for (const [attribute, direction] of [
        ["questionUp", -1],
        ["questionDown", 1],
      ])
        document
          .querySelectorAll(`[data-question-${direction < 0 ? "up" : "down"}]`)
          .forEach(
            (b) =>
              (b.onclick = () => {
                syncMeta();
                const [si, qi] = b.dataset[attribute].split(":").map(Number),
                  questions = draft.sections[si].questions;
                [questions[qi], questions[qi + direction]] = [
                  questions[qi + direction],
                  questions[qi],
                ];
                mark();
                draw();
              }),
          );
      document.querySelectorAll("[data-section-drag]").forEach(
        (heading) =>
          (heading.ondragstart = (event) => {
            if (event.target.closest("button")) return event.preventDefault();
            event.dataTransfer.setData(
              "application/x-dedc-section",
              heading.dataset.sectionDrag,
            );
          }),
      );
      document.querySelectorAll("[data-section-index]").forEach((section) => {
        section.addEventListener("dragover", (event) => event.preventDefault());
        section.addEventListener("drop", (event) => {
          const raw = event.dataTransfer.getData("application/x-dedc-section");
          if (raw === "") return;
          event.preventDefault();
          syncMeta();
          const from = Number(raw),
            to = Number(section.dataset.sectionIndex);
          if (from === to) return;
          const [moved] = draft.sections.splice(from, 1);
          draft.sections.splice(to, 0, moved);
          mark();
          draw();
        });
      });
      let dragged;
      document.querySelectorAll("[data-question]").forEach((row) => {
        row.ondragstart = (event) => {
          if (event.target.closest("button,input"))
            return event.preventDefault();
          dragged = row.dataset.question;
        };
        row.ondragover = (event) => event.preventDefault();
        row.ondrop = (event) => {
          event.preventDefault();
          if (!dragged) return;
          syncMeta();
          const [fromS, fromQ] = dragged.split(":").map(Number),
            [toS, toQ] = row.dataset.question.split(":").map(Number),
            [question] = draft.sections[fromS].questions.splice(fromQ, 1);
          draft.sections[toS].questions.splice(toQ, 0, question);
          mark();
          draw();
        };
      });
    } else
      document.querySelector("#new-version").onclick = (event) =>
        busy(event.currentTarget, async () => {
          try {
            await api(`/forms/${formId}/versions`, { method: "POST" });
            location.href = "/dashboard/forms/" + formId;
          } catch (error) {
            toast(error.message);
          }
        });
    document.querySelector("#duplicate-form").onclick = (event) =>
      busy(event.currentTarget, async () => {
        try {
          const copy = await api(`/forms/${formId}/duplicate`, {
            method: "POST",
          });
          unsaved = false;
          location.href = "/dashboard/forms/" + copy.id;
        } catch (error) {
          toast(error.message);
        }
      });
    document.querySelector("#archive-form").onclick = (event) =>
      busy(event.currentTarget, async () => {
        if (
          !confirm(
            form.archived
              ? "Restore this form?"
              : "Archive this form? Published schemas will no longer accept new submissions.",
          )
        )
          return;
        await api(`/forms/${formId}/archive`, {
          method: "POST",
          body: { archived: !form.archived },
        });
        unsaved = false;
        loadEditor(formId);
      });
    if (editable)
      document.querySelector("#delete-form").onclick = (event) =>
        busy(event.currentTarget, async () => {
          if (
            !confirm(
              "Delete this unpublished form and its draft questions? Imported source answers and published history cannot be deleted here.",
            )
          )
            return;
          try {
            await api("/forms/" + formId, { method: "DELETE" });
            unsaved = false;
            location.href = "/dashboard/forms";
          } catch (error) {
            toast(error.message);
          }
        });
  }
  function syncMeta() {
    draft.title = document.querySelector("#draft-title").value;
    draft.description = document.querySelector("#draft-description").value;
    draft.language = document.querySelector("#draft-language").value;
    draft.starts_at = document.querySelector("#draft-start").value || null;
    draft.ends_at = document.querySelector("#draft-end").value || null;
    draft.reporting_start =
      document.querySelector("#draft-report-start").value || null;
    draft.reporting_end =
      document.querySelector("#draft-report-end").value || null;
  }
  function editSection(index) {
    syncMeta();
    const section =
        index === undefined
          ? {
              title: "",
              description: "",
              enabled: true,
              questions: [],
              conditions: null,
            }
          : draft.sections[index],
      dialog = modal(
        index === undefined ? "Add section" : "Edit section",
        `<form id="section-form" class="field-stack"><label>Section title<input name="title" required value="${e(section.title)}"></label><label>Description<textarea name="description">${e(section.description)}</textarea></label><label class="check-label"><input type="checkbox" name="enabled" ${section.enabled ? "checked" : ""}>Enabled</label><div id="section-conditions" class="field-stack"></div><div class="dialog-actions">${index !== undefined ? '<button class="button danger" type="button" id="remove-section">Delete section</button><button class="button" type="button" id="copy-section">Duplicate</button>' : ""}<button class="button primary" type="submit">Save section</button></div></form>`,
      );
    const readSectionConditions = conditionEditor(
      document.querySelector("#section-conditions"),
      draft.sections
        .flatMap((s) => s.questions)
        .filter((q) => !section.questions.some((own) => own.key === q.key)),
      section.conditions,
    );
    document.querySelector("#section-form").onsubmit = (event) => {
      event.preventDefault();
      try {
        const values = Object.fromEntries(new FormData(event.target)),
          updated = {
            ...section,
            title: values.title,
            description: values.description,
            enabled: event.target.enabled.checked,
            conditions: readSectionConditions(),
          };
        if (index === undefined) draft.sections.push(updated);
        else draft.sections[index] = updated;
        mark();
        dialog.close();
        draw();
      } catch (error) {
        errorMessage(error);
      }
    };
    if (index !== undefined) {
      document.querySelector("#remove-section").onclick = () => {
        if (confirm("Delete this section and its draft questions?")) {
          draft.sections.splice(index, 1);
          mark();
          dialog.close();
          draw();
        }
      };
      document.querySelector("#copy-section").onclick = () => {
        const copy = structuredClone(section);
        copy.title += " (copy)";
        copy.questions.forEach(
          (q) =>
            (q.key =
              q.key.slice(0, 85) + "_" + crypto.randomUUID().slice(0, 8)),
        );
        draft.sections.splice(index + 1, 0, copy);
        mark();
        dialog.close();
        draw();
      };
    }
  }
  function editQuestion(si, qi) {
    syncMeta();
    const questions = draft.sections[si].questions,
      q =
        qi === undefined
          ? {
              key: "question_" + crypto.randomUUID().slice(0, 8),
              title: "",
              title_my: "",
              title_en: "",
              kind: "short_text",
              required: false,
              enabled: true,
              help_text: "",
              placeholder: "",
              config: {},
              conditions: null,
              options: [],
            }
          : questions[qi];
    const dialog = modal(
      qi === undefined ? "Add question" : "Edit question",
      `<form id="question-form" class="field-stack"><div class="form-grid"><label class="full">Question title<textarea name="title" required>${e(q.title)}</textarea></label><label>Unique key<input name="key" required pattern="[a-z][a-z0-9_]{0,99}" value="${e(q.key)}"></label><label>Question type<select name="kind">${kinds.map((k) => `<option value="${k}" ${q.kind === k ? "selected" : ""}>${k.replaceAll("_", " ")}</option>`).join("")}</select></label><label>Burmese title<textarea name="title_my">${e(q.title_my)}</textarea></label><label>English title<textarea name="title_en">${e(q.title_en)}</textarea></label><label>Help text<input name="help_text" value="${e(q.help_text)}"></label><label>Placeholder<input name="placeholder" maxlength="255" value="${e(q.placeholder)}"></label><label class="check-label"><input type="checkbox" name="required" ${q.required ? "checked" : ""}>Required</label><label class="check-label"><input type="checkbox" name="enabled" ${q.enabled ? "checked" : ""}>Enabled</label><label class="full">Choice options (one value | label per line)<textarea name="options" placeholder="yes | Yes\nno | No">${q.options.map((o) => e(o.value + " | " + o.label)).join("\n")}</textarea></label><label>Minimum value<input type="number" step="any" name="min" value="${e(q.config.min ?? "")}"></label><label>Maximum value<input type="number" step="any" name="max" value="${e(q.config.max ?? "")}"></label><label>Minimum text length<input type="number" min="0" name="min_length" value="${e(q.config.min_length ?? "")}"></label><label>Maximum text length<input type="number" min="0" name="max_length" value="${e(q.config.max_length ?? "")}"></label></div><label>Custom text validation (regular expression)<input name="pattern" maxlength="500" value="${e(q.config.pattern || "")}" placeholder="e.g. [A-Z]{2}[0-9]{4}"></label><label>Default value (JSON, optional)<input name="default_value" value="${q.config.default !== undefined ? e(JSON.stringify(q.config.default)) : ""}" placeholder='e.g. 0 or "Text"'></label><label>Calculated field configuration (JSON)<textarea name="formula" class="code-input" placeholder='{"operation":"sum","questions":["first_count","second_count"]}'>${q.config.formula ? e(JSON.stringify(q.config.formula, null, 2)) : ""}</textarea></label><label>Repeating group fields (JSON array)<textarea name="repeat_fields" class="code-input" placeholder='[{"key":"name","title":"Name","kind":"short_text","required":true}]'>${q.config.fields ? e(JSON.stringify(q.config.fields, null, 2)) : ""}</textarea></label><div id="question-conditions" class="field-stack"></div><div class="dialog-actions">${qi !== undefined ? '<button type="button" class="button danger" id="remove-question">Delete question</button><button type="button" class="button" id="copy-question">Duplicate</button>' : ""}<button class="button primary" type="submit">Save question</button></div></form>`,
    );
    const readQuestionConditions = conditionEditor(
      document.querySelector("#question-conditions"),
      draft.sections
        .flatMap((s) => s.questions)
        .filter((other) => other.key !== q.key),
      q.conditions,
    );
    document.querySelector("#question-form").onsubmit = (event) => {
      event.preventDefault();
      try {
        const values = Object.fromEntries(new FormData(event.target)),
          config = { ...q.config };
        for (const key of ["min", "max", "min_length", "max_length"]) {
          if (values[key] !== "") config[key] = Number(values[key]);
          else delete config[key];
        }
        if (values.pattern) config.pattern = values.pattern;
        else delete config.pattern;
        if (values.default_value !== "")
          config.default = JSON.parse(values.default_value);
        else delete config.default;
        if (values.formula) config.formula = JSON.parse(values.formula);
        else delete config.formula;
        if (values.repeat_fields)
          config.fields = JSON.parse(values.repeat_fields);
        else delete config.fields;
        const options = values.options
          .split("\n")
          .map((v) => v.trim())
          .filter(Boolean)
          .map((line) => {
            const [value, ...rest] = line.split("|");
            return {
              value: value.trim(),
              label: (rest.join("|") || value).trim(),
            };
          });
        const updated = {
          ...q,
          ...Object.fromEntries(
            [
              "key",
              "title",
              "title_my",
              "title_en",
              "kind",
              "help_text",
              "placeholder",
            ].map((k) => [k, values[k]]),
          ),
          required: event.target.required.checked,
          enabled: event.target.enabled.checked,
          config,
          conditions: readQuestionConditions(),
          options,
        };
        if (qi === undefined) questions.push(updated);
        else questions[qi] = updated;
        mark();
        dialog.close();
        draw();
      } catch (error) {
        errorMessage(error);
      }
    };
    if (qi !== undefined) {
      document.querySelector("#remove-question").onclick = () => {
        if (confirm("Delete this draft question?")) {
          questions.splice(qi, 1);
          mark();
          dialog.close();
          draw();
        }
      };
      document.querySelector("#copy-question").onclick = () => {
        const copy = structuredClone(q);
        copy.key = q.key.slice(0, 85) + "_" + crypto.randomUUID().slice(0, 8);
        questions.splice(qi + 1, 0, copy);
        mark();
        dialog.close();
        draw();
      };
    }
  }
  draw();
}
export async function loadPreview(formId) {
  const form = await api("/forms/" + formId),
    params = new URLSearchParams(location.search),
    version =
      form.versions.find((v) => v.id == params.get("version")) ||
      form.versions.at(-1);
  describe(
    `Version ${version.number} · The same dynamic renderer used by the survey page.`,
  );
  actions(
    button(
      "Back to builder",
      `/dashboard/forms/${formId}?version=${version.id}`,
    ),
  );
  setContent(
    `<div class="preview-controls"><span class="badge">${e(version.status)}</span><button class="button small" data-width="900">Desktop</button><button class="button small" data-width="768">Tablet</button><button class="button small" data-width="390">Mobile</button><label class="sr-only" for="preview-language">Preview language</label><select id="preview-language" style="width:auto"><option value="my">Burmese</option><option value="en">English (original label fallback)</option></select></div><div id="preview-frame" class="preview-frame"></div>`,
  );
  const paint = () =>
    renderSurvey(document.querySelector("#preview-frame"), version, {
      language: document.querySelector("#preview-language").value,
      uploadFile: async (key, file) => {
        const body = new FormData();
        body.set("key", key);
        body.set("file", file);
        return api(`/forms/${formId}/versions/${version.id}/files`, {
          method: "POST",
          body,
        });
      },
      onSubmit: async (answers) => {
        await api(`/forms/${formId}/versions/${version.id}/validate`, {
          method: "POST",
          body: { answers },
        });
        toast(
          "All visible answers passed validation. No submission was saved.",
        );
      },
    });
  paint();
  document.querySelector("#preview-language").onchange = paint;
  document
    .querySelectorAll("[data-width]")
    .forEach(
      (b) =>
        (b.onclick = () =>
          (document.querySelector("#preview-frame").style.maxWidth =
            b.dataset.width + "px")),
    );
}
