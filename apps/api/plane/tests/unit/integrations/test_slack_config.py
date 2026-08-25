# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest

from plane.integrations.slack.config import get_slack_credentials


pytestmark = pytest.mark.unit


def test_slack_credentials_are_read_from_environment(monkeypatch):
    monkeypatch.setenv("SLACK_CLIENT_ID", " environment-client-id ")
    monkeypatch.setenv("SLACK_CLIENT_SECRET", " environment-client-secret ")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", " environment-signing-secret ")

    credentials = get_slack_credentials()

    assert credentials.client_id == "environment-client-id"
    assert credentials.client_secret == "environment-client-secret"
    assert credentials.signing_secret == "environment-signing-secret"


def test_missing_slack_credentials_are_empty(monkeypatch):
    monkeypatch.delenv("SLACK_CLIENT_ID", raising=False)
    monkeypatch.delenv("SLACK_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)

    credentials = get_slack_credentials()

    assert credentials.client_id == ""
    assert credentials.client_secret == ""
    assert credentials.signing_secret == ""
