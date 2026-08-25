# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from math import ceil
from typing import Any

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from plane.db.models import IdentitySource, SlackEventReceipt
from plane.integrations.identity import configured_identity_provider
from plane.integrations.slack import (
    SlackAuthenticationError,
    SlackClient,
    SlackClientError,
    SlackRateLimited,
    reconcile_installation,
    revoke_installation,
    sync_slack_team_metadata,
    sync_slack_user,
)

SLACK_EVENT_MAX_ATTEMPTS = 6
SLACK_EVENT_LEASE = timedelta(minutes=1)
SLACK_EVENT_DEFAULT_RETRY_SECONDS = 60
SLACK_RECONNECT_EVENT_GRACE = timedelta(minutes=2)
SLACK_LIFECYCLE_EVENT_TYPES = frozenset({"app_uninstalled", "tokens_revoked"})
SLACK_DEFERRED_EVENT_TYPES = frozenset(
    {
        *SLACK_LIFECYCLE_EVENT_TYPES,
        "team_domain_change",
        "team_join",
        "team_rename",
        "user_change",
    }
)


class _SlackEventDeferred(Exception):
    """Keep an authoritative event alive while an install may be in flight."""

    def __init__(self, retry_after: int):
        super().__init__("Slack event is waiting for installation fencing")
        self.retry_after = retry_after


class _SlackLifecycleValidationError(SlackClientError):
    """A same-second lifecycle event whose current token cannot be verified."""

    def __init__(self, message: str, *, expected_generation: int, retry_after: int = 60):
        super().__init__(message)
        self.expected_generation = expected_generation
        self.retry_after = retry_after


def _record_sync_error(
    installation_id: str,
    expected_generation: int,
    failure_started_at,
    exc: Exception,
) -> None:
    IdentitySource.objects.filter(
        Q(last_synced_at__isnull=True) | Q(last_synced_at__lt=failure_started_at),
        Q(sync_error_at__isnull=True) | Q(sync_error_at__lt=failure_started_at),
        pk=installation_id,
        provider=IdentitySource.Provider.SLACK,
        generation=expected_generation,
    ).exclude(status=IdentitySource.Status.REVOKED).update(
        sync_error=str(exc)[:2000],
        sync_error_at=failure_started_at,
        updated_at=timezone.now(),
    )


def _retry_or_fail_closed(
    task,
    installation: IdentitySource,
    expected_generation: int,
    failure_started_at,
    exc: Exception,
    *,
    countdown: int,
) -> None:
    """Retry transient failures, then suspend access if Slack stays unverifiable."""

    if task.request.retries >= task.max_retries:
        revoke_installation(
            installation,
            f"Slack identity sync failed after retries: {exc}",
            expected_generation=expected_generation,
            expected_no_success_since=failure_started_at,
        )
        return
    raise task.retry(
        exc=exc,
        countdown=countdown,
        args=(
            str(installation.id),
            failure_started_at.isoformat(),
            expected_generation,
        ),
        kwargs={},
    ) from exc


def _failure_started_at(raw_value: str | None):
    if raw_value:
        try:
            value = datetime.fromisoformat(raw_value)
            if timezone.is_naive(value):
                value = timezone.make_aware(value)
            return value
        except (TypeError, ValueError):
            pass
    return timezone.now()


