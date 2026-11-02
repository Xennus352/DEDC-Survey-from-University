"""Bounded, validated definitions used by both the editor and renderer."""

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
import math
from pydantic import BaseModel, ConfigDict, Field, model_validator

QuestionKind = Literal[
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
    "calculated",
    "repeating_group",
    "image",
    "file",
]


class OptionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1, max_length=1024)


class QuestionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,99}$")
    title: str = Field(min_length=1, max_length=10000)
    title_my: str = Field(default="", max_length=10000)
    title_en: str = Field(default="", max_length=10000)
    kind: QuestionKind = "short_text"
    help_text: str = Field(default="", max_length=5000)
    placeholder: str = Field(default="", max_length=255)
    required: bool = False
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)
    conditions: dict[str, Any] | None = None
    options: list[OptionInput] = Field(default_factory=list, max_length=200)

    @model_validator(mode="after")
    def unique_options(self):
        if len({o.value for o in self.options}) != len(self.options):
            raise ValueError("Option values must be unique.")
        if (
            self.kind
            in {"single_choice", "multiple_choice", "dropdown", "radio", "checkboxes"}
            and not self.options
        ):
            raise ValueError("Choice questions need at least one option.")
        allowed = {
            "min",
            "max",
            "min_length",
            "max_length",
            "default",
            "fields",
            "formula",
            "pattern",
            "source_cell",
            "source_number",
            "source_question",
            "source_component",
        }
        if set(self.config) - allowed:
            raise ValueError(
                "Unsupported validation configuration. Use explicit minimum/maximum values and text lengths."
            )
        for key in ["min", "max", "min_length", "max_length"]:
            if key in self.config:
                try:
                    value = Decimal(str(self.config[key]))
                    if not value.is_finite() or isinstance(self.config[key], bool):
                        raise ValueError()
                    if "length" in key and (
                        value < 0 or value != value.to_integral_value() or value > 20000
                    ):
                        raise ValueError()
                    self.config[key] = int(value) if "length" in key else float(value)
                    if not math.isfinite(self.config[key]):
                        raise ValueError()
                except (ValueError, InvalidOperation):
                    raise ValueError(
                        "Validation limits must be finite numbers; lengths must be whole numbers up to 20,000."
                    )
        for low, high in [("min", "max"), ("min_length", "max_length")]:
            if (
                low in self.config
                and high in self.config
                and self.config[low] > self.config[high]
            ):
                raise ValueError(f"{low} must not exceed {high}.")
        if len(str(self.config)) > 20000:
            raise ValueError("Question configuration is too large.")
        if "pattern" in self.config:
            import regex

            pattern = self.config["pattern"]
            if not isinstance(pattern, str) or len(pattern) > 500:
                raise ValueError("Custom patterns must contain at most 500 characters.")
            try:
                regex.compile(pattern)
            except regex.error:
                raise ValueError("The custom validation pattern is invalid.")
        if self.kind in {"file", "image"} and "default" in self.config:
            raise ValueError("Attachments cannot have preselected defaults.")
        if self.kind == "repeating_group":
            children = self.config.get("fields", [])
            if not isinstance(children, list) or not 1 <= len(children) <= 30:
                raise ValueError("Repeating groups need 1–30 child fields.")
            for child in children:
                if child.get("kind") in {
                    "repeating_group",
                    "calculated",
                    "file",
                    "image",
                }:
                    raise ValueError(
                        "Repeating groups currently support scalar child fields."
                    )
            parsed = [QuestionInput.model_validate(child) for child in children]
            if len({child.key for child in parsed}) != len(parsed):
                raise ValueError("Repeating field keys must be unique.")
            if any(child.conditions for child in parsed):
                raise ValueError("Configure visibility on the whole repeating group.")
            self.config["fields"] = [child.model_dump() for child in parsed]
        if self.kind == "calculated":
            formula = self.config.get("formula", {})
            if (
                formula.get("operation")
                not in {"sum", "difference", "product", "average"}
                or not isinstance(formula.get("questions"), list)
                or not 1 <= len(formula["questions"]) <= 30
            ):
                raise ValueError(
                    "Choose sum/difference/product/average and 1–30 source question keys."
                )
        return self


class SectionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=10000)
    description: str = Field(default="", max_length=10000)
    enabled: bool = True
    conditions: dict[str, Any] | None = None
    questions: list[QuestionInput] = Field(default_factory=list, max_length=500)


class DraftInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=10000)
    language: Literal["my", "en", "bilingual"] = "my"
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    reporting_start: date | None = None
    reporting_end: date | None = None
    revision: int = Field(default=1, ge=1)
    sections: list[SectionInput] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def valid_structure(self):
        for name in ["starts_at", "ends_at"]:
            value = getattr(self, name)
            if value and value.tzinfo:
                setattr(self, name, value.astimezone(timezone.utc).replace(tzinfo=None))
        if self.starts_at and self.ends_at and self.starts_at >= self.ends_at:
            raise ValueError("End date must follow start date.")
        if (
            self.reporting_start
            and self.reporting_end
            and self.reporting_start > self.reporting_end
        ):
            raise ValueError("Reporting end date must be on or after its start date.")
        keys = [q.key for s in self.sections for q in s.questions]
        if len(keys) != len(set(keys)):
            raise ValueError("Question keys must be unique across the form.")
        if len(keys) > 1000:
            raise ValueError("A form can contain at most 1000 questions.")
        return self


class CreateForm(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    audience: Literal["university", "ministry", "general"] = "university"


class SubmissionInput(BaseModel):
    answers: dict[str, Any]
    reporting_start: date
    reporting_end: date
    location: dict[str, str] = Field(default_factory=dict)
    started_at: datetime | None = None

    @model_validator(mode="after")
    def valid_period(self):
        if self.reporting_start > self.reporting_end:
            raise ValueError("Reporting end date must be on or after its start date.")
        return self


class PreviewInput(BaseModel):
    answers: dict[str, Any]
