"""Full-stack UI checks called by the isolated browser harness."""

from pathlib import Path
import json
from urllib.parse import urlparse

SOURCE = Path(
    __import__("os").environ.get(
        "DEDC_WORKBOOK_PATH",
        "/home/kazue/Downloads/Telegram Desktop/DEDC_Survey_Form_University_of_Computer_Studies_Taungoo_27875ea2.xlsx",
    )
)


def start_period(page):
    page.get_by_label("From date", exact=True).fill("2021-01-01")
    page.get_by_label("To date", exact=True).fill("2026-03-31")
    page.get_by_role("button", name="Start survey", exact=False).click()


def check(page, context, base):
    page.on("dialog", lambda dialog: dialog.accept())
    page.goto(base + "/dashboard/forms")
    page.get_by_role("button", name="Create form", exact=False).click()
    page.get_by_label("Form title", exact=True).fill("Browser verified survey")
    page.get_by_role("button", name="Create draft", exact=True).click()
    page.wait_for_url("**/dashboard/forms/*")
    form_id = int(urlparse(page.url).path.split("/")[-1])
    page.get_by_role("button", name="Add section", exact=False).click()
    page.get_by_label("Section title", exact=True).fill("Household data")
    page.get_by_role("button", name="Save section", exact=True).click()
    page.get_by_role("button", name="Add question", exact=False).click()
    page.get_by_label("Question title", exact=True).fill("How many households?")
    page.get_by_label("Unique key", exact=True).fill("households")
    page.locator("select[name=kind]").select_option("number")
    page.get_by_label("Required", exact=True).check()
    page.get_by_label("Minimum value", exact=True).fill("1")
    page.get_by_role("button", name="Save question", exact=True).click()
    page.get_by_role("button", name="Add section", exact=False).click()
    page.get_by_label("Section title", exact=True).fill("Additional section")
    page.get_by_role("button", name="Save section", exact=True).click()
    page.locator('[data-section-drag="0"]').drag_to(
        page.locator('[data-section-index="1"]')
    )
    assert (
        "Additional section" in page.locator("[data-section-drag]").first.inner_text()
    )
    page.locator('[data-section-index="1"]').get_by_role(
        "button", name="Move section up", exact=True
    ).click()
    page.locator('[data-section-index="1"]').get_by_role(
        "button", name="Edit", exact=True
    ).click()
    page.get_by_role("button", name="Delete section", exact=True).click()
    print(
        "PASS: dynamic section creation, drag-and-drop, keyboard reordering and deletion",
        flush=True,
    )
    page.get_by_role("button", name="Save changes", exact=True).click()
    page.get_by_text("All changes saved", exact=True).wait_for()
    page.get_by_role("link", name="Preview", exact=True).click()
    assert not page.get_by_label("How many households?", exact=False).is_visible()
    start_period(page)
    page.get_by_label("How many households?", exact=False).fill("12")
    page.get_by_role("button", name="Validate preview", exact=True).click()
    page.get_by_role("status").filter(has_text="All visible answers passed").wait_for()
    page.get_by_role("link", name="Back to builder").click()
    page.get_by_role("button", name="Publish this version", exact=True).click()
    page.get_by_role("button", name="Create new draft", exact=True).wait_for()
    token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    response = context.request.post(
        base + f"/api/admin/forms/{form_id}/submit",
        headers={"X-CSRF-Token": token},
        data={
            "answers": {"households": 12},
            "reporting_start": "2021-01-01",
            "reporting_end": "2026-03-31",
        },
    )
    assert response.status == 201, response.text()
    page.goto(base + "/dashboard/reports")
    page.get_by_role("button", name="View answers", exact=True).wait_for()
    page.get_by_role("button", name="View answers", exact=True).click()
    page.get_by_text("How many households?", exact=True).wait_for()
    page.get_by_role("button", name="Close dialog").click()
    page.get_by_text("Export report", exact=True).click()
    with page.expect_download() as download:
        page.get_by_role("link", name="Export CSV", exact=True).click()
    assert "households" in Path(download.value.path()).read_text()
    print(
        "PASS: browser creates, saves, previews, validates and publishes a form; real submission appears in reports and CSV",
        flush=True,
    )

    page.goto(base + "/dashboard/data")
    page.locator("#workbook-file").set_input_files(str(SOURCE))
    page.get_by_role("button", name="Read workbook", exact=True).click()
    page.get_by_role("button", name="Confirm & create draft", exact=True).wait_for()
    assert page.locator("#worksheet option").count() == 4
    page.get_by_role("button", name="Confirm & create draft", exact=True).click()
    page.wait_for_url("**/dashboard/forms/*")
    page.get_by_text("Form settings", exact=True).wait_for()
    imported_form_id = int(urlparse(page.url).path.split("/")[-1])
    page.goto(base + f"/dashboard/forms/{imported_form_id}/preview")
    assert page.get_by_label("From date", exact=True).input_value() == "2010-01-01"
    assert page.get_by_label("To date", exact=True).input_value() == "2015-12-31"
    page.get_by_role("button", name="Start survey", exact=False).click()
    page.locator("input[name=q1_quantity]").fill("42")
    page.get_by_role("button", name="Next section", exact=False).click()
    assert page.locator('[data-section="1"]').is_visible()
    page.get_by_role("button", name="Back", exact=True).click()
    assert page.locator("input[name=q1_quantity]").input_value() == "42"
    print(
        "PASS: reporting period is first; imported period defaults and section navigation preserve entered answers",
        flush=True,
    )

    page.goto(base + "/dashboard/data?tab=answers")
    page.get_by_role("heading", name="Original workbook answers").wait_for()
    page.get_by_text("Export workbook", exact=True).click()
    with page.expect_download() as exact_export:
        page.get_by_role(
            "link", name="Original format: questions & answers", exact=True
        ).click()
    assert Path(exact_export.value.path()).read_bytes() == SOURCE.read_bytes()
    print(
        "PASS: browser downloads a byte-identical original-format questions-and-answers workbook",
        flush=True,
    )

    page.get_by_text("B.C.Sc.= 210", exact=False).wait_for()
    with page.expect_download() as download:
        page.get_by_role("link", name="Export Excel", exact=True).click()
    from openpyxl import load_workbook
    from io import BytesIO

    book = load_workbook(BytesIO(Path(download.value.path()).read_bytes()))
    assert book.active.max_row == 30
    book.close()
    print(
        "PASS: actual workbook uploads, detects four sheets, creates a draft, preserves source answers and exports Excel",
        flush=True,
    )

    page.goto(base + "/dashboard/users")
    page.get_by_role("button", name="Add user", exact=False).click()
    page.get_by_label("Username", exact=True).fill("browser-created-user")
    page.get_by_label("Password", exact=True).fill("browser-user-password")
    page.locator("select[name=role_id]").select_option(label="University")
    page.get_by_role("button", name="Save user", exact=True).click()
    page.get_by_text("browser-created-user", exact=True).wait_for()
    print("PASS: user creation persists through the real user API", flush=True)

    respondent = context.browser.new_context(viewport={"width": 390, "height": 900})
    other = respondent.new_page()
    other.goto(base + "/survey/login")
    other.get_by_label("Username", exact=True).fill("browser-created-user")
    other.get_by_label("Password", exact=True).fill("browser-user-password")
    other.get_by_role("button", name="Sign in", exact=True).click()
    other.wait_for_url(base + "/survey")
    other.get_by_role("link", name="Open survey").click()
    start_period(other)
    other.get_by_label("How many households?", exact=False).fill("18")
    other.get_by_role("button", name="Submit survey", exact=True).click()
    other.get_by_role(
        "heading", name="Your response has been saved", exact=True
    ).wait_for()
    assert respondent.request.get(base + "/api/admin/session").status == 403
    respondent.close()
    page.bring_to_front()
    print(
        "PASS: normal respondent signs in, completes the shared survey renderer and submits while admin APIs stay forbidden",
        flush=True,
    )

    page.goto(base + "/dashboard")
    page.locator("#content .stats").wait_for()
    token = page.locator('meta[name="csrf-token"]').get_attribute("content")
    headers = {"X-CSRF-Token": token}

    def post(path, data):
        response = context.request.post(
            base + "/api/admin" + path, headers=headers, data=data
        )
        assert response.ok, response.text()
        return response.json()

    composite = post("/forms", {"title": "Advanced field verification"})
    composite_id = composite["id"]
    version_id = composite["versions"][0]["id"]
    fields = [
        {"key": "first", "title": "First number", "kind": "number"},
        {"key": "second", "title": "Second number", "kind": "decimal"},
        {
            "key": "total",
            "title": "Computed total",
            "kind": "calculated",
            "config": {
                "formula": {"operation": "sum", "questions": ["first", "second"]}
            },
        },
        {
            "key": "members",
            "title": "Household members",
            "kind": "repeating_group",
            "config": {
                "fields": [
                    {
                        "key": "name",
                        "title": "Member name",
                        "kind": "short_text",
                        "required": True,
                    }
                ]
            },
        },
        {
            "key": "document",
            "title": "Supporting file",
            "kind": "file",
            "required": True,
        },
        {
            "key": "image",
            "title": "Supporting image",
            "kind": "image",
            "required": True,
        },
    ]
    response = context.request.put(
        base + f"/api/admin/forms/{composite_id}/versions/{version_id}",
        headers=headers,
        data={
            "title": "Advanced field verification",
            "revision": 1,
            "sections": [{"title": "Advanced fields", "questions": fields}],
        },
    )
    assert response.ok, response.text()
    page.goto(base + f"/dashboard/forms/{composite_id}/preview")
    start_period(page)
    page.get_by_label("First number", exact=True).fill("3")
    page.get_by_label("Second number", exact=True).fill("2.5")
    assert page.get_by_label("Computed total", exact=True).input_value() == "5.5"
    page.get_by_role("button", name="Add row", exact=False).click()
    page.get_by_label("Member name", exact=False).fill("Test member")
    page.get_by_label("Supporting file", exact=False).set_input_files(
        {
            "name": "notes.txt",
            "mimeType": "text/plain",
            "buffer": b"Actual uploaded content",
        }
    )
    from PIL import Image
    from io import BytesIO

    png = BytesIO()
    Image.new("RGB", (2, 2), "white").save(png, format="PNG")
    page.get_by_label("Supporting image", exact=False).set_input_files(
        {"name": "photo.png", "mimeType": "image/png", "buffer": png.getvalue()}
    )
    page.get_by_text("Uploaded: notes.txt", exact=True).wait_for()
    page.get_by_text("Uploaded: photo.png", exact=True).wait_for()
    page.get_by_role("button", name="Validate preview", exact=True).click()
    page.get_by_role("status").filter(has_text="All visible answers passed").wait_for()
    print(
        "PASS: calculated fields, repeating groups, real file/image uploads and preview validation work through the browser",
        flush=True,
    )

    screenshots = Path("/tmp/dedc-workspace-review")
    screenshots.mkdir(exist_ok=True)
    for width in (390, 768, 1024, 1440):
        page.set_viewport_size({"width": width, "height": 1000})
        for route in (
            "",
            "/forms",
            "/questions",
            "/submissions",
            "/reports",
            "/users",
            "/data",
            "/settings",
            "/audit",
            f"/forms/{form_id}",
        ):
            page.goto(base + "/dashboard" + route)
            page.locator("#content .skeleton").wait_for(state="detached")
            assert page.locator("#content > .notice.error").count() == 0, (
                width,
                route,
                page.locator("#content").inner_text(),
            )
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth"
            ), (width, route, "horizontal overflow")
        page.goto(base + "/dashboard")
        page.locator("#content .stats").wait_for()
        page.screenshot(
            path=str(screenshots / f"overview-{width}.png"),
            full_page=True,
            animations="disabled",
        )
    page.goto(base + f"/dashboard/forms/{form_id}")
    page.locator("#content .editor-layout").wait_for()
    page.screenshot(
        path=str(screenshots / "form-builder.png"),
        full_page=True,
        animations="disabled",
    )
    page.goto(base + "/dashboard/settings")
    page.locator("#theme-setting").select_option("dark")
    page.goto(base + "/dashboard")
    page.locator("#content .stats").wait_for()
    assert page.evaluate("document.documentElement.dataset.theme") == "dark"
    page.screenshot(
        path=str(screenshots / "overview-dark.png"),
        full_page=True,
        animations="disabled",
    )
    print(
        "PASS: ten real admin routes render without page overflow at 390/768/1024/1440 px; dark theme persists",
        flush=True,
    )
