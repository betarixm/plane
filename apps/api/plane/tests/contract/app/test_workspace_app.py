# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.urls import reverse
from rest_framework import status

from plane.db.models import Workspace


@pytest.mark.contract
class TestWorkspaceAPI:
    """Test workspace CRUD operations"""

    @pytest.mark.django_db
    def test_workspace_collection_route_is_removed(self, session_client):
        response = session_client.get("/api/workspaces/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.django_db
    def test_workspace_create_route_is_disabled(self, session_client):
        """The singleton workspace is created only during instance setup."""
        url = "/api/workspaces/"

        response = session_client.post(
            url,
            {"name": "Second Workspace", "slug": "second-workspace"},
            format="json",
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert Workspace.objects.count() == 0

    @pytest.mark.django_db
    def test_workspace_delete_route_is_disabled(self, session_client, workspace):
        response = session_client.delete(reverse("workspace", kwargs={"slug": workspace.slug}))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Workspace.objects.filter(pk=workspace.pk).exists()
