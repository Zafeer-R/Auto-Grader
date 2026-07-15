import json
from types import SimpleNamespace

import httpx
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jinja2 import Environment, FileSystemLoader
from jose import jwt

from app.config import settings
from app.routers.ta import _ags_client
from app.services.ags import ASSERTION_TYPE, TOKEN_SCOPE, AGSClient, AGSError

TOKEN_URL = "https://canvas.test/login/oauth2/token"
LINEITEM = "https://canvas.test/api/lti/courses/1/line_items/9?type=none"
SCORES_URL = "https://canvas.test/api/lti/courses/1/line_items/9/scores?type=none"


def _test_key_pem() -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


KEY_PEM = _test_key_pem()


def _client(handler, **kwargs) -> AGSClient:
    return AGSClient(
        mode="live",
        token_url=TOKEN_URL,
        client_id="client-123",
        private_key_pem=KEY_PEM,
        transport=httpx.MockTransport(handler),
        backoff_base=0,  # no real sleeping in tests
        **kwargs,
    )


class TestClientAssertion:
    def test_configured_key_id_is_in_protected_header(self):
        client = AGSClient(
            mode="live",
            token_url=TOKEN_URL,
            client_id="client-123",
            private_key_pem=KEY_PEM,
            key_id="canvas-key-2026",
        )

        header = jwt.get_unverified_header(client._client_assertion())

        assert header["kid"] == "canvas-key-2026"
        assert header["alg"] == "RS256"

    def test_blank_key_id_remains_backward_compatible(self):
        client = AGSClient(
            mode="live",
            token_url=TOKEN_URL,
            client_id="client-123",
            private_key_pem=KEY_PEM,
        )

        assert "kid" not in jwt.get_unverified_header(client._client_assertion())

    def test_ta_client_uses_configured_key_id(self, monkeypatch):
        monkeypatch.setattr(settings, "lti_tool_key_id", "configured-key")

        assert _ags_client().key_id == "configured-key"


class TestDryRunAndDisabled:
    async def test_dry_run_returns_payload_without_http(self):
        client = AGSClient(mode="dry_run")
        result = await client.post_score(LINEITEM, "lti-user-1", 94.0, 100.0)
        assert result["status"] == "dry_run"
        assert result["payload"]["scoreGiven"] == 94.0
        assert result["payload"]["gradingProgress"] == "FullyGraded"

    async def test_disabled_raises(self):
        client = AGSClient(mode="disabled")
        with pytest.raises(AGSError, match="disabled") as exc_info:
            await client.post_score(LINEITEM, "lti-user-1", 94.0, 100.0)
        assert exc_info.value.attempts == 1

    async def test_live_unconfigured_raises(self):
        client = AGSClient(mode="live")
        with pytest.raises(AGSError, match="not configured") as exc_info:
            await client.post_score(LINEITEM, "lti-user-1", 94.0, 100.0)
        assert exc_info.value.attempts == 1


