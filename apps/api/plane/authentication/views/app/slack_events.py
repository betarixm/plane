# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from plane.bgtasks.slack_sync import enqueue_slack_event_receipt
from plane.db.models import IdentitySource, SlackEventReceipt
from plane.integrations.identity import configured_identity_provider
from plane.integrations.slack import get_slack_credentials, verify_slack_signature


ORDERED_EVENT_TYPES = frozenset(
    {
        "app_uninstalled",
        "team_domain_change",
        "team_join",
        "team_rename",
        "tokens_revoked",
        "user_change",
    }
)
USER_EVENT_TYPES = frozenset({"team_join", "user_change"})


def _event_datetime(value) -> datetime | None:
    try:
        timestamp = Decimal(str(value))
        if timestamp <= 0:
            return None
        return datetime.fromtimestamp(float(timestamp), tz=UTC)
    except (InvalidOperation, OSError, OverflowError, TypeError, ValueError):
        return None


@method_decorator(csrf_exempt, name="dispatch")
class SlackEventsEndpoint(View):
    """Verify, deduplicate, and enqueue Slack Events API deliveries."""

    def post(self, request):
        if configured_identity_provider() != IdentitySource.Provider.SLACK:
            return JsonResponse({"error": "Slack Events API is not configured"}, status=503)
        signing_secret = get_slack_credentials().signing_secret
        if not signing_secret:
            return JsonResponse({"error": "Slack Events API is not configured"}, status=503)

        body = request.body
        if not verify_slack_signature(
            signing_secret=signing_secret,
            timestamp=request.headers.get("X-Slack-Request-Timestamp", ""),
            body=body,
            signature=request.headers.get("X-Slack-Signature", ""),
        ):
            return JsonResponse({"error": "Invalid Slack signature"}, status=401)

        try:
            payload = json.loads(body)
        except (TypeError, ValueError):
            return JsonResponse({"error": "Invalid JSON payload"}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({"error": "Invalid Slack event payload"}, status=400)

        if payload.get("type") == "url_verification":
            challenge = payload.get("challenge")
            if not isinstance(challenge, str):
                return JsonResponse({"error": "Missing Slack challenge"}, status=400)
            return JsonResponse({"challenge": challenge})

        if payload.get("type") != "event_callback":
            return JsonResponse({"ok": True})

        event_id = str(payload.get("event_id") or "").strip()
        team_id = str(payload.get("team_id") or "").strip()
        event = payload.get("event")
        if not event_id or not team_id or not isinstance(event, dict) or not event:
            return JsonResponse({"error": "Incomplete Slack event payload"}, status=400)
        installation = IdentitySource.objects.only(
            "external_organization_id",
            "generation",
        ).filter(provider=IdentitySource.Provider.SLACK).first()
        if installation is not None and installation.external_organization_id != team_id:
            # Slack signs events for every workspace where this app is installed.
            # Once the singleton source is bound, acknowledge foreign-workspace
            # deliveries without turning them into durable work. A generation-0
            # receipt is reserved for the installation-free bootstrap window.
            return JsonResponse({"ok": True})

        event_type = str(event.get("type") or "unknown")
        event_time = _event_datetime(payload.get("event_time"))
        if event_type in ORDERED_EVENT_TYPES and event_time is None:
            return JsonResponse({"error": "Missing Slack event time"}, status=400)
        if event_type in USER_EVENT_TYPES and _event_datetime(event.get("event_ts")) is None:
            return JsonResponse({"error": "Missing Slack user event timestamp"}, status=400)
        try:
            with transaction.atomic():
                receipt, created = SlackEventReceipt.objects.get_or_create(
                    event_id=event_id,
                    defaults={
                        "source": installation,
                        "team_id": team_id,
                        "event_type": event_type,
                        "source_generation": (
                            installation.generation if installation is not None else 0
                        ),
                        "event_time": event_time,
                        "payload": event,
                    },
                )
        except IntegrityError:
            receipt = SlackEventReceipt.objects.get(event_id=event_id)
            created = False

        if not created and receipt.team_id != team_id:
            return JsonResponse({"error": "Slack event ID collision"}, status=400)
        if not created:
            # The original delivery is already durable. Never wait on its row
            # lock while Slack is retrying the same event.
            return JsonResponse({"ok": True})

        # Best-effort immediate dispatch uses a no-retry publish and a bounded
        # broker connect timeout. The receipt is already durable, so a publish
        # failure is acknowledged and the outbox sweep safely recovers it.
        try:
            enqueue_slack_event_receipt(str(receipt.id))
        except Exception:
            pass
        return JsonResponse({"ok": True})
