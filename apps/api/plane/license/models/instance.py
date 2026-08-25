# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
from enum import Enum

# Django imports
from django.core.exceptions import ValidationError
from django.db import models

# Module imports
from plane.db.models import BaseModel


class InstanceEdition(Enum):
    PLANE_COMMUNITY = "PLANE_COMMUNITY"


class SingletonInstanceQuerySet(models.QuerySet):
    def delete(self, *args, **kwargs):
        raise ValidationError("The singleton instance cannot be deleted")


class ActiveInstanceManager(models.Manager.from_queryset(SingletonInstanceQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class AllInstanceManager(models.Manager.from_queryset(SingletonInstanceQuerySet)):
    pass


class Instance(BaseModel):
    # A deployment has one immutable metadata row. The constant key turns
    # that invariant into a database-enforced uniqueness constraint, including
    # concurrent first-boot registration attempts from multiple API replicas.
    singleton_key = models.BooleanField(default=True, editable=False)
    objects = ActiveInstanceManager()
    all_objects = AllInstanceManager()
    # General information
    instance_name = models.CharField(max_length=255)
    instance_id = models.CharField(max_length=255, unique=True)
    current_version = models.CharField(max_length=255)
    latest_version = models.CharField(max_length=255, null=True, blank=True)
    edition = models.CharField(max_length=255, default=InstanceEdition.PLANE_COMMUNITY.value)
    # Instance specifics
    last_checked_at = models.DateTimeField()
    # telemetry and support
    is_telemetry_enabled = models.BooleanField(default=True)
    # is setup done
    is_setup_done = models.BooleanField(default=False)

    def delete(self, *args, **kwargs):
        raise ValidationError("The singleton instance cannot be deleted")

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(singleton_key=True),
                name="instance_singleton_key_must_be_true",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True),
                name="instance_cannot_be_soft_deleted",
            ),
            models.UniqueConstraint(
                fields=["singleton_key"],
                name="instance_only_one",
            ),
        ]
        verbose_name = "Instance"
        verbose_name_plural = "Instances"
        db_table = "instances"
        ordering = ("-created_at",)
