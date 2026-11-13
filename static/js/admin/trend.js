const svgNS = "http://www.w3.org/2000/svg";

function svgNode(tag, attributes = {}) {
  const node = document.createElementNS(svgNS, tag);
  for (const [name, value] of Object.entries(attributes)) node.setAttribute(name, String(value));
  return node;
}

function textElement(tag, className, value) {
  const element = document.createElement(tag);
  element.className = className;
  element.textContent = value;
  return element;
}

export function renderYearlyBars(container, years, series, audience) {
  const requestedTypes = audience === "University" ? ["CU", "PU", "TU"] : [];
  const ranked = [...series].sort((a, b) => {
    const aTotal = a.values.reduce((sum, count) => sum + count, 0);
    const bTotal = b.values.reduce((sum, count) => sum + count, 0);
    const aPriority = requestedTypes.indexOf(a.label);
    const bPriority = requestedTypes.indexOf(b.label);
    return bTotal - aTotal ||
      (aPriority < 0 ? requestedTypes.length : aPriority) -
      (bPriority < 0 ? requestedTypes.length : bPriority) ||
      a.label.localeCompare(b.label);
  });
  const active = ranked.filter((item) => item.values.some((count) => count > 0));
  const maximum = Math.max(1, ...active.flatMap((item) => item.values));
  const axisLabel = textElement("p", "year-chart-axis-label", "Y · ဖြေဆိုပြီး မေးခွန်းအရေအတွက်");
  const viewport = document.createElement("div");
  viewport.className = "year-chart-viewport";
  const groupWidth = Math.max(62, active.length * 20 + 2);
  const width = Math.max(280, 36 + years.length * groupWidth + 8);
  const groupStart = 36 + (width - 44 - years.length * groupWidth) / 2;
  const svg = svgNode("svg", {
    viewBox: "0 0 " + width + " 205",
    width,
    height: 205,
    role: "img",
    "aria-label": audience + " အဖွဲ့အစည်းများ၏ တင်သွင်းသည့် နှစ်အလိုက် ဖြေဆိုပြီး မေးခွန်းအရေအတွက်",
  });
  const title = svgNode("title");
  title.textContent = audience + " တင်သွင်းသည့် နှစ်အလိုက် ဖြေဆိုပြီး မေးခွန်းများ";
  svg.append(title);
  const ticks = maximum > 1 ? [0, Math.ceil(maximum / 2), maximum] : [0, maximum];
  for (const count of [...new Set(ticks)]) {
    const y = 164 - count / maximum * 132;
    svg.append(svgNode("line", {
      class: "year-chart-grid", x1: 32, x2: width - 8, y1: y, y2: y,
    }));
    const tick = svgNode("text", {
      class: "year-chart-tick", x: 26, y: y + 4, "text-anchor": "end",
    });
    tick.textContent = count.toLocaleString();
    svg.append(tick);
  }
  years.forEach((year, yearIndex) => {
    const center = groupStart + (yearIndex + .5) * groupWidth;
    const barWidth = 18;
    const gap = 2;
    const barsWidth = active.length * (barWidth + gap) - gap;
    active.forEach((item, seriesIndex) => {
      const count = item.values[yearIndex] || 0;
      const x = center - barsWidth / 2 + seriesIndex * (barWidth + gap);
      const height = count / maximum * 128;
      if (count > 0) {
        svg.append(svgNode("rect", {
          x, y: 164 - height, width: barWidth, height, rx: 2,
          class: "year-chart-bar year-chart-tone--" + seriesIndex % 8,
        }));
      }
      if (count > 0) {
        const value = svgNode("text", {
          class: "year-chart-value", x: x + barWidth / 2,
          y: Math.max(16, 158 - height), "text-anchor": "middle",
        });
        value.textContent = count.toLocaleString();
        svg.append(value);
      }
    });
    if (active.length && !active.some((item) => item.values[yearIndex])) {
      const zero = svgNode("text", {
        class: "year-chart-value", x: center, y: 157, "text-anchor": "middle",
      });
      zero.textContent = "0";
      svg.append(zero);
    }
    const yearLabel = svgNode("text", {
      class: "year-chart-year", x: center, y: 190, "text-anchor": "middle",
    });
    yearLabel.textContent = String(year);
    svg.append(yearLabel);
  });
  if (!active.length) {
    const empty = svgNode("text", {
      class: "year-chart-empty", x: width / 2, y: 91, "text-anchor": "middle",
    });
    empty.textContent = "ဖြေဆိုပြီး မေးခွန်း မရှိသေးပါ";
    svg.append(empty);
  }
  viewport.append(svg);

  const xLabel = textElement("p", "year-chart-x-label", "X · တင်သွင်းသည့် နှစ်");
  const legend = document.createElement("div");
  legend.className = "year-chart-legend";
  legend.setAttribute("aria-label", audience + " အဖွဲ့အစည်းများနှင့် ဖြေဆိုမှု စုစုပေါင်း");
  const legendTitle = textElement(
    "strong", "year-chart-legend__title",
    audience === "University" ? "တက္ကသိုလ် အမျိုးအစားများ" : "ဝန်ကြီးဌာနများ",
  );
  const legendList = document.createElement("ul");
  for (const item of ranked) {
    const total = item.values.reduce((sum, count) => sum + count, 0);
    const row = document.createElement("li");
    const swatch = document.createElement("i");
    swatch.className = "year-chart-swatch " + (total
      ? "year-chart-tone--" + active.indexOf(item) % 8
      : "year-chart-swatch--empty");
    swatch.setAttribute("aria-hidden", "true");
    const name = textElement("span", "year-chart-legend__name", item.label);
    name.title = item.label;
    row.append(swatch, name, textElement("strong", "year-chart-legend__value", total.toLocaleString()));
    legendList.append(row);
  }
  legend.append(legendTitle, legendList);
  container.replaceChildren(axisLabel, viewport, xLabel, legend);
}
