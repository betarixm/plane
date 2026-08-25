# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.db import models
from django.utils import timezone

from .base import BaseModel
from .identity import IdentitySource


class SlackUserTombstone(BaseModel):
    """An ordering barrier for Slack users that have no local identity row."""

    source = models.ForeignKey(
        IdentitySource,
        on_delete=models.CASCADE,
        related_name="slack_user_tombstones",
    )
    external_user_id = models.CharField(max_length=255)
    source_updated_at = models.BigIntegerField(default=0)
    source_generation = models.PositiveBigIntegerField(default=1)
    snapshot_terminal_at = models.DateTimeField(null=True, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "slack_user_tombstones"
        ordering = ("-observed_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_user_id"],
                name="slack_user_tombstone_unique_source_user",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True),
                name="slack_user_tombstone_cannot_soft_delete",
            ),
        ]


class SlackEventReceipt(BaseModel):
    """A durable idempotency record for Slack Events API deliveries."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"
        DEAD_LETTER = "dead_letter", "Dead letter"

    event_id = models.CharField(max_length=255, unique=True)
    source = models.ForeignKey(
        IdentitySource,
        on_delete=models.CASCADE,
        related_name="slack_event_receipts",
        null=True,
        blank=True,
    )
    team_id = models.CharField(max_length=64, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    source_generation = models.PositiveBigIntegerField(default=0)
    event_time = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RECEIVED,
        db_index=True,
    )
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error = models.TextField(blank=True, default="")
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "slack_event_receipts"
        ordering = ("-received_at",)
