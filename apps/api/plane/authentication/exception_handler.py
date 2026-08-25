# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from rest_framework.exceptions import NotAuthenticated, Throttled
from rest_framework.views import exception_handler

from plane.authentication.errors import identity_error_payload


def identity_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    if isinstance(exc, NotAuthenticated):
        response.status_code = 401
    elif isinstance(exc, Throttled):
        response.data = identity_error_payload("RATE_LIMIT_EXCEEDED")
        response.status_code = 429
    return response
