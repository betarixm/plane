# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import models
from django.utils import timezone

from .base import BaseModel


class IdentitySource(BaseModel):
    """The external organization authoritative for the singleton workspace."""

    class Provider(models.TextChoices):
        SLACK = "slack", "Slack"
        DISCORD = "discord", "Discord"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        REVOKED = "revoked", "Revoked"
        ERROR = "error", "Error"

    workspace = models.OneToOneField(
        "db.Workspace",
        on_delete=models.CASCADE,
        related_name="identity_source",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    external_organization_id = models.CharField(max_length=255)
    external_organization_name = models.CharField(max_length=255)
    external_organization_domain = models.CharField(max_length=255, blank=True, default="")
    external_organization_icon_url = models.TextField(blank=True, default="")
    encrypted_access_token = models.TextField(blank=True, default="")
    service_account_id = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    generation = models.PositiveBigIntegerField(default=1)
    connected_at = models.DateTimeField(default=timezone.now)
    metadata_synced_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(blank=True, default="")
    sync_error_at = models.DateTimeField(null=True, blank=True)

    def set_access_token(self, token: str) -> None:
        """Encrypt a provider access token before persisting it."""

        from plane.license.utils.encryption import encrypt_data

        encrypted_token = encrypt_data(token)
        if not encrypted_token:
            raise ValueError("External identity source token encryption failed")
        self.encrypted_access_token = encrypted_token

    def get_access_token(self) -> str:
        """Return the decrypted provider token for server-side use only."""

        from plane.license.utils.encryption import decrypt_data

        token = decrypt_data(self.encrypted_access_token)
        if self.encrypted_access_token and not token:
            raise ValueError("External identity source token decryption failed")
        return token

    @property
    def access_token(self) -> str:
        return self.get_access_token()

    class Meta:
        db_table = "identity_sources"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_organization_id"],
                name="identity_source_unique_provider_organization",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True),
                name="identity_source_cannot_soft_delete",
            ),
        ]


class ExternalIdentity(BaseModel):
    """A local read projection of a human identity owned by an external source."""

    user = models.OneToOneField(
        "db.User",
        on_delete=models.CASCADE,
        related_name="external_identity",
    )
    source = models.ForeignKey(
        IdentitySource,
        on_delete=models.CASCADE,
        related_name="identities",
    )
    external_user_id = models.CharField(max_length=255)
    profile = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    workspace_role = models.PositiveSmallIntegerField(default=5)
    source_updated_at = models.BigIntegerField(default=0)
    source_generation = models.PositiveBigIntegerField(default=1)
    authoritative_synced_at = models.DateTimeField(null=True, blank=True)
    snapshot_absent_at = models.DateTimeField(null=True, blank=True)
    synced_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "external_identities"
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_user_id"],
                name="external_identity_unique_source_user",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True),
                name="external_identity_cannot_soft_delete",
            ),
        ]