@shared_task(bind=True, max_retries=5)
def reconcile_slack_installation(
    self,
    installation_id: str,
    failure_started_at: str | None = None,
    expected_generation: int | None = None,
) -> None:
    """Celery entry point for an idempotent full Slack reconciliation."""

    if configured_identity_provider() != IdentitySource.Provider.SLACK:
        return
    failure_started = _failure_started_at(failure_started_at)
    try:
        installation = IdentitySource.objects.get(
            pk=installation_id,
            provider=IdentitySource.Provider.SLACK,
        )
    except IdentitySource.DoesNotExist:
        return
    if expected_generation is None:
        expected_generation = installation.generation
    elif installation.generation != expected_generation:
        return
    if (
        failure_started_at is not None
        and installation.last_synced_at is not None
        and installation.last_synced_at >= failure_started
    ):
        return

    try:
        reconcile_installation(installation)
    except SlackAuthenticationError as exc:
        error_code = exc.error_code or "unknown_auth_error"
        revoke_installation(
            installation,
            f"Slack bot authentication failed: {error_code}",
            expected_generation=expected_generation,
        )
    except SlackRateLimited as exc:
        _record_sync_error(
            installation_id,
            expected_generation,
            failure_started,
            exc,
        )
        _retry_or_fail_closed(
            self,
            installation,
            expected_generation,
            failure_started,
            exc,
            countdown=exc.retry_after,
        )
    except SlackClientError as exc:
        _record_sync_error(
            installation_id,
            expected_generation,
            failure_started,
            exc,
        )
        _retry_or_fail_closed(
            self,
            installation,
            expected_generation,
            failure_started,
            exc,
            countdown=60,
        )
    except Exception as exc:
        _record_sync_error(
            installation_id,
            expected_generation,
            failure_started,
            exc,
        )
        _retry_or_fail_closed(
            self,
            installation,
            expected_generation,
            failure_started,
            exc,
            countdown=60,
        )


@shared_task
def reconcile_all_slack_installations() -> None:
    """Fan out periodic reconciliation for every recoverable Slack installation."""

    if configured_identity_provider() != IdentitySource.Provider.SLACK:
        return
    installation_ids = (
        IdentitySource.objects.filter(provider=IdentitySource.Provider.SLACK)
        .exclude(status=IdentitySource.Status.REVOKED)
        .values_list("id", flat=True)
    )
    for installation_id in installation_ids.iterator():
        reconcile_slack_installation.delay(str(installation_id))


@shared_task
def delete_old_slack_event_receipts() -> None:
    """Hard-delete Slack delivery idempotency records after their retry horizon."""

    cutoff = timezone.now() - timedelta(days=30)
    SlackEventReceipt.all_objects.filter(received_at__lt=cutoff).delete()


def _dead_letter_receipt(receipt: SlackEventReceipt, error: str) -> None:
    now = timezone.now()
    receipt.status = SlackEventReceipt.Status.DEAD_LETTER
    receipt.next_attempt_at = None
    receipt.last_error = error[:2000]
    receipt.processed_at = now
    receipt.save(
        update_fields=[
            "status",
            "next_attempt_at",
            "last_error",
            "processed_at",
            "updated_at",
        ]
    )


def enqueue_slack_event_receipt(
    receipt_id: str,
    *,
    recover_stale: bool = False,
) -> tuple[bool, bool]:
    """Atomically claim an outbox row before publishing it.

    Returns ``(claimed, published)``. A claimed row remains QUEUED when broker
    publication fails so the lease-based sweeper can safely recover the
    ambiguous publish outcome without racing another dispatcher.
    """

    now = timezone.now()
    stale_cutoff = now - SLACK_EVENT_LEASE
    with transaction.atomic():
        try:
            receipt = SlackEventReceipt.objects.select_for_update().get(pk=receipt_id)
        except SlackEventReceipt.DoesNotExist:
            return False, False

        if receipt.status in {
            SlackEventReceipt.Status.PROCESSED,
            SlackEventReceipt.Status.DEAD_LETTER,
        }:
            return False, False

        eligible = receipt.status == SlackEventReceipt.Status.RECEIVED
        if receipt.status == SlackEventReceipt.Status.FAILED:
            eligible = (
                receipt.attempt_count >= SLACK_EVENT_MAX_ATTEMPTS
                or receipt.next_attempt_at is None
                or receipt.next_attempt_at <= now
            )
        if recover_stale and receipt.status in {
            SlackEventReceipt.Status.QUEUED,
            SlackEventReceipt.Status.PROCESSING,
        }:
            eligible = receipt.updated_at < stale_cutoff
        if not eligible:
            return False, False
        # A final PROCESSING attempt remains authoritative until its lease
        # expires. Only an otherwise dispatchable row may consume the retry
        # cap and transition to dead letter.
        if receipt.attempt_count >= SLACK_EVENT_MAX_ATTEMPTS:
            _dead_letter_retry_exhausted(
                receipt,
                "Slack event retry limit reached",
            )
            return False, False

        receipt.status = SlackEventReceipt.Status.QUEUED
        receipt.next_attempt_at = None
        receipt.save(update_fields=["status", "next_attempt_at", "updated_at"])

    try:
        process_slack_event.apply_async(
            args=[str(receipt_id)],
            retry=False,
        )
    except Exception:
        return True, False
    return True, True


