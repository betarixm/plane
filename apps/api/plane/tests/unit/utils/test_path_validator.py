# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from urllib.parse import parse_qs, urlparse

import pytest
from django.test import override_settings

from plane.utils.path_validator import get_safe_redirect_url


@pytest.mark.unit
@override_settings(
    WEB_URL="https://app.example.com",
    APP_BASE_URL="https://app.example.com",
    SPACE_BASE_URL="https://space.example.com",
)
def test_safe_redirect_url_preserves_next_path_query_parameters():
    next_path = "/projects/?view=assigned&group_by=state#active"

    redirect_url = get_safe_redirect_url("https://app.example.com", next_path)
    query = parse_qs(urlparse(redirect_url).query)

    assert query == {"next_path": [next_path]}
