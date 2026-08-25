# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import hmac
import json
import time
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.utils import timezone

from plane.bgtasks.slack_sync import (
    SLACK_EVENT_MAX_ATTEMPTS,
    process_slack_event,
    requeue_stale_slack_event_receipts,
)
from plane.db.models import SlackEventReceipt, IdentitySource
from plane.integrations.slack import (
    SlackAuthenticationError,
    SlackClientError,
    SlackCredentials,
    sync_slack_user,
)

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


def signed_headers(body, *, secret="signing-secret", timestamp=None):
    timestamp = str(int(time.time()) if timestamp is None else timestamp)
    base = b"v0:" + timestamp.encode() + b":" + body
    signature = "v0=" + hmac.new(secret.encode(), base, hashlib.sha256).hexdigest()
    return {
        "HTTP_X_SLACK_REQUEST_TIMESTAMP": timestamp,
        "HTTP_X_SLACK_SIGNATURE": signature,
    }


@pytest.fixture
def slack_installation(workspace):
    installation = IdentitySource(
        workspace=workspace,
        provider=IdentitySource.Provider.SLACK,
        external_organization_id="T123",
        external_organization_name="Slack Team",
    )
    installation.set_access_token("xoxb-secret")
    installation.save()
    return installation


@patch(
    "plane.authentication.views.app.slack_events.get_slack_credentials",
    return_value=SlackCredentials("client", "client-secret", "signing-secret"),
)
@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_event_is_verified_enqueued_once_and_deduplicated(publish, _credentials, slack_installation):
    event_timestamp = str(time.time())
    body = json.dumps(
        {
            "type": "event_callback",
            "team_id": slack_installation.external_organization_id,
            "event_id": "Ev123",
            "event_time": int(time.time()),
            "event": {
                "type": "user_change",
                "event_ts": event_timestamp,
                "user": {"id": "U123"},
            },
        },
        separators=(",", ":"),
    ).encode()
    client = Client()

    first = client.generic("POST", "/auth/slack/events/", body, content_type="application/json", **signed_headers(body))
    second = client.generic(
        "POST", "/auth/slack/events/", body, content_type="application/json", **signed_headers(body)
    )

    assert first.status_code == 200
    assert second.status_code == 200
    receipt = SlackEventReceipt.objects.get(event_id="Ev123")
    assert receipt.source_generation == slack_installation.generation
    assert receipt.event_time is not None
    assert receipt.payload["type"] == "user_change"
    assert receipt.status == SlackEventReceipt.Status.QUEUED
    publish.assert_called_once_with(args=[str(receipt.id)], retry=False)


@patch(
    "plane.authentication.views.app.slack_events.get_slack_credentials",
    return_value=SlackCredentials("client", "client-secret", "signing-secret"),
)
@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_event_for_installation_still_bootstrapping_is_persisted(
    publish,
    _credentials,
):
    event_timestamp = str(time.time())
    body = json.dumps(
        {
            "type": "event_callback",
            "team_id": "TBOOTSTRAP",
            "event_id": "EvBootstrapPending",
            "event_time": int(time.time()),
            "event": {
                "type": "user_change",
                "event_ts": event_timestamp,
                "user": {"id": "UADMIN"},
            },
        },
        separators=(",", ":"),
    ).encode()

    response = Client().generic(
        "POST",
        "/auth/slack/events/",
        body,
        content_type="application/json",
        **signed_headers(body),
    )

    assert response.status_code == 200
    receipt = SlackEventReceipt.objects.get(event_id="EvBootstrapPending")
    assert receipt.source_generation == 0
    assert receipt.status == SlackEventReceipt.Status.QUEUED
    publish.assert_called_once_with(args=[str(receipt.id)], retry=False)


