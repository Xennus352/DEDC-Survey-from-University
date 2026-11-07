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
  short_text: "အဖြေတို", long_text: "အဖြေရှည်", number: "ကိန်းပြည့်",
  decimal: "ဒသမကိန်း", single_choice: "တစ်ခုရွေးချယ်ရန်", multiple_choice: "အများအပြား ရွေးချယ်ရန်",
  dropdown: "ရွေးချယ်စာရင်း", radio: "ရေဒီယိုခလုတ်", checkboxes: "အမှန်ခြစ်ကွက်",
  date: "ရက်စွဲ", time: "အချိန်", datetime: "ရက်စွဲနှင့် အချိန်", yes_no: "ဟုတ် / မဟုတ်",
  location: "တည်နေရာ", information: "အချက်အလက်", calculated: "တွက်ချက်ထားသည့် အဖြေ",
  repeating_group: "ထပ်ခါထပ်ခါ အုပ်စု", image: "ရုပ်ပုံ", file: "ဖိုင်",
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
    throw new Error("ရွေးချယ်စရာတစ်ခုကို တစ်ကြောင်းစီ ထည့်ပါ (တန်ဖိုးတစ်ခုလျှင် စာလုံး ၂၅၅ လုံးအထိ)။");
  if (options.length > 200 || new Set(options.map((o) => o.value)).size !== options.length)
    throw new Error("ရွေးချယ်စရာ ၂၀၀ ခုအထိ ထည့်နိုင်ပြီး တစ်ခုစီအတွက် မတူညီသော တန်ဖိုး ထားပါ။");
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
        "တည်းဖြတ်ကိရိယာကို ဖွင့်မရပါ။ " + error.message
      )}</div><button class="button" id="retry-editor">ထပ်စမ်းကြည့်ရန်</button>`
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
    `ဗားရှင်း ${version.number} · ${version.status === "draft" ? "မေးခွန်းများနှင့် ကဏ္ဍများကို ပြင်ဆင်ပြီး သိမ်းဆည်းကာ အစမ်းကြည့်ပါ။" : "ဤထုတ်ဝေပြီး ဗားရှင်းကို ပြင်ဆင်၍ မရတော့ပါ။"}`,
  );
  const mark = () => {
    unsaved = true;
    const note = document.querySelector("#save-status");
    if (note) note.textContent = "မသိမ်းရသေးသော ပြောင်းလဲမှုများ";
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
    document.querySelector("#save-status").textContent = "ပြောင်းလဲမှုအားလုံး သိမ်းဆည်းပြီး";
    toast("မူကြမ်း သိမ်းဆည်းပြီးပါပြီ။");
  }
  function draw() {
    try {
      _draw();
    } catch (error) {
      console.error("Editor draw error:", error);
      toast("တည်းဖြတ်ကိရိယာကို ပြသနိုင်ခြင်း မရှိပါ။ " + error.message);
    }
  }

  function _draw() {
    actions(
      `${button("အစမ်းကြည့်ရန်", `/dashboard/forms/${formId}/preview?version=${version.id}`)}<details class="export-menu"><summary class="button">Excel ဒေါင်းလုဒ်</summary><div><a href="/api/admin/forms/${formId}/export/excel?version_id=${version.id}">မေးခွန်းများ သီးသန့်</a><a href="/api/admin/forms/${formId}/export/excel?version_id=${version.id}&answers=true">မေးခွန်းများနှင့် အဖြေများ</a></div></details>${editable ? '<button class="button primary" id="save-draft">ပြောင်းလဲမှုများ သိမ်းဆည်းရန်</button>' : '<button class="button primary" id="new-version">မူကြမ်းအသစ် ဖန်တီးရန်</button>'}`,
    );
    setContent(
      `<div class="editor-layout"><div>${!editable ? '<p class="notice">ဤဗားရှင်းကို ပြင်ဆင်၍ မရတော့ပါ။ ပြောင်းလဲလိုပါက မူကြမ်းအသစ် ဖန်တီးပါ။</p>' : ""}${draft.sections.map((s, si) => `<section class="panel section-block" data-section-index="${si}"><div class="section-heading" ${editable ? `draggable="true" data-section-drag="${si}"` : ""}><span class="badge">${si + 1}</span><h2>${e(s.title)}</h2>${!s.enabled ? badge("disabled") : ""}${editable ? `<div class="actions"><button class="icon-button" data-section-up="${si}" aria-label="ကဏ္ဍကို အပေါ်သို့ ရွှေ့ရန်" ${si === 0 ? "disabled" : ""}>↑</button><button class="icon-button" data-section-down="${si}" aria-label="ကဏ္ဍကို အောက်သို့ ရွှေ့ရန်" ${si === draft.sections.length - 1 ? "disabled" : ""}>↓</button><button class="button small" data-edit-section="${si}">ပြင်ဆင်ရန်</button></div>` : ""}</div>${s.questions.map((q, qi) => `<div class="question-row" data-question="${si}:${qi}" ${editable ? 'draggable="true"' : ""}><span class="question-handle" aria-hidden="true">⠿</span><div class="question-main"><strong>${e(q.title)}</strong><div class="question-meta"><span>${e(q.key)}</span><span>·</span><span>${e(kindLabels[q.kind] || q.kind)}</span>${q.required ? "<span>· မဖြစ်မနေ</span>" : ""}${q.conditions ? "<span>· အခြေအနေအလိုက်</span>" : ""}${!q.enabled ? "<span>· ပိတ်ထားသည်</span>" : ""}</div></div>${editable ? `<div class="actions"><button class="icon-button" data-question-up="${si}:${qi}" aria-label="မေးခွန်းကို အပေါ်သို့ ရွှေ့ရန်" ${qi === 0 ? "disabled" : ""}>↑</button><button class="icon-button" data-question-down="${si}:${qi}" aria-label="မေးခွန်းကို အောက်သို့ ရွှေ့ရန်" ${qi === s.questions.length - 1 ? "disabled" : ""}>↓</button><button class="button small" data-edit-question="${si}:${qi}">ပြင်ဆင်ရန်</button></div>` : ""}</div>`).join("")}${editable ? `<div class="section-footer actions"><button class="button small" data-add-question="${si}">＋ မေးခွန်း ထည့်ရန်</button><button class="button small" data-paste-questions="${si}">မေးခွန်းများ ကူးထည့်ရန်</button></div>` : ""}</section>`).join("") || empty("ပထမဆုံး မေးခွန်း ထည့်ပါ", "မေးခွန်းတစ်ခု ရေးပါ သို့မဟုတ် စာရင်းတစ်ခု ကူးထည့်ပါ။ ပထမဆုံး ကဏ္ဍကို အလိုအလျောက် ဖန်တီးပေးပါမည်။", editable ? '<div class="actions"><button class="button primary" id="first-question">မေးခွန်း ထည့်ရန်</button><button class="button" id="first-paste">မေးခွန်းများ ကူးထည့်ရန်</button></div>' : "")}${editable ? '<button class="button" id="add-section">＋ ကဏ္ဍ ထည့်ရန်</button>' : ""}</div><aside class="editor-sidebar stack"><section class="panel"><div class="panel-head"><h2>စစ်တမ်း ဆက်တင်များ</h2>${badge(form.archived ? "archived" : version.status)}</div><div class="panel-body field-stack"><label>ခေါင်းစဉ်<input id="draft-title" value="${e(draft.title)}" maxlength="255" ${editable ? "" : "disabled"}></label><label>ဖော်ပြချက်<textarea id="draft-description" ${editable ? "" : "disabled"}>${e(draft.description)}</textarea></label><label>အစီရင်ခံကာလ စတင်<input type="date" id="draft-report-start" value="${e(draft.reporting_start || "")}" ${editable ? "" : "disabled"}></label><label>အစီရင်ခံကာလ ပြီးဆုံး<input type="date" id="draft-report-end" value="${e(draft.reporting_end || "")}" ${editable ? "" : "disabled"}></label><p class="editor-meta" id="save-status">${unsaved ? "မသိမ်းရသေးသော ပြောင်းလဲမှုများ" : "ပြောင်းလဲမှုအားလုံး သိမ်းဆည်းပြီး"}</p>${editable ? '<button class="button primary" id="publish-form">ဤဗားရှင်းကို ထုတ်ဝေရန်</button>' : ""}</div></section><section class="panel"><div class="panel-head"><h2>ဗားရှင်း မှတ်တမ်း</h2></div><div class="panel-body">${form.versions.map((v) => `<a class="quick-link" href="?version=${v.id}"><strong>ဗားရှင်း ${v.number}</strong>${badge(v.status)}</a>`).join("")}</div></section><section class="panel panel-body field-stack"><button class="button" id="duplicate-form">စစ်တမ်း ပုံတူကူးရန်</button><button class="button" id="archive-form">${form.archived ? "စစ်တမ်း ပြန်လည်အသုံးပြုရန်" : "စစ်တမ်း မော်ကွန်းတင်ရန်"}</button>${editable ? '<button class="button danger" id="delete-form">မထုတ်ဝေရသေးသော စစ်တမ်း ဖျက်ရန်</button>' : ""}</section></aside></div>`,
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
              "ဤဗားရှင်းကို ထုတ်ဝေမလား။ ထုတ်ဝေပြီးပါက မေးခွန်းများကို ပြင်ဆင်၍ မရတော့ပါ။",
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
              ? "ဤစစ်တမ်းကို ပြန်လည်အသုံးပြုမလား။"
              : "ဤစစ်တမ်းကို မော်ကွန်းတင်မလား။ မော်ကွန်းတင်ပြီးပါက တင်သွင်းချက်အသစ်များကို လက်ခံတော့မည် မဟုတ်ပါ။",
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
              "ဤမထုတ်ဝေရသေးသော စစ်တမ်းနှင့် ၎င်း၏ မူကြမ်းမေးခွန်းများကို ဖျက်မလား။ တင်သွင်းထားသော မူရင်းအဖြေများနှင့် ထုတ်ဝေပြီး မှတ်တမ်းများကို ဤနေရာမှ ဖျက်၍ မရပါ။",
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
        index === undefined ? "ကဏ္ဍ ထည့်ရန်" : "ကဏ္ဍ ပြင်ဆင်ရန်",
        `<form id="section-form" class="field-stack"><label>ကဏ္ဍ ခေါင်းစဉ်<input name="title" required value="${e(section.title)}"></label><label class="check-label"><input type="checkbox" name="enabled" ${section.enabled ? "checked" : ""}>ပြသမည်</label><div class="dialog-actions">${index !== undefined ? '<button class="button danger" type="button" id="remove-section">ကဏ္ဍ ဖျက်ရန်</button><button class="button" type="button" id="copy-section">ပုံတူကူးရန်</button>' : ""}<button class="button primary" type="submit">ကဏ္ဍ သိမ်းဆည်းရန်</button></div></form>`,
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
        if (confirm("ဤကဏ္ဍနှင့် ၎င်း၏ မူကြမ်းမေးခွန်းများကို ဖျက်မလား။")) {
          draft.sections.splice(index, 1);
          mark();
          dialog.close();
          draw();
        }
      };
      document.querySelector("#copy-section").onclick = () => {
        const copy = structuredClone(section);
        copy.title += " (ပုံတူ)";
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
      throw new Error("ကဏ္ဍတစ်ခုလျှင် မေးခွန်း ၅၀၀ အထိ ထည့်နိုင်သည်။ စစ်တမ်းတစ်ခုလျှင် ကဏ္ဍ ၅၀ ခုနှင့် မေးခွန်း ၁,၀၀၀ အထိ ထည့်နိုင်သည်။");
  }
  function pasteQuestions(si) {
    syncMeta();
    const dialog = modal("မေးခွန်းများ ကူးထည့်ရန်", `<form id="paste-form" class="field-stack">
      <label>မေးခွန်းများ<textarea name="titles" rows="8" required autofocus aria-describedby="paste-hint" placeholder="ပထမမေးခွန်း\nဒုတိယမေးခွန်း\nတတိယမေးခွန်း"></textarea><span class="field-hint" id="paste-hint">တစ်ကြောင်းလျှင် မေးခွန်းတစ်ခု ထည့်ပါ။ မေးခွန်းအားလုံး အောက်ပါ အဖြေအမျိုးအစားကို အသုံးပြုမည် ဖြစ်ပြီး နောက်ပိုင်းတွင် တစ်ခုချင်းစီ ပြင်ဆင်နိုင်ပါသည်။</span></label>
      <label>အဖြေ အမျိုးအစား<select name="kind">${kindOptions("short_text")}</select></label>
      <label data-bulk-choices hidden>ရွေးချယ်စရာများ<textarea name="options" placeholder="တစ်ကြောင်းလျှင် ရွေးချယ်စရာတစ်ခု"></textarea><span class="field-hint">ဤရွေးချယ်စရာများကို ဤအုပ်စုရှိ မေးခွန်းအားလုံးအတွက် အသုံးပြုမည်။</span></label>
      <label class="check-label"><input type="checkbox" name="required">မဖြစ်မနေ</label>
      <p class="field-hint" id="paste-count" role="status">မေးခွန်း ၀ ခု ထည့်ရန် အသင့်ဖြစ်နေသည်</p>
      <div class="dialog-actions"><button type="submit" class="button primary">မေးခွန်းများ ထည့်ရန်</button></div>
    </form>`);
    const form = document.querySelector("#paste-form");
    const titles = () => form.elements.titles.value.split("\n").map((line) => line.trim()).filter(Boolean);
    form.elements.titles.oninput = () => {
      document.querySelector("#paste-count").textContent = `မေးခွန်း ${titles().length} ခု ထည့်ရန် အသင့်ဖြစ်နေသည်`;
    };
    form.elements.kind.onchange = () => {
      form.querySelector("[data-bulk-choices]").hidden = !choiceKinds.includes(form.elements.kind.value);
    };
    form.onsubmit = (event) => {
      event.preventDefault();
      try {
        const lines = titles();
        if (!lines.length || lines.some((title) => title.length > 10000))
          throw new Error("တစ်ကြောင်းလျှင် မေးခွန်းတစ်ခု ထည့်ပါ၊ မေးခွန်းတစ်ခုလျှင် စာလုံး ၁၀,၀၀၀ အထိ။");
        checkCapacity(si, lines.length);
        const kind = form.elements.kind.value;
        const options = choiceKinds.includes(kind) ? readOptions(form.elements.options.value) : [];
        const batch = lines.map((title) => ({ ...newQuestion(), title, kind,
          required: form.elements.required.checked, options: structuredClone(options) }));
        if (si === undefined) draft.sections.push({ title: "မေးခွန်းများ", description: "", enabled: true, conditions: null, questions: batch });
        else draft.sections[si].questions.push(...batch);
        mark();
        dialog.close();
        draw();
        toast(`မေးခွန်း ${batch.length} ခု ထည့်ပြီးပါပြီ။ သိမ်းဆည်းရန် ပြောင်းလဲမှုများကို မမေ့ပါနှင့်။`);
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
      qi === undefined ? "မေးခွန်း ထည့်ရန်" : "မေးခွန်း ပြင်ဆင်ရန်",
      `<form id="question-form" class="field-stack">
        <label><span id="question-title-label">မေးခွန်း ခေါင်းစဉ်</span><textarea aria-labelledby="question-title-label" name="title" required maxlength="10000" autofocus aria-describedby="question-library-hint" placeholder="မေးခွန်းကို မြန်မာ သို့မဟုတ် အင်္ဂလိပ်လို ရိုက်ပါ…">${e(q.title)}</textarea></label>
        <p class="field-hint" id="question-library-hint">သင်ရိုက်ထည့်သည်နှင့်အမျှ သိမ်းဆည်းထားသော မေးခွန်းများ ပေါ်လာပါမည်။ မေးခွန်းအသစ် ထည့်သည့်အခါ မေးခွန်းစာကြည့်တိုက်သို့ အလိုအလျောက် သိမ်းဆည်းပါမည်။</p>
        <div class="question-suggestions" id="question-suggestions" aria-live="polite" hidden></div>
        <label><span id="question-kind-label">အဖြေ အမျိုးအစား</span><select aria-labelledby="question-kind-label" name="kind">${kindOptions(q.kind)}</select></label>
        <label class="check-label"><input type="checkbox" name="required" ${q.required ? "checked" : ""}>မဖြစ်မနေ</label>
        <label data-choice-options ${choiceKinds.includes(q.kind) ? "" : "hidden"}><span id="question-options-label">ရွေးချယ်စရာများ</span><textarea name="options" aria-labelledby="question-options-label" aria-describedby="choices-hint" placeholder="တစ်ကြောင်းလျှင် ရွေးချယ်စရာတစ်ခု">${q.options.map((o) => e(o.value === o.label ? o.label : o.value + " | " + o.label)).join("\n")}</textarea><span class="field-hint" id="choices-hint">တစ်ကြောင်းလျှင် ရွေးချယ်စရာတစ်ခု။ သီးခြား တန်ဖိုးသိမ်းလိုပါက value | label ပုံစံ သုံးပါ။</span></label>
        <div class="form-grid" data-number-settings ${["number", "decimal"].includes(q.kind) ? "" : "hidden"}>
          <label>အနည်းဆုံးတန်ဖိုး<input type="number" step="any" name="min" value="${e(q.config.min ?? "")}"></label>
          <label>အများဆုံးတန်ဖိုး<input type="number" step="any" name="max" value="${e(q.config.max ?? "")}"></label>
        </div>
        <details class="editor-advanced" ${["calculated", "repeating_group"].includes(q.kind) ? "open" : ""}>
          <summary>နောက်ထပ် ဆက်တင်များ</summary><div class="field-stack">
            <label>အကူအညီ စာသား<input name="help_text" maxlength="5000" value="${e(q.help_text)}"></label>
            <label>ဖြည့်ရန် စာသား<input name="placeholder" maxlength="255" value="${e(q.placeholder)}"></label>
            <div class="form-grid">
              <label><span id="question-burmese-label">မြန်မာ ခေါင်းစဉ်</span><textarea aria-labelledby="question-burmese-label" name="title_my" maxlength="10000">${e(q.title_my)}</textarea></label>
              <label><span id="question-english-label">အင်္ဂလိပ် ခေါင်းစဉ်</span><textarea aria-labelledby="question-english-label" name="title_en" maxlength="10000">${e(q.title_en)}</textarea></label>
            </div>
            <div class="form-grid" data-text-settings>
              <label>အနည်းဆုံး စာသားအရှည်<input type="number" min="0" max="20000" name="min_length" value="${e(q.config.min_length ?? "")}"></label>
              <label>အများဆုံး စာသားအရှည်<input type="number" min="0" max="20000" name="max_length" value="${e(q.config.max_length ?? "")}"></label>
              <label class="full">စိတ်ကြိုက် စာသားစစ်ဆေးမှု (Regular Expression)<input name="pattern" maxlength="500" value="${e(q.config.pattern || "")}"></label>
            </div>
            <label>ပုံသေတန်ဖိုး (JSON၊ ရွေးချယ်နိုင်)<input name="default_value" value="${q.config.default !== undefined ? e(JSON.stringify(q.config.default)) : ""}" placeholder='ဥပမာ 0 သို့မဟုတ် "စာသား"'></label>
            <label data-formula>တွက်ချက်မှု ဖော်မြူလာ (JSON)<textarea name="formula" class="code-input" placeholder='{"operation":"sum","questions":["first_count","second_count"]}'>${q.config.formula ? e(JSON.stringify(q.config.formula, null, 2)) : ""}</textarea></label>
            <label data-repeat>ထပ်ခါထပ်ခါ အုပ်စု အကွက်များ (JSON array)<textarea name="repeat_fields" class="code-input" placeholder='[{"key":"name","title":"Name","kind":"short_text"}]'>${q.config.fields ? e(JSON.stringify(q.config.fields, null, 2)) : ""}</textarea></label>
            <div id="question-conditions" class="field-stack"></div>
            <label><span id="question-key-label">မေးခွန်း ကုဒ်</span><input aria-labelledby="question-key-label" name="key" required pattern="[a-z][a-z0-9_]{0,99}" value="${e(q.key)}" aria-describedby="key-hint"><span class="field-hint" id="key-hint">အလိုအလျောက် ဖန်တီးထားသည်။ ရှိပြီးသား မေးခွန်းကို ပြင်ဆင်သည့်အခါ ဤကုဒ်ကို မပြောင်းပါနှင့်။</span></label>
            <label class="check-label"><input type="checkbox" name="enabled" ${q.enabled ? "checked" : ""}>ပြသမည်</label>
          </div>
        </details>
        <div class="dialog-actions">
          ${qi !== undefined ? '<button type="button" class="button danger" id="remove-question">မေးခွန်း ဖျက်ရန်</button><button type="button" class="button" id="copy-question">ပုံတူကူးရန်</button>' : '<button class="button" type="submit" name="next" value="yes">သိမ်းဆည်းပြီး နောက်တစ်ခု ထည့်ရန်</button>'}
          <button class="button primary" type="submit">မေးခွန်း သိမ်းဆည်းရန်</button>
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
      document.querySelector("#question-library-hint").textContent = "သိမ်းဆည်းထားသော မေးခွန်းကို ရွေးပြီးပါပြီ။ ဆက်တင်များကို ပြန်စစ်ပြီး ဤစစ်တမ်းထဲ ထည့်ပါ။";
      questionForm.elements.kind.focus();
    };
    questionForm.elements.title.addEventListener("input", () => {
      clearTimeout(searchTimer);
      const request = ++searchRequest;
      const text = questionForm.elements.title.value.trim();
      suggestions.hidden = !text;
      if (!text) return;
      suggestions.innerHTML = '<p class="field-hint" role="status">သိမ်းဆည်းထားသော မေးခွန်းများ ရှာဖွေနေသည်…</p>';
      searchTimer = setTimeout(async () => {
        try {
          const result = await api("/question-library?search=" + encodeURIComponent(text));
          if (request !== searchRequest || !dialog.open || !suggestions.isConnected) return;
          suggestions.innerHTML = result.items.length
            ? `<p class="suggestion-heading">ကိုက်ညီသော သိမ်းဆည်းထားသည့် မေးခွန်း ${result.total} ခု</p><div class="suggestion-list">${result.items.map((item, index) => `<button type="button" class="question-suggestion" data-suggestion="${index}"><span>${e(item.question.title)}</span><small>${e(kindLabels[item.question.kind] || item.question.kind)} · ဤမေးခွန်းကို သုံးရန်</small></button>`).join("")}</div>`
            : '<p class="field-hint">ကိုက်ညီသော သိမ်းဆည်းထားသည့် မေးခွန်း မရှိပါ။ နောက်တစ်ကြိမ် ပြန်သုံးလိုပါက ဤမေးခွန်းကို သိမ်းထားပါ။</p>';
          suggestions.querySelectorAll("[data-suggestion]").forEach((button) => {
            button.onclick = () => applySuggestion(result.items[Number(button.dataset.suggestion)].question);
          });
        } catch (error) {
          if (request === searchRequest && suggestions.isConnected) suggestions.innerHTML = '<p class="field-hint">အကြံပြုချက်များ မရပါ။ မေးခွန်းကို ဆက်ရေးပြီး ထည့်ကြည့်နိုင်ပါသည်။</p>';
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
          if (!values.title.trim()) throw new Error("မေးခွန်း ခေါင်းစဉ် ထည့်ပါ။");
          if (draft.sections.flatMap((s) => s.questions).some((other) => other !== originalQuestion && other.key === values.key))
            throw new Error("ဤမေးခွန်းကုဒ်ကို အခြားမေးခွန်းတစ်ခုက အသုံးပြုထားပြီး ဖြစ်သည်။");
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
              draft.sections.push({ title: "မေးခွန်းများ", description: "", enabled: true, conditions: null, questions });
              si = draft.sections.length - 1;
            }
          }
          else questions[qi] = updated;
          mark();
          dialog.close();
          draw();
          toast("မေးခွန်းကို စာကြည့်တိုက်တွင် သိမ်းဆည်းပြီးပါပြီ။ စစ်တမ်းတွင် အသက်ဝင်စေရန် ပြောင်းလဲမှုများကို သိမ်းဆည်းပါ။");
          if (event.submitter?.name === "next") editQuestion(si);
        } catch (error) {
          errorMessage(error);
        }
      });
    };
    if (qi !== undefined) {
      document.querySelector("#remove-question").onclick = () => {
        if (confirm("ဤမူကြမ်းမေးခွန်းကို ဖျက်မလား။")) {
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
        "အစမ်းကြည့်ရှုမှုကို ဖွင့်မရပါ။ " + error.message
      )}</div><button class="button" id="retry-preview">ထပ်စမ်းကြည့်ရန်</button>`
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
    `ဗားရှင်း ${version.number} · မျှဝေမီ စစ်တမ်းကို ဒက်စတော့၊ တက်ဘလက်နှင့် မိုဘိုင်းတွင် စစ်ဆေးပါ။`,
  );
  actions(
    button(
      "တည်းဖြတ်ရန် ပြန်သွားရန်",
      `/dashboard/forms/${formId}?version=${version.id}`,
    ),
  );
  setContent(
    `<div class="preview-controls" role="group" aria-label="အစမ်းကြည့် စက်ပစ္စည်း">${badge(version.status)}<button class="button small" data-width="900" aria-pressed="true">ဒက်စတော့</button><button class="button small" data-width="768" aria-pressed="false">တက်ဘလက်</button><button class="button small" data-width="390" aria-pressed="false">မိုဘိုင်း</button></div><div id="preview-frame" class="preview-frame"></div>`,
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
          "အဖြေအားလုံး စစ်ဆေးမှု အောင်မြင်ပါသည်။ တင်သွင်းမှုကို သိမ်းဆည်းထားခြင်း မရှိပါ။",
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