@shared_task
def requeue_stale_slack_event_receipts() -> None:
    """Re-enqueue durable Slack events lost to broker or worker failure."""

    now = timezone.now()
    stale_cutoff = now - SLACK_EVENT_LEASE
    receipt_ids = SlackEventReceipt.objects.filter(
        Q(status=SlackEventReceipt.Status.RECEIVED)
        | Q(
            status=SlackEventReceipt.Status.FAILED,
            next_attempt_at__lte=now,
        )
        | Q(
            status=SlackEventReceipt.Status.FAILED,
            next_attempt_at__isnull=True,
        )
        | Q(
            status__in=[SlackEventReceipt.Status.QUEUED, SlackEventReceipt.Status.PROCESSING],
            updated_at__lt=stale_cutoff,
        )
        | Q(
            status__in=[
                SlackEventReceipt.Status.RECEIVED,
                SlackEventReceipt.Status.FAILED,
                SlackEventReceipt.Status.QUEUED,
                SlackEventReceipt.Status.PROCESSING,
            ],
            attempt_count__gte=SLACK_EVENT_MAX_ATTEMPTS,
        )
    ).values_list("id", flat=True)
    for receipt_id in receipt_ids.iterator():
        enqueue_slack_event_receipt(str(receipt_id), recover_stale=True)


def _process_event(
    installation: IdentitySource,
    event: dict[str, Any],
    *,
    event_time=None,
) -> None:
    # An uninstall/token revocation is terminal. A delayed user event must not
    # reactivate an identity after the installation has been revoked.
    if installation.status == IdentitySource.Status.REVOKED:
        return

    event_type = str(event.get("type") or "")
    if event_type in {"team_join", "user_change"}:
        user_payload = event.get("user")
        if isinstance(user_payload, dict):
            user_payload.setdefault("team_id", installation.external_organization_id)
            sync_slack_user(
                installation,
                user_payload,
                source_timestamp=(
                    event.get("event_ts")
                    or (event_time.timestamp() if event_time is not None else None)
                ),
            )
        return

    if event_type == "app_uninstalled":
        revoke_installation(
            installation,
            "Slack app was uninstalled",
            expected_generation=installation.generation,
        )
        return

    if event_type == "tokens_revoked":
        tokens = event.get("tokens")
        bot_ids = tokens.get("bot", []) if isinstance(tokens, dict) else []
        if isinstance(bot_ids, list) and installation.service_account_id in bot_ids:
            revoke_installation(
                installation,
                "Slack bot token was revoked",
                expected_generation=installation.generation,
            )
        return

    if event_type in {"team_rename", "team_domain_change"}:
        # The worker applies a current team.info snapshot prepared outside the
        # database transaction, so the event payload itself is never trusted.
        return


def _slack_event_datetime(raw_value):
    try:
        value = Decimal(str(raw_value))
        if not value.is_finite() or value <= 0:
            return None
        return datetime.fromtimestamp(float(value), tz=UTC)
    except (InvalidOperation, OSError, OverflowError, TypeError, ValueError):
        return None