@patch(
    "plane.authentication.views.app.slack_events.get_slack_credentials",
    return_value=SlackCredentials("client", "client-secret", "signing-secret"),
)
@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_event_from_foreign_team_is_acknowledged_without_persistence_or_publish(
    publish,
    _credentials,
    slack_installation,
):
    event_timestamp = str(time.time())
    body = json.dumps(
        {
            "type": "event_callback",
            "team_id": "TFOREIGN",
            "event_id": "EvForeignWorkspace",
            "event_time": int(time.time()),
            "event": {
                "type": "user_change",
                "event_ts": event_timestamp,
                "user": {"id": "UFOREIGN"},
            },
        },
        separators=(",", ":"),
    ).encode()

    response = Client().generic(
        "POST",
        "/auth/slack/events/",
        body,
        content_type="application/json",
        **signed_headers(body),
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert not SlackEventReceipt.objects.filter(event_id="EvForeignWorkspace").exists()
    publish.assert_not_called()


@patch(
    "plane.authentication.views.app.slack_events.get_slack_credentials",
    return_value=SlackCredentials("client", "client-secret", "signing-secret"),
)
@patch(
    "plane.bgtasks.slack_sync.process_slack_event.apply_async",
    side_effect=RuntimeError("broker unavailable"),
)
def test_broker_failure_keeps_the_event_durable_and_still_acknowledges_slack(
    publish,
    _credentials,
    slack_installation,
):
    body = json.dumps(
        {
            "type": "event_callback",
            "team_id": slack_installation.external_organization_id,
            "event_id": "EvBrokerFailure",
            "event_time": int(time.time()),
            "event": {"type": "app_uninstalled"},
        },
        separators=(",", ":"),
    ).encode()

    response = Client().generic(
        "POST",
        "/auth/slack/events/",
        body,
        content_type="application/json",
        **signed_headers(body),
    )

    assert response.status_code == 200
    receipt = SlackEventReceipt.objects.get(event_id="EvBrokerFailure")
    assert receipt.status == SlackEventReceipt.Status.QUEUED
    assert receipt.payload == {"type": "app_uninstalled"}
    publish.assert_called_once_with(args=[str(receipt.id)], retry=False)


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_outbox_sweeper_requeues_a_received_event(publish, slack_installation):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvPendingOutbox",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "app_uninstalled"},
    )

    requeue_stale_slack_event_receipts.run()

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.QUEUED
    publish.assert_called_once_with(args=[str(receipt.id)], retry=False)


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_outbox_sweeper_claims_an_event_only_once(publish, slack_installation):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvSingleOutboxClaim",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "app_uninstalled"},
    )

    requeue_stale_slack_event_receipts.run()
    requeue_stale_slack_event_receipts.run()

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.QUEUED
    publish.assert_called_once_with(args=[str(receipt.id)], retry=False)


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_outbox_sweeper_preserves_a_fresh_final_processing_attempt(
    publish,
    slack_installation,
):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvFreshFinalAttempt",
        team_id=slack_installation.external_organization_id,
        event_type="team_rename",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "team_rename"},
        status=SlackEventReceipt.Status.PROCESSING,
        attempt_count=SLACK_EVENT_MAX_ATTEMPTS,
    )

    requeue_stale_slack_event_receipts.run()

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSING
    assert receipt.processed_at is None
    publish.assert_not_called()


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_outbox_sweeper_dead_letters_an_expired_final_processing_attempt(
    publish,
    slack_installation,
):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvExpiredFinalAttempt",
        team_id=slack_installation.external_organization_id,
        event_type="team_rename",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "team_rename"},
        status=SlackEventReceipt.Status.PROCESSING,
        attempt_count=SLACK_EVENT_MAX_ATTEMPTS,
    )
    SlackEventReceipt.objects.filter(pk=receipt.pk).update(
        updated_at=timezone.now() - timedelta(minutes=2)
    )

    requeue_stale_slack_event_receipts.run()

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.DEAD_LETTER
    assert receipt.processed_at is not None
    publish.assert_not_called()


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_outbox_sweeper_fails_closed_after_a_final_lifecycle_worker_crash(
    publish,
    slack_installation,
):
    connected_at = timezone.now().replace(microsecond=500_000)
    slack_installation.connected_at = connected_at
    slack_installation.save(update_fields=["connected_at", "updated_at"])
    receipt = SlackEventReceipt.objects.create(
        event_id="EvExpiredLifecycleAttempt",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=slack_installation.generation,
        event_time=connected_at.replace(microsecond=0),
        payload={"type": "app_uninstalled"},
        status=SlackEventReceipt.Status.PROCESSING,
        attempt_count=SLACK_EVENT_MAX_ATTEMPTS,
    )
    SlackEventReceipt.objects.filter(pk=receipt.pk).update(
        updated_at=timezone.now() - timedelta(minutes=2)
    )

    requeue_stale_slack_event_receipts.run()

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.DEAD_LETTER
    assert slack_installation.status == IdentitySource.Status.REVOKED
    assert slack_installation.encrypted_access_token == ""
    publish.assert_not_called()


