import { escape as e } from "./ui.js";
const operators = [
  "equals",
  "not_equals",
  "greater_than",
  "less_than",
  "contains",
  "is_empty",
  "is_not_empty",
];
const operatorLabels = {
  equals: "တူညီသည်",
  not_equals: "မတူညီပါ",
  greater_than: "ပိုကြီးသည်",
  less_than: "ပိုငယ်သည်",
  contains: "ပါဝင်သည်",
  is_empty: "အဖြေ မရှိ",
  is_not_empty: "အဖြေ ရှိသည်",
};
export function conditionEditor(container, fields, initial) {
  const nested =
    initial &&
    (initial.all || initial.any)?.some((rule) => rule.all || rule.any);
  const rules = nested
    ? []
    : initial?.all || initial?.any || (initial ? [initial] : []);
  const original = initial ? JSON.stringify(initial, null, 2) : "";
  container.innerHTML = `<h3>ဘယ်အချိန် ပြမလဲ</h3><p class="editor-meta">အခြေအနေ မသတ်မှတ်ပါက ဤမေးခွန်းကို အမြဲ ပြပါမည်။</p><label>အခြေအနေ ပေါင်းစပ်ပုံ<select data-condition-combine><option value="all">အားလုံး ကိုက်ညီမှ ပြမည် (AND)</option><option value="any" ${initial?.any ? "selected" : ""}>တစ်ခုခု ကိုက်ညီပါက ပြမည် (OR)</option></select></label><div data-condition-rows class="field-stack"></div><button type="button" class="button small" data-add-condition>＋ အခြေအနေ ထည့်ရန်</button><details><summary>အဆင့်မြင့် အခြေအနေ (JSON)</summary><label>အခြေအနေ ဖွဲ့စည်းပုံ<textarea data-condition-json class="code-input">${e(original)}</textarea></label></details>`;
  const rows = container.querySelector("[data-condition-rows]");
  const add = (rule) => {
    const row = document.createElement("div");
    row.className = "notice field-stack";
    row.innerHTML = `<label>မေးခွန်း<select data-condition-key>${fields.map((q) => `<option value="${e(q.key)}" ${rule?.question === q.key ? "selected" : ""}>${e(q.title.slice(0, 70))} (${e(q.key)})</option>`).join("")}</select></label><div class="form-grid"><label>နှိုင်းယှဉ်ပုံ<select data-condition-operator>${operators.map((op) => `<option value="${op}" ${rule?.operator === op ? "selected" : ""}>${operatorLabels[op]}</option>`).join("")}</select></label><label>နှိုင်းယှဉ်မည့် တန်ဖိုး<input data-condition-value value="${e(rule?.value === undefined ? "" : typeof rule.value === "string" ? rule.value : JSON.stringify(rule.value))}" placeholder="စာသား၊ ကိန်းဂဏန်း၊ true သို့မဟုတ် false"></label></div><button class="button small danger" type="button" data-remove-condition>ဖယ်ရှားရန်</button>`;
    row.querySelector("[data-remove-condition]").onclick = () => row.remove();
    rows.append(row);
  };
  rules.forEach(add);
  container.querySelector("[data-add-condition]").onclick = () => add();
  return () => {
    const raw = container.querySelector("[data-condition-json]").value;
    if (raw !== original) return raw ? JSON.parse(raw) : null;
    if (nested && !rows.children.length) return initial;
    const conditions = [...rows.children].map((row) => {
      const text = row.querySelector("[data-condition-value]").value;
      let value = text;
      try {
        value = JSON.parse(text);
      } catch {}
      return {
        question: row.querySelector("[data-condition-key]").value,
        operator: row.querySelector("[data-condition-operator]").value,
        value,
      };
    });
    return conditions.length
      ? {
          [container.querySelector("[data-condition-combine]").value]:
            conditions,
        }
      : null;
  };
}
