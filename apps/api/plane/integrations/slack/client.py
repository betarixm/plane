# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from typing import Any

import requests

from .config import get_slack_credentials


class SlackClientError(Exception):
    """Raised when Slack rejects a request or returns an invalid response."""

    def __init__(self, message: str, *, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class SlackAuthenticationError(SlackClientError):
    """Raised when Slack identity access can no longer be trusted."""


TERMINAL_AUTH_ERRORS = frozenset(
    {
        "account_inactive",
        "access_denied",
        "deprecated_endpoint",
        "enterprise_is_restricted",
        "invalid_auth",
        "invalid_token",
        "missing_scope",
        "no_permission",
        "not_authed",
        "not_allowed_token_type",
        "org_login_required",
        "team_access_not_granted",
        "token_expired",
        "token_not_found",
        "token_revoked",
    }
)


class SlackRateLimited(SlackClientError):
    def __init__(self, retry_after: int):
        super().__init__("Slack API rate limit exceeded")
        self.retry_after = retry_after


class SlackClient:
    API_BASE_URL = "https://slack.com/api/"
    REQUEST_TIMEOUT = (3.05, 15)

    def __init__(self, bot_token: str | None = None, *, session: Any | None = None):
        self.bot_token = bot_token
        self.session = session or requests.Session()

    def _request(
        self,
        method: str,
        endpoint: str,
        *,
        token: str | None = None,
        data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        auth_token = token if token is not None else self.bot_token
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        try:
            response = self.session.request(
                method,
                f"{self.API_BASE_URL}{endpoint}",
                data=data,
                params=params,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT,
            )
        except requests.RequestException as exc:
            raise SlackClientError("Slack API request failed") from exc

        if response.status_code == 429:
            raw_retry_after = response.headers.get("Retry-After", "1")
            try:
                retry_after = max(1, int(raw_retry_after))
            except (TypeError, ValueError):
                retry_after = 1
            raise SlackRateLimited(retry_after)

        try:
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise SlackClientError("Slack API returned an invalid response") from exc

        if not isinstance(payload, dict) or payload.get("ok") is not True:
            error = payload.get("error", "unknown_error") if isinstance(payload, dict) else "invalid_json"
            exception_class = SlackAuthenticationError if error in TERMINAL_AUTH_ERRORS else SlackClientError
            raise exception_class(f"Slack API error: {error}", error_code=str(error))
        return payload

    def exchange_oauth_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        credentials = get_slack_credentials()
        return self._request(
            "POST",
            "oauth.v2.access",
            token="",
            data={
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

    def exchange_openid_code(self, code: str, redirect_uri: str) -> dict[str, Any]:
        credentials = get_slack_credentials()
        return self._request(
            "POST",
            "openid.connect.token",
            token="",
            data={
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            },
        )

    def openid_userinfo(self, access_token: str) -> dict[str, Any]:
        return self._request("GET", "openid.connect.userInfo", token=access_token)

    def auth_test(self) -> dict[str, Any]:
        self._require_bot_token()
        return self._request("POST", "auth.test")

    def team_info(self) -> dict[str, Any]:
        self._require_bot_token()
        return self._request("GET", "team.info")

    def users_info(self, user_id: str) -> dict[str, Any]:
        self._require_bot_token()
        return self._request("GET", "users.info", params={"user": user_id})

    def users_list(self, cursor: str | None = None) -> dict[str, Any]:
        self._require_bot_token()
        params: dict[str, Any] = {"limit": 200}
        if cursor:
            params["cursor"] = cursor
        return self._request("GET", "users.list", params=params)

    def _require_bot_token(self) -> None:
        if not self.bot_token:
            raise SlackAuthenticationError(
                "Slack bot token is not configured",
                error_code="bot_token_missing",
            )
