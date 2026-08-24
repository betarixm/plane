# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.utils import timezone

from plane.db.models import Workspace, WorkspaceMember


@pytest.mark.unit
class TestWorkspaceModel:
    """Test the Workspace model"""

    @pytest.mark.django_db
    def test_workspace_creation(self, create_user):
        """Test creating a workspace"""
        # Create a workspace
        workspace = Workspace.objects.create(
            name="Test Workspace", slug="test-workspace", id=uuid4(), owner=create_user
        )

        # Verify it was created
        assert workspace.id is not None
        assert workspace.name == "Test Workspace"
        assert workspace.slug == "test-workspace"
        assert workspace.owner == create_user

    @pytest.mark.django_db
    def test_workspace_member_creation(self, create_user):
        """Test creating a workspace member"""
        # Create a workspace
        workspace = Workspace.objects.create(
            name="Test Workspace", slug="test-workspace", id=uuid4(), owner=create_user
        )

        # Create a workspace member
        workspace_member = WorkspaceMember.objects.create(
            workspace=workspace,
            member=create_user,
            role=20,  # Admin role
        )

        # Verify it was created
        assert workspace_member.id is not None
        assert workspace_member.workspace == workspace
        assert workspace_member.member == create_user
        assert workspace_member.role == 20

    @pytest.mark.django_db
    def test_second_workspace_is_rejected_by_database(self, create_user):
        workspace = Workspace.objects.create(
            name="Only Workspace",
            slug="only-workspace",
            owner=create_user,
        )

        with pytest.raises(IntegrityError), transaction.atomic():
            Workspace.objects.create(
                name="Second Workspace",
                slug="second-workspace",
                owner=create_user,
            )

        assert Workspace.all_objects.get() == workspace

    @pytest.mark.django_db
    def test_singleton_workspace_cannot_be_deleted(self, create_user):
        workspace = Workspace.objects.create(
            name="Only Workspace",
            slug="only-workspace",
            owner=create_user,
        )

        with pytest.raises(ValidationError, match="cannot be deleted"):
            workspace.delete()
        with pytest.raises(ValidationError, match="cannot be deleted"):
            Workspace.objects.filter(pk=workspace.pk).delete()
        with pytest.raises(ValidationError, match="cannot be deleted"):
            Workspace.all_objects.filter(pk=workspace.pk).delete()
        with pytest.raises(IntegrityError), transaction.atomic():
            Workspace.all_objects.filter(pk=workspace.pk).update(deleted_at=timezone.now())

        assert Workspace.objects.get() == workspace

    @pytest.mark.django_db
    def test_singleton_workspace_protects_its_owner(self, create_user):
        workspace = Workspace.objects.create(
            name="Only Workspace",
            slug="only-workspace",
            owner=create_user,
        )

        with pytest.raises(ProtectedError):
            create_user.delete()

        assert Workspace.objects.get() == workspace
