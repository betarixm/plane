# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

IDENTITY_ERROR_CODES = {
    "IDENTITY_SOURCE_NOT_CONFIGURED": 5150,
    "IDENTITY_SOURCE_OAUTH_STATE_INVALID": 5151,
    "IDENTITY_SOURCE_OAUTH_ERROR": 5152,
    "IDENTITY_SOURCE_ADMIN_REQUIRED": 5153,
    "IDENTITY_SOURCE_ORGANIZATION_MISMATCH": 5154,
    "EXTERNAL_IDENTITY_NOT_FOUND": 5155,
    "EXTERNAL_IDENTITY_INACTIVE": 5156,
    "IDENTITY_SOURCE_SETUP_NOT_ALLOWED": 5157,
    "EXTERNAL_IDENTITY_INVALID": 5158,
    "RATE_LIMIT_EXCEEDED": 5900,
}


def identity_error_payload(error_name: str) -> dict[str, int | str]:
    return {
        "error_code": IDENTITY_ERROR_CODES[error_name],
        "error_message": error_name,
    }
