# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
import requests
from django.urls import reverse


@pytest.mark.smoke
class TestAuthSmoke:
    """Smoke tests for the Slack-only interactive authentication surface."""

    @pytest.mark.django_db
    def test_slack_login_endpoint_is_available(self, plane_server):
        response = requests.get(
            f"{plane_server.url}{reverse('slack-login')}",
            allow_redirects=False,
        )

        # An unconfigured identity source redirects with a typed setup error. The
        # endpoint must exist and must not make a Slack network call yet.
        assert response.status_code in (302, 303)
        location = response.headers["Location"]
        assert location.startswith("https://slack.com/openid/connect/authorize") or (
            "IDENTITY_SOURCE_NOT_CONFIGURED" in location
        )


@pytest.mark.smoke
class TestHealthCheckSmoke:
    def test_healthcheck_endpoint(self, plane_server):
        response = requests.get(f"{plane_server.url}/")

        assert response.status_code == 200
