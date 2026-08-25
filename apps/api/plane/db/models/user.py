# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Python imports
import uuid

import pytz

# Django imports
from django.db import models

# Module imports
from plane.db.models import FileAsset
from ..mixins import TimeAuditModel


# Kept for compatibility with historical migrations that serialize these
# callables. The corresponding fields are no longer part of the current model.
def get_default_onboarding():
    return {
        "profile_complete": False,
        "workspace_join": False,
    }


def get_mobile_default_onboarding():
    return {
        "profile_complete": False,
        "workspace_join": False,
    }


def get_default_product_tour():
    return {
        "work_items": False,
        "cycles": False,
        "modules": False,
        "intake": False,
        "pages": False,
    }


class User(models.Model):
    """Local projection of a person owned by the active identity source."""

    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True)
    username = models.CharField(max_length=128, unique=True)
    email = models.CharField(max_length=255, null=True, blank=True, unique=True)

    # identity
    display_name = models.CharField(max_length=255, default="")
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    # avatar
    avatar = models.TextField(blank=True)
    avatar_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_avatar",
    )
    # cover image
    cover_image = models.URLField(blank=True, null=True, max_length=800)
    cover_image_asset = models.ForeignKey(
        FileAsset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user_cover_image",
    )

    # tracking metrics
    date_joined = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Last Modified At")
    is_active = models.BooleanField(default=True)

    # timezone
    USER_TIMEZONE_CHOICES = tuple(zip(pytz.common_timezones, pytz.common_timezones))
    user_timezone = models.CharField(max_length=255, default="UTC", choices=USER_TIMEZONE_CHOICES)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        db_table = "users"
        ordering = ("-created_at",)

    def __str__(self):
        return self.display_name or self.username

    def get_username(self):
        return self.username

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    @property
    def avatar_url(self):
        # Return the logo asset url if it exists
        if self.avatar_asset:
            return self.avatar_asset.asset_url

        # Return the logo url if it exists
        if self.avatar:
            return self.avatar
        return None

    @property
    def cover_image_url(self):
        # Return the logo asset url if it exists
        if self.cover_image_asset:
            return self.cover_image_asset.asset_url

        # Return the logo url if it exists
        if self.cover_image:
            return self.cover_image
        return None

    @property
    def full_name(self):
        """Return user's full name (first + last)."""
        return f"{self.first_name} {self.last_name}".strip()

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.lower().strip()

        if not self.display_name:
            self.display_name = self.email.split("@", maxsplit=1)[0] if self.email else self.username

        super().save(*args, **kwargs)


class Profile(TimeAuditModel):
    SUNDAY = 0
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6

    START_OF_THE_WEEK_CHOICES = (
        (SUNDAY, "Sunday"),
        (MONDAY, "Monday"),
        (TUESDAY, "Tuesday"),
        (WEDNESDAY, "Wednesday"),
        (THURSDAY, "Thursday"),
        (FRIDAY, "Friday"),
        (SATURDAY, "Saturday"),
    )

    id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True, primary_key=True)
    # User
    user = models.OneToOneField("db.User", on_delete=models.CASCADE, related_name="profile")
    # General
    theme = models.JSONField(default=dict)
    is_tour_completed = models.BooleanField(default=False)
    # language
    language = models.CharField(max_length=255, default="en")
    start_of_the_week = models.PositiveSmallIntegerField(choices=START_OF_THE_WEEK_CHOICES, default=SUNDAY)

    class Meta:
        verbose_name = "Profile"
        verbose_name_plural = "Profiles"
        db_table = "profiles"
        ordering = ("-created_at",)