def _mark_receipt_processed(receipt: SlackEventReceipt) -> None:
    receipt.status = SlackEventReceipt.Status.PROCESSED
    receipt.next_attempt_at = None
    receipt.last_error = ""
    receipt.processed_at = timezone.now()
    receipt.save(
        update_fields=[
            "status",
            "next_attempt_at",
            "last_error",
            "processed_at",
            "updated_at",
        ]
    )


def _claim_slack_event_receipt(receipt_id: str) -> int | None:
    with transaction.atomic():
        try:
            receipt = SlackEventReceipt.objects.select_for_update().get(pk=receipt_id)
        except SlackEventReceipt.DoesNotExist:
            return None
        now = timezone.now()
        if receipt.status in {
            SlackEventReceipt.Status.PROCESSED,
            SlackEventReceipt.Status.DEAD_LETTER,
        }:
            return None
        if receipt.status == SlackEventReceipt.Status.FAILED and (
            receipt.next_attempt_at is not None and receipt.next_attempt_at > now
        ):
            return None
        if (
            receipt.status == SlackEventReceipt.Status.PROCESSING
            and receipt.updated_at >= now - SLACK_EVENT_LEASE
        ):
            return None
        if receipt.attempt_count >= SLACK_EVENT_MAX_ATTEMPTS:
            _dead_letter_retry_exhausted(
                receipt,
                "Slack event retry limit reached",
            )
            return None

        receipt.attempt_count += 1
        receipt.status = SlackEventReceipt.Status.PROCESSING
        receipt.next_attempt_at = None
        receipt.save(
            update_fields=[
                "attempt_count",
                "status",
                "next_attempt_at",
                "updated_at",
            ]
        )
        return receipt.attempt_count


def _record_event_failure(
    receipt_id: str,
    claimed_attempt: int,
    exc: Exception,
    *,
    countdown: int,
    fail_closed_generation: int | None = None,
) -> bool:
    """Persist a fenced retry or dead-letter transition."""

    with transaction.atomic():
        receipt = SlackEventReceipt.objects.select_for_update().filter(
            pk=receipt_id,
            status=SlackEventReceipt.Status.PROCESSING,
            attempt_count=claimed_attempt,
        ).first()
        if receipt is None:
            return False
        error = f"{type(exc).__name__}: {exc}"
        if claimed_attempt >= SLACK_EVENT_MAX_ATTEMPTS:
            _dead_letter_retry_exhausted(
                receipt,
                error,
                expected_generation=fail_closed_generation,
            )
            return False

        now = timezone.now()
        receipt.status = SlackEventReceipt.Status.FAILED
        receipt.next_attempt_at = now + timedelta(seconds=max(1, countdown))
        receipt.last_error = error[:2000]
        receipt.save(
            update_fields=[
                "status",
                "next_attempt_at",
                "last_error",
                "updated_at",
            ]
        )
        return True


def _record_event_deferral(
    receipt_id: str,
    claimed_attempt: int,
    exc: Exception,
    *,
    countdown: int,
) -> bool:
    """Persist a fenced delay without consuming the processing retry budget."""

    with transaction.atomic():
        receipt = SlackEventReceipt.objects.select_for_update().filter(
            pk=receipt_id,
            status=SlackEventReceipt.Status.PROCESSING,
            attempt_count=claimed_attempt,
        ).first()
        if receipt is None:
            return False
        now = timezone.now()
        receipt.status = SlackEventReceipt.Status.FAILED
        receipt.attempt_count = max(0, claimed_attempt - 1)
        receipt.next_attempt_at = now + timedelta(seconds=max(1, countdown))
        receipt.last_error = f"{type(exc).__name__}: {exc}"[:2000]
        receipt.save(
            update_fields=[
                "status",
                "attempt_count",
                "next_attempt_at",
                "last_error",
                "updated_at",
            ]
        )
        return True


