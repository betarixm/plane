# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from django.utils import timezone

from plane.db.models import Page, Project, ProjectMember, ProjectPage, User

pytestmark = pytest.mark.contract


@pytest.fixture
def live_page(workspace, create_user):
    project = Project.objects.create(
        name="Live access project",
        identifier="LIVE",
        workspace=workspace,
    )
    project_member = ProjectMember.objects.create(
        project=project,
        workspace=workspace,
        member=create_user,
        role=15,
    )
    page = Page.objects.create(
        name="Live page",
        workspace=workspace,
        owned_by=create_user,
    )
    project_page = ProjectPage.objects.create(
        project=project,
        workspace=workspace,
        page=page,
    )
    return project, project_member, page, project_page


def live_access_url(workspace, project, page):
    return f"/api/workspaces/{workspace.slug}/projects/{project.id}/pages/{page.id}/live-edit-access/"


@pytest.mark.django_db
@pytest.mark.parametrize("role", [15, 20])
def test_live_edit_access_allows_active_project_editors(
    session_client,
    workspace,
    live_page,
    role,
):
    project, project_member, page, _ = live_page
    project_member.role = role
    project_member.save(update_fields=["role", "updated_at"])

    response = session_client.get(live_access_url(workspace, project, page))

    assert response.status_code == 204
    assert "private" in response["Cache-Control"]
    assert "no-store" in response["Cache-Control"]


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("role", "is_active"),
    [
        (5, True),
        (15, False),
    ],
)
def test_live_edit_access_denies_guest_or_inactive_project_member(
    session_client,
    workspace,
    live_page,
    role,
    is_active,
):
    project, project_member, page, _ = live_page
    project_member.role = role
    project_member.is_active = is_active
    project_member.save(update_fields=["role", "is_active", "updated_at"])

    response = session_client.get(live_access_url(workspace, project, page))

    assert response.status_code == 403


@pytest.mark.django_db
def test_live_edit_access_enforces_private_page_ownership(session_client, workspace, live_page):
    project, _, page, _ = live_page
    other_user = User.objects.create(email="other-owner@example.com", username="other-owner")
    page.access = Page.PRIVATE_ACCESS
    page.owned_by = other_user
    page.save(update_fields=["access", "owned_by", "updated_at"])

    response = session_client.get(live_access_url(workspace, project, page))

    assert response.status_code == 403


@pytest.mark.django_db
def test_live_edit_access_allows_private_page_owner(session_client, workspace, live_page):
    project, _, page, _ = live_page
    page.access = Page.PRIVATE_ACCESS
    page.save(update_fields=["access", "updated_at"])

    response = session_client.get(live_access_url(workspace, project, page))

    assert response.status_code == 204


@pytest.mark.django_db
@pytest.mark.parametrize("page_state", ["locked", "archived", "unlinked"])
def test_live_edit_access_denies_non_editable_page_state(
    session_client,
    workspace,
    live_page,
    page_state,
):
    project, _, page, project_page = live_page
    if page_state == "locked":
        page.is_locked = True
        page.save(update_fields=["is_locked", "updated_at"])
    elif page_state == "archived":
        page.archived_at = timezone.localdate()
        page.save(update_fields=["archived_at", "updated_at"])
    else:
        ProjectPage.objects.filter(pk=project_page.pk).update(deleted_at=timezone.now())

    response = session_client.get(live_access_url(workspace, project, page))

    assert response.status_code == 403
