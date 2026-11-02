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
export function conditionEditor(container, fields, initial) {
  const nested =
    initial &&
    (initial.all || initial.any)?.some((rule) => rule.all || rule.any);
  const rules = nested
    ? []
    : initial?.all || initial?.any || (initial ? [initial] : []);
  const original = initial ? JSON.stringify(initial, null, 2) : "";
  container.innerHTML = `<h3>Show when</h3><p class="editor-meta">Without conditions this field is always visible.</p><label>Combine conditions<select data-condition-combine><option value="all">All conditions match (AND)</option><option value="any" ${initial?.any ? "selected" : ""}>Any condition matches (OR)</option></select></label><div data-condition-rows class="field-stack"></div><button type="button" class="button small" data-add-condition>＋ Add condition</button><details><summary>Advanced nested conditions</summary><label>Condition tree (JSON)<textarea data-condition-json class="code-input">${e(original)}</textarea></label></details>`;
  const rows = container.querySelector("[data-condition-rows]");
  const add = (rule) => {
    const row = document.createElement("div");
    row.className = "notice field-stack";
    row.innerHTML = `<label>Question<select data-condition-key>${fields.map((q) => `<option value="${e(q.key)}" ${rule?.question === q.key ? "selected" : ""}>${e(q.title.slice(0, 70))} (${e(q.key)})</option>`).join("")}</select></label><div class="form-grid"><label>Comparison<select data-condition-operator>${operators.map((op) => `<option value="${op}" ${rule?.operator === op ? "selected" : ""}>${op.replaceAll("_", " ")}</option>`).join("")}</select></label><label>Answer value<input data-condition-value value="${e(rule?.value === undefined ? "" : typeof rule.value === "string" ? rule.value : JSON.stringify(rule.value))}" placeholder="Text, a number, true or false"></label></div><button class="button small danger" type="button" data-remove-condition>Remove condition</button>`;
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
