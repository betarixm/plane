# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import os
from dataclasses import dataclass
from typing import Callable

from django.core.exceptions import ImproperlyConfigured


DEFAULT_IDENTITY_PROVIDER = "slack"
KNOWN_IDENTITY_PROVIDERS = frozenset({"slack", "discord"})


@dataclass(frozen=True, slots=True)
class IdentityProviderAdapter:
    auth_url: str
    install_url: str
    credentials_configured: Callable[[], bool]


def _slack_credentials_configured() -> bool:
    from plane.integrations.slack import get_slack_credentials

    credentials = get_slack_credentials()
    return bool(credentials.client_id and credentials.client_secret and credentials.signing_secret)


_PROVIDER_ADAPTERS = {
    "slack": IdentityProviderAdapter(
        auth_url="/auth/slack/",
        install_url="/auth/slack/install/",
        credentials_configured=_slack_credentials_configured,
    ),
}


def configured_identity_provider() -> str:
    """Return the provider selected for this deployment."""

    provider = os.environ.get("IDENTITY_PROVIDER", DEFAULT_IDENTITY_PROVIDER).strip().lower()
    if provider not in KNOWN_IDENTITY_PROVIDERS:
        raise ImproperlyConfigured(f"Unsupported IDENTITY_PROVIDER: {provider}")
    return provider


def identity_provider_adapter(provider: str) -> IdentityProviderAdapter | None:
    """Return the installed adapter for a provider, if implemented."""

    return _PROVIDER_ADAPTERS.get(provider)
