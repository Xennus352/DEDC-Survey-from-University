"""Shared display formatting for the public survey pages."""

MYANMAR_DIGITS = str.maketrans("0123456789", "၀၁၂၃၄၅၆၇၈၉")

MYANMAR_MONTHS = {
    1: "ဇန်နဝါရီ",
    2: "ဖေဖော်ဝါရီ",
    3: "မတ်",
    4: "ဧပြီ",
    5: "မေ",
    6: "ဇွန်",
    7: "ဇူလိုင်",
    8: "သြဂုတ်",
    9: "စက်တင်ဘာ",
    10: "အောက်တိုဘာ",
    11: "နိုဝင်ဘာ",
    12: "ဒီဇင်ဘာ",
}


def to_myanmar_number(value):
    return str(value).translate(MYANMAR_DIGITS)


def year_label(year_from, year_to, year_id):
    """Return a full Burmese year range, including the end month."""
    from_text = to_myanmar_number(year_from.year) if year_from else ""
    to_text = to_myanmar_number(year_to.year) if year_to else ""
    end_month = MYANMAR_MONTHS.get(year_to.month, "") if year_to else ""
    until = f"{end_month}လအထိ" if end_month else ""

    if from_text and to_text and year_from.year != year_to.year:
        if until:
            return f"{from_text} ခုနှစ် မှ {to_text} ခုနှစ်၊ {until}"
        return f"{from_text} ခုနှစ် မှ {to_text} ခုနှစ်"
    if from_text:
        if until:
            return f"{from_text} ခုနှစ်၊ {until}"
        return f"{from_text} ခုနှစ်"
    if to_text:
        if until:
            return f"{to_text} ခုနှစ်၊ {until}"
        return f"{to_text} ခုနှစ်"
    return f"ခုနှစ် #{year_id}"


def year_view(year):
    year_from = year.get("yearFrom")
    year_to = year.get("yearTo")
    end_month = MYANMAR_MONTHS.get(year_to.month, "") if year_to else ""
    start_year = (
        to_myanmar_number(year_from.year)
        if year_from
        else (to_myanmar_number(year_to.year) if year_to else "")
    )
    end_year = to_myanmar_number(year_to.year) if year_to else ""
    show_range = bool(
        year_from and year_to and year_from.year != year_to.year
    )
    return {
        **year,
        "label": year_label(year_from, year_to, year["yID"]),
        "startYear": start_year,
        "endYear": end_year,
        "endMonth": end_month,
        "showRange": show_range,
    }
