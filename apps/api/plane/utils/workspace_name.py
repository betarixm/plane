# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.core.exceptions import ValidationError

from plane.utils.content_validator import has_alphanumeric
from plane.utils.url import contains_url


def validate_workspace_name(value):
    """Normalize and validate the singleton workspace name."""

    normalized = value.strip() if isinstance(value, str) else ""
    if not normalized:
        raise ValidationError("Workspace name is required")
    if len(normalized) > 80:
        raise ValidationError("Workspace name cannot exceed 80 characters")
    if contains_url(normalized):
        raise ValidationError("Name must not contain URLs")
    if not has_alphanumeric(normalized):
        raise ValidationError("Name must contain at least one letter or number")
    return normalized