@patch(
    "plane.authentication.views.app.slack_events.get_slack_credentials",
    return_value=SlackCredentials("client", "client-secret", "signing-secret"),
)
@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_invalid_signature_is_rejected(publish, _credentials):
    body = b'{"type":"event_callback"}'

    response = Client().generic(
        "POST",
        "/auth/slack/events/",
        body,
        content_type="application/json",
        HTTP_X_SLACK_REQUEST_TIMESTAMP=str(int(time.time())),
        HTTP_X_SLACK_SIGNATURE="v0=invalid",
    )

    assert response.status_code == 401
    assert not SlackEventReceipt.objects.exists()
    publish.assert_not_called()


@patch(
    "plane.authentication.views.app.slack_events.get_slack_credentials",
    return_value=SlackCredentials("client", "client-secret", "signing-secret"),
)
def test_url_verification_returns_challenge(_credentials):
    body = b'{"type":"url_verification","challenge":"challenge-value"}'

    response = Client().generic(
        "POST",
        "/auth/slack/events/",
        body,
        content_type="application/json",
        **signed_headers(body),
    )

    assert response.status_code == 200
    assert response.json() == {"challenge": "challenge-value"}


def test_event_from_previous_source_generation_cannot_revoke_reconnected_token(
    slack_installation,
):
    old_generation = slack_installation.generation
    receipt = SlackEventReceipt.objects.create(
        event_id="EvBeforeReconnect",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=old_generation,
        event_time=timezone.now() - timedelta(minutes=1),
        payload={"type": "app_uninstalled"},
    )
    slack_installation.generation += 1
    slack_installation.connected_at = timezone.now()
    slack_installation.save(update_fields=["generation", "connected_at", "updated_at"])

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert slack_installation.status == IdentitySource.Status.ACTIVE
    assert slack_installation.get_access_token() == "xoxb-secret"


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
@pytest.mark.parametrize(
    "disconnected_status",
    [IdentitySource.Status.ERROR, IdentitySource.Status.REVOKED],
)
def test_lifecycle_event_received_during_reconnect_is_deferred_then_fenced(
    apply_async,
    disconnected_status,
    slack_installation,
):
    old_generation = slack_installation.generation
    slack_installation.status = disconnected_status
    slack_installation.encrypted_access_token = ""
    slack_installation.save(update_fields=["status", "encrypted_access_token", "updated_at"])
    event_time = timezone.now()
    receipt = SlackEventReceipt.objects.create(
        event_id="EvDuringReconnect",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=old_generation,
        event_time=event_time,
        payload={"type": "app_uninstalled"},
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.FAILED
    assert receipt.attempt_count == 0
    assert receipt.next_attempt_at is not None
    apply_async.assert_called_once()

    slack_installation.generation += 1
    slack_installation.connected_at = event_time - timedelta(seconds=2)
    slack_installation.status = IdentitySource.Status.ACTIVE
    slack_installation.set_access_token("xoxb-reconnected")
    slack_installation.save()
    SlackEventReceipt.objects.filter(pk=receipt.pk).update(
        next_attempt_at=timezone.now() - timedelta(seconds=1)
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert receipt.attempt_count == 1
    assert slack_installation.status == IdentitySource.Status.REVOKED
    assert slack_installation.encrypted_access_token == ""


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_user_event_received_during_reconnect_overrides_an_older_installer_lookup(
    apply_async,
    slack_installation,
):
    old_generation = slack_installation.generation
    slack_installation.status = IdentitySource.Status.REVOKED
    slack_installation.encrypted_access_token = ""
    slack_installation.save(update_fields=["status", "encrypted_access_token", "updated_at"])
    event_at = timezone.now()
    event_timestamp = event_at.timestamp()
    receipt = SlackEventReceipt.objects.create(
        event_id="EvUserDuringReconnect",
        team_id=slack_installation.external_organization_id,
        event_type="user_change",
        source_generation=old_generation,
        event_time=event_at.replace(microsecond=0),
        payload={
            "type": "user_change",
            "event_ts": str(event_timestamp),
            "user": {
                "id": "UADMIN",
                "team_id": slack_installation.external_organization_id,
                "name": "admin",
                "deleted": True,
                "updated": int(event_timestamp),
                "profile": {"email": "admin@example.com"},
            },
        },
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.FAILED
    assert receipt.attempt_count == 0

    slack_installation.generation += 1
    slack_installation.connected_at = event_at - timedelta(seconds=2)
    slack_installation.status = IdentitySource.Status.ACTIVE
    slack_installation.set_access_token("xoxb-reconnected")
    slack_installation.save()
    identity = sync_slack_user(
        slack_installation,
        {
            "id": "UADMIN",
            "team_id": slack_installation.external_organization_id,
            "name": "admin",
            "deleted": False,
            "updated": int(event_timestamp) - 10,
            "profile": {"email": "admin@example.com", "display_name": "Admin"},
        },
        authoritative=True,
        authoritative_started_at=event_at - timedelta(seconds=1),
    )
    assert identity is not None
    SlackEventReceipt.objects.filter(pk=receipt.pk).update(
        next_attempt_at=timezone.now() - timedelta(seconds=1)
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert receipt.attempt_count == 1
    assert identity.is_active is False
    assert identity.user.is_active is False
    apply_async.assert_called_once()


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
@patch("plane.bgtasks.slack_sync._process_event")
def test_bootstrap_event_is_retried_against_the_committed_installation(
    process_event,
    apply_async,
    workspace,
):
    event_at = timezone.now()
    receipt = SlackEventReceipt.objects.create(
        event_id="EvBeforeBootstrapCommit",
        team_id="TBOOTSTRAP",
        event_type="user_change",
        source_generation=0,
        event_time=event_at.replace(microsecond=0),
        payload={
            "type": "user_change",
            "event_ts": str(event_at.timestamp()),
            "user": {"id": "UADMIN"},
        },
    )

    process_slack_event.run(str(receipt.id))
    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.FAILED
    assert receipt.attempt_count == 0

    installation = IdentitySource(
        workspace=workspace,
        provider=IdentitySource.Provider.SLACK,
        external_organization_id="TBOOTSTRAP",
        external_organization_name="Bootstrap Team",
        connected_at=event_at - timedelta(seconds=1),
    )
    installation.set_access_token("xoxb-bootstrap")
    installation.save()
    SlackEventReceipt.objects.filter(pk=receipt.pk).update(
        next_attempt_at=timezone.now() - timedelta(seconds=1)
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert receipt.attempt_count == 1
    process_event.assert_called_once()
    apply_async.assert_called_once()


@patch("plane.bgtasks.slack_sync._process_event")
def test_fractional_user_event_after_reconnect_is_not_dropped_by_outer_second(
    process_event,
    slack_installation,
):
    connected_at = timezone.now().replace(microsecond=500_000)
    slack_installation.connected_at = connected_at
    slack_installation.save(update_fields=["connected_at", "updated_at"])
    event = {
        "type": "user_change",
        "event_ts": str((connected_at + timedelta(milliseconds=100)).timestamp()),
        "user": {"id": "UAFTER"},
    }
    receipt = SlackEventReceipt.objects.create(
        event_id="EvSameSecondAfterReconnect",
        team_id=slack_installation.external_organization_id,
        event_type="user_change",
        source_generation=slack_installation.generation,
        event_time=connected_at.replace(microsecond=0),
        payload=event,
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    process_event.assert_called_once()


@patch(
    "plane.bgtasks.slack_sync.SlackClient.auth_test",
    return_value={"ok": True, "team_id": "T123", "user_id": "UBOT"},
)
@patch("plane.bgtasks.slack_sync._process_event")
def test_stale_lifecycle_event_in_reconnect_second_keeps_valid_current_token(
    process_event,
    _auth_test,
    slack_installation,
):
    connected_at = timezone.now().replace(microsecond=500_000)
    slack_installation.generation += 1
    slack_installation.connected_at = connected_at
    slack_installation.save(update_fields=["generation", "connected_at", "updated_at"])
    event = {"type": "app_uninstalled"}
    receipt = SlackEventReceipt.objects.create(
        event_id="EvLifecycleSameSecondAfterReconnect",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=slack_installation.generation - 1,
        event_time=connected_at.replace(microsecond=0),
        payload=event,
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert slack_installation.status == IdentitySource.Status.ACTIVE
    process_event.assert_not_called()


@patch(
    "plane.bgtasks.slack_sync.SlackClient.auth_test",
    side_effect=SlackAuthenticationError("revoked", error_code="token_revoked"),
)
def test_current_lifecycle_event_in_reconnect_second_revokes_invalid_token(
    _auth_test,
    slack_installation,
):
    connected_at = timezone.now().replace(microsecond=500_000)
    slack_installation.connected_at = connected_at
    slack_installation.save(update_fields=["connected_at", "updated_at"])
    receipt = SlackEventReceipt.objects.create(
        event_id="EvCurrentLifecycleSameSecond",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=slack_installation.generation,
        event_time=connected_at.replace(microsecond=0),
        payload={"type": "app_uninstalled"},
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert slack_installation.status == IdentitySource.Status.REVOKED
    assert slack_installation.encrypted_access_token == ""


@patch(
    "plane.bgtasks.slack_sync.SlackClient.auth_test",
    side_effect=SlackClientError("temporary Slack outage"),
)
@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_unverifiable_lifecycle_event_fails_closed_on_its_final_attempt(
    apply_async,
    _auth_test,
    slack_installation,
):
    connected_at = timezone.now().replace(microsecond=500_000)
    slack_installation.connected_at = connected_at
    slack_installation.save(update_fields=["connected_at", "updated_at"])
    receipt = SlackEventReceipt.objects.create(
        event_id="EvUnverifiableLifecycle",
        team_id=slack_installation.external_organization_id,
        event_type="app_uninstalled",
        source_generation=slack_installation.generation,
        event_time=connected_at.replace(microsecond=0),
        payload={"type": "app_uninstalled"},
        attempt_count=SLACK_EVENT_MAX_ATTEMPTS - 1,
        status=SlackEventReceipt.Status.QUEUED,
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.DEAD_LETTER
    assert receipt.attempt_count == SLACK_EVENT_MAX_ATTEMPTS
    assert slack_installation.status == IdentitySource.Status.REVOKED
    assert slack_installation.encrypted_access_token == ""
    apply_async.assert_not_called()


def test_malformed_event_is_dead_lettered(slack_installation):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvMalformed",
        team_id=slack_installation.external_organization_id,
        event_type="unknown",
        source_generation=slack_installation.generation,
        payload={},
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.DEAD_LETTER
    assert receipt.attempt_count == 1
    assert receipt.processed_at is not None
    assert "no durable payload" in receipt.last_error


def test_event_for_missing_installation_is_dead_lettered():
    receipt = SlackEventReceipt.objects.create(
        event_id="EvMissingInstallation",
        team_id="TMISSING",
        event_type="user_change",
        event_time=timezone.now(),
        payload={"type": "user_change", "event_ts": str(time.time()), "user": {"id": "U1"}},
        received_at=timezone.now() - timedelta(minutes=3),
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.DEAD_LETTER
    assert receipt.attempt_count == 1
    assert "does not exist" in receipt.last_error


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
def test_recent_event_for_missing_installation_is_deferred_without_spending_budget(
    apply_async,
):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvBootstrapGrace",
        team_id="TBOOTSTRAP",
        event_type="user_change",
        source_generation=0,
        event_time=timezone.now(),
        payload={
            "type": "user_change",
            "event_ts": str(time.time()),
            "user": {"id": "UADMIN"},
        },
    )

    for _ in range(3):
        process_slack_event.run(str(receipt.id))
        receipt.refresh_from_db()
        assert receipt.status == SlackEventReceipt.Status.FAILED
        assert receipt.attempt_count == 0
        assert receipt.next_attempt_at is not None
        SlackEventReceipt.objects.filter(pk=receipt.pk).update(
            next_attempt_at=timezone.now() - timedelta(seconds=1)
        )

    assert apply_async.call_count == 3


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
@patch("plane.bgtasks.slack_sync._process_event", side_effect=SlackClientError("temporary"))
def test_transient_event_failure_uses_persisted_retry_budget(
    _process_event,
    apply_async,
    slack_installation,
):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvTransient",
        team_id=slack_installation.external_organization_id,
        event_type="unknown",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "unknown"},
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.FAILED
    assert receipt.attempt_count == 1
    assert receipt.next_attempt_at is not None
    assert "SlackClientError: temporary" in receipt.last_error
    apply_async.assert_called_once_with(args=[str(receipt.id)], countdown=60)


@patch("plane.bgtasks.slack_sync.process_slack_event.apply_async")
@patch("plane.bgtasks.slack_sync._process_event", side_effect=SlackClientError("poison"))
def test_final_event_attempt_is_dead_lettered(
    _process_event,
    apply_async,
    slack_installation,
):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvPoison",
        team_id=slack_installation.external_organization_id,
        event_type="unknown",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "unknown"},
        attempt_count=SLACK_EVENT_MAX_ATTEMPTS - 1,
        status=SlackEventReceipt.Status.QUEUED,
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.DEAD_LETTER
    assert receipt.attempt_count == SLACK_EVENT_MAX_ATTEMPTS
    assert receipt.processed_at is not None
    apply_async.assert_not_called()


@patch("plane.bgtasks.slack_sync._process_event")
def test_event_does_not_run_before_persisted_retry_time(process_event, slack_installation):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvFutureRetry",
        team_id=slack_installation.external_organization_id,
        event_type="unknown",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "unknown"},
        attempt_count=1,
        status=SlackEventReceipt.Status.FAILED,
        next_attempt_at=timezone.now() + timedelta(minutes=5),
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.FAILED
    assert receipt.attempt_count == 1
    process_event.assert_not_called()


@patch(
    "plane.bgtasks.slack_sync.SlackClient.team_info",
    return_value={
        "ok": True,
        "team": {
            "id": "T123",
            "name": "Current Team Name",
            "domain": "current-domain",
            "icon": {},
        },
    },
)
def test_team_event_refreshes_current_metadata_instead_of_applying_stale_payload(
    _team_info,
    slack_installation,
):
    receipt = SlackEventReceipt.objects.create(
        event_id="EvStaleRename",
        team_id=slack_installation.external_organization_id,
        event_type="team_rename",
        source_generation=slack_installation.generation,
        event_time=timezone.now(),
        payload={"type": "team_rename", "name": "Stale Event Name"},
    )

    process_slack_event.run(str(receipt.id))

    receipt.refresh_from_db()
    slack_installation.refresh_from_db()
    slack_installation.workspace.refresh_from_db()
    assert receipt.status == SlackEventReceipt.Status.PROCESSED
    assert slack_installation.external_organization_name == "Current Team Name"
    assert slack_installation.external_organization_domain == "current-domain"
    assert slack_installation.workspace.name == "Current Team Name"
