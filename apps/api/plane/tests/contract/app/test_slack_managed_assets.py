# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework import status

from plane.db.models import (
    DeployBoard,
    FileAsset,
    Issue,
    Project,
    ProjectMember,
)
from plane.utils.external_assets import (
    EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES,
    EXTERNALLY_MANAGED_ASSET_ERROR,
)


pytestmark = [pytest.mark.contract, pytest.mark.django_db]


@pytest.fixture
def project(workspace, create_user):
    project = Project.objects.create(
        name="Slack asset fence",
        identifier=f"SA{uuid4().hex[:4].upper()}",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=create_user,
        role=20,
        is_active=True,
    )
    return project


@pytest.fixture
def issue(workspace, project, create_user):
    return Issue.objects.create(
        name="Slack asset fence issue",
        workspace=workspace,
        project=project,
        created_by=create_user,
    )


@pytest.fixture
def deploy_board(workspace, project):
    return DeployBoard.objects.create(
        workspace=workspace,
        project=project,
        entity_identifier=project.id,
        entity_name="project",
    )


@pytest.fixture
def asset_factory(workspace, create_user):
    def create(entity_type, *, project=None, issue=None, is_uploaded=False):
        asset_name = f"{uuid4().hex}.png"
        asset = FileAsset(
            attributes={"name": asset_name, "type": "image/png", "size": 1},
            asset=f"{workspace.id}/{asset_name}",
            size=1,
            workspace=workspace,
            project=project,
            issue=issue,
            user=(
                create_user
                if entity_type
                in {
                    FileAsset.EntityTypeContext.USER_AVATAR,
                    FileAsset.EntityTypeContext.USER_COVER,
                }
                else None
            ),
            created_by=create_user,
            entity_type=entity_type,
            is_uploaded=is_uploaded,
            storage_metadata={"size": 1},
        )
        asset.save(created_by_id=create_user.id)
        return asset

    return create


def assert_slack_managed(response):
    assert response.status_code == status.HTTP_403_FORBIDDEN
    assert response.json()["error"] == EXTERNALLY_MANAGED_ASSET_ERROR


@pytest.mark.parametrize("entity_type", EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES)
def test_legacy_asset_create_delete_and_restore_are_slack_fenced(
    session_client,
    external_identity_source,
    workspace,
    asset_factory,
    entity_type,
):
    managed_count = FileAsset.all_objects.filter(entity_type=entity_type).count()
    create_response = session_client.post(
        "/api/workspace/file-assets/",
        {"entity_type": entity_type},
        format="json",
    )
    assert_slack_managed(create_response)
    assert (
        FileAsset.all_objects.filter(entity_type=entity_type).count()
        == managed_count
    )

    asset = asset_factory(entity_type)
    asset_key = asset.asset.name.removeprefix(f"{workspace.id}/")
    detail_url = f"/api/workspace/file-assets/{asset_key}/"
    restore_url = (
        f"/api/workspace/file-assets/{asset_key}/restore/"
    )

    assert_slack_managed(session_client.delete(detail_url))
    asset.is_deleted = True
    asset.save(update_fields=["is_deleted"])
    assert_slack_managed(session_client.post(restore_url, {}, format="json"))

    asset.refresh_from_db()
    assert asset.is_deleted is True


@pytest.mark.parametrize("entity_type", EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES)
def test_workspace_asset_mutations_are_slack_fenced(
    session_client,
    external_identity_source,
    workspace,
    asset_factory,
    entity_type,
):
    managed_count = FileAsset.all_objects.filter(entity_type=entity_type).count()
    assert_slack_managed(
        session_client.post(
            "/api/assets/v2/workspace/",
            {"entity_type": entity_type},
            format="json",
        )
    )
    assert (
        FileAsset.all_objects.filter(entity_type=entity_type).count()
        == managed_count
    )

    asset = asset_factory(entity_type)
    detail_url = f"/api/assets/v2/workspace/{asset.id}/"
    assert_slack_managed(session_client.patch(detail_url, {}, format="json"))
    assert_slack_managed(session_client.delete(detail_url))

    asset.is_deleted = True
    asset.deleted_at = timezone.now()
    asset.save(update_fields=["is_deleted", "deleted_at"])
    restore_url = (
        f"/api/assets/v2/workspace/restore/{asset.id}/"
    )
    assert_slack_managed(session_client.post(restore_url, {}, format="json"))

    persisted_asset = FileAsset.all_objects.get(pk=asset.pk)
    assert persisted_asset.is_deleted is True
    assert persisted_asset.is_uploaded is False


