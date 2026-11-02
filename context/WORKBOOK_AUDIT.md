# Workbook Audit

Inspected every worksheet and populated cell in:
`/home/kazue/Downloads/Telegram Desktop/DEDC_Survey_Form_University_of_Computer_Studies_Taungoo_27875ea2.xlsx`.

`workbook-structure.json` records the source hash, exact original question labels, question numbers, cell references, style IDs, section ordering, merges and worksheet metadata. It intentionally excludes filled-in institutional answers. Reproduce with:

```bash
uv run python scripts/inspect_survey_workbook.py "/path/to/workbook.xlsx"
```

## Observed structure

| Worksheet | Used range | Numbered questions | Sections |
| --- | --- | --- | --- |
| University (2010-2015) | A1:F44 | 1–25 | 4 |
| University (2016-2020) | A1:F44 | 1–25 | 4 |
| University (2021-2025) | A1:F44 | 1–25 | 4 |
| University (2021-2026) | A1:F38 | 1–25 | 4 |

Rows 1–3 are merged survey/institution/period headings. Row 4 defines six columns: A `စဉ်` (number), B `လုပ်ငန်းစဉ်` (question/process), C `ရှိ` (present), D `မရှိ` (absent), E `အရေအတွက်` (count), F `အကြောင်းအရာ` (details). Full-width merged section headings occur at rows 5, 16, 19 and 29:

1. Human Capital: questions 1–10, rows 6–15.
2. Connectivity: questions 11–12, rows 17–18.
3. Integration of Digital Technology: questions 13–21, rows 20–28.
4. Digital Public Services: questions 22–25, rows 30–33.

The original headings and question labels are Burmese, with occasional English terms and English section names. There is no separate English question column. Question 1 and period headings vary between sheets. Sheet-local identifiers repeat across periods; do not treat question number alone as a globally unique key or automatically merge all four sheets.

## Answer semantics and uncertainty

C/D express yes/no-style answers, not independent question labels. E contains both numeric counts and compound/free-text values (degree-specific counts, arithmetic-looking text, subject ratios, names and explanatory notes). F contains supplemental details. Filled cells are existing example responses, not default values or choice lists. The workbook matches the live database's `hasItem`, `itemCount`, and `surveyDescription` concepts much more closely than the generic survey models.

Degree breakdowns and institutional lists suggest repeatable substructures, but the workbook does not define their schema. None of the four worksheets contains formal Excel tables, data-validation lists, or formulas. There are no machine-readable required flags, numeric bounds, conditional dependencies or calculation definitions. Font, alignment, fill, border and wrap style differences communicate presentation; they are insufficient proof of validation or branching rules.

## Import contract for implementation

- Detect this six-column layout and merged sections; retain source worksheet/cell, original wording, newlines and question order.
- Let administrators select worksheets/periods and review duplicate identifiers before creating draft forms.
- Model each numbered row as a question/group with optional presence, count and details fields; let administrators correct types before saving. Do not coerce every E cell to a number.
- Warn about missing English labels, ambiguous types, undefined required/validation rules, and inferred repeating structures. Do not invent translated question text or branching rules.
- Exclude filled-in answers from question configuration. Importing historical responses requires a separate explicit workflow with institution/period mapping.
- Provide editable section/question/option previews and validation errors; confirm transactionally into a draft only. Never publish automatically.

The administrator upload/parser/preview/confirmation workflow is now implemented in Data management. Original questions and historical answer rows are retained separately; imported forms remain drafts. The source workbook is archived in the database for exact-format exports. Questions-only exports preserve layout/styles while clearing answer cells; full original questions+answers exports are byte-identical. Respondents enter From/To reporting dates first. See `IMPLEMENTATION_REPORT.md` for verification and current limits.
