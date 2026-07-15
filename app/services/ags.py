"""LTI 1.3 Assignment and Grade Services (AGS) score passback client.

Posts scores to the platform's line item per the AGS spec:
token via OAuth2 client_credentials with a signed JWT assertion, then
POST {lineitem}/scores. Canvas's manual posting policy holds posted scores
in the gradebook until the instructor releases them — nothing special is
required in the payload.

Failures follow the milestone error-handling strategy: retry transient
errors with exponential backoff, raise AGSError with detail on exhaustion,
and let callers persist the failure for the TA dashboard — grades are
never silently dropped.
"""

import asyncio
import datetime
import uuid

import httpx
from jose import jwt

TOKEN_SCOPE = "https://purl.imsglobal.org/spec/lti-ags/scope/score"
ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


class AGSError(Exception):
    """Raised when a score could not be posted. Message is TA-facing."""


class _TransientError(Exception):
    """Internal: retryable failure (network, 5xx, 429)."""


class AGSClient:
    """Posts AGS scores. Modes: live, dry_run (no HTTP), disabled."""

    def __init__(
        self,
        mode: str,
        token_url: str = "",
        client_id: str = "",
        private_key_pem: str = "",
        transport: httpx.AsyncBaseTransport | None = None,
        max_attempts: int = 3,
        backoff_base: float = 1.0,
    ):
        self.mode = mode
        self.token_url = token_url
        self.client_id = client_id
        self.private_key_pem = private_key_pem
        self.transport = transport
        self.max_attempts = max_attempts
        self.backoff_base = backoff_base

    def _client_assertion(self) -> str:
        now = datetime.datetime.now(datetime.timezone.utc)
        claims = {
            "iss": self.client_id,
            "sub": self.client_id,
            "aud": self.token_url,
            "iat": now,
            "exp": now + datetime.timedelta(minutes=5),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(claims, self.private_key_pem, algorithm="RS256")

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        response = await client.post(
            self.token_url,
            data={
                "grant_type": "client_credentials",
                "client_assertion_type": ASSERTION_TYPE,
                "client_assertion": self._client_assertion(),
                "scope": TOKEN_SCOPE,
            },
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        detail = f"Token request failed ({response.status_code}): {response.text[:200]}"
        if response.status_code >= 500 or response.status_code == 429:
            raise _TransientError(detail)
        raise AGSError(detail)

    @staticmethod
    def build_score_payload(
        lti_user_id: str, score_given: float, score_maximum: float
    ) -> dict:
        return {
            "userId": lti_user_id,
            "scoreGiven": score_given,
            "scoreMaximum": score_maximum,
            "activityProgress": "Completed",
            "gradingProgress": "FullyGraded",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    async def post_score(
        self,
        lineitem_url: str,
        lti_user_id: str,
        score_given: float,
        score_maximum: float,
    ) -> dict:
        """Post one score. Returns {status, attempts, payload}; raises AGSError.

        Transient failures (network errors, 5xx, 429) retry with exponential
        backoff; other 4xx responses fail immediately.
        """
        payload = self.build_score_payload(lti_user_id, score_given, score_maximum)

        if self.mode == "disabled":
            raise AGSError("AGS passback is disabled (AGS_MODE=disabled).")
        if self.mode == "dry_run":
            return {"status": "dry_run", "attempts": 0, "payload": payload}
        if not (self.token_url and self.client_id and self.private_key_pem):
            raise AGSError(
                "AGS live mode is not configured (need LTI_TOKEN_URL, "
                "LTI_CLIENT_ID, LTI_TOOL_PRIVATE_KEY)."
            )

        # AGS requires the /scores suffix on the line item URL (before any query)
        scores_url = lineitem_url.split("?")[0].rstrip("/") + "/scores"

        last_error = ""
        async with httpx.AsyncClient(transport=self.transport, timeout=30) as client:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    token = await self._get_access_token(client)
                    response = await client.post(
                        scores_url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/vnd.ims.lis.v1.score+json",
                        },
                    )
                    if response.status_code in (200, 201, 202, 204):
                        return {"status": "posted", "attempts": attempt, "payload": payload}
                    body = response.text[:200]
                    last_error = f"HTTP {response.status_code}: {body}"
                    if response.status_code < 500 and response.status_code != 429:
                        raise AGSError(f"Score post rejected — {last_error}")
                except AGSError:
                    raise
                except (_TransientError, httpx.HTTPError) as exc:
                    last_error = str(exc) if isinstance(exc, _TransientError) else (
                        f"{type(exc).__name__}: {exc}"
                    )

                if attempt < self.max_attempts:
                    await asyncio.sleep(self.backoff_base * 2 ** (attempt - 1))

        raise AGSError(
            f"Score post failed after {self.max_attempts} attempts — {last_error}"
        )
