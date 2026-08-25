# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import time
from importlib import import_module

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.db import transaction
from django.utils.cache import patch_vary_headers
from django.utils.deprecation import MiddlewareMixin
from django.utils.http import http_date


class SessionMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        super().__init__(get_response)
        engine = import_module(settings.SESSION_ENGINE)
        self.SessionStore = engine.SessionStore

    def process_request(self, request):
        session_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
        request.session = self.SessionStore(session_key)

    @staticmethod
    def _save_identity_fenced_session(request) -> bool:
        """Revalidate an externally-owned identity around a session save."""

        from plane.utils.identity_access import (
            IDENTITY_SOURCE_GENERATION_SESSION_KEY,
            IDENTITY_SOURCE_ID_SESSION_KEY,
            lock_current_session_identity,
        )

        auth_user_id = request.session.get(SESSION_KEY)
        source_id = request.session.get(IDENTITY_SOURCE_ID_SESSION_KEY)
        expected_generation = request.session.get(
            IDENTITY_SOURCE_GENERATION_SESSION_KEY
        )
        callback_fence = getattr(request, "_identity_session_fence", None)
        if callback_fence is None:
            fence = {
                "source_id": source_id,
                "expected_generation": expected_generation,
                "user_id": auth_user_id,
                "session_key": request.session.session_key,
            }
        elif isinstance(callback_fence, dict):
            fence = callback_fence
        else:
            request.session.flush()
            return False

        if (
            not auth_user_id
            or not request.session.session_key
            or request.session.session_key != fence.get("session_key")
            or not source_id
            or str(source_id) != str(fence.get("source_id") or "")
            or str(auth_user_id) != str(fence.get("user_id") or "")
            or not isinstance(expected_generation, int)
            or expected_generation <= 0
            or expected_generation != fence.get("expected_generation")
        ):
            request.session.flush()
            return False

        with transaction.atomic(using="default"):
            identity = lock_current_session_identity(
                source_id=source_id,
                expected_generation=expected_generation,
                user_id=auth_user_id,
            )
            if identity is None:
                request.session.flush()
                return False
            try:
                request.session.save()
            except UpdateError:
                raise SessionInterrupted(
                    "The external login session was deleted before the response "
                    "could be persisted."
                )
        return True

    def process_response(self, request, response):
        """
        If request.session was modified, or if the configuration is to save the
        session every time, save the changes and set a session cookie or delete
        the session cookie if the session has been emptied.
        """
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response

        identity_fenced_session_saved = False
        callback_fence = getattr(request, "_identity_session_fence", None)
        should_save = bool(
            modified
            or settings.SESSION_SAVE_EVERY_REQUEST
            or callback_fence is not None
        )
        auth_user_id = request.session.get(SESSION_KEY) if not empty else None
        if callback_fence is not None and response.status_code >= 500 and not empty:
            request.session.flush()
        elif (
            response.status_code < 500
            and should_save
            and not empty
            and (auth_user_id or callback_fence is not None)
        ):
            identity_fenced_session_saved = self._save_identity_fenced_session(request)

        if callback_fence is not None or identity_fenced_session_saved or should_save:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        # First check if we need to delete this cookie.
        # The session should be deleted only if the session is entirely empty.
        cookie_name = settings.SESSION_COOKIE_NAME

        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            patch_vary_headers(response, ("Cookie",))
        else:
            if accessed:
                patch_vary_headers(response, ("Cookie",))
            if (
                modified
                or settings.SESSION_SAVE_EVERY_REQUEST
                or identity_fenced_session_saved
            ) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()

                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)

                # Save the session data and refresh the client cookie.
                if response.status_code < 500:
                    try:
                        if not identity_fenced_session_saved:
                            request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
        return response
