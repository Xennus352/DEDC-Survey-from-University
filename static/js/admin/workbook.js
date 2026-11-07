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
    "သင့် DEDC အလုပ်စာအုပ်ကို တင်သွင်းပါ။ ဖွဲ့စည်းပုံကို စစ်ဆေးပြီး မူရင်းအဖြေများကို သိမ်းဆည်းထားပါမည်။",
  );
  actions(
    `<details class="export-menu"><summary class="button">အလုပ်စာအုပ် ဒေါင်းလုဒ်</summary><div><a href="/api/admin/workbook/export/excel">မူရင်းပုံစံ · မေးခွန်းများ</a><a href="/api/admin/workbook/export/excel?answers=true">မူရင်းပုံစံ · မေးခွန်းများနှင့် အဖြေများ</a></div></details>`,
  );
  const params = new URLSearchParams(location.search);
  const tabs = `<nav class="data-tabs" aria-label="ဒေတာ စီမံခန့်ခွဲမှု"><a href="/dashboard/data" ${params.get('tab') !== 'answers' ? 'aria-current="page"' : ''}>အလုပ်စာအုပ် တင်သွင်းရန်</a><a href="/dashboard/data?tab=answers" ${params.get('tab') === 'answers' ? 'aria-current="page"' : ''}>မူရင်း အဖြေများ</a></nav>`;
  if (params.get("tab") === "answers") return sourceAnswers(params, tabs);
  setContent(
    `${tabs}<section class="panel"><div class="import-layout"><div class="import-copy"><h2>အလုပ်စာအုပ်မှ စစ်တမ်းအသစ် ဖန်တီးရန်</h2><p>သင့်လက်ရှိ DEDC မေးခွန်းများကို အလုပ်ခွင်ထဲ ယူဆောင်လာပြီး မူကြမ်း မဖန်တီးမီ ဖွဲ့စည်းပုံကို စစ်ဆေးပါ။</p><ul class="import-notes"><li>မူရင်းစာသားကို မပြောင်းဘဲ သိမ်းထားသည်</li><li>မူရင်းအဖြေများကို သီးခြား သိမ်းဆည်းထားသည်</li><li>မည်သည့်အရာကိုမျှ အလိုအလျောက် မထုတ်ဝေပါ</li></ul></div><form id="upload-form"><div class="import-drop" id="workbook-drop"><svg class="import-upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/></svg><h2>သင့်အလုပ်စာအုပ်ကို ဤနေရာသို့ ဆွဲချပါ</h2><p id="workbook-help">DEDC ကော်လံခြောက်ခု ပုံစံ · .xlsx ဖိုင် ၁ ခု၊ ၁၀ MB အထိ</p><input type="file" id="workbook-file" name="file" accept=".xlsx" aria-label="Excel အလုပ်စာအုပ်" aria-describedby="workbook-help" hidden><button class="button" type="button" id="choose-workbook">အလုပ်စာအုပ် ရွေးရန်</button><div class="import-file" id="workbook-selection" hidden><div><strong id="workbook-name"></strong><span id="workbook-size"></span></div><button class="button small" type="button" id="remove-workbook" aria-label="ရွေးထားသော အလုပ်စာအုပ်ကို ဖယ်ရှားရန်">ဖယ်ရှားရန်</button></div><p class="import-status" id="workbook-status" role="status" aria-live="polite"></p></div><button class="button primary" id="read-workbook" type="submit" disabled>အလုပ်စာအုပ် ဖတ်ရန်</button></form></div><div id="import-preview"></div></section>`,
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
    if (files.length !== 1) error = "တစ်ကြိမ်လျှင် အလုပ်စာအုပ် တစ်ခု ရွေးပါ။";
    else if (!/\.xlsx$/i.test(candidate.name)) error = "Excel အလုပ်စာအုပ် (.xlsx) ရွေးပါ။";
    else if (candidate.size > 10 * 1024 * 1024) error = "အလုပ်စာအုပ်သည် ၁၀ MB ကျော်နေသည်။ ပိုသေးသော ဖိုင် ရွေးပါ။";
    else if (!candidate.size) error = "ဤဖိုင် ဗလာဖြစ်နေသည်။ အကြောင်းအရာ ပါသော အလုပ်စာအုပ် ရွေးပါ။";
    status.textContent = error;
    drop.classList.toggle("has-error", Boolean(error));
    if (error) return;
    selectedFile = candidate;
    selection.hidden = false;
    document.querySelector("#workbook-name").textContent = candidate.name;
    document.querySelector("#workbook-size").textContent = candidate.size < 1024 * 1024
      ? `${Math.max(1, Math.ceil(candidate.size / 1024))} KB · ဖတ်ရန် အသင့်`
      : `${(candidate.size / (1024 * 1024)).toFixed(1)} MB · ဖတ်ရန် အသင့်`;
    choose.textContent = "အလုပ်စာအုပ် ပြောင်းရန်";
    read.disabled = reading;
    preview = null;
    document.querySelector("#import-preview").replaceChildren();
    status.textContent = "အလုပ်စာအုပ် ရွေးပြီးပါပြီ။ စစ်ဆေးရန် 'အလုပ်စာအုပ် ဖတ်ရန်' ကို နှိပ်ပါ။";
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
    choose.textContent = "အလုပ်စာအုပ် ရွေးရန်";
    status.textContent = "အလုပ်စာအုပ် ဖယ်ရှားပြီးပါပြီ။";
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
    target.innerHTML = `<hr style="border:0;border-top:1px solid var(--border);margin:28px 0"><label>စာရွက်<select id="worksheet">${preview.sheets.map((s, i) => `<option value="${i}" ${i === index ? "selected" : ""}>${e(s.worksheet)}</option>`).join("")}</select></label>${
      sheet.error
        ? `<p class="notice error">${e(sheet.error)}</p>`
        : `<div class="source-summary" style="margin-top:20px"><div><strong>${sheet.question_rows}</strong><span>မူရင်း မေးခွန်းတန်းများ</span></div><div><strong>${sheet.definition.sections.length}</strong><span>ကဏ္ဍများ</span></div><div><strong>${sheet.field_count}</strong><span>ပြင်ဆင်နိုင်သော အဖြေအကွက်များ</span></div><div><strong>${sheet.rows.length}</strong><span>သမိုင်းဝင် အဖြေတန်းများ</span></div></div><div class="notice">${sheet.warnings.map((w) => `<p>${e(w)}</p>`).join("")}</div><h3>မေးခွန်းနှင့် အဖြေ စစ်ဆေးမှု</h3>${table(
            [
              "#",
              "မူရင်း မေးခွန်း",
              "ရှိ / မရှိ",
              "မှတ်တမ်းတင်ထားသော အရေအတွက် / အသေးစိတ်",
            ],
            sheet.rows.map(
              (r) =>
                `<tr><td>${e(r.number)}</td><td class="title">${e(r.question)}<small>${e(r.source_cell)}</small></td><td>${e(r.present_text || r.absent_text || "—")}</td><td class="source-text">${e(r.quantity_text)}${r.details_text ? "<br>" + e(r.details_text) : ""}</td></tr>`,
            ),
          )}<details style="margin-top:24px"><summary>ရှာဖွေတွေ့ရှိထားသော စစ်တမ်းဖွဲ့စည်းပုံကို စစ်ဆေးပါ သို့မဟုတ် ပြင်ဆင်ပါ</summary><p class="editor-meta">မသိမ်းဆည်းမီ အညွှန်းများ၊ အမျိုးအစားများ၊ မဖြစ်မနေ အမှတ်အသားများနှင့် ရွေးချယ်စရာများကို ပြင်နိုင်ပါသည်။ မှတ်တမ်းတင်ထားသော မူရင်းအဖြေများ မပြောင်းလဲပါ။</p><label>မူကြမ်း ဖွဲ့စည်းပုံ (JSON)<textarea id="import-definition" class="code-input">${e(JSON.stringify(sheet.definition, null, 2))}</textarea></label></details><div class="actions" style="margin-top:24px"><button type="button" class="button primary" id="confirm-import">အတည်ပြုပြီး မူကြမ်းဖန်တီးရန်</button><p class="editor-meta">မည်သည့်အရာကိုမျှ အလိုအလျောက် မထုတ်ဝေပါ။</p></div>`
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
    `${tabs}<section class="panel"><div class="panel-head"><div><h2>မူရင်း အလုပ်စာအုပ် အဖြေများ</h2><p>အသစ် စုဆောင်းထားသော တင်သွင်းချက်များနှင့် သီးခြား သိမ်းဆည်းထားသော မူရင်းအဖြေများ။</p></div><div class="actions"><a class="button small" href="/api/admin/source-answers/export/csv?${e(params)}">CSV ဒေါင်းလုဒ်</a><a class="button small" href="/api/admin/source-answers/export/xlsx?${e(params)}">Excel ဒေါင်းလုဒ်</a><a class="button small" href="/api/admin/source-answers/export/pdf?${e(params)}">PDF ဒေါင်းလုဒ်</a></div></div><form class="filters" data-filter-form><input type="hidden" name="tab" value="answers"><input type="search" name="search" aria-label="အလုပ်စာအုပ် မေးခွန်းများ ရှာဖွေရန်" placeholder="မူရင်းမေးခွန်းများ ရှာဖွေရန်…" value="${e(params.get("search") || "")}"><select name="import_id" aria-label="စာရွက်"><option value="">စာရွက်အားလုံး</option>${data.imports.map((i) => `<option value="${i.id}" ${params.get("import_id") == i.id ? "selected" : ""}>${e(i.worksheet)}</option>`).join("")}</select><button class="button small" type="submit">စစ်ထုတ်ရန်</button></form>${
      data.items.length
        ? table(
            [
              "ကာလ / #",
              "မူရင်း မေးခွန်း",
              "ရှိသည်",
              "မရှိပါ",
              "မှတ်တမ်းတင်ထားသော အရေအတွက်",
              "အသေးစိတ်",
            ],
            data.items.map(
              (r) =>
                `<tr><td>${e(r.worksheet)}<small>မေးခွန်း ${e(r.number)} · ${e(r.source_cell)}</small></td><td class="title source-text">${e(r.question)}</td><td>${e(r.present || "—")}</td><td>${e(r.absent || "—")}</td><td class="source-text">${e(r.quantity || "—")}</td><td class="source-text">${e(r.details || "—")}</td></tr>`,
            ),
          )
        : empty(
            "မူရင်းအဖြေ မရှိပါ",
            "မေးခွန်းများနှင့် မူရင်းအဖြေအကွက်များကို သိမ်းဆည်းထားရန် အလုပ်စာအုပ်တစ်ခု တင်သွင်းပါ။",
            button("အလုပ်စာအုပ် တင်သွင်းရန်", "/dashboard/data"),
          )
    }${pagination(data.total)}</section>`,
  );
  bindFilters(loadImport);
}
