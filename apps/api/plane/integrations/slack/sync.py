# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import pytz
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from plane.db.models import (
    Profile,
    ProjectMember,
    Session,
    ExternalIdentity,
    IdentitySource,
    SlackUserTombstone,
    User,
    Workspace,
    WorkspaceMember,
)

from .client import SlackAuthenticationError, SlackClient, SlackClientError

SLACK_ADMIN_ROLE = 20
SLACK_MEMBER_ROLE = 15
SLACK_GUEST_ROLE = 5

logger = logging.getLogger(__name__)


def _require_slack_source(source: IdentitySource) -> None:
    if source.provider != IdentitySource.Provider.SLACK:
        raise SlackClientError("Identity source is not configured for Slack")


def slack_role_for_user(payload: dict[str, Any]) -> int:
    """Map Slack's authoritative team role to Plane's workspace role."""

    if payload.get("is_restricted") or payload.get("is_ultra_restricted"):
        return SLACK_GUEST_ROLE
    if payload.get("is_admin") or payload.get("is_owner") or payload.get("is_primary_owner"):
        return SLACK_ADMIN_ROLE
    return SLACK_MEMBER_ROLE


def _is_bot(payload: dict[str, Any]) -> bool:
    external_user_id = str(payload.get("id") or "")
    return bool(
        external_user_id == "USLACKBOT"
        or str(payload.get("name") or "").lower() == "slackbot"
        or payload.get("is_bot")
        or payload.get("is_app_user")
        or payload.get("is_workflow_bot")
        or payload.get("is_agentforce_bot")
    )


def _is_inactive(payload: dict[str, Any]) -> bool:
    return bool(
        payload.get("deleted")
        or payload.get("suspended")
        or payload.get("is_forgotten")
        or payload.get("is_invited_user")
        or payload.get("is_profile_only_user")
    )


def _normalized_email(profile: dict[str, Any]) -> str | None:
    raw_email = profile.get("email")
    if not raw_email:
        return None
    email = str(raw_email).strip().lower()
    try:
        validate_email(email)
    except ValidationError:
        return None
    return email


def _available_local_email(
    *,
    real_email: str | None,
    user_id=None,
) -> str | None:
    if real_email:
        collision = User.objects.filter(email=real_email)
        if user_id is not None:
            collision = collision.exclude(pk=user_id)
        if not collision.exists():
            return real_email
    return None


def _profile_value(profile: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = profile.get(key)
        if value:
            return str(value)
    return ""


def _avatar_url(profile: dict[str, Any]) -> str:
    return _profile_value(
        profile,
        "image_original",
        "image_512",
        "image_192",
        "image_72",
        "image_48",
    )


def _timestamp_value(raw_value: Any) -> int:
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError):
        return 0
    if not value.is_finite() or value <= 0:
        return 0
    return int(value * 1_000_000)


def _datetime_value(raw_value: Any):
    timestamp = _timestamp_value(raw_value)
    if not timestamp:
        return None
    seconds, microseconds = divmod(timestamp, 1_000_000)
    try:
        return datetime.fromtimestamp(seconds, tz=UTC).replace(microsecond=microseconds)
    except (OSError, OverflowError, ValueError):
        return None


def _source_updated_at(payload: dict[str, Any], fallback: Any = None) -> int:
    return max(
        _timestamp_value(payload.get("updated")),
        _timestamp_value(fallback),
    )


