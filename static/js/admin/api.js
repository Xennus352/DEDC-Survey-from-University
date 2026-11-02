export async function api(path, options = {}) {
  const headers = { ...options.headers };
  if (options.body && !(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(options.body);
  }
  if (options.method && options.method !== "GET")
    headers["X-CSRF-Token"] = document.querySelector(
      'meta[name="csrf-token"]',
    ).content;
  const response = await fetch("/api/admin" + path, {
    credentials: "same-origin",
    cache: "no-store",
    ...options,
    headers,
  });
  if (response.status === 401) {
    document.body.hidden = true;
    location.replace("/portal");
    throw new Error("Your session expired.");
  }
  if (!response.ok) {
    let data;
    try {
      data = await response.json();
    } catch {
      data = { detail: "The server could not complete this request." };
    }
    const detail = data.detail;
    throw new Error(
      typeof detail === "string"
        ? detail
        : detail?.message || JSON.stringify(detail),
    );
  }
  return response.status === 204 ? null : response.json();
}
