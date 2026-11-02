"""Shared, bounded condition semantics and server-side answer validation."""

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
import math
from fastapi import HTTPException

CHOICES = {"single_choice", "multiple_choice", "dropdown", "radio", "checkboxes"}
MULTIPLE = {"multiple_choice", "checkboxes"}
SUPPORTED = {
    "short_text",
    "long_text",
    "number",
    "decimal",
    "single_choice",
    "multiple_choice",
    "dropdown",
    "radio",
    "checkboxes",
    "date",
    "time",
    "datetime",
    "yes_no",
    "location",
    "information",
    "repeating_group",
    "calculated",
    "image",
    "file",
}
OPERATORS = {
    "equals",
    "not_equals",
    "greater_than",
    "less_than",
    "contains",
    "is_empty",
    "is_not_empty",
}


def references(rule, keys, depth=0):
    if not rule:
        return set()
    if depth > 8 or not isinstance(rule, dict):
        raise ValueError("Conditions must be a bounded condition tree.")
    if "all" in rule or "any" in rule:
        if set(rule) not in ({"all"}, {"any"}):
            raise ValueError("Use one condition group type per node.")
        group = rule.get("all", rule.get("any"))
        if not isinstance(group, list) or not 1 <= len(group) <= 30:
            raise ValueError("Condition groups must contain 1–30 rules.")
        return set().union(*(references(item, keys, depth + 1) for item in group))
    if rule.get("operator") not in OPERATORS or rule.get("question") not in keys:
        raise ValueError(
            "Conditions must reference an existing question and supported operator."
        )
    return {rule["question"]}


def visible(rule, answers):
    if not rule:
        return True
    if "all" in rule:
        return all(visible(item, answers) for item in rule["all"])
    if "any" in rule:
        return any(visible(item, answers) for item in rule["any"])
    value = answers.get(rule["question"])
    expected = rule.get("value")
    op = rule["operator"]
    empty = value is None or value == "" or value == []
    if op == "is_empty":
        return empty
    if op == "is_not_empty":
        return not empty
    if op == "equals":
        return value == expected
    if op == "not_equals":
        return value != expected
    if op == "contains":
        return (
            expected in value
            if isinstance(value, (str, list)) and isinstance(expected, str)
            else False
        )
    try:
        if empty:
            return False
        left, right = Decimal(str(value)), Decimal(str(expected))
        if not left.is_finite() or not right.is_finite():
            return False
        return left > right if op == "greater_than" else left < right
    except (InvalidOperation, TypeError, ValueError):
        return False


def validate_rules(definition):
    fields = {q.key: q for section in definition.sections for q in section.questions}
    dependencies = {key: set() for key in fields}
    for section in definition.sections:
        section_refs = references(section.conditions, fields)
        for q in section.questions:
            dependencies[q.key] = section_refs | references(q.conditions, fields)
            if q.kind == "calculated":
                source = q.config["formula"]["questions"]
                if any(
                    key not in fields
                    or fields[key].kind not in {"number", "decimal", "calculated"}
                    for key in source
                ):
                    raise ValueError(
                        "Calculations must reference existing numeric questions."
                    )
                dependencies[q.key].update(source)
    visited = set()

    def visit(key, ancestors):
        if key in ancestors:
            raise ValueError("Visibility rules contain a circular dependency.")
        if len(ancestors) > 64:
            raise ValueError("Visibility dependencies are too deeply nested.")
        if key in visited:
            return
        for dep in dependencies[key]:
            visit(dep, ancestors | {key})
        visited.add(key)

    for key in fields:
        visit(key, set())


def calculate(config, answers):
    formula = config["formula"]
    values = [answers.get(key) for key in formula["questions"]]
    if any(value is None or value == "" for value in values):
        return None
    try:
        values = [Decimal(str(value)) for value in values]
        if not all(value.is_finite() for value in values):
            return None
        op = formula["operation"]
        if op == "sum":
            result = sum(values)
        elif op == "difference":
            result = values[0] - sum(values[1:])
        elif op == "average":
            result = sum(values) / len(values)
        else:
            result = Decimal(1)
            for value in values:
                result *= value
        return (
            float(result)
            if result.is_finite() and math.isfinite(float(result))
            else None
        )
    except (InvalidOperation, ValueError, OverflowError):
        return None


