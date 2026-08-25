# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status

from plane.license.models import Instance
from plane.utils.identity_access import (
    IDENTITY_SOURCE_GENERATION_SESSION_KEY,
    IDENTITY_SOURCE_ID_SESSION_KEY,
)


@pytest.fixture
def unconfigured_instance(db):
    return Instance.objects.create(
        instance_name="Plane Community Edition",
        instance_id=uuid4().hex,
        current_version="test",
        last_checked_at=timezone.now(),
    )


@pytest.mark.contract
@pytest.mark.django_db
def test_identity_owned_instance_settings_are_read_only(
    client,
    unconfigured_instance,
    create_user,
    external_identity_source,
):
    client.force_login(create_user)
    session = client.session
    session[IDENTITY_SOURCE_ID_SESSION_KEY] = str(
        external_identity_source.source_id
    )
    session[IDENTITY_SOURCE_GENERATION_SESSION_KEY] = (
        external_identity_source.source_generation
    )
    session.save()

    response = client.patch(
        "/api/instances/",
        {
            "instance_name": "Locally overridden name",
            "is_telemetry_enabled": False,
        },
        content_type="application/json",
    )

    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    unconfigured_instance.refresh_from_db()
    assert unconfigured_instance.instance_name == "Plane Community Edition"
    assert unconfigured_instance.is_telemetry_enabled is True
