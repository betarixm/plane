# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import hmac
import time


def verify_slack_signature(
    *,
    signing_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
    now: int | None = None,
    tolerance_seconds: int = 300,
) -> bool:
    """Verify a Slack v0 request signature and reject replayed requests."""

    if not signing_secret or not timestamp or not signature or not signature.startswith("v0="):
        return False

    if not timestamp.isascii() or not timestamp.isdigit():
        return False

    try:
        request_timestamp = int(timestamp)
    except (TypeError, ValueError):
        return False

    current_timestamp = int(time.time()) if now is None else now
    if abs(current_timestamp - request_timestamp) > tolerance_seconds:
        return False

    base_string = b"v0:" + timestamp.encode("ascii") + b":" + body
    expected = "v0=" + hmac.new(signing_secret.encode(), base_string, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
