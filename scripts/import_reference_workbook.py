"""Explicit CLI import of a reviewed DEDC workbook into draft forms only.

Usage: uv run python scripts/import_reference_workbook.py /path/to/file.xlsx --actor-id 1 --confirm
An exact workbook/worksheet already imported is skipped, never overwritten.
"""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.database import SessionLocal
from app.models.forms import WorkbookImport
from app.models.user import User, UserRole
from app.config import settings
from app.schemas.forms import DraftInput
from app.services import workbook


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--actor-id", type=int, required=True)
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    preview = workbook.parse_workbook(args.path.read_bytes())
    print("Workbook SHA256:", preview["digest"])
    for sheet in preview["sheets"]:
        if "error" in sheet:
            raise SystemExit(sheet["worksheet"] + ": " + sheet["error"])
        print(
            sheet["worksheet"],
            sheet["question_rows"],
            "question rows,",
            sheet["field_count"],
            "fields,",
            len(sheet["rows"]),
            "source observations; status=draft",
        )
    if not args.confirm:
        print(
            "Review complete. Add --confirm to save drafts and original source answers."
        )
        return
    with SessionLocal() as db:
        from app.services.workbook_export import archive_template

        archive_template(db, args.path.read_bytes(), args.path.name)
        account = db.get(User, args.actor_id)
        role = db.get(UserRole, account.role_id) if account else None
        if (
            not account
            or not account.is_active
            or not role
            or role.name != settings.ADMIN_ROLE_NAME
        ):
            raise SystemExit("Actor must be an active administrator.")
        for sheet in preview["sheets"]:
            if (
                db.query(WorkbookImport)
                .filter_by(digest=preview["digest"], worksheet=sheet["worksheet"])
                .first()
            ):
                source = (
                    db.query(WorkbookImport)
                    .filter_by(digest=preview["digest"], worksheet=sheet["worksheet"])
                    .one()
                )
                from app.models.forms import FormVersion
                from datetime import date

                v = db.get(FormVersion, source.version_id)
                if v.status == "draft" and not v.reporting_start:
                    v.reporting_start = (
                        date.fromisoformat(sheet["definition"]["reporting_start"])
                        if sheet["definition"].get("reporting_start")
                        else None
                    )
                    v.reporting_end = (
                        date.fromisoformat(sheet["definition"]["reporting_end"])
                        if sheet["definition"].get("reporting_end")
                        else None
                    )
                db.commit()
                print("Already imported; source template retained:", sheet["worksheet"])
                continue
            form = workbook.import_sheet(
                db,
                preview,
                sheet["worksheet"],
                DraftInput.model_validate(sheet["definition"]),
                account.id,
            )
            print("Saved draft form", form.id, ":", sheet["worksheet"])

        db.commit()


if __name__ == "__main__":
    main()
