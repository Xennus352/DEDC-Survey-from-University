import re
import unittest
from datetime import date
from http.cookies import SimpleCookie
from urllib.parse import urlencode, urlsplit

from fastapi import FastAPI
from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from app.dependencies import get_survey_connection
from app.routers.web import university_survey
from app.storage import university_survey_schema as survey_schema


class SurveyClient:
    def __init__(self, app):
        self.app = app
        self.cookies = SimpleCookie()

    async def request(self, method, path, data=None):
        parsed = urlsplit(path)
        body = urlencode(data).encode() if data is not None else b""
        headers = [
            (b"host", b"testserver"),
            (b"content-type", b"application/x-www-form-urlencoded"),
            (b"content-length", str(len(body)).encode()),
        ]
        if self.cookies:
            cookie_header = "; ".join(
                f"{item.key}={item.value}" for item in self.cookies.values()
            )
            headers.append((b"cookie", cookie_header.encode()))

        messages = []

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        async def send(message):
            messages.append(message)

        await self.app(
            {
                "type": "http",
                "asgi": {"version": "3.0", "spec_version": "2.4"},
                "http_version": "1.1",
                "method": method,
                "scheme": "http",
                "path": parsed.path,
                "raw_path": parsed.path.encode(),
                "query_string": parsed.query.encode(),
                "root_path": "",
                "headers": headers,
                "client": ("127.0.0.1", 1234),
                "server": ("testserver", 80),
            },
            receive,
            send,
        )
        start = messages[0]
        for key, value in start["headers"]:
            if key == b"set-cookie":
                self.cookies.load(value.decode())
        text = b"".join(
            message.get("body", b"") for message in messages[1:]
        ).decode()
        return start["status"], dict(start["headers"]), text


class UniversitySurveyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        survey_schema.metadata.create_all(self.engine)
        with self.engine.begin() as connection:
            connection.execute(
                survey_schema.year.insert(),
                [
                    {
                        "yID": 1,
                        "yearFrom": date(2024, 1, 1),
                        "yearTo": date(2024, 12, 31),
                        "status": 1,
                    },
                    {
                        "yID": 2,
                        "yearFrom": date(2023, 1, 1),
                        "yearTo": date(2023, 12, 31),
                        "status": 0,
                    },
                    {
                        "yID": 3,
                        "yearFrom": date(2025, 1, 1),
                        "yearTo": date(2025, 12, 31),
                        "status": 1,
                    },
                ],
            )
            connection.execute(
                survey_schema.questiontitle.insert(),
                {
                    "qTID": 10,
                    "qTDetail": "သုတေသနနှင့် ဆန်းသစ်တီထွင်မှု",
                    "description": "သုတေသနဆိုင်ရာ အချက်အလက်များ",
                },
            )
            connection.execute(
                survey_schema.uniquestion.insert(),
                [
                    {
                        "uQId": 100,
                        "uQDetail": "သုတေသန စီမံကိန်း ရှိပါသလား။",
                        "qTID": 10,
                        "yID": 1,
                    },
                    {
                        "uQId": 101,
                        "uQDetail": "နိုင်ငံတကာ ပူးပေါင်းဆောင်ရွက်မှု ရှိပါသလား။",
                        "qTID": 10,
                        "yID": 1,
                    },
                    {
                        "uQId": 102,
                        "uQDetail": "အခြား အချက်အလက် ရှိပါသလား။",
                        "qTID": None,
                        "yID": 1,
                    },
                ],
            )
            connection.execute(
                survey_schema.university.insert(),
                [
                    {
                        "uniId": 1,
                        "uniType": "CU",
                        "uniName": "ကွန်ပျူတာတက္ကသိုလ် (ရန်ကုန်)",
                    },
                    {
                        "uniId": 2,
                        "uniType": "TU",
                        "uniName": "ရန်ကုန် နည်းပညာတက္ကသိုလ်",
                    },
                ],
            )

        app = FastAPI()
        app.include_router(university_survey.router)

        def override_connection():
            with self.engine.begin() as connection:
                yield connection

        app.dependency_overrides[get_survey_connection] = override_connection
        self.client = SurveyClient(app)

    async def asyncTearDown(self):
        self.engine.dispose()

    async def get_csrf(self, path):
        status, _, text = await self.client.request("GET", path)
        self.assertEqual(status, 200)
        match = re.search(r'name="csrf_token" value="([^"]+)"', text)
        self.assertIsNotNone(match)
        return text, match.group(1)

    def valid_answers(self, csrf_token):
        return {
            "csrf_token": csrf_token,
            "uniId": "1",
            "has_100": "1",
            "count_100": "3",
            "description_100": "သုတေသန စီမံကိန်း သုံးခု",
            "has_101": "0",
            "has_102": "1",
            "count_102": "5",
            "description_102": "အခြား အချက်အလက်",
        }

    async def test_year_chooser_lists_only_active_years_with_questions(self):
        status, _, text = await self.client.request("GET", "/surveys/university")
        self.assertEqual(status, 200)
        self.assertIn("၂၀၂၄", text)
        self.assertIn("ဒီဇင်ဘာလအထိ", text)
        self.assertNotIn("၂၀၂၃", text)
        self.assertNotIn("၂၀၂၅", text)
        self.assertIn("/surveys/university/1", text)

    async def test_form_groups_questions_and_renders_three_answers(self):
        text, _ = await self.get_csrf("/surveys/university/1")
        self.assertIn("သုတေသနနှင့် ဆန်းသစ်တီထွင်မှု", text)
        self.assertIn("အခြား မေးခွန်းများ", text)
        self.assertIn('name="has_100"', text)
        self.assertIn('name="count_100"', text)
        self.assertIn('name="description_100"', text)
        self.assertIn("ကွန်ပျူတာတက္ကသိုလ် (ရန်ကုန်)", text)
        self.assertIn("ရန်ကုန် နည်းပညာတက္ကသိုလ်", text)

    async def test_submission_saves_one_row_per_question_and_skips_duplicates(self):
        _, token = await self.get_csrf("/surveys/university/1")
        data = self.valid_answers(token)

        status, headers, _ = await self.client.request(
            "POST", "/surveys/university/1", data
        )
        self.assertEqual(status, 303)
        self.assertIn("status=saved", headers[b"location"].decode())

        with self.engine.connect() as connection:
            rows = connection.execute(
                select(survey_schema.unisurvey).order_by(
                    survey_schema.unisurvey.c.uQId
                )
            ).mappings().all()
        self.assertEqual(len(rows), 3)
        self.assertTrue(rows[0]["hasItem"])
        self.assertEqual(rows[0]["itemCount"], 3)
        self.assertFalse(rows[1]["hasItem"])
        self.assertIsNone(rows[1]["itemCount"])
        self.assertIsNone(rows[1]["surveyDescription"])
        self.assertIsNone(rows[0]["remark"])

        status, headers, _ = await self.client.request(
            "POST", "/surveys/university/1", data
        )
        self.assertEqual(status, 303)
        self.assertIn("status=already", headers[b"location"].decode())
        with self.engine.connect() as connection:
            count = connection.execute(
                select(survey_schema.unisurvey)
            ).mappings().all()
        self.assertEqual(len(count), 3)

    async def test_submission_reports_partial_when_some_answers_exist(self):
        with self.engine.begin() as connection:
            connection.execute(
                survey_schema.unisurvey.insert().values(
                    uniId=1,
                    uQId=100,
                    hasItem=0,
                    itemCount=None,
                    surveyDescription=None,
                    remark=None,
                )
            )
        _, token = await self.get_csrf("/surveys/university/1")
        data = self.valid_answers(token)

        status, headers, _ = await self.client.request(
            "POST", "/surveys/university/1", data
        )
        self.assertEqual(status, 303)
        location = headers[b"location"].decode()
        self.assertIn("status=partial", location)
        self.assertIn("saved=2", location)
        self.assertIn("skipped=1", location)

        with self.engine.connect() as connection:
            rows = connection.execute(
                select(survey_schema.unisurvey).order_by(
                    survey_schema.unisurvey.c.uQId
                )
            ).mappings().all()
        self.assertEqual(len(rows), 3)
        self.assertFalse(rows[0]["hasItem"])
        self.assertIsNone(rows[0]["itemCount"])

    async def test_submission_rejects_invalid_csrf(self):
        _, token = await self.get_csrf("/surveys/university/1")
        data = self.valid_answers(token)
        data["csrf_token"] = "not-the-cookie-token"

        status, _, text = await self.client.request(
            "POST", "/surveys/university/1", data
        )
        self.assertEqual(status, 400)
        self.assertIn("သက်တမ်းကုန်ဆုံးသွားပါသည်", text)
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(survey_schema.unisurvey)
            ).mappings().all()
        self.assertEqual(rows, [])

    async def test_submission_marks_missing_university_as_invalid(self):
        _, token = await self.get_csrf("/surveys/university/1")
        data = self.valid_answers(token)
        data.pop("uniId")

        status, _, text = await self.client.request(
            "POST", "/surveys/university/1", data
        )
        self.assertEqual(status, 400)
        self.assertIn("uni-combobox is-invalid", text)
        self.assertIn("တက္ကသိုလ်ကို စာရင်းမှ ရွေးချယ်ပါ။", text)
        self.assertIn("novalidate", text)

    async def test_submission_rejects_missing_answers(self):
        _, token = await self.get_csrf("/surveys/university/1")
        data = self.valid_answers(token)
        data.pop("has_101")

        status, _, text = await self.client.request(
            "POST", "/surveys/university/1", data
        )
        self.assertEqual(status, 400)
        self.assertIn("ရှိ/မရှိ ကို ရွေးချယ်ပါ", text)
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(survey_schema.unisurvey)
            ).mappings().all()
        self.assertEqual(rows, [])