def _installation_grace_retry_after(
    receipt: SlackEventReceipt,
    event_type: str,
) -> int | None:
    if event_type not in SLACK_DEFERRED_EVENT_TYPES:
        return None
    remaining = (
        receipt.received_at + SLACK_RECONNECT_EVENT_GRACE - timezone.now()
    ).total_seconds()
    if remaining <= 0:
        return None
    return max(1, min(10, ceil(remaining)))


def _lifecycle_event_targets_installation(
    installation: IdentitySource,
    event: dict[str, Any],
) -> bool:
    event_type = str(event.get("type") or "")
    if event_type == "app_uninstalled":
        return True
    if event_type != "tokens_revoked":
        return False
    tokens = event.get("tokens")
    bot_ids = tokens.get("bot", []) if isinstance(tokens, dict) else []
    return bool(
        installation.service_account_id
        and isinstance(bot_ids, list)
        and installation.service_account_id in bot_ids
    )


def _dead_letter_retry_exhausted(
    receipt: SlackEventReceipt,
    error: str,
    *,
    expected_generation: int | None = None,
) -> None:
    """Fail closed before abandoning an unverifiable current lifecycle event."""

    event = receipt.payload if isinstance(receipt.payload, dict) else {}
    event_type = str(event.get("type") or receipt.event_type)
    if event_type in SLACK_LIFECYCLE_EVENT_TYPES:
        installation = IdentitySource.objects.select_for_update().filter(
            provider=IdentitySource.Provider.SLACK,
            external_organization_id=receipt.team_id,
        ).first()
        if (
            installation is not None
            and installation.status != IdentitySource.Status.REVOKED
            and (
                expected_generation is None
                or installation.generation == expected_generation
            )
            and _lifecycle_event_targets_installation(installation, event)
            and receipt.event_time is not None
            and receipt.event_time
            >= installation.connected_at.replace(microsecond=0)
        ):
            revoke_installation(
                installation,
                "Slack lifecycle event could not validate the current bot token",
                expected_generation=installation.generation,
            )
    _dead_letter_receipt(receipt, error)


def _current_bot_token_is_valid(installation: IdentitySource) -> bool:
    try:
        bot_token = installation.get_access_token()
    except ValueError:
        return False
    try:
        response = SlackClient(bot_token).auth_test()
    except SlackAuthenticationError:
        return False

    team_id = str(response.get("team_id") or "")
    bot_user_id = str(response.get("user_id") or "")
    return bool(
        team_id == installation.external_organization_id
        and (
            not installation.service_account_id
            or bot_user_id == installation.service_account_id
        )
    )


def _prepare_external_event_state(
    receipt_id: str,
    claimed_attempt: int,
) -> dict[str, Any] | None:
    """Perform Slack network checks without holding receipt/installation locks."""

    receipt = SlackEventReceipt.objects.filter(
        pk=receipt_id,
        status=SlackEventReceipt.Status.PROCESSING,
        attempt_count=claimed_attempt,
    ).only(
        "team_id",
        "payload",
        "event_time",
        "source_generation",
    ).first()
    if receipt is None or not isinstance(receipt.payload, dict):
        return None

    event = receipt.payload
    event_type = str(event.get("type") or "")
    if event_type not in {
        "team_rename",
        "team_domain_change",
        *SLACK_LIFECYCLE_EVENT_TYPES,
    }:
        return None

    installation = IdentitySource.objects.filter(
        provider=IdentitySource.Provider.SLACK,
        external_organization_id=receipt.team_id,
    ).first()
    if installation is None:
        return None
    prepared: dict[str, Any] = {"generation": installation.generation}
    connected_second = installation.connected_at.replace(microsecond=0)
    if receipt.event_time is not None and receipt.event_time < connected_second:
        return prepared

    if event_type in SLACK_LIFECYCLE_EVENT_TYPES:
        if not _lifecycle_event_targets_installation(installation, event):
            return prepared
        if receipt.event_time == connected_second:
            prepared["kind"] = "ambiguous_lifecycle"
            try:
                prepared["current_token_valid"] = _current_bot_token_is_valid(installation)
            except SlackRateLimited as exc:
                raise _SlackLifecycleValidationError(
                    "Slack rate-limited lifecycle token validation",
                    expected_generation=installation.generation,
                    retry_after=exc.retry_after,
                ) from exc
            except SlackClientError as exc:
                raise _SlackLifecycleValidationError(
                    "Slack lifecycle token validation failed",
                    expected_generation=installation.generation,
                ) from exc
        elif receipt.source_generation != installation.generation:
            # A lifecycle event can be delivered while the OAuth callback has
            # a new token but has not committed its new generation yet. A
            # strictly later event belongs to the current connection even if
            # ingress observed the previous generation.
            prepared["kind"] = "cross_generation_lifecycle"
        return prepared

    if event_type in {"team_rename", "team_domain_change"}:
        prepared["kind"] = "team_metadata"
        try:
            bot_token = installation.get_access_token()
        except ValueError:
            prepared["authentication_error"] = "Slack bot token could not be decrypted"
            return prepared
        snapshot_at = timezone.now()
        try:
            response = SlackClient(bot_token).team_info()
        except SlackAuthenticationError as exc:
            prepared["authentication_error"] = (
                f"Slack bot authentication failed: {exc.error_code or 'unknown_auth_error'}"
            )
            return prepared
        team = response.get("team")
        if not isinstance(team, dict):
            raise SlackClientError("Slack team.info response is missing team")
        prepared["snapshot_at"] = snapshot_at
        prepared["team"] = team
        return prepared

    if receipt.source_generation != installation.generation:
        return prepared

    return prepared


