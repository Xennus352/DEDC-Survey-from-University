import sys
import types
import unittest
from unittest.mock import patch

try:
    import fcntl  # noqa: F401
except ImportError:
    fcntl = types.ModuleType("fcntl")
    fcntl.flock = lambda *args, **kwargs: None
    fcntl.LOCK_EX = 1
    fcntl.LOCK_UN = 2
    sys.modules["fcntl"] = fcntl

from sqlalchemy.exc import OperationalError

from app import dependencies
from app.dependencies import get_survey_connection
from app.errors import SurveyDatabaseUnavailable
from app.main import app


async def asgi_get(application, path):
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await application(
        {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.4"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": path,
            "raw_path": path.encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [(b"host", b"testserver")],
            "client": ("127.0.0.1", 1234),
            "server": ("testserver", 80),
        },
        receive,
        send,
    )
    start = messages[0]
    body = b"".join(
        message.get("body", b"") for message in messages[1:]
    ).decode()
    return start["status"], dict(start["headers"]), body


class SurveyDatabaseDependencyTests(unittest.TestCase):
    def test_connection_failure_becomes_typed_error(self):
        class FailingEngine:
            def begin(self):
                raise OperationalError(
                    "connect", None, Exception("connection refused")
                )

        with patch.object(dependencies, "engine", FailingEngine()):
            with self.assertRaises(SurveyDatabaseUnavailable):
                next(dependencies.get_survey_connection())


class SurveyDatabaseHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        def unavailable_connection():
            raise SurveyDatabaseUnavailable()
            yield

        app.dependency_overrides[get_survey_connection] = unavailable_connection

    async def asyncTearDown(self):
        app.dependency_overrides.pop(get_survey_connection, None)

    async def test_survey_page_returns_503_html(self):
        status, headers, body = await asgi_get(app, "/surveys/ministry")
        self.assertEqual(status, 503)
        self.assertEqual(headers[b"cache-control"], b"no-store")
        self.assertEqual(headers[b"retry-after"], b"5")
        self.assertIn("text/html", headers[b"content-type"].decode())
        self.assertIn("ဒေတာဘေ့စ်နှင့် ချိတ်ဆက်၍ မရပါ", body)