def sync_slack_team_metadata(
    installation: IdentitySource,
    team: dict[str, Any],
    *,
    snapshot_at,
) -> bool:
    """Apply the newest-started ``team.info`` snapshot.

    Slack's rename/domain event payloads have only second-granularity envelope
    timestamps. Refreshing ``team.info`` and fencing writes by the local
    request-start time prevents delayed events and a slower full roster
    reconciliation from restoring older workspace metadata.
    """

    _require_slack_source(installation)
    if str(team.get("id") or "") != installation.external_organization_id:
        raise SlackClientError("Slack team.info returned the wrong team")
    if installation.metadata_synced_at is not None and installation.metadata_synced_at >= snapshot_at:
        return False

    team_name = str(team.get("name") or installation.external_organization_name)
    team_domain = str(team.get("domain") or "")
    team_icon_url = _team_icon_url(team)
    installation.external_organization_name = team_name
    installation.external_organization_domain = team_domain
    installation.external_organization_icon_url = team_icon_url
    installation.metadata_synced_at = snapshot_at
    installation.save(
        update_fields=[
            "external_organization_name",
            "external_organization_domain",
            "external_organization_icon_url",
            "metadata_synced_at",
            "updated_at",
        ]
    )

    workspace = Workspace.objects.select_for_update().get(pk=installation.workspace_id)
    workspace.name = team_name[:80]
    workspace.logo = team_icon_url
    workspace.logo_asset = None
    workspace.save(update_fields=["name", "logo", "logo_asset", "updated_at"])

    from plane.license.models import Instance

    instance = Instance.objects.select_for_update().first()
    if instance is not None:
        instance.instance_name = team_name
        instance.save(update_fields=["instance_name", "updated_at"])
    return True


def _record_user_tombstone(
    *,
    installation: IdentitySource,
    external_user_id: str,
    source_updated_at: int,
    authoritative_started_at=None,
    observed_at=None,
) -> SlackUserTombstone:
    """Persist a negative user projection without manufacturing a local user."""

    tombstone = SlackUserTombstone.objects.select_for_update().filter(
        source=installation,
        external_user_id=external_user_id,
    ).first()
    observed_at = observed_at or authoritative_started_at or timezone.now()
    if tombstone is None:
        return SlackUserTombstone.objects.create(
            source=installation,
            external_user_id=external_user_id,
            source_updated_at=source_updated_at,
            source_generation=installation.generation,
            snapshot_terminal_at=authoritative_started_at,
            observed_at=observed_at,
        )
    same_generation = tombstone.source_generation == installation.generation
    if same_generation:
        newer_source = source_updated_at > tombstone.source_updated_at
        newer_snapshot = bool(
            authoritative_started_at is not None
            and (
                tombstone.snapshot_terminal_at is None
                or authoritative_started_at > tombstone.snapshot_terminal_at
            )
        )
        if not newer_source and not newer_snapshot:
            return tombstone
        tombstone.source_updated_at = max(tombstone.source_updated_at, source_updated_at)
        if newer_snapshot:
            tombstone.snapshot_terminal_at = authoritative_started_at
    else:
        tombstone.source_updated_at = source_updated_at
        tombstone.snapshot_terminal_at = authoritative_started_at
    tombstone.source_generation = installation.generation
    tombstone.observed_at = observed_at
    tombstone.save(
        update_fields=[
            "source_updated_at",
            "source_generation",
            "snapshot_terminal_at",
            "observed_at",
            "updated_at",
        ]
    )
    return tombstone


def deactivate_identity(
    identity: ExternalIdentity,
    *,
    deactivate_project_memberships: bool = True,
    source_updated_at: int = 0,
    snapshot_absent_at=None,
    clear_snapshot_absence: bool = False,
    source_generation: int | None = None,
    observed_at=None,
    authoritative_synced_at=None,
) -> None:
    """Deactivate a Slack-owned identity and revoke all of its local sessions."""

    with transaction.atomic():
        identity = ExternalIdentity.objects.select_for_update().select_related("user").get(pk=identity.pk)
        now = timezone.now()
        projection_observed_at = observed_at or now
        identity.is_active = False
        if source_updated_at > identity.source_updated_at:
            identity.source_updated_at = source_updated_at
        if source_generation is not None:
            identity.source_generation = source_generation
        if authoritative_synced_at is not None and (
            identity.authoritative_synced_at is None
            or authoritative_synced_at > identity.authoritative_synced_at
        ):
            identity.authoritative_synced_at = authoritative_synced_at
        if clear_snapshot_absence:
            identity.snapshot_absent_at = None
        elif snapshot_absent_at is not None and (
            identity.snapshot_absent_at is None
            or snapshot_absent_at > identity.snapshot_absent_at
        ):
            identity.snapshot_absent_at = snapshot_absent_at
        identity.synced_at = projection_observed_at
        identity.save(
            update_fields=[
                "is_active",
                "source_updated_at",
                "source_generation",
                "authoritative_synced_at",
                "snapshot_absent_at",
                "synced_at",
                "updated_at",
            ]
        )

        User.objects.filter(pk=identity.user_id).update(
            is_active=False,
            updated_at=now,
        )
        WorkspaceMember.objects.filter(member_id=identity.user_id, is_active=True).update(
            is_active=False,
            updated_at=now,
        )
        if deactivate_project_memberships:
            ProjectMember.objects.filter(member_id=identity.user_id, is_active=True).update(
                is_active=False,
                updated_at=now,
            )
        Session.objects.filter(user_id=str(identity.user_id)).delete()


