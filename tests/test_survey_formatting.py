import unittest
from datetime import date

from app.services.survey_formatting import to_myanmar_number, year_label, year_view


class SurveyFormattingTests(unittest.TestCase):
    def test_range_label_includes_burmese_years_and_end_month(self):
        label = year_label(
            date(2016, 1, 1),
            date(2020, 12, 31),
            7,
        )
        self.assertEqual(
            label,
            "၂၀၁၆ ခုနှစ် မှ ၂၀၂၀ ခုနှစ်၊ ဒီဇင်ဘာလအထိ",
        )

    def test_single_year_label_includes_end_month_once(self):
        label = year_label(
            date(2024, 1, 1),
            date(2024, 12, 31),
            1,
        )
        self.assertEqual(label, "၂၀၂၄ ခုနှစ်၊ ဒီဇင်ဘာလအထိ")

    def test_year_view_exposes_parts_for_card_layout(self):
        view = year_view(
            {
                "yID": 1,
                "yearFrom": date(2016, 1, 1),
                "yearTo": date(2020, 12, 31),
                "questionCount": 4,
            }
        )
        self.assertEqual(view["startYear"], "၂၀၁၆")
        self.assertEqual(view["endYear"], "၂၀၂၀")
        self.assertEqual(view["endMonth"], "ဒီဇင်ဘာ")
        self.assertTrue(view["showRange"])
        self.assertEqual(
            view["label"],
            "၂၀၁၆ ခုနှစ် မှ ၂၀၂၀ ခုနှစ်၊ ဒီဇင်ဘာလအထိ",
        )

    def test_missing_dates_fall_back_to_identifier(self):
        self.assertEqual(year_label(None, None, 9), "ခုနှစ် #9")
        self.assertEqual(to_myanmar_number(2026), "၂၀၂၆")


if __name__ == "__main__":
    unittest.main()
