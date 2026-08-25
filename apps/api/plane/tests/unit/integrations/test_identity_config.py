# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.core.exceptions import ImproperlyConfigured

from plane.integrations.identity import (
    configured_identity_provider,
    identity_provider_adapter,
)

pytestmark = pytest.mark.unit


def test_slack_is_the_default_and_only_implemented_provider(monkeypatch):
    monkeypatch.delenv("IDENTITY_PROVIDER", raising=False)

    assert configured_identity_provider() == "slack"
    assert identity_provider_adapter("slack") is not None


def test_discord_is_reserved_without_claiming_an_implemented_adapter(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER", " Discord ")

    assert configured_identity_provider() == "discord"
    assert identity_provider_adapter("discord") is None


def test_unknown_identity_provider_fails_closed(monkeypatch):
    monkeypatch.setenv("IDENTITY_PROVIDER", "unknown")

    with pytest.raises(ImproperlyConfigured, match="Unsupported IDENTITY_PROVIDER"):
        configured_identity_provider()
