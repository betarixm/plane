# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from dataclasses import dataclass

from plane.license.utils.instance_value import get_configuration_value


@dataclass(frozen=True)
class SlackCredentials:
    client_id: str
    client_secret: str
    signing_secret: str


def get_slack_credentials() -> SlackCredentials:
    """Load Slack application credentials from the process environment."""

    configured_client_id, configured_client_secret, configured_signing_secret = get_configuration_value(
        [
            {"key": "SLACK_CLIENT_ID", "default": ""},
            {"key": "SLACK_CLIENT_SECRET", "default": ""},
            {"key": "SLACK_SIGNING_SECRET", "default": ""},
        ]
    )

    return SlackCredentials(
        client_id=str(configured_client_id or "").strip(),
        client_secret=str(configured_client_secret or "").strip(),
        signing_secret=str(configured_signing_secret or "").strip(),
    )