class TestLivePosting:
    @pytest.mark.parametrize(
        "private_key_pem",
        [
            "not-a-private-key",
            r"-----BEGIN PRIVATE KEY-----\nnot-real\n-----END PRIVATE KEY-----",
        ],
    )
    async def test_invalid_private_key_fails_without_retry_or_http(self, private_key_pem):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(500)

        client = AGSClient(
            mode="live",
            token_url=TOKEN_URL,
            client_id="client-123",
            private_key_pem=private_key_pem,
            transport=httpx.MockTransport(handler),
            max_attempts=3,
            backoff_base=0,
        )

        with pytest.raises(AGSError, match="sign.*LTI_TOOL_PRIVATE_KEY") as exc_info:
            await client.post_score(LINEITEM, "u", 50.0, 100.0)

        assert exc_info.value.attempts == 1
        assert calls == []

    async def test_posts_score_with_token(self):
        calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if str(request.url) == TOKEN_URL:
                body = request.content.decode()
                assert "grant_type=client_credentials" in body
                assert ASSERTION_TYPE.replace(":", "%3A") in body
                assert TOKEN_SCOPE.replace(":", "%3A").replace("/", "%2F") in body
                return httpx.Response(200, json={"access_token": "tok-abc"})
            assert str(request.url) == SCORES_URL
            assert request.headers["Authorization"] == "Bearer tok-abc"
            assert request.headers["Content-Type"] == "application/vnd.ims.lis.v1.score+json"
            payload = json.loads(request.content)
            assert payload["userId"] == "lti-user-1"
            assert payload["scoreGiven"] == 94.0
            assert payload["scoreMaximum"] == 100.0
            assert payload["activityProgress"] == "Completed"
            return httpx.Response(200, json={"resultUrl": "..."})

        result = await _client(handler).post_score(LINEITEM, "lti-user-1", 94.0, 100.0)
        assert result["status"] == "posted"
        assert result["attempts"] == 1
        assert len(calls) == 2  # token + score

    async def test_retries_transient_500_then_succeeds(self):
        score_calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == TOKEN_URL:
                return httpx.Response(200, json={"access_token": "tok"})
            score_calls.append(request)
            if len(score_calls) < 3:
                return httpx.Response(502, text="bad gateway")
            return httpx.Response(200, json={})

        result = await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert result["status"] == "posted"
        assert result["attempts"] == 3
        assert len(score_calls) == 3

    async def test_exhausted_retries_raise_with_detail(self):
        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == TOKEN_URL:
                return httpx.Response(200, json={"access_token": "tok"})
            return httpx.Response(503, text="maintenance")

        with pytest.raises(AGSError, match="after 3 attempts.*503") as exc_info:
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert exc_info.value.attempts == 3

    async def test_4xx_fails_immediately_without_retry(self):
        score_calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == TOKEN_URL:
                return httpx.Response(200, json={"access_token": "tok"})
            score_calls.append(request)
            return httpx.Response(422, text="unprocessable")

        with pytest.raises(AGSError, match="rejected.*422") as exc_info:
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert exc_info.value.attempts == 1
        assert len(score_calls) == 1

    async def test_retry_then_4xx_reports_all_attempts(self):
        score_calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == TOKEN_URL:
                return httpx.Response(200, json={"access_token": "tok"})
            score_calls.append(request)
            if len(score_calls) == 1:
                return httpx.Response(503, text="maintenance")
            return httpx.Response(422, text="unprocessable")

        with pytest.raises(AGSError, match="rejected.*422") as exc_info:
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)

        assert exc_info.value.attempts == 2
        assert len(score_calls) == 2

    async def test_token_5xx_retries_then_raises(self):
        token_calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            token_calls.append(request)
            return httpx.Response(500, text="ise")

        with pytest.raises(AGSError, match="after 3 attempts"):
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert len(token_calls) == 3

    async def test_invalid_json_token_response_retries_then_raises(self):
        token_calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            token_calls.append(request)
            return httpx.Response(200, text="<html>not json</html>")

        with pytest.raises(AGSError, match="after 3 attempts.*invalid JSON"):
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert len(token_calls) == 3

    @pytest.mark.parametrize(
        "payload",
        [{}, {"access_token": None}, {"access_token": ""}, {"access_token": "   "}],
    )
    async def test_missing_or_empty_access_token_retries_then_raises(self, payload):
        token_calls = []

        def handler(request: httpx.Request) -> httpx.Response:
            token_calls.append(request)
            return httpx.Response(200, json=payload)

        with pytest.raises(AGSError, match="after 3 attempts.*non-empty access_token"):
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert len(token_calls) == 3

    async def test_token_4xx_fails_immediately(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="invalid_client")

        with pytest.raises(AGSError, match="Token request failed \\(401\\)"):
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)

    async def test_network_error_retries(self):
        attempts = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts.append(request)
            raise httpx.ConnectError("connection refused")

        with pytest.raises(AGSError, match="ConnectError"):
            await _client(handler).post_score(LINEITEM, "u", 50.0, 100.0)
        assert len(attempts) == 3


class TestDashboardPassbackDisplay:
    def _render_row(self, passback):
        env = Environment(loader=FileSystemLoader("app/templates"))
        row = {
            "submission": SimpleNamespace(id=3, submitted_at=None, max_score=70.0),
            "student": SimpleNamespace(display_name="S", lti_user_id="u"),
            "score": {"auto_score": 40.0, "checkpoint_score": 0.0,
                      "checkpoint_max": 30.0, "total": 40.0, "checkpoints": []},
            "flags": [],
            "passback": passback,
            "grade_max": 100,
        }
        return env.get_template("_ta_row.html").render(row=row)

    def test_failed_chip_shows_error_and_retry(self):
        passback = SimpleNamespace(
            status="failed", attempts=3, last_error="HTTP 503: maintenance", posted_at=None
        )
        html = self._render_row(passback)
        assert "failed (3)" in html
        assert "HTTP 503: maintenance" in html
        assert ">Retry" in html.replace("\n", "").replace("  ", "")

    def test_posted_and_dry_run_chips(self):
        posted = SimpleNamespace(status="posted", attempts=1, last_error="", posted_at="t")
        assert "posted" in self._render_row(posted)
        dry = SimpleNamespace(status="dry_run", attempts=0, last_error="", posted_at=None)
        assert "dry run" in self._render_row(dry)

    def test_no_passback_shows_post_button(self):
        html = self._render_row(None)
        assert "post-grade" in html
        assert ">Post" in html.replace("\n", "").replace("  ", "")
