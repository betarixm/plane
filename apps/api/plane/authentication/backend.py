# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from django.contrib.auth.backends import BaseBackend

from plane.db.models import User


class ExternalIdentitySessionBackend(BaseBackend):
    """Restore externally-authenticated users from a local Django session."""

    def authenticate(self, request, **credentials):
        return None

    def get_user(self, user_id):
        user = User.objects.filter(pk=user_id, is_active=True).first()
        return user
