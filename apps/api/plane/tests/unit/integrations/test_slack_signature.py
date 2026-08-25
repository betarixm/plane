# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import hmac

import pytest

from plane.integrations.slack import verify_slack_signature

pytestmark = pytest.mark.unit


def signature(secret, timestamp, body):
    base = b"v0:" + timestamp.encode() + b":" + body
    return "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()


def test_verifies_raw_body_signature():
    body = b'{"type":"event_callback"}'
    timestamp = "1000"
    assert verify_slack_signature(
        signing_secret="secret",
        timestamp=timestamp,
        body=body,
        signature=signature("secret", timestamp, body),
        now=1000,
    )


def test_rejects_tampering_and_stale_timestamp():
    body = b'{"type":"event_callback"}'
    timestamp = "1000"
    signed = signature("secret", timestamp, body)
    assert not verify_slack_signature(
        signing_secret="secret",
        timestamp=timestamp,
        body=body + b" ",
        signature=signed,
        now=1000,
    )
    assert not verify_slack_signature(
        signing_secret="secret",
        timestamp=timestamp,
        body=body,
        signature=signed,
        now=1301,
    )


def test_rejects_non_ascii_timestamp_without_raising():
    assert not verify_slack_signature(
        signing_secret="secret",
        timestamp="١٠٠٠",
        body=b"{}",
        signature="v0=invalid",
        now=1000,
    )
