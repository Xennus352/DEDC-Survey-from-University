const svgNS = "http://www.w3.org/2000/svg";

function svgNode(tag, attributes = {}) {
  const node = document.createElementNS(svgNS, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}

function buckets(trend, period) {
  if (period === "daily") return trend.map((item) => ({ label: item.date, count: item.count }));
  const groups = new Map();
  trend.forEach((item, index) => {
    const key = period === "weekly" ? String(Math.floor(index / 7)) : item.date.slice(0, 7);
    const group = groups.get(key) || { label: item.date, end: item.date, count: 0 };
    group.count += item.count;
    group.end = item.date;
    groups.set(key, group);
  });
  return [...groups.values()].map((group) => ({
    label: period === "weekly" ? group.label + " – " + group.end : group.label.slice(0, 7),
    count: group.count,
  }));
}

export function renderOverviewTrend(container, trend, period) {
  const points = buckets(trend, period);
  const maximum = Math.max(1, ...points.map((point) => point.count));
  const x = (index) => points.length === 1 ? 300 : 24 + index * 552 / (points.length - 1);
  const y = (count) => 156 - count / maximum * 126;
  const svg = svgNode("svg", {
    viewBox: "0 0 600 184",
    preserveAspectRatio: "none",
    role: "group",
    "aria-label": "တင်သွင်းမှု အချိန်လိုက် ပြောင်းလဲမှု",
  });
  for (let index = 0; index < 4; index += 1) {
    svg.append(svgNode("line", { class: "overview-trend__grid", x1: 24, x2: 576, y1: 30 + index * 42, y2: 30 + index * 42 }));
  }
  const readout = document.createElement("p");
  readout.className = "overview-trend__readout";
  readout.setAttribute("aria-live", "polite");
  readout.textContent = "တင်သွင်းမှုရှိသော အချက်တစ်ခုကို ရွေးပါ";
  const selectable = [];
  const selectPoint = (circle, point) => {
    selectable.forEach((item) => {
      item.classList.toggle("is-selected", item === circle);
      item.setAttribute("aria-pressed", String(item === circle));
    });
    readout.textContent = point.label + " · " + point.count.toLocaleString() + " တင်သွင်းမှု";
  };
  if (points.some((point) => point.count > 0)) {
    const path = points.map((point, index) => (index ? "L" : "M") + x(index) + " " + y(point.count)).join(" ");
    svg.append(svgNode("path", { class: "overview-trend__area", d: path + " L" + x(points.length - 1) + " 156 L" + x(0) + " 156 Z" }));
    svg.append(svgNode("path", { class: "overview-trend__line", d: path }));
    points.forEach((point, index) => {
      if (point.count === 0) return;
      const circle = svgNode("circle", {
        class: "overview-trend__point",
        cx: x(index), cy: y(point.count), r: 5, tabindex: 0,
        role: "button", "aria-pressed": "false",
        "aria-label": point.label + ": " + point.count + " တင်သွင်းမှု",
      });
      const title = svgNode("title");
      title.textContent = point.label + ": " + point.count + " တင်သွင်းမှု";
      circle.append(title);
      circle.addEventListener("click", () => selectPoint(circle, point));
      circle.addEventListener("focus", () => selectPoint(circle, point));
      circle.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          selectPoint(circle, point);
        }
      });
      selectable.push(circle);
      svg.append(circle);
    });
    const lastIndex = points.findLastIndex((point) => point.count > 0);
    selectPoint(selectable.at(-1), points[lastIndex]);
  } else {
    readout.textContent = "တင်သွင်းမှု မရှိသေးပါ";
  }
  const axis = document.createElement("div");
  axis.className = "chart-axis";
  const first = document.createElement("span");
  const last = document.createElement("span");
  first.textContent = points[0]?.label || "—";
  last.textContent = points.at(-1)?.label || "—";
  axis.append(first, last);
  container.replaceChildren(svg, axis, readout);
}
