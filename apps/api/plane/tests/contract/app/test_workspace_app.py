# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.urls import Resolver404, resolve, reverse
from rest_framework import status

from plane.db.models import Workspace


@pytest.mark.contract
class TestWorkspaceAPI:
    """Test workspace CRUD operations"""

    @pytest.mark.django_db
    def test_singleton_workspace_route_returns_workspace(
        self, session_client, workspace
    ):
        response = session_client.get("/api/workspace/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == workspace.id

    @pytest.mark.django_db
    def test_workspace_create_route_is_disabled(self, session_client, workspace):
        """The singleton workspace is created only during instance setup."""
        url = "/api/workspace/"

        response = session_client.post(
            url,
            {"name": "Second Workspace", "slug": "second-workspace"},
            format="json",
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Workspace.objects.count() == 1
        assert Workspace.objects.get() == workspace

    @pytest.mark.django_db
    def test_workspace_delete_route_is_disabled(self, session_client, workspace):
        response = session_client.delete(reverse("workspace"))

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert Workspace.objects.filter(pk=workspace.pk).exists()



@pytest.mark.parametrize(
    "path",
    [
        "/api/workspace/",
        "/api/workspace/projects/",
        "/api/workspace/webhooks/",
        "/api/v1/workspace/projects/",
        "/api/assets/v2/workspace/",
        "/api/users/me/workspace/dashboard/",
        "/api/public/workspace/project-boards/",
        "/auth/slack/",
        "/auth/slack/events/",
    ],
)
def test_singleton_api_routes_resolve_without_a_workspace_slug(path):
    match = resolve(path)

    assert "slug" not in match.kwargs


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path_template",
    [
        "/api/workspaces/{slug}/",
        "/api/workspaces/{slug}/projects/",
        "/api/workspaces/{slug}/webhooks/",
        "/api/v1/workspaces/{slug}/projects/",
        "/api/assets/v2/workspaces/{slug}/",
        "/api/users/me/workspaces/{slug}/dashboard/",
        "/api/public/workspaces/{slug}/project-boards/",
    ],
)
def test_legacy_plural_workspace_slug_routes_do_not_resolve(
    workspace, path_template
):
    with pytest.raises(Resolver404):
        resolve(path_template.format(slug=workspace.slug))
