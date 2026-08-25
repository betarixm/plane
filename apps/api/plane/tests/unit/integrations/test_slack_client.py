# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from unittest.mock import Mock

import pytest

from plane.integrations.slack import SlackAuthenticationError, SlackClient, SlackClientError

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("error_code", ["invalid_auth", "missing_scope", "no_permission"])
def test_terminal_slack_access_error_is_typed_for_fail_closed_handling(error_code):
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {"ok": False, "error": error_code}
    response.raise_for_status.return_value = None
    session = Mock()
    session.request.return_value = response

    with pytest.raises(SlackAuthenticationError) as exc_info:
        SlackClient("xoxb-invalid", session=session).team_info()

    assert exc_info.value.error_code == error_code


def test_transient_slack_error_remains_retryable():
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.json.return_value = {"ok": False, "error": "internal_error"}
    response.raise_for_status.return_value = None
    session = Mock()
    session.request.return_value = response

    with pytest.raises(SlackClientError) as exc_info:
        SlackClient("xoxb-valid", session=session).team_info()

    assert not isinstance(exc_info.value, SlackAuthenticationError)
    assert exc_info.value.error_code == "internal_error"


def test_missing_bot_token_is_terminal():
    with pytest.raises(SlackAuthenticationError) as exc_info:
        SlackClient().users_list()

    assert exc_info.value.error_code == "bot_token_missing"
