# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Contract tests for the singleton public REST API asset endpoint."""

import pytest
from rest_framework import status

from plane.db.models import FileAsset


@pytest.mark.contract
class TestGenericAssetSingletonWorkspace:

    def detail_url(self, asset_id):
        return f"/api/v1/workspace/assets/{asset_id}/"

    @pytest.mark.django_db
    def test_member_can_patch_own_workspace_asset(self, api_key_client, workspace, create_user):
        """Positive control: an active member of the workspace can still update
        their own asset, so the fix does not over-block legitimate callers."""
        asset = FileAsset.objects.create(
            attributes={"name": "mine.pdf", "type": "application/pdf", "size": 10},
            asset=f"{workspace.id}/mine.pdf",
            size=10,
            workspace=workspace,
            created_by=create_user,
            entity_type=FileAsset.EntityTypeContext.ISSUE_ATTACHMENT,
            is_uploaded=False,
            storage_metadata={"size": 10},
        )
        url = self.detail_url(asset.id)

        response = api_key_client.patch(url, {"is_uploaded": True}, format="json")

        assert response.status_code == status.HTTP_204_NO_CONTENT, f"Got {response.status_code}: {response.data!r}"
        asset.refresh_from_db()
        assert asset.is_uploaded is True