@shared_task(acks_late=True, reject_on_worker_lost=True)
def process_slack_event(receipt_id: str) -> None:
    """Apply one verified event using a persisted, fenced retry budget."""

    claimed_attempt = _claim_slack_event_receipt(receipt_id)
    if claimed_attempt is None:
        return

    retry_error: Exception | None = None
    retry_countdown = SLACK_EVENT_DEFAULT_RETRY_SECONDS
    try:
        external_state = _prepare_external_event_state(receipt_id, claimed_attempt)
        with transaction.atomic():
            receipt = SlackEventReceipt.objects.select_for_update().filter(
                pk=receipt_id,
                status=SlackEventReceipt.Status.PROCESSING,
                attempt_count=claimed_attempt,
            ).first()
            if receipt is None:
                return

            event = receipt.payload
            if not isinstance(event, dict) or not event:
                _dead_letter_receipt(receipt, "Slack event receipt has no durable payload")
                return
            event_type = str(event.get("type") or "")

            installation = IdentitySource.objects.select_for_update().filter(
                provider=IdentitySource.Provider.SLACK,
                external_organization_id=receipt.team_id,
            ).first()
            if installation is None:
                retry_after = _installation_grace_retry_after(receipt, event_type)
                if retry_after is not None:
                    raise _SlackEventDeferred(retry_after)
                _dead_letter_receipt(receipt, "Slack installation does not exist")
                return
            if receipt.source_id is None:
                receipt.source = installation
                receipt.save(update_fields=["source", "updated_at"])
            if installation.status in {
                IdentitySource.Status.ERROR,
                IdentitySource.Status.REVOKED,
            }:
                retry_after = _installation_grace_retry_after(receipt, event_type)
                if retry_after is not None:
                    raise _SlackEventDeferred(retry_after)
            if installation.status == IdentitySource.Status.REVOKED:
                _mark_receipt_processed(receipt)
                return

            inner_event_time = _slack_event_datetime(event.get("event_ts"))
            if event_type in {"team_join", "user_change"}:
                # The fractional inner timestamp disambiguates reconnect-second
                # user events even though the outer envelope is second-based.
                event_predates_connection = bool(
                    inner_event_time is None
                    or inner_event_time < installation.connected_at
                )
            else:
                connected_second = installation.connected_at.replace(microsecond=0)
                event_predates_connection = bool(
                    receipt.event_time
                    and receipt.event_time < connected_second
                )
            if (
                event_type
                in {
                    *SLACK_LIFECYCLE_EVENT_TYPES,
                    "team_domain_change",
                    "team_rename",
                }
                and external_state is not None
                and external_state.get("generation") != installation.generation
            ):
                raise SlackClientError(
                    "Slack installation changed while lifecycle validation was in flight"
                )
            lifecycle_generation_override = bool(
                event_type in SLACK_LIFECYCLE_EVENT_TYPES
                and external_state is not None
                and external_state.get("generation") == installation.generation
                and (
                    external_state.get("kind") == "cross_generation_lifecycle"
                    or (
                        external_state.get("kind") == "ambiguous_lifecycle"
                        and external_state.get("current_token_valid") is False
                    )
                )
            )
            user_generation_override = bool(
                event_type in {"team_join", "user_change"}
                and inner_event_time is not None
                and inner_event_time >= installation.connected_at
            )
            team_generation_override = bool(
                event_type in {"team_rename", "team_domain_change"}
                and external_state is not None
                and external_state.get("generation") == installation.generation
                and external_state.get("kind") == "team_metadata"
            )
            if event_predates_connection or (
                receipt.source_generation != installation.generation
                and not (
                    lifecycle_generation_override
                    or team_generation_override
                    or user_generation_override
                )
            ):
                _mark_receipt_processed(receipt)
                return

            if (
                external_state is not None
                and external_state.get("generation") == installation.generation
                and external_state.get("kind") == "ambiguous_lifecycle"
                and external_state.get("current_token_valid") is True
            ):
                # The event envelope cannot say whether this same-second event
                # predates reconnect. Preserve a valid, team-bound current
                # token instead of letting an ambiguous old event revoke it.
                _mark_receipt_processed(receipt)
                return

            if event_type in {"team_rename", "team_domain_change"}:
                if (
                    external_state is None
                    or external_state.get("generation") != installation.generation
                ):
                    _mark_receipt_processed(receipt)
                    return
                authentication_error = external_state.get("authentication_error")
                if isinstance(authentication_error, str):
                    revoke_installation(
                        installation,
                        authentication_error,
                        expected_generation=installation.generation,
                    )
                    _mark_receipt_processed(receipt)
                    return
                team = external_state.get("team")
                snapshot_at = external_state.get("snapshot_at")
                if not isinstance(team, dict) or snapshot_at is None:
                    raise SlackClientError("Slack team metadata snapshot is incomplete")
                sync_slack_team_metadata(
                    installation,
                    team,
                    snapshot_at=snapshot_at,
                )
                _mark_receipt_processed(receipt)
                return

            _process_event(
                installation,
                event,
                event_time=receipt.event_time,
            )
            _mark_receipt_processed(receipt)
    except _SlackEventDeferred as exc:
        retry_error = exc
        retry_countdown = exc.retry_after
    except _SlackLifecycleValidationError as exc:
        retry_error = exc
        retry_countdown = exc.retry_after
    except SlackRateLimited as exc:
        retry_error = exc
        retry_countdown = exc.retry_after
    except SlackClientError as exc:
        retry_error = exc
    except Exception as exc:
        retry_error = exc

    if retry_error is None:
        return
    if isinstance(retry_error, _SlackEventDeferred):
        should_schedule = _record_event_deferral(
            receipt_id,
            claimed_attempt,
            retry_error,
            countdown=retry_countdown,
        )
    else:
        should_schedule = _record_event_failure(
            receipt_id,
            claimed_attempt,
            retry_error,
            countdown=retry_countdown,
            fail_closed_generation=(
                retry_error.expected_generation
                if isinstance(retry_error, _SlackLifecycleValidationError)
                else None
            ),
        )
    if should_schedule:
        try:
            process_slack_event.apply_async(
                args=[str(receipt_id)],
                countdown=retry_countdown,
            )
        except Exception:
            # The durable FAILED row remains eligible for the periodic sweep.
            pass
