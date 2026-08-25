# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from uuid import UUID

from django.contrib.auth import SESSION_KEY
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import AuthenticationFailed

from plane.utils.identity_access import (
    IDENTITY_SOURCE_GENERATION_SESSION_KEY,
    IDENTITY_SOURCE_ID_SESSION_KEY,
    has_session_bound_external_identity,
)


class BaseSessionAuthentication(SessionAuthentication):
    """Accept sessions only for their exact live identity-source generation."""

    @staticmethod
    def _reject_session(request):
        request.session.flush()
        raise AuthenticationFailed("An active external identity is required")

    def authenticate(self, request):
        has_session_user = SESSION_KEY in request.session
        session_user_uuid = None
        source_uuid = None
        source_generation = None
        if has_session_user:
            session_user_id = request.session.get(SESSION_KEY)
            source_id = request.session.get(IDENTITY_SOURCE_ID_SESSION_KEY)
            source_generation = request.session.get(
                IDENTITY_SOURCE_GENERATION_SESSION_KEY
            )
            try:
                session_user_uuid = UUID(session_user_id)
                source_uuid = UUID(source_id)
            except (AttributeError, TypeError, ValueError):
                self._reject_session(request)
            if (
                not isinstance(source_generation, int)
                or isinstance(source_generation, bool)
                or source_generation <= 0
            ):
                self._reject_session(request)

        authenticated = super().authenticate(request)
        if authenticated is None:
            if has_session_user:
                self._reject_session(request)
            return None

        user, auth = authenticated
        if (
            not has_session_user
            or session_user_uuid != user.pk
            or not has_session_bound_external_identity(
                user,
                source_id=source_uuid,
                source_generation=source_generation,
            )
        ):
            self._reject_session(request)
        return user, auth

    # Disable csrf for the rest apis
    def enforce_csrf(self, request):
        return