def revoke_installation(
    installation: IdentitySource,
    reason: str,
    *,
    expected_generation: int | None = None,
    expected_no_success_since=None,
) -> bool:
    """Fail closed when Slack can no longer authenticate the identity source."""

    with transaction.atomic():
        installation = IdentitySource.objects.select_for_update().get(pk=installation.pk)
        _require_slack_source(installation)
        if expected_generation is not None and installation.generation != expected_generation:
            return False
        if (
            expected_no_success_since is not None
            and installation.last_synced_at is not None
            and installation.last_synced_at >= expected_no_success_since
        ):
            return False
        installation.status = IdentitySource.Status.REVOKED
        installation.encrypted_access_token = ""
        installation.sync_error = reason[:2000]
        installation.sync_error_at = timezone.now()
        installation.save(
            update_fields=[
                "status",
                "encrypted_access_token",
                "sync_error",
                "sync_error_at",
                "updated_at",
            ]
        )
        for identity in installation.identities.select_related("user"):
            # An installation outage suspends workspace access but must not
            # erase local project authorization that should return on reconnect.
            deactivate_identity(identity, deactivate_project_memberships=False)
    return True


def sync_slack_user(
    installation: IdentitySource,
    payload: dict[str, Any],
    *,
    user: User | None = None,
    source_timestamp: Any = None,
    authoritative: bool = False,
    authoritative_started_at=None,
) -> ExternalIdentity | None:
    """Project one Slack member into local user/profile/membership read models."""

    expected_generation = installation.generation
    external_user_id = str(payload.get("id") or "").strip()
    if not external_user_id:
        raise ValueError("Slack user payload is missing id")

    payload_team_id = str(payload.get("team_id") or "")

    with transaction.atomic():
        installation = (
            IdentitySource.objects.select_for_update()
            .select_related("workspace")
            .get(pk=installation.pk)
        )
        _require_slack_source(installation)
        if installation.generation != expected_generation:
            raise SlackClientError(
                "Slack installation changed while the member payload was in flight"
            )
        if installation.status == IdentitySource.Status.REVOKED:
            raise SlackClientError("Slack installation has been revoked")
        identity = (
            ExternalIdentity.objects.select_for_update()
            .select_related("user")
            .filter(source=installation, external_user_id=external_user_id)
            .first()
        )
        tombstone = SlackUserTombstone.objects.select_for_update().filter(
            source=installation,
            external_user_id=external_user_id,
            source_generation=installation.generation,
        ).first()
        if identity is not None and user is not None and identity.user_id != user.id:
            raise ValueError("Slack identity is already bound to another local user")

        foreign_user = payload.get("is_stranger") or payload.get("is_external") or (
            payload_team_id and payload_team_id != installation.external_organization_id
        )
        terminal_projection = bool(foreign_user or _is_bot(payload) or _is_inactive(payload))
        source_updated_at = _source_updated_at(payload, source_timestamp)
        event_source_updated_at = _timestamp_value(source_timestamp)
        event_observed_at = _datetime_value(source_timestamp)
        projection_observed_at = (
            authoritative_started_at
            if authoritative and authoritative_started_at is not None
            else event_observed_at or timezone.now()
        )
        if identity is not None:
            if (
                authoritative_started_at is not None
                and identity.synced_at >= authoritative_started_at
            ):
                if identity.source_generation != installation.generation:
                    raise SlackClientError(
                        "Slack identity changed while an authoritative lookup was in flight"
                    )
                return identity
            generation_changed = identity.source_generation != installation.generation
            if not authoritative and not generation_changed:
                if identity.authoritative_synced_at is not None and (
                    not event_source_updated_at
                    or event_source_updated_at
                    <= _timestamp_value(identity.authoritative_synced_at.timestamp())
                ):
                    return identity
                if source_updated_at and source_updated_at < identity.source_updated_at:
                    return identity
                if (
                    not terminal_projection
                    and identity.source_updated_at
                    and source_updated_at <= identity.source_updated_at
                ):
                    return identity
                if (
                    not terminal_projection
                    and identity.snapshot_absent_at is not None
                    and (
                        not event_source_updated_at
                        or event_source_updated_at
                        <= _timestamp_value(identity.snapshot_absent_at.timestamp())
                    )
                ):
                    return identity

        if (
            identity is None
            and tombstone is not None
            and authoritative_started_at is not None
            and tombstone.observed_at >= authoritative_started_at
        ):
            return None

        if identity is None and tombstone is not None and not terminal_projection:
            if (
                not authoritative
                and (
                    not source_updated_at
                    or source_updated_at <= tombstone.source_updated_at
                )
            ):
                return None
            if (
                not authoritative
                and tombstone.snapshot_terminal_at is not None
                and (
                    not event_source_updated_at
                    or event_source_updated_at
                    <= _timestamp_value(tombstone.snapshot_terminal_at.timestamp())
                )
            ):
                return None

        if foreign_user:
            if identity is not None:
                deactivate_identity(
                    identity,
                    source_updated_at=source_updated_at,
                    clear_snapshot_absence=True,
                    source_generation=installation.generation,
                    observed_at=projection_observed_at,
                    authoritative_synced_at=authoritative_started_at,
                )
            else:
                _record_user_tombstone(
                    installation=installation,
                    external_user_id=external_user_id,
                    source_updated_at=source_updated_at,
                    authoritative_started_at=authoritative_started_at,
                    observed_at=projection_observed_at,
                )
            return None

        if _is_bot(payload):
            if identity is not None:
                deactivate_identity(
                    identity,
                    source_updated_at=source_updated_at,
                    clear_snapshot_absence=True,
                    source_generation=installation.generation,
                    observed_at=projection_observed_at,
                    authoritative_synced_at=authoritative_started_at,
                )
            else:
                _record_user_tombstone(
                    installation=installation,
                    external_user_id=external_user_id,
                    source_updated_at=source_updated_at,
                    authoritative_started_at=authoritative_started_at,
                    observed_at=projection_observed_at,
                )
            return None

        if _is_inactive(payload):
            if identity is not None:
                deactivate_identity(
                    identity,
                    source_updated_at=source_updated_at,
                    clear_snapshot_absence=True,
                    source_generation=installation.generation,
                    observed_at=projection_observed_at,
                    authoritative_synced_at=authoritative_started_at,
                )
            else:
                _record_user_tombstone(
                    installation=installation,
                    external_user_id=external_user_id,
                    source_updated_at=source_updated_at,
                    authoritative_started_at=authoritative_started_at,
                    observed_at=projection_observed_at,
                )
            return identity

        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
        role = slack_role_for_user(payload)
        real_email = _normalized_email(profile)
        local_email = _available_local_email(
            real_email=real_email,
            user_id=(identity.user_id if identity is not None else user.id if user is not None else None),
        )
        display_name = _profile_value(
            profile,
            "display_name_normalized",
            "display_name",
            "real_name_normalized",
            "real_name",
        ) or str(payload.get("real_name") or payload.get("name") or external_user_id)
        first_name = _profile_value(profile, "first_name")
        last_name = _profile_value(profile, "last_name")
        avatar = _avatar_url(profile)
        user_timezone = str(payload.get("tz") or "UTC")
        if user_timezone not in pytz.common_timezones:
            user_timezone = "UTC"
        now = timezone.now()

        if identity is None and user is None:
            username_source = (
                f"{installation.external_organization_id}:{external_user_id}"
            )
            username_digest = hashlib.sha256(username_source.encode()).hexdigest()[:32]
            user = User(
                email=local_email,
                username=f"slack-{username_digest}",
                display_name=display_name,
                first_name=first_name,
                last_name=last_name,
                avatar=avatar,
                user_timezone=user_timezone,
                is_active=True,
            )
            user.save()
            Profile.objects.create(user=user)
            identity = ExternalIdentity.objects.create(
                user=user,
                source=installation,
                external_user_id=external_user_id,
                workspace_role=role,
                source_generation=installation.generation,
            )
        else:
            if identity is not None:
                user = identity.user
            else:
                user = User.objects.select_for_update().get(pk=user.pk)
                if ExternalIdentity.objects.filter(user=user).exists():
                    raise ValueError("Local user is already bound to another Slack identity")
            User.objects.filter(pk=user.pk).update(
                email=local_email,
                display_name=display_name,
                first_name=first_name,
                last_name=last_name,
                avatar=avatar,
                avatar_asset=None,
                cover_image=None,
                cover_image_asset=None,
                user_timezone=user_timezone,
                is_active=True,
                updated_at=now,
            )
            # Keep the returned identity's related User coherent with the
            # direct update above. Login consumes this object immediately,
            # including when a previously deleted Slack member is reactivated.
            user.email = local_email
            user.display_name = display_name
            user.first_name = first_name
            user.last_name = last_name
            user.avatar = avatar
            user.avatar_asset = None
            user.cover_image = None
            user.cover_image_asset = None
            user.user_timezone = user_timezone
            user.is_active = True
            user.updated_at = now
            Profile.objects.get_or_create(user=user)
            if identity is None:
                identity = ExternalIdentity.objects.create(
                    user=user,
                    source=installation,
                    external_user_id=external_user_id,
                    workspace_role=role,
                    source_generation=installation.generation,
                )

        identity.profile = profile
        identity.is_active = True
        identity.workspace_role = role
        identity.source_generation = installation.generation
        identity.snapshot_absent_at = None
        if authoritative_started_at is not None and (
            identity.authoritative_synced_at is None
            or authoritative_started_at > identity.authoritative_synced_at
        ):
            identity.authoritative_synced_at = authoritative_started_at
        if source_updated_at > identity.source_updated_at:
            identity.source_updated_at = source_updated_at
        identity.synced_at = projection_observed_at
        identity.save(
            update_fields=[
                "profile",
                "is_active",
                "workspace_role",
                "source_updated_at",
                "source_generation",
                "authoritative_synced_at",
                "snapshot_absent_at",
                "synced_at",
                "updated_at",
            ]
        )

        workspace_member, workspace_member_created = WorkspaceMember.objects.get_or_create(
            workspace=installation.workspace,
            member=user,
            defaults={"role": role, "is_active": True},
        )
        workspace_access_changed = not workspace_member_created and (
            workspace_member.role != role or not workspace_member.is_active
        )
        if workspace_access_changed:
            workspace_member.role = role
            workspace_member.is_active = True
            workspace_member.save(update_fields=["role", "is_active", "updated_at"])

        if role in {SLACK_GUEST_ROLE, SLACK_ADMIN_ROLE}:
            ProjectMember.objects.filter(
                workspace=installation.workspace,
                member=user,
            ).exclude(role=role).update(
                role=role,
                updated_at=now,
            )

        SlackUserTombstone.all_objects.filter(
            source=installation,
            external_user_id=external_user_id,
        ).delete()

        return identity