def validate_answers(version, answers):
    fields = {q.key: q for section in version.sections for q in section.questions}
    if set(answers) - set(fields):
        raise HTTPException(422, "Answers contain unknown question keys.")
    clean = {}
    errors = {}
    # Hidden/disabled controlling answers must not make descendants visible.
    context = {
        key: answers.get(key, field.config.get("default"))
        for key, field in fields.items()
    }
    for _ in range(len(fields) + 1):
        old = dict(context)
        for key, field in fields.items():
            if field.kind == "calculated":
                context[key] = calculate(field.config, context)
        if context == old:
            break
    for _ in range(len(fields) + 1):
        hidden = {
            q.key
            for section in version.sections
            for q in section.questions
            if not section.enabled
            or not q.enabled
            or not visible(section.conditions, context)
            or not visible(q.conditions, context)
        }
        reduced = {key: value for key, value in context.items() if key not in hidden}
        if reduced == context:
            break
        context = reduced
        for key, field in fields.items():
            if field.kind == "calculated" and key in context:
                context[key] = calculate(field.config, context)
    for section in version.sections:
        for q in section.questions:
            if q.key in hidden or q.kind == "information":
                continue
            value = context.get(q.key)
            if value is None or value == "" or value == []:
                if q.required:
                    errors[q.key] = "This answer is required."
                continue
            try:
                if q.kind in {"number", "decimal", "calculated"}:
                    if isinstance(value, bool):
                        raise ValueError("Enter a number.")
                    numeric = Decimal(str(value))
                    if not numeric.is_finite():
                        raise ValueError("Enter a finite number.")
                    if q.kind == "number" and numeric != numeric.to_integral_value():
                        raise ValueError("Enter a whole number.")
                    if "min" in q.config and numeric < Decimal(str(q.config["min"])):
                        raise ValueError("Value is below the minimum.")
                    if "max" in q.config and numeric > Decimal(str(q.config["max"])):
                        raise ValueError("Value exceeds the maximum.")
                    value = int(numeric) if q.kind == "number" else float(numeric)
                    if not math.isfinite(value):
                        raise ValueError("Number is too large.")
                elif q.kind == "repeating_group":
                    if not isinstance(value, list) or len(value) > 100:
                        raise ValueError("Provide up to 100 repeated rows.")
                    from types import SimpleNamespace
                    from app.schemas.forms import QuestionInput

                    children = [
                        QuestionInput.model_validate(child)
                        for child in q.config["fields"]
                    ]
                    nested = SimpleNamespace(
                        sections=[
                            SimpleNamespace(
                                enabled=True, conditions=None, questions=children
                            )
                        ]
                    )
                    value = [validate_answers(nested, row) for row in value]
                elif q.kind in {"file", "image"}:
                    if (
                        not isinstance(value, dict)
                        or not isinstance(value.get("file_id"), int)
                        or isinstance(value["file_id"], bool)
                    ):
                        raise ValueError("Upload a file first.")
                    value = {"file_id": value["file_id"]}
                elif q.kind == "yes_no":
                    if not isinstance(value, bool):
                        raise ValueError("Choose Yes or No.")
                elif q.kind in CHOICES:
                    choices = {option.value for option in q.options}
                    if q.kind in MULTIPLE:
                        if (
                            not isinstance(value, list)
                            or any(not isinstance(item, str) for item in value)
                            or len(value) != len(set(value))
                            or not set(value) <= choices
                        ):
                            raise ValueError("Choose valid options without duplicates.")
                    elif not isinstance(value, str) or value not in choices:
                        raise ValueError("Choose a valid option.")
                elif q.kind == "location":
                    if not isinstance(value, dict) or set(value) != {
                        "latitude",
                        "longitude",
                    }:
                        raise ValueError("Provide latitude and longitude.")
                    lat, lon = float(value["latitude"]), float(value["longitude"])
                    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                        raise ValueError("Invalid coordinates.")
                    value = {"latitude": lat, "longitude": lon}
                else:
                    if not isinstance(value, str) or len(value) > 20000:
                        raise ValueError("Enter text up to 20,000 characters.")
                    if len(value) < q.config.get("min_length", 0) or len(
                        value
                    ) > q.config.get("max_length", 20000):
                        raise ValueError("Text length is outside the allowed range.")
                    if q.kind in {"date", "time", "datetime"}:
                        {"date": date, "time": time, "datetime": datetime}[
                            q.kind
                        ].fromisoformat(value)
                    if q.config.get("pattern"):
                        import regex

                        if not regex.fullmatch(
                            q.config["pattern"], value, timeout=0.05
                        ):
                            raise ValueError("Custom validation failed.")
                clean[q.key] = value
            except (
                ValueError,
                TypeError,
                InvalidOperation,
                OverflowError,
                TimeoutError,
            ):
                errors[q.key] = "Answer is invalid or outside its configured limits."
    if errors:
        raise HTTPException(
            422, {"message": "Check the highlighted answers.", "fields": errors}
        )
    return clean
