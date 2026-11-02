import { escape as e, toast } from "./ui.js";

export function condition(rule, answers) {
  if (!rule) return true;
  if (rule.all) return rule.all.every((r) => condition(r, answers));
  if (rule.any) return rule.any.some((r) => condition(r, answers));
  const value = answers[rule.question],
    expected = rule.value,
    empty =
      value === undefined ||
      value === null ||
      value === "" ||
      (Array.isArray(value) && !value.length);
  switch (rule.operator) {
    case "equals":
      return value === expected;
    case "not_equals":
      return value !== expected;
    case "greater_than":
      return !empty && Number(value) > Number(expected);
    case "less_than":
      return !empty && Number(value) < Number(expected);
    case "contains":
      return (
        (typeof value === "string" || Array.isArray(value)) &&
        value.includes(expected)
      );
    case "is_empty":
      return empty;
    case "is_not_empty":
      return !empty;
    default:
      return false;
  }
}
export function renderSurvey(
  container,
  version,
  {
    language = "my",
    onSubmit,
    uploadFile,
    submitLabel = "Validate preview",
  } = {},
) {
  const fieldHtml = (q) => {
    const fullTitle = (language === "en" ? q.title_en : q.title_my) || q.title,
      title = q.config?.source_component
        ? fullTitle.split(" — ").at(-1)
        : fullTitle,
      required = q.required
        ? '<span class="required" aria-label="required">*</span>'
        : "",
      id = "answer-" + q.key,
      label = `${e(title)} ${required}`,
      config = q.config || {},
      attrs = `${q.required ? "required" : ""} placeholder="${e(q.placeholder)}" ${config.min !== undefined ? `min="${e(config.min)}"` : ""} ${config.max !== undefined ? `max="${e(config.max)}"` : ""} ${config.min_length !== undefined ? `minlength="${e(config.min_length)}"` : ""} ${config.max_length !== undefined ? `maxlength="${e(config.max_length)}"` : ""}`;
    let control;
    if (q.kind === "information") control = `<p>${e(title)}</p>`;
    else if (
      ["multiple_choice", "checkboxes", "radio", "single_choice"].includes(
        q.kind,
      )
    ) {
      const multiple = ["multiple_choice", "checkboxes"].includes(q.kind);
      control = `<fieldset><legend>${label}</legend>${q.options.map((o) => `<label class="check-label"><input type="${multiple ? "checkbox" : "radio"}" name="${q.key}" value="${e(o.value)}" ${!multiple && q.required ? "required" : ""}>${e(o.label)}</label>`).join("")}</fieldset>`;
    } else if (q.kind === "yes_no")
      control = `<label for="${id}">${label}</label><select id="${id}" name="${q.key}" ${attrs}><option value="">Select an answer</option><option value="true">ရှိ / Yes</option><option value="false">မရှိ / No</option></select>`;
    else if (q.kind === "dropdown")
      control = `<label for="${id}">${label}</label><select id="${id}" name="${q.key}" ${attrs}><option value="">Select an option</option>${q.options.map((o) => `<option value="${e(o.value)}">${e(o.label)}</option>`).join("")}</select>`;
    else if (q.kind === "calculated")
      control = `<label for="${id}">${label}</label><input id="${id}" name="${q.key}" readonly aria-readonly="true" placeholder="Calculated from your answers">`;
    else if (q.kind === "repeating_group")
      control = `<fieldset><legend>${label}</legend><div data-repeating-rows="${q.key}"></div><button type="button" class="button small" data-add-row="${q.key}">＋ Add row</button></fieldset>`;
    else if (["file", "image"].includes(q.kind))
      control = `<label for="${id}">${label}</label><input id="${id}" type="file" name="${q.key}" ${q.kind === "image" ? 'accept="image/png,image/jpeg,image/webp"' : ""} ${q.required ? "required" : ""}><p class="help" data-upload-status="${q.key}">Maximum 5 MB.</p>`;
    else if (q.kind === "long_text")
      control = `<label for="${id}">${label}</label><textarea id="${id}" name="${q.key}" ${attrs}></textarea>`;
    else if (q.kind === "location")
      control = `<fieldset><legend>${label}</legend><div class="form-grid"><label>Latitude<input name="${q.key}_latitude" type="number" step="any" min="-90" max="90" ${q.required ? "required" : ""}></label><label>Longitude<input name="${q.key}_longitude" type="number" step="any" min="-180" max="180" ${q.required ? "required" : ""}></label></div><button type="button" class="button small" data-location="${q.key}">Use current location</button></fieldset>`;
    else {
      const type =
        {
          number: "number",
          decimal: "number",
          date: "date",
          time: "time",
          datetime: "datetime-local",
        }[q.kind] || "text";
      control = `<label for="${id}">${label}</label><input id="${id}" name="${q.key}" type="${type}" ${attrs} ${q.kind === "decimal" ? 'step="any"' : ""}>`;
    }
    return `<div class="survey-field" data-field="${q.key}">${control}${q.help_text ? `<p class="help">${e(q.help_text)}</p>` : ""}<p class="required" data-error="${q.key}" hidden></p></div>`;
  };
  container.innerHTML = `<form id="dynamic-survey"><div class="panel panel-body survey-title"><h2>${e(version.title)}</h2><p class="editor-meta source-text">${e(version.description)}</p></div><div class="notice error" data-survey-error role="alert" tabindex="-1" hidden></div><section class="panel panel-body" data-period-step><h2>Choose the reporting period</h2><p class="editor-meta">Enter the From and To dates before filling the questions. This period is included in your Excel export.</p><div class="form-grid"><label>From date<input type="date" name="__reporting_start" value="${e(version.reporting_start || "")}" required></label><label>To date<input type="date" name="__reporting_end" value="${e(version.reporting_end || "")}" required></label></div><div class="actions" style="margin-top:24px"><button class="button primary" type="button" data-start-survey>Start survey →</button></div></section><div data-question-pages hidden><div class="survey-progress"><span data-survey-progress></span><button type="button" class="button small" data-edit-period>Edit reporting period</button></div>${version.sections
    .map((section, index) => {
      const shown = new Set();
      return `<section class="panel section-block" data-section="${index}"><div class="panel-head"><div><h2 tabindex="-1">${e(section.title)}</h2>${section.description ? `<p>${e(section.description)}</p>` : ""}</div></div><div class="panel-body">${section.questions
        .filter((q) => q.enabled)
        .map((q) => {
          const cell = q.config?.source_cell;
          let heading = "";
          if (cell && !shown.has(cell)) {
            shown.add(cell);
            heading = `<h3 class="source-question-heading">${e(q.config.source_number)}. ${e(q.title.split(" — ").slice(0, -1).join(" — "))}</h3>`;
          }
          return heading + fieldHtml(q);
        })
        .join("")}</div></section>`;
    })
    .join(
      "",
    )}<div class="survey-navigation"><button class="button" type="button" data-survey-back>Back</button><button class="button primary" type="button" data-survey-next>Next section →</button><button class="button primary" type="submit">${e(submitLabel)}</button></div><p class="editor-meta">${submitLabel === "Validate preview" ? "Preview validation does not save a submission." : "Your answers are stored with this published form version."}</p></div></form>`;
  let started = false,
    activeSection = 0;
  const form = container.querySelector("form"),
    fields = version.sections.flatMap((s) => s.questions);
  const uploads = {},
    pending = new Set();
  function readValue(q, key, data) {
    if (["multiple_choice", "checkboxes"].includes(q.kind))
      return data.getAll(key);
    if (q.kind === "location") {
      const lat = data.get(key + "_latitude"),
        lon = data.get(key + "_longitude");
      return lat !== null && lat !== "" && lon !== null && lon !== ""
        ? { latitude: Number(lat), longitude: Number(lon) }
        : undefined;
    }
    if (["file", "image"].includes(q.kind))
      return uploads[key] ? { file_id: uploads[key].file_id } : undefined;
    const raw = data.get(key);
    return raw !== null && raw !== ""
      ? q.kind === "yes_no"
        ? raw === "true"
        : ["number", "decimal"].includes(q.kind)
          ? Number(raw)
          : raw
      : undefined;
  }
  function calculated(q, values) {
    const f = q.config.formula,
      raw = f.questions.map((key) => values[key]);
    if (raw.some((v) => v === undefined || v === null || v === ""))
      return undefined;
    const v = raw.map(Number);
    if (v.some((n) => !Number.isFinite(n))) return undefined;
    const result =
      f.operation === "sum"
        ? v.reduce((a, b) => a + b, 0)
        : f.operation === "difference"
          ? v[0] - v.slice(1).reduce((a, b) => a + b, 0)
          : f.operation === "average"
            ? v.reduce((a, b) => a + b, 0) / v.length
            : v.reduce((a, b) => a * b, 1);
    return Number.isFinite(result) ? result : undefined;
  }
  function answers() {
    const disabled = [...form.elements].filter((input) => input.disabled);
    disabled.forEach((input) => (input.disabled = false));
    const data = new FormData(form),
      values = {};
    disabled.forEach((input) => (input.disabled = true));
    for (const q of fields) {
      if (q.kind === "repeating_group") {
        values[q.key] = [
          ...form.querySelectorAll(
            `[data-repeating-rows="${q.key}"] > [data-repeat-row]`,
          ),
        ].map((row) =>
          Object.fromEntries(
            q.config.fields
              .map((child) => [
                child.key,
                readValue(
                  child,
                  q.key + "_" + row.dataset.repeatRow + "_" + child.key,
                  data,
                ),
              ])
              .filter(([, value]) => value !== undefined),
          ),
        );
      } else if (q.kind !== "calculated") {
        const value = readValue(q, q.key, data);
        if (value !== undefined) values[q.key] = value;
      }
    }
    for (let n = 0; n <= fields.length; n++)
      for (const q of fields)
        if (q.kind === "calculated") values[q.key] = calculated(q, values);
    return values;
  }
  function update() {
    let values = answers();
    for (let n = 0; n <= fields.length; n++) {
      let changed = false;
      version.sections.forEach((s, index) => {
        const sectionNode = form.querySelector(`[data-section="${index}"]`),
          showSection = s.enabled && condition(s.conditions, values);
        sectionNode.hidden = !showSection;
        for (const q of s.questions) {
          const node = form.querySelector(`[data-field="${q.key}"]`);
          if (!node) continue;
          const show =
            showSection && q.enabled && condition(q.conditions, values);
          node.hidden = !show;
          node
            .querySelectorAll("input,select,textarea")
            .forEach((input) => (input.disabled = !show || !started));
          if (!show && q.key in values) {
            delete values[q.key];
            changed = true;
          }
        }
      });
      if (!changed) break;
      for (const q of fields)
        if (q.kind === "calculated" && q.key in values)
          values[q.key] = calculated(q, values);
    }
    const available = version.sections
      .map((section, index) =>
        section.enabled && condition(section.conditions, values) ? index : null,
      )
      .filter((index) => index !== null);
    if (!available.includes(activeSection)) activeSection = available[0] ?? 0;
    version.sections.forEach((section, index) => {
      const node = form.querySelector(`[data-section="${index}"]`);
      node.hidden = !available.includes(index) || index !== activeSection;
    });
    const current = Math.max(0, available.indexOf(activeSection));
    form.querySelector("[data-survey-progress]").textContent =
      `Section ${current + 1} of ${Math.max(1, available.length)} · ${form.elements.__reporting_start.value} → ${form.elements.__reporting_end.value}`;
    form.querySelector("[data-survey-next]").hidden =
      current >= available.length - 1;
    form.querySelector("button[type=submit]").hidden =
      current < available.length - 1;
    for (const q of fields)
      if (q.kind === "calculated") {
        const input = form.elements[q.key];
        if (input) input.value = values[q.key] ?? "";
      }
  }
  for (const q of fields) {
    if (
      q.config.default === undefined ||
      ["file", "image", "repeating_group", "calculated"].includes(q.kind)
    )
      continue;
    if (q.kind === "location" && q.config.default) {
      for (const part of ["latitude", "longitude"])
        if (form.elements[q.key + "_" + part])
          form.elements[q.key + "_" + part].value =
            q.config.default[part] ?? "";
    }
    const input = form.elements[q.key];
    if (input && typeof input.value === "string")
      input.value = String(q.config.default);
    if (
      ["radio", "single_choice", "multiple_choice", "checkboxes"].includes(
        q.kind,
      )
    )
      form
        .querySelectorAll(`[name="${q.key}"]`)
        .forEach(
          (element) =>
            (element.checked = Array.isArray(q.config.default)
              ? q.config.default.includes(element.value)
              : element.value === String(q.config.default)),
        );
  }
  form.querySelectorAll("[data-add-row]").forEach(
    (button) =>
      (button.onclick = () => {
        const q = fields.find((q) => q.key === button.dataset.addRow),
          rows = form.querySelector(`[data-repeating-rows="${q.key}"]`);
        if (rows.children.length >= 100)
          return toast("A repeating group supports at most 100 rows.");
        const id = crypto.randomUUID().slice(0, 8),
          row = document.createElement("div");
        row.dataset.repeatRow = id;
        row.className = "notice";
        row.innerHTML =
          q.config.fields
            .map((child) =>
              fieldHtml({ ...child, key: q.key + "_" + id + "_" + child.key }),
            )
            .join("") +
          '<button type="button" class="button small danger" data-remove-row>Remove row</button>';
        row.querySelector("[data-remove-row]").onclick = () => {
          row.remove();
          update();
        };
        rows.append(row);
        update();
      }),
  );
  form.addEventListener("change", async (event) => {
    const input = event.target;
    if (input.type !== "file") return;
    const file = input.files[0];
    delete uploads[input.name];
    if (!file) return;
    const status = form.querySelector(`[data-upload-status="${input.name}"]`);
    pending.add(input.name);
    status.textContent = "Uploading…";
    try {
      if (file.size > 5 * 1024 * 1024)
        throw new Error("Maximum upload size is 5 MB.");
      if (!uploadFile) throw new Error("Uploads are unavailable.");
      uploads[input.name] = await uploadFile(input.name, file);
      status.textContent = "Uploaded: " + uploads[input.name].filename;
    } catch (error) {
      input.value = "";
      status.textContent = error.message;
    } finally {
      pending.delete(input.name);
      update();
    }
  });
  function periodStep() {
    started = false;
    form.querySelector("[data-period-step]").hidden = false;
    form.querySelector("[data-question-pages]").hidden = true;
    update();
    form.elements.__reporting_start.focus();
  }
  form.querySelector("[data-start-survey]").onclick = () => {
    const from = form.elements.__reporting_start,
      to = form.elements.__reporting_end;
    to.setCustomValidity("");
    if (!from.reportValidity() || !to.reportValidity()) return;
    if (to.value < from.value) {
      to.setCustomValidity("To date must be on or after From date.");
      to.reportValidity();
      return;
    }
    started = true;
    form.querySelector("[data-period-step]").hidden = true;
    form.querySelector("[data-question-pages]").hidden = false;
    update();
    form.querySelector(`[data-section="${activeSection}"] h2`)?.focus();
  };
  form.querySelector("[data-edit-period]").onclick = periodStep;
  form.querySelector("[data-survey-next]").onclick = () => {
    const current = form.querySelector(`[data-section="${activeSection}"]`);
    for (const input of current.querySelectorAll("input,select,textarea"))
      if (!input.disabled && !input.reportValidity()) return;
    const values = answers(),
      available = version.sections
        .map((section, index) =>
          section.enabled && condition(section.conditions, values)
            ? index
            : null,
        )
        .filter((index) => index !== null);
    activeSection =
      available[available.indexOf(activeSection) + 1] ?? activeSection;
    update();
    form.querySelector(`[data-section="${activeSection}"] h2`)?.focus();
  };
  form.querySelector("[data-survey-back]").onclick = () => {
    const values = answers(),
      available = version.sections
        .map((section, index) =>
          section.enabled && condition(section.conditions, values)
            ? index
            : null,
        )
        .filter((index) => index !== null),
      index = available.indexOf(activeSection);
    if (index <= 0) return periodStep();
    activeSection = available[index - 1];
    update();
    form.querySelector(`[data-section="${activeSection}"] h2`)?.focus();
  };
  form.addEventListener("input", update);
  form.addEventListener("change", update);
  update();
  form.querySelectorAll("[data-location]").forEach(
    (button) =>
      (button.onclick = () => {
        if (!navigator.geolocation)
          return toast(
            "Location is unavailable in this browser. Enter coordinates manually.",
          );
        button.disabled = true;
        navigator.geolocation.getCurrentPosition(
          (position) => {
            form.elements[button.dataset.location + "_latitude"].value =
              position.coords.latitude;
            form.elements[button.dataset.location + "_longitude"].value =
              position.coords.longitude;
            button.disabled = false;
            update();
          },
          () => {
            button.disabled = false;
            toast(
              "Location permission was denied. Enter coordinates manually.",
            );
          },
        );
      }),
  );
  form.onsubmit = async (event) => {
    event.preventDefault();
    const button = event.submitter,
      error = form.querySelector("[data-survey-error]");
    error.hidden = true;
    button.disabled = true;
    try {
      if (pending.size) throw new Error("Wait for the file upload to finish.");
      if (!started) throw new Error("Choose a reporting period first.");
      await onSubmit(answers(), {
        reporting_start: form.elements.__reporting_start.value,
        reporting_end: form.elements.__reporting_end.value,
      });
    } catch (problem) {
      error.textContent = problem.message;
      error.hidden = false;
      error.focus();
    } finally {
      button.disabled = false;
    }
  };
}