def _team_icon_url(team: dict[str, Any]) -> str:
    icon = team.get("icon") if isinstance(team.get("icon"), dict) else {}
    return _profile_value(icon, "image_original", "image_230", "image_132", "image_102", "image_68")


def reconcile_installation(
    installation: IdentitySource,
    *,
    client: SlackClient | None = None,
) -> None:
    """Fully reconcile workspace metadata and members from the bound Slack team."""

    reconcile_started_at = timezone.now()
    expected_generation = installation.generation
    if installation.status == IdentitySource.Status.REVOKED:
        raise SlackClientError("Slack installation has been revoked")
    _require_slack_source(installation)

    if client is None:
        try:
            bot_token = installation.access_token
        except ValueError as exc:
            raise SlackAuthenticationError(
                "Slack bot token could not be decrypted",
                error_code="bot_token_decryption_failed",
            ) from exc
        client = SlackClient(bot_token=bot_token)
    team_snapshot_at = timezone.now()
    team_response = client.team_info()
    team = team_response.get("team")
    if not isinstance(team, dict) or str(team.get("id") or "") != installation.external_organization_id:
        raise SlackClientError("Slack team.info returned the wrong team")

    members: list[dict[str, Any]] = []
    cursor = None
    seen_cursors: set[str] = set()
    while True:
        response = client.users_list(cursor=cursor)
        page_members = response.get("members")
        if not isinstance(page_members, list):
            raise SlackClientError("Slack users.list response is missing members")
        members.extend(member for member in page_members if isinstance(member, dict))

        response_metadata = response.get("response_metadata")
        next_cursor = (
            str(response_metadata.get("next_cursor") or "").strip() if isinstance(response_metadata, dict) else ""
        )
        if not next_cursor:
            break
        if next_cursor in seen_cursors:
            raise SlackClientError("Slack users.list returned a repeated cursor")
        seen_cursors.add(next_cursor)
        cursor = next_cursor

    with transaction.atomic():
        installation = (
            IdentitySource.objects.select_for_update()
            .select_related("workspace")
            .get(pk=installation.pk)
        )
        if installation.generation != expected_generation:
            return
        if installation.status == IdentitySource.Status.REVOKED:
            raise SlackClientError("Slack installation has been revoked")
        sync_slack_team_metadata(
            installation,
            team,
            snapshot_at=team_snapshot_at,
        )

        recently_synced_ids = set(
            installation.identities.filter(synced_at__gte=reconcile_started_at).values_list(
                "external_user_id",
                flat=True,
            )
        )
        seen_external_user_ids: set[str] = set()
        for member in members:
            external_user_id = str(member.get("id") or "").strip()
            if not external_user_id:
                continue
            seen_external_user_ids.add(external_user_id)
            if external_user_id in recently_synced_ids:
                continue
            sync_slack_user(
                installation,
                member,
                authoritative=True,
                authoritative_started_at=reconcile_started_at,
            )

        stale_identities = installation.identities.filter(synced_at__lt=reconcile_started_at).exclude(
            external_user_id__in=seen_external_user_ids
        )
        for identity in stale_identities.select_related("user"):
            deactivate_identity(
                identity,
                snapshot_absent_at=reconcile_started_at,
                source_generation=installation.generation,
                observed_at=reconcile_started_at,
                authoritative_synced_at=reconcile_started_at,
            )

        if (
            installation.last_synced_at is None
            or installation.last_synced_at < reconcile_started_at
        ):
            installation.status = IdentitySource.Status.ACTIVE
            installation.last_synced_at = reconcile_started_at
            update_fields = [
                "status",
                "last_synced_at",
                "updated_at",
            ]
            if (
                installation.sync_error_at is None
                or installation.sync_error_at <= reconcile_started_at
            ):
                installation.sync_error = ""
                installation.sync_error_at = None
                update_fields.extend(["sync_error", "sync_error_at"])
            installation.save(
                update_fields=update_fields
            )
