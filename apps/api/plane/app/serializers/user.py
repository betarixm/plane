# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module import
from plane.db.models import Profile, User, Workspace

from .base import BaseSerializer


class UserMeSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "avatar",
            "cover_image",
            "avatar_url",
            "cover_image_url",
            "date_joined",
            "display_name",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "user_timezone",
            "username",
        ]
        read_only_fields = fields


class UserMeSettingsSerializer(BaseSerializer):
    workspace = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "workspace"]
        read_only_fields = fields

    def get_workspace(self, obj):
        workspace = (
            Workspace.objects.filter(
                workspace_member__member_id=obj.id,
                workspace_member__is_active=True,
            )
            .select_related("logo_asset")
            .first()
        )
        return {
            "id": workspace.id if workspace is not None else None,
            "slug": workspace.slug if workspace is not None else None,
            "name": workspace.name if workspace is not None else None,
            "logo": workspace.logo_url if workspace is not None else None,
        }


class UserLiteSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "avatar",
            "avatar_url",
            "display_name",
        ]
        read_only_fields = fields


class UserAdminLiteSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "avatar",
            "avatar_url",
            "display_name",
            "email",
        ]
        read_only_fields = fields


class ProfileSerializer(BaseSerializer):
    class Meta:
        model = Profile
        fields = "__all__"
        read_only_fields = ["user"]
