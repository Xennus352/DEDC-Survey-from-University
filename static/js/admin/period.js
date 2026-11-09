import { escape as e } from "./ui.js";

export const burmeseNumber = (value) => String(value).replace(/\d/g, (digit) => "၀၁၂၃၄၅၆၇၈၉"[digit]);
const months = ["ဇန်နဝါရီ", "ဖေဖော်ဝါရီ", "မတ်", "ဧပြီ", "မေ", "ဇွန်", "ဇူလိုင်", "ဩဂုတ်", "စက်တင်ဘာ", "အောက်တိုဘာ", "နိုဝင်ဘာ", "ဒီဇင်ဘာ"];

export function reportingYears(version) {
  const years = [version?.reporting_start, version?.reporting_end].filter(Boolean).map(value => value.slice(0, 4));
  return [...new Set(years)].map(burmeseNumber).join(" – ") || "မသတ်မှတ်ရသေးပါ";
}

export function monthYearFields(id, title, value, editable) {
  const [year = "", month = ""] = (value || "").split("-");
  return `<fieldset class="reporting-period"><legend>${e(title)}</legend><div class="month-year-fields"><label for="${id}-month">လ<select id="${id}-month" ${editable ? "" : "disabled"}><option value="">လ ရွေးရန်</option>${months.map((name, index) => `<option value="${String(index + 1).padStart(2, "0")}" ${Number(month) === index + 1 ? "selected" : ""}>${name}</option>`).join("")}</select></label><label for="${id}-year">နှစ်<input id="${id}-year" inputmode="numeric" maxlength="4" placeholder="၂၀၂၆" value="${e(burmeseNumber(year))}" ${editable ? "" : "disabled"}></label></div></fieldset>`;
}

export function readMonthYear(id, end = false) {
  const month = document.getElementById(id + "-month").value;
  const rawYear = document.getElementById(id + "-year").value.trim();
  const year = rawYear.replace(/[၀-၉]/g, digit => "၀၁၂၃၄၅၆၇၈၉".indexOf(digit));
  if (!month && !year) return null;
  if (!month || !/^[0-9]{4}$/.test(year) || Number(year) < 1)
    throw new Error("အစီရင်ခံကာလအတွက် လနှင့် ဂဏန်းလေးလုံးပါ နှစ်ကို ထည့်ပါ။");
  // Gregorian leap-year rules, including February and century boundaries.
  const y = Number(year);
  const days = [31, y % 4 === 0 && (y % 100 !== 0 || y % 400 === 0) ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return `${year}-${month}-${end ? days[Number(month) - 1] : "01"}`;
}
