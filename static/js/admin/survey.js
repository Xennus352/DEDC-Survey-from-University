import { renderSurvey } from "./renderer.js";
import { escape as e, button, empty, toast } from "./ui.js";
const container = document.querySelector("#survey-content"),
  formId = document.body.dataset.formId;
async function request(path, body) {
  const response = await fetch(path, {
    credentials: "same-origin",
    cache: "no-store",
    method: body ? "POST" : "GET",
    headers: body
      ? {
          "Content-Type": "application/json",
          "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')
            .content,
        }
      : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (response.status === 401) {
    location.replace("/survey/login");
    throw new Error("Sign in again.");
  }
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.message || "Check your answers and try again.",
    );
  return data;
}
try {
  if (formId) {
    const version = await request("/api/forms/" + formId + "/schema");
    const started_at = new Date().toISOString();
    renderSurvey(container, version, {
      submitLabel: "Submit survey",
      uploadFile: async (key, file) => {
        const body = new FormData();
        body.set("key", key);
        body.set("file", file);
        const response = await fetch("/api/forms/" + formId + "/files", {
          method: "POST",
          credentials: "same-origin",
          headers: {
            "X-CSRF-Token": document.querySelector('meta[name="csrf-token"]')
              .content,
          },
          body,
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Upload failed.");
        return data;
      },
      onSubmit: async (answers, period) => {
        const saved = await request("/api/forms/" + formId + "/submissions", {
          answers,
          ...period,
          started_at,
        });
        container.innerHTML = `<section class="panel">${empty("Your response has been saved", `Submission #${saved.id} · Form version ${version.number}`, button("Back to surveys", "/survey"))}</section>`;
        toast("Survey submitted.");
      },
    });
  } else {
    const forms = await request("/api/forms");
    container.innerHTML = `<div class="page-heading"><div><h1>Your available surveys</h1><p class="editor-meta">Published surveys available for your account.</p></div></div>${forms.length ? forms.map((f) => `<section class="panel panel-body section-block"><h2>${e(f.title)}</h2><p class="editor-meta">${e(f.audience)}</p>${button("Open survey", "/survey/forms/" + f.id, true)}</section>`).join("") : `<section class="panel">${empty("No published surveys yet", "Your administrator will publish a survey when it is ready.")}</section>`}`;
  }
} catch (error) {
  container.innerHTML = `<p class="notice error" role="alert">${e(error.message)}</p>`;
}