@pytest.mark.parametrize("entity_type", EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES)
def test_project_and_duplicate_asset_mutations_are_slack_fenced(
    session_client,
    create_user,
    external_identity_source,
    workspace,
    project,
    issue,
    asset_factory,
    entity_type,
):
    project_url = (
        f"/api/assets/v2/workspace/projects/{project.id}/"
    )
    managed_count = FileAsset.all_objects.filter(entity_type=entity_type).count()
    assert_slack_managed(
        session_client.post(
            project_url,
            {"entity_type": entity_type},
            format="json",
        )
    )
    assert (
        FileAsset.all_objects.filter(entity_type=entity_type).count()
        == managed_count
    )

    asset = asset_factory(entity_type, project=project)
    detail_url = f"{project_url}{asset.id}/"
    assert_slack_managed(session_client.patch(detail_url, {}, format="json"))
    assert_slack_managed(session_client.delete(detail_url))

    bulk_url = f"{project_url}{issue.id}/bulk/"
    assert_slack_managed(
        session_client.post(
            bulk_url,
            {"asset_ids": [str(asset.id)]},
            format="json",
        )
    )

    source = asset_factory(
        FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        project=project,
        issue=issue,
        is_uploaded=True,
    )
    duplicate_url = (
        "/api/assets/v2/workspace/duplicate-assets/"
        f"{source.id}/"
    )
    managed_count = FileAsset.all_objects.filter(entity_type=entity_type).count()
    assert_slack_managed(
        session_client.post(
            duplicate_url,
            {
                "entity_type": entity_type,
                "entity_id": str(create_user.id),
                "project_id": str(project.id),
            },
            format="json",
        )
    )
    assert (
        FileAsset.all_objects.filter(entity_type=entity_type).count()
        == managed_count
    )

    asset.refresh_from_db()
    assert asset.is_deleted is False
    assert asset.is_uploaded is False


@pytest.mark.parametrize("entity_type", EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES)
def test_space_asset_mutations_are_slack_fenced(
    session_client,
    external_identity_source,
    workspace,
    project,
    issue,
    deploy_board,
    asset_factory,
    entity_type,
):
    collection_url = f"/api/public/assets/v2/anchor/{deploy_board.anchor}/"
    managed_count = FileAsset.all_objects.filter(entity_type=entity_type).count()
    assert_slack_managed(
        session_client.post(
            collection_url,
            {"entity_type": entity_type},
            format="json",
        )
    )
    assert (
        FileAsset.all_objects.filter(entity_type=entity_type).count()
        == managed_count
    )

    asset = asset_factory(entity_type, project=project)
    detail_url = f"{collection_url}{asset.id}/"
    assert_slack_managed(session_client.patch(detail_url, {}, format="json"))
    assert_slack_managed(session_client.delete(detail_url))

    bulk_url = f"{collection_url}{issue.id}/bulk/"
    assert_slack_managed(
        session_client.post(
            bulk_url,
            {"asset_ids": [str(asset.id)]},
            format="json",
        )
    )

    asset.is_deleted = True
    asset.deleted_at = timezone.now()
    asset.save(update_fields=["is_deleted", "deleted_at"])
    restore_url = f"{collection_url}restore/{asset.id}/"
    assert_slack_managed(session_client.post(restore_url, {}, format="json"))

    persisted_asset = FileAsset.all_objects.get(pk=asset.pk)
    assert persisted_asset.is_deleted is True
    assert persisted_asset.is_uploaded is False


@pytest.mark.parametrize("entity_type", EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES)
def test_public_api_generic_patch_is_slack_fenced(
    api_key_client,
    workspace,
    asset_factory,
    entity_type,
):
    asset = asset_factory(entity_type)
    response = api_key_client.patch(
        f"/api/v1/workspace/assets/{asset.id}/",
        {"is_uploaded": True},
        format="json",
    )

    assert_slack_managed(response)
    asset.refresh_from_db()
    assert asset.is_uploaded is False


@pytest.mark.parametrize("entity_type", EXTERNALLY_MANAGED_ASSET_ENTITY_TYPES)
def test_issue_attachment_routes_cannot_mutate_managed_assets(
    session_client,
    api_key_client,
    workspace,
    project,
    issue,
    asset_factory,
    entity_type,
):
    asset = asset_factory(entity_type, project=project, issue=issue)
    app_legacy_url = (
        f"/api/workspace/projects/{project.id}/issues/"
        f"{issue.id}/issue-attachments/{asset.id}/"
    )
    app_v2_url = (
        f"/api/assets/v2/workspace/projects/{project.id}/"
        f"issues/{issue.id}/attachments/{asset.id}/"
    )
    api_url = (
        f"/api/v1/workspace/projects/{project.id}/work-items/"
        f"{issue.id}/attachments/{asset.id}/"
    )

    assert session_client.delete(app_legacy_url).status_code == status.HTTP_404_NOT_FOUND
    assert (
        session_client.patch(app_v2_url, {}, format="json").status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert session_client.delete(app_v2_url).status_code == status.HTTP_404_NOT_FOUND
    assert (
        api_key_client.patch(api_url, {}, format="json").status_code
        == status.HTTP_404_NOT_FOUND
    )
    assert api_key_client.delete(api_url).status_code == status.HTTP_404_NOT_FOUND

    asset.refresh_from_db()
    assert asset.is_deleted is False
    assert asset.is_uploaded is False


def test_file_asset_urls_use_the_slugless_singleton_workspace_route(
    workspace, project, issue, asset_factory
):
    attachment = asset_factory(
        FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
        project=project,
        issue=issue,
    )
    description = asset_factory(
        FileAsset.EntityTypeContext.ISSUE_DESCRIPTION,
        project=project,
    )

    assert attachment.asset_url == (
        f"/api/assets/v2/workspace/projects/{project.id}/issues/{issue.id}/"
        f"attachments/{attachment.id}/"
    )
    assert description.asset_url == (
        f"/api/assets/v2/workspace/projects/{project.id}/{description.id}/"
    )
    assert workspace.slug not in attachment.asset_url
    assert workspace.slug not in description.asset_url
