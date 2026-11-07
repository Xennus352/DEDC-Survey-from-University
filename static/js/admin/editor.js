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
  safeRegExp,
  safeTest,
  safeFullMatch,
  escapeRegExp,
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
const kindLabels = {
  short_text: "Short answer", long_text: "Paragraph", number: "Whole number",
  decimal: "Decimal number", single_choice: "Choose one", multiple_choice: "Choose several",
  dropdown: "Dropdown", radio: "Radio buttons", checkboxes: "Checkboxes",
  date: "Date", time: "Time", datetime: "Date and time", yes_no: "Yes / No",
  location: "Location", information: "Information only", calculated: "Calculated answer",
  repeating_group: "Repeated answers", image: "Image upload", file: "File upload",
};
const choiceKinds = ["single_choice", "multiple_choice", "dropdown", "radio", "checkboxes"];
function kindOptions(selected) {
  return kinds.map((kind) => `<option value="${kind}" ${kind === selected ? "selected" : ""}>${kindLabels[kind]}</option>`).join("");
}
function readOptions(text) {
  const options = text.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const [value, ...label] = line.split("|");
    return { value: value.trim(), label: (label.join("|") || value).trim() };
  });
  if (!options.length || options.some((o) => !o.value || o.value.length > 255 || o.label.length > 1024))
    throw new Error("Add an answer choice on each line (up to 255 characters per value).");
  if (options.length > 200 || new Set(options.map((o) => o.value)).size !== options.length)
    throw new Error("Use at most 200 choices, with a different value for each choice.");
  return options;
}
function newQuestion() {
  return { key: "question_" + crypto.randomUUID().slice(0, 8), title: "", title_my: "",
    title_en: "", kind: "short_text", required: false, enabled: true, help_text: "",
    placeholder: "", config: {}, conditions: null, options: [] };
}
function definition(v) {
  return Object.fromEntries(
    [
      "title",
      "description",
      "language",
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
  try {
    return await _loadEditor(formId);
  } catch (error) {
    console.error("Editor load error:", error);
    setContent(
      `<div class="notice error" role="alert">${e(
        "Failed to load editor: " + error.message
      )}</div><button class="button" id="retry-editor">Retry</button>`
    );
    document.querySelector("#retry-editor").onclick = () => loadEditor(formId);
  }
}

async function _loadEditor(formId) {
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
    try {
      _draw();
    } catch (error) {
      console.error("Editor draw error:", error);
      toast("Failed to render editor: " + error.message);
    }
  }

  function _draw() {
    actions(
      `${button("Preview", `/dashboard/forms/${formId}/preview?version=${version.id}`)}<details class="export-menu"><summary class="button">Export Excel</summary><div><a href="/api/admin/forms/${formId}/export/excel?version_id=${version.id}">Questions only</a><a href="/api/admin/forms/${formId}/export/excel?version_id=${version.id}&answers=true">Questions & answers</a></div></details>${editable ? '<button class="button primary" id="save-draft">Save changes</button>' : '<button class="button primary" id="new-version">Create new draft</button>'}`,
    );
    setContent(
      `<div class="editor-layout"><div>${!editable ? '<p class="notice">This version is preserved. Create a new draft to make changes.</p>' : ""}${draft.sections.map((s, si) => `<section class="panel section-block" data-section-index="${si}"><div class="section-heading" ${editable ? `draggable="true" data-section-drag="${si}"` : ""}><span class="badge">${si + 1}</span><h2>${e(s.title)}</h2>${!s.enabled ? badge("disabled") : ""}${editable ? `<div class="actions"><button class="icon-button" data-section-up="${si}" aria-label="Move section up" ${si === 0 ? "disabled" : ""}>↑</button><button class="icon-button" data-section-down="${si}" aria-label="Move section down" ${si === draft.sections.length - 1 ? "disabled" : ""}>↓</button><button class="button small" data-edit-section="${si}">Edit</button></div>` : ""}</div>${s.questions.map((q, qi) => `<div class="question-row" data-question="${si}:${qi}" ${editable ? 'draggable="true"' : ""}><span class="question-handle" aria-hidden="true">⠿</span><div class="question-main"><strong>${e(q.title)}</strong><div class="question-meta"><span>${e(q.key)}</span><span>·</span><span>${e(kindLabels[q.kind] || q.kind)}</span>${q.required ? "<span>· Required</span>" : ""}${q.conditions ? "<span>· Conditional</span>" : ""}${!q.enabled ? "<span>· Disabled</span>" : ""}</div></div>${editable ? `<div class="actions"><button class="icon-button" data-question-up="${si}:${qi}" aria-label="Move question up" ${qi === 0 ? "disabled" : ""}>↑</button><button class="icon-button" data-question-down="${si}:${qi}" aria-label="Move question down" ${qi === s.questions.length - 1 ? "disabled" : ""}>↓</button><button class="button small" data-edit-question="${si}:${qi}">Edit</button></div>` : ""}</div>`).join("")}${editable ? `<div class="section-footer actions"><button class="button small" data-add-question="${si}">＋ Add question</button><button class="button small" data-paste-questions="${si}">Paste questions</button></div>` : ""}</section>`).join("") || empty("Add your first question", "Write a question or paste a list. Your first section is created for you.", editable ? '<div class="actions"><button class="button primary" id="first-question">Add question</button><button class="button" id="first-paste">Paste questions</button></div>' : "")}${editable ? '<button class="button" id="add-section">＋ Add section</button>' : ""}</div><aside class="editor-sidebar stack"><section class="panel"><div class="panel-head"><h2>Form settings</h2>${badge(form.archived ? "archived" : version.status)}</div><div class="panel-body field-stack"><label>Title<input id="draft-title" value="${e(draft.title)}" maxlength="255" ${editable ? "" : "disabled"}></label><label>Description<textarea id="draft-description" ${editable ? "" : "disabled"}>${e(draft.description)}</textarea></label><label>Reporting from (year A)<input type="date" id="draft-report-start" value="${e(draft.reporting_start || "")}" ${editable ? "" : "disabled"}></label><label>Reporting to (year B)<input type="date" id="draft-report-end" value="${e(draft.reporting_end || "")}" ${editable ? "" : "disabled"}></label><p class="editor-meta" id="save-status">${unsaved ? "Unsaved changes" : "All changes saved"}</p>${editable ? '<button class="button primary" id="publish-form">Publish this version</button>' : ""}</div></section><section class="panel"><div class="panel-head"><h2>Version history</h2></div><div class="panel-body">${form.versions.map((v) => `<a class="quick-link" href="?version=${v.id}"><strong>Version ${v.number}</strong>${badge(v.status)}</a>`).join("")}</div></section><section class="panel panel-body field-stack"><button class="button" id="duplicate-form">Duplicate form</button><button class="button" id="archive-form">${form.archived ? "Restore form" : "Archive form"}</button>${editable ? '<button class="button danger" id="delete-form">Delete unpublished form</button>' : ""}</section></aside></div>`,
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
      const first = document.querySelector("#first-question");
      if (first) first.onclick = () => editQuestion();
      const paste = document.querySelector("#first-paste");
      if (paste) paste.onclick = () => pasteQuestions();
      document.querySelectorAll("[data-paste-questions]").forEach((button) => {
        button.onclick = () => pasteQuestions(Number(button.dataset.pasteQuestions));
      });
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
        `<form id="section-form" class="field-stack"><label>Section title<input name="title" required value="${e(section.title)}"></label><label class="check-label"><input type="checkbox" name="enabled" ${section.enabled ? "checked" : ""}>Enabled</label><div class="dialog-actions">${index !== undefined ? '<button class="button danger" type="button" id="remove-section">Delete section</button><button class="button" type="button" id="copy-section">Duplicate</button>' : ""}<button class="button primary" type="submit">Save section</button></div></form>`,
      );
    document.querySelector("#section-form").onsubmit = (event) => {
      event.preventDefault();
      try {
        const values = Object.fromEntries(new FormData(event.target)),
          updated = {
            ...section,
            title: values.title,
            enabled: event.target.enabled.checked,
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
        draft.sections.splice(index + 1, 0, copy);
        mark();
        dialog.close();
        draw();
      };
    }
  }
  function checkCapacity(si, count) {
    if ((si === undefined ? 0 : draft.sections[si].questions.length) + count > 500 ||
        draft.sections.flatMap((s) => s.questions).length + count > 1000 ||
        (si === undefined && draft.sections.length >= 50))
      throw new Error("A section supports up to 500 questions; a form supports up to 50 sections and 1,000 questions.");
  }
  function pasteQuestions(si) {
    syncMeta();
    const dialog = modal("Paste questions", `<form id="paste-form" class="field-stack">
      <label>Questions<textarea name="titles" rows="8" required autofocus aria-describedby="paste-hint" placeholder="First question\nSecond question\nThird question"></textarea><span class="field-hint" id="paste-hint">One question per line. All questions use the answer type below; you can edit each later.</span></label>
      <label>Answer type<select name="kind">${kindOptions("short_text")}</select></label>
      <label data-bulk-choices hidden>Answer choices<textarea name="options" placeholder="One choice per line"></textarea><span class="field-hint">These choices apply to every question in this batch.</span></label>
      <label class="check-label"><input type="checkbox" name="required">Required</label>
      <p class="field-hint" id="paste-count" role="status">0 questions ready to add</p>
      <div class="dialog-actions"><button type="submit" class="button primary">Add questions</button></div>
    </form>`);
    const form = document.querySelector("#paste-form");
    const titles = () => form.elements.titles.value.split("\n").map((line) => line.trim()).filter(Boolean);
    form.elements.titles.oninput = () => {
      document.querySelector("#paste-count").textContent = `${titles().length} questions ready to add`;
    };
    form.elements.kind.onchange = () => {
      form.querySelector("[data-bulk-choices]").hidden = !choiceKinds.includes(form.elements.kind.value);
    };
    form.onsubmit = (event) => {
      event.preventDefault();
      try {
        const lines = titles();
        if (!lines.length || lines.some((title) => title.length > 10000))
          throw new Error("Enter a question on each line, up to 10,000 characters per question.");
        checkCapacity(si, lines.length);
        const kind = form.elements.kind.value;
        const options = choiceKinds.includes(kind) ? readOptions(form.elements.options.value) : [];
        const batch = lines.map((title) => ({ ...newQuestion(), title, kind,
          required: form.elements.required.checked, options: structuredClone(options) }));
        if (si === undefined) draft.sections.push({ title: "Questions", description: "", enabled: true, conditions: null, questions: batch });
        else draft.sections[si].questions.push(...batch);
        mark();
        dialog.close();
        draw();
        toast(`${batch.length} questions added. Save changes to keep them.`);
      } catch (error) { errorMessage(error); }
    };
  }
  function editQuestion(si, qi) {
    syncMeta();
    const questions = si === undefined ? [] : draft.sections[si].questions;
    const originalQuestion = qi === undefined ? null : questions[qi];
    let q =
        qi === undefined
          ? newQuestion()
          : questions[qi];
    const dialog = modal(
      qi === undefined ? "Add question" : "Edit question",
      `<form id="question-form" class="field-stack">
        <label><span id="question-title-label">Question title</span><textarea aria-labelledby="question-title-label" name="title" required maxlength="10000" autofocus aria-describedby="question-library-hint" placeholder="Type your question in Burmese or English…">${e(q.title)}</textarea></label>
        <p class="field-hint" id="question-library-hint">Saved questions appear as you type. New questions are saved to the library when you add them.</p>
        <div class="question-suggestions" id="question-suggestions" aria-live="polite" hidden></div>
        <label><span id="question-kind-label">Answer type</span><select aria-labelledby="question-kind-label" name="kind">${kindOptions(q.kind)}</select></label>
        <label class="check-label"><input type="checkbox" name="required" ${q.required ? "checked" : ""}>Required</label>
        <label data-choice-options ${choiceKinds.includes(q.kind) ? "" : "hidden"}><span id="question-options-label">Answer choices</span><textarea name="options" aria-labelledby="question-options-label" aria-describedby="choices-hint" placeholder="One choice per line">${q.options.map((o) => e(o.value === o.label ? o.label : o.value + " | " + o.label)).join("\n")}</textarea><span class="field-hint" id="choices-hint">One choice per line. For a separate stored value, use value | label.</span></label>
        <div class="form-grid" data-number-settings ${["number", "decimal"].includes(q.kind) ? "" : "hidden"}>
          <label>Minimum value<input type="number" step="any" name="min" value="${e(q.config.min ?? "")}"></label>
          <label>Maximum value<input type="number" step="any" name="max" value="${e(q.config.max ?? "")}"></label>
        </div>
        <details class="editor-advanced" ${["calculated", "repeating_group"].includes(q.kind) ? "open" : ""}>
          <summary>More settings</summary><div class="field-stack">
            <label>Help text<input name="help_text" maxlength="5000" value="${e(q.help_text)}"></label>
            <label>Placeholder<input name="placeholder" maxlength="255" value="${e(q.placeholder)}"></label>
            <div class="form-grid">
              <label><span id="question-burmese-label">Burmese title</span><textarea aria-labelledby="question-burmese-label" name="title_my" maxlength="10000">${e(q.title_my)}</textarea></label>
              <label><span id="question-english-label">English title</span><textarea aria-labelledby="question-english-label" name="title_en" maxlength="10000">${e(q.title_en)}</textarea></label>
            </div>
            <div class="form-grid" data-text-settings>
              <label>Minimum text length<input type="number" min="0" max="20000" name="min_length" value="${e(q.config.min_length ?? "")}"></label>
              <label>Maximum text length<input type="number" min="0" max="20000" name="max_length" value="${e(q.config.max_length ?? "")}"></label>
              <label class="full">Custom text validation (regular expression)<input name="pattern" maxlength="500" value="${e(q.config.pattern || "")}"></label>
            </div>
            <label>Default value (JSON, optional)<input name="default_value" value="${q.config.default !== undefined ? e(JSON.stringify(q.config.default)) : ""}" placeholder='e.g. 0 or "Text"'></label>
            <label data-formula>Calculated field configuration (JSON)<textarea name="formula" class="code-input" placeholder='{"operation":"sum","questions":["first_count","second_count"]}'>${q.config.formula ? e(JSON.stringify(q.config.formula, null, 2)) : ""}</textarea></label>
            <label data-repeat>Repeating group fields (JSON array)<textarea name="repeat_fields" class="code-input" placeholder='[{"key":"name","title":"Name","kind":"short_text"}]'>${q.config.fields ? e(JSON.stringify(q.config.fields, null, 2)) : ""}</textarea></label>
            <div id="question-conditions" class="field-stack"></div>
            <label><span id="question-key-label">Unique key</span><input aria-labelledby="question-key-label" name="key" required pattern="[a-z][a-z0-9_]{0,99}" value="${e(q.key)}" aria-describedby="key-hint"><span class="field-hint" id="key-hint">Generated automatically. Keep this key when editing an existing question.</span></label>
            <label class="check-label"><input type="checkbox" name="enabled" ${q.enabled ? "checked" : ""}>Enabled</label>
          </div>
        </details>
        <div class="dialog-actions">
          ${qi !== undefined ? '<button type="button" class="button danger" id="remove-question">Delete question</button><button type="button" class="button" id="copy-question">Duplicate</button>' : '<button class="button" type="submit" name="next" value="yes">Save & add another</button>'}
          <button class="button primary" type="submit">Save question</button>
        </div>
      </form>`,
    );
    const questionForm = document.querySelector("#question-form");
    function updateFields() {
      const kind = questionForm.elements.kind.value;
      questionForm.querySelector("[data-choice-options]").hidden = !choiceKinds.includes(kind);
      questionForm.querySelector("[data-number-settings]").hidden = !["number", "decimal"].includes(kind);
      questionForm.querySelector("[data-text-settings]").hidden = !["short_text", "long_text"].includes(kind);
      questionForm.querySelector("[data-formula]").hidden = kind !== "calculated";
      questionForm.querySelector("[data-repeat]").hidden = kind !== "repeating_group";
      if (["calculated", "repeating_group"].includes(kind)) questionForm.querySelector("details").open = true;
    }
    questionForm.elements.kind.onchange = updateFields;
    updateFields();
    const readQuestionConditions = conditionEditor(
      document.querySelector("#question-conditions"),
      draft.sections
        .flatMap((s) => s.questions)
        .filter((other) => other.key !== q.key),
      q.conditions,
    );
    const suggestions = document.querySelector("#question-suggestions");
    let searchTimer, searchRequest = 0;
    const applySuggestion = (template) => {
      q = { ...q, ...structuredClone(template) };
      for (const name of ["title", "title_my", "title_en", "kind", "help_text", "placeholder"]) questionForm.elements[name].value = q[name] || "";
      questionForm.elements.required.checked = q.required;
      questionForm.elements.enabled.checked = q.enabled;
      questionForm.elements.options.value = q.options.map((o) => o.value === o.label ? o.label : `${o.value} | ${o.label}`).join("\n");
      for (const name of ["min", "max", "min_length", "max_length", "pattern"]) questionForm.elements[name].value = q.config[name] ?? "";
      questionForm.elements.default_value.value = q.config.default === undefined ? "" : JSON.stringify(q.config.default);
      questionForm.elements.formula.value = q.config.formula ? JSON.stringify(q.config.formula) : "";
      questionForm.elements.repeat_fields.value = q.config.fields ? JSON.stringify(q.config.fields) : "";
      searchRequest++;
      suggestions.hidden = true;
      updateFields();
      document.querySelector("#question-library-hint").textContent = "Saved question selected. Review its settings, then add it to this form.";
      questionForm.elements.kind.focus();
    };
    questionForm.elements.title.addEventListener("input", () => {
      clearTimeout(searchTimer);
      const request = ++searchRequest;
      const text = questionForm.elements.title.value.trim();
      suggestions.hidden = !text;
      if (!text) return;
      suggestions.innerHTML = '<p class="field-hint" role="status">Looking for saved questions…</p>';
      searchTimer = setTimeout(async () => {
        try {
          const result = await api("/question-library?search=" + encodeURIComponent(text));
          if (request !== searchRequest || !dialog.open || !suggestions.isConnected) return;
          suggestions.innerHTML = result.items.length
            ? `<p class="suggestion-heading">${result.total} matching saved question${result.total === 1 ? "" : "s"}</p><div class="suggestion-list">${result.items.map((item, index) => `<button type="button" class="question-suggestion" data-suggestion="${index}"><span>${e(item.question.title)}</span><small>${e(kindLabels[item.question.kind] || item.question.kind)} · Use question</small></button>`).join("")}</div>`
            : '<p class="field-hint">No saved question matches. Add this question to save it for reuse.</p>';
          suggestions.querySelectorAll("[data-suggestion]").forEach((button) => {
            button.onclick = () => applySuggestion(result.items[Number(button.dataset.suggestion)].question);
          });
        } catch (error) {
          if (request === searchRequest && suggestions.isConnected) suggestions.innerHTML = '<p class="field-hint">Suggestions are unavailable. You can still write your question and retry adding it.</p>';
        }
      }, 250);
    });
    dialog.addEventListener("close", () => { clearTimeout(searchTimer); searchRequest++; }, { once: true });
    document.querySelector("#question-form").onsubmit = (event) => {
      event.preventDefault();
      busy(event.submitter, async () => {
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
          if (!values.title.trim()) throw new Error("Enter a question title.");
          if (draft.sections.flatMap((s) => s.questions).some((other) => other !== originalQuestion && other.key === values.key))
            throw new Error("This unique key is already used by another question.");
          const options = choiceKinds.includes(values.kind) ? readOptions(values.options) : [];
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
          if (qi === undefined) checkCapacity(si, 1);
          await api("/question-library", { method: "POST", body: updated });
          if (qi === undefined) {
            questions.push(updated);
            if (si === undefined) {
              draft.sections.push({ title: "Questions", description: "", enabled: true, conditions: null, questions });
              si = draft.sections.length - 1;
            }
          }
          else questions[qi] = updated;
          mark();
          dialog.close();
          draw();
          toast("Question saved in the library. Save changes to keep the form updated.");
          if (event.submitter?.name === "next") editQuestion(si);
        } catch (error) {
          errorMessage(error);
        }
      });
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
  try {
    return await _loadPreview(formId);
  } catch (error) {
    console.error("Preview load error:", error);
    setContent(
      `<div class="notice error" role="alert">${e(
        "Failed to load preview: " + error.message
      )}</div><button class="button" id="retry-preview">Retry</button>`
    );
    document.querySelector("#retry-preview").onclick = () => loadPreview(formId);
  }
}

async function _loadPreview(formId) {
  const form = await api("/forms/" + formId),
    params = new URLSearchParams(location.search),
    version =
      form.versions.find((v) => v.id == params.get("version")) ||
      form.versions.at(-1);
  describe(
    `Version ${version.number} · Check the survey on desktop, tablet and mobile before sharing.`,
  );
  actions(
    button(
      "Back to builder",
      `/dashboard/forms/${formId}?version=${version.id}`,
    ),
  );
  setContent(
    `<div class="preview-controls" role="group" aria-label="Preview device"><span class="badge">${e(version.status)}</span><button class="button small" data-width="900" aria-pressed="true">Desktop</button><button class="button small" data-width="768" aria-pressed="false">Tablet</button><button class="button small" data-width="390" aria-pressed="false">Mobile</button></div><div id="preview-frame" class="preview-frame"></div>`,
  );
  const paint = () =>
    renderSurvey(document.querySelector("#preview-frame"), version, {
      language: version.language || "my",
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
  document
    .querySelectorAll("[data-width]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          document.querySelector("#preview-frame").style.maxWidth = b.dataset.width + "px";
          document.querySelectorAll("[data-width]").forEach((control) =>
            control.setAttribute("aria-pressed", String(control === b)));
        }),
    );
}
