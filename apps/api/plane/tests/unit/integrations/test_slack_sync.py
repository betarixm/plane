# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import json
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from celery.exceptions import Retry
from django.db import IntegrityError, transaction
from django.utils import timezone

from plane.bgtasks.slack_sync import (
    delete_old_slack_event_receipts,
    publish_live_user_revocation,
    reconcile_slack_installation,
)
from plane.db.models import (
    FileAsset,
    Profile,
    Project,
    ProjectMember,
    Session,
    SlackEventReceipt,
    ExternalIdentity,
    IdentitySource,
    SlackUserTombstone,
    User,
    WorkspaceMember,
)
from plane.integrations.slack import (
    SlackAuthenticationError,
    SlackClientError,
    deactivate_identity,
    reconcile_installation,
    revoke_installation,
    slack_role_for_user,
    sync_slack_team_metadata,
    sync_slack_user,
)
from plane.license.models import Instance

pytestmark = pytest.mark.unit


def slack_user(
    external_user_id="U123",
    *,
    email="member@example.com",
    is_admin=False,
    is_restricted=False,
    deleted=False,
    suspended=False,
    is_forgotten=False,
    is_external=False,
    is_bot=False,
):
    return {
        "id": external_user_id,
        "team_id": "T123",
        "name": "member",
        "real_name": "Slack Member",
        "deleted": deleted,
        "suspended": suspended,
        "is_forgotten": is_forgotten,
        "is_external": is_external,
        "is_bot": is_bot,
        "is_admin": is_admin,
        "is_owner": False,
        "is_primary_owner": False,
        "is_restricted": is_restricted,
        "is_ultra_restricted": False,
        "updated": 1_700_000_000,
        "tz": "Asia/Seoul",
        "profile": {
            "email": email,
            "display_name": "slack-display",
            "real_name": "Slack Member",
            "first_name": "Slack",
            "last_name": "Member",
            "title": "Engineering",
            "image_192": "https://avatars.slack-edge.com/member.png",
        },
    }


@pytest.fixture
def installation(workspace):
    installation = IdentitySource(
        workspace=workspace,
        provider=IdentitySource.Provider.SLACK,
        external_organization_id="T123",
        external_organization_name="Slack Team",
    )
    installation.set_access_token("xoxb-secret")
    installation.save()
    return installation


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("payload", "expected_role"),
    [
        ({"is_admin": True}, 20),
        ({"is_owner": True}, 20),
        ({"is_primary_owner": True}, 20),
        ({}, 15),
        ({"is_restricted": True, "is_admin": True}, 5),
        ({"is_ultra_restricted": True}, 5),
    ],
)
def test_slack_role_mapping(payload, expected_role):
    assert slack_role_for_user(payload) == expected_role


@pytest.mark.django_db
def test_sync_projects_authoritative_slack_profile_and_admin_membership(installation):
    identity = sync_slack_user(installation, slack_user(is_admin=True))

    assert identity is not None
    identity.refresh_from_db()
    identity.user.refresh_from_db()
    membership = WorkspaceMember.objects.get(workspace=installation.workspace, member=identity.user)
    profile = Profile.objects.get(user=identity.user)

    assert identity.external_user_id == "U123"
    assert identity.user.email == "member@example.com"
    assert identity.user.display_name == "slack-display"
    assert identity.user.first_name == "Slack"
    assert identity.user.last_name == "Member"
    assert identity.user.avatar == "https://avatars.slack-edge.com/member.png"
    assert identity.user.user_timezone == "Asia/Seoul"
    assert identity.user.is_active is True
    assert identity.profile["title"] == "Engineering"
    assert profile.theme == {}
    assert membership.role == 20
    assert membership.is_active is True


@pytest.mark.django_db
def test_sync_clears_local_cover_fields_that_slack_does_not_own(installation):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None
    cover_asset = FileAsset.objects.create(
        workspace=installation.workspace,
        user=identity.user,
        asset=f"{installation.workspace_id}/local-cover.png",
        entity_type=FileAsset.EntityTypeContext.USER_COVER,
        is_uploaded=True,
    )
    identity.user.cover_image = "https://local.example/cover.png"
    identity.user.cover_image_asset = cover_asset
    identity.user.save(update_fields=["cover_image", "cover_image_asset"])
    refreshed_payload = slack_user()
    refreshed_payload["updated"] += 1

    refreshed_identity = sync_slack_user(installation, refreshed_payload)

    assert refreshed_identity is not None
    refreshed_identity.user.refresh_from_db()
    assert refreshed_identity.user.cover_image is None
    assert refreshed_identity.user.cover_image_asset_id is None


@pytest.mark.django_db
def test_slack_guest_role_caps_existing_project_authority(installation):
    identity = sync_slack_user(installation, slack_user(is_admin=True))
    assert identity is not None
    project = Project.objects.create(
        name="Slack role project",
        identifier="SLACKROLE",
        workspace=installation.workspace,
    )
    project_member = ProjectMember.objects.create(
        project=project,
        workspace=installation.workspace,
        member=identity.user,
        role=20,
        is_active=False,
    )
    guest_payload = slack_user(is_restricted=True)
    guest_payload["updated"] += 1

    sync_slack_user(installation, guest_payload)

    project_member.refresh_from_db()
    membership = WorkspaceMember.objects.get(
        workspace=installation.workspace,
        member=identity.user,
    )
    assert membership.role == 5
    assert project_member.role == 5
    assert project_member.is_active is False


@pytest.mark.django_db
def test_slack_admin_promotion_updates_existing_project_authority(installation):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None
    project = Project.objects.create(
        name="Slack admin project",
        identifier="SLACKADMIN",
        workspace=installation.workspace,
    )
    project_member = ProjectMember.objects.create(
        project=project,
        workspace=installation.workspace,
        member=identity.user,
        role=5,
    )
    admin_payload = slack_user(is_admin=True)
    admin_payload["updated"] += 1

    sync_slack_user(installation, admin_payload)

    project_member.refresh_from_db()
    assert project_member.role == 20


@pytest.mark.django_db
def test_sync_never_links_by_email_and_leaves_a_colliding_local_email_empty(installation):
    existing = User.objects.create(email="member@example.com", username="existing-user")

    identity = sync_slack_user(installation, slack_user())

    assert identity is not None
    assert identity.user_id != existing.id
    assert identity.user.email is None
    assert sync_slack_user(installation, slack_user()).user.email is None


@pytest.mark.django_db
def test_sync_skips_slack_bots(installation):
    user_count = User.objects.count()

    assert sync_slack_user(installation, slack_user("UBOT", is_bot=True)) is None
    assert sync_slack_user(installation, slack_user("USLACKBOT")) is None
    assert User.objects.count() == user_count
    assert ExternalIdentity.objects.count() == 0


@pytest.mark.django_db
def test_sync_excludes_slack_connect_strangers(installation):
    identity = sync_slack_user(installation, slack_user("UEXTERNAL"))
    assert identity is not None

    external_payload = slack_user("UEXTERNAL")
    external_payload["team_id"] = "TOTHER"
    external_payload["is_stranger"] = True

    assert sync_slack_user(installation, external_payload) is None
    identity.refresh_from_db()
    identity.user.refresh_from_db()
    membership = WorkspaceMember.objects.get(
        workspace=installation.workspace,
        member=identity.user,
    )
    assert identity.is_active is False
    assert identity.user.is_active is False
    assert membership.is_active is False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "inactive_flag",
    ["suspended", "is_forgotten"],
)
def test_sync_deactivates_inactive_slack_accounts(installation, inactive_flag):
    identity = sync_slack_user(installation, slack_user("UINACTIVE"))
    assert identity is not None
    inactive_payload = slack_user("UINACTIVE")
    inactive_payload[inactive_flag] = True
    inactive_payload["updated"] += 1

    sync_slack_user(installation, inactive_payload)

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    membership = WorkspaceMember.objects.get(
        workspace=installation.workspace,
        member=identity.user,
    )
    assert identity.is_active is False
    assert identity.user.is_active is False
    assert membership.is_active is False


@pytest.mark.django_db
def test_sync_excludes_same_team_external_users(installation):
    assert sync_slack_user(installation, slack_user("UEXTERNAL", is_external=True)) is None

    assert not ExternalIdentity.objects.filter(external_user_id="UEXTERNAL").exists()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "terminal_payload",
    [
        slack_user("UNEGATIVE", deleted=True),
        {**slack_user("UNEGATIVE", is_external=True), "team_id": "TOTHER"},
    ],
)
def test_nonexistent_terminal_event_blocks_an_inflight_active_snapshot(
    installation,
    terminal_payload,
):
    snapshot_started_at = timezone.now()
    event_timestamp = snapshot_started_at.timestamp() + 1

    assert (
        sync_slack_user(
            installation,
            terminal_payload,
            source_timestamp=event_timestamp,
        )
        is None
    )
    result = sync_slack_user(
        installation,
        slack_user("UNEGATIVE"),
        authoritative=True,
        authoritative_started_at=snapshot_started_at,
    )

    assert result is None
    assert not ExternalIdentity.objects.filter(external_user_id="UNEGATIVE").exists()
    assert SlackUserTombstone.objects.filter(external_user_id="UNEGATIVE").exists()


@pytest.mark.django_db
def test_stale_authoritative_terminal_lookup_cannot_fence_a_newer_active_event(
    installation,
):
    snapshot_started_at = timezone.now()
    identity = sync_slack_user(
        installation,
        slack_user("UNEWERACTIVE"),
        source_timestamp=snapshot_started_at.timestamp() + 1,
    )
    assert identity is not None

    result = sync_slack_user(
        installation,
        slack_user("UNEWERACTIVE", deleted=True),
        authoritative=True,
        authoritative_started_at=snapshot_started_at,
    )

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert result is not None
    assert identity.is_active is True
    assert identity.user.is_active is True
    assert not SlackUserTombstone.objects.filter(external_user_id="UNEWERACTIVE").exists()


@pytest.mark.django_db
def test_delayed_active_event_cannot_fence_a_newer_terminal_lookup(installation):
    identity = sync_slack_user(installation, slack_user("UOLDERACTIVE"))
    assert identity is not None
    snapshot_started_at = timezone.now()

    sync_slack_user(
        installation,
        slack_user("UOLDERACTIVE"),
        source_timestamp=snapshot_started_at.timestamp() - 1,
    )
    sync_slack_user(
        installation,
        slack_user("UOLDERACTIVE", deleted=True),
        authoritative=True,
        authoritative_started_at=snapshot_started_at,
    )

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is False
    assert identity.user.is_active is False
    assert identity.authoritative_synced_at == snapshot_started_at


@pytest.mark.django_db
def test_authoritative_active_lookup_recovers_from_an_older_tombstone(installation):
    assert (
        sync_slack_user(
            installation,
            slack_user("UAUTHRECOVERY", deleted=True),
            source_timestamp=timezone.now().timestamp(),
        )
        is None
    )
    lookup_started_at = timezone.now()

    identity = sync_slack_user(
        installation,
        slack_user("UAUTHRECOVERY"),
        authoritative=True,
        authoritative_started_at=lookup_started_at,
    )

    assert identity is not None
    assert identity.is_active is True
    assert identity.user.is_active is True
    assert not SlackUserTombstone.objects.filter(external_user_id="UAUTHRECOVERY").exists()


@pytest.mark.django_db
def test_delayed_terminal_event_cannot_override_a_newer_active_lookup(installation):
    event_at = timezone.now()
    authoritative_started_at = event_at + timedelta(seconds=1)
    identity = sync_slack_user(
        installation,
        slack_user("UNEWERAUTH"),
        authoritative=True,
        authoritative_started_at=authoritative_started_at,
    )
    assert identity is not None

    sync_slack_user(
        installation,
        slack_user("UNEWERAUTH", deleted=True),
        source_timestamp=event_at.timestamp(),
    )

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is True
    assert identity.user.is_active is True


@pytest.mark.django_db
def test_older_terminal_snapshot_cannot_block_a_newer_active_snapshot(installation):
    older_started_at = timezone.now()
    newer_started_at = older_started_at + timedelta(microseconds=1)
    sync_slack_user(
        installation,
        slack_user("UOVERLAPACTIVE", deleted=True),
        authoritative=True,
        authoritative_started_at=older_started_at,
    )

    identity = sync_slack_user(
        installation,
        slack_user("UOVERLAPACTIVE"),
        authoritative=True,
        authoritative_started_at=newer_started_at,
    )

    assert identity is not None
    assert identity.is_active is True
    assert identity.synced_at == newer_started_at
    assert not SlackUserTombstone.objects.filter(external_user_id="UOVERLAPACTIVE").exists()


@pytest.mark.django_db
def test_older_absence_cannot_block_a_newer_active_snapshot(installation):
    identity = sync_slack_user(installation, slack_user("UOVERLAPABSENCE"))
    assert identity is not None
    older_started_at = timezone.now()
    newer_started_at = older_started_at + timedelta(microseconds=1)

    deactivate_identity(
        identity,
        snapshot_absent_at=older_started_at,
        source_generation=installation.generation,
        observed_at=older_started_at,
        authoritative_synced_at=older_started_at,
    )
    refreshed = sync_slack_user(
        installation,
        slack_user("UOVERLAPABSENCE"),
        authoritative=True,
        authoritative_started_at=newer_started_at,
    )

    assert refreshed is not None
    assert refreshed.is_active is True
    assert refreshed.user.is_active is True
    assert refreshed.synced_at == newer_started_at


@pytest.mark.django_db
def test_user_tombstone_orders_delayed_and_newer_active_events(installation):
    terminal_timestamp = timezone.now().timestamp()
    assert (
        sync_slack_user(
            installation,
            slack_user("UTOMBSTONE", deleted=True),
            source_timestamp=terminal_timestamp,
        )
        is None
    )

    assert (
        sync_slack_user(
            installation,
            slack_user("UTOMBSTONE"),
            source_timestamp=terminal_timestamp - 1,
        )
        is None
    )
    assert SlackUserTombstone.objects.filter(external_user_id="UTOMBSTONE").exists()

    identity = sync_slack_user(
        installation,
        slack_user("UTOMBSTONE"),
        source_timestamp=terminal_timestamp + 1,
    )

    assert identity is not None
    assert identity.is_active is True
    assert not SlackUserTombstone.objects.filter(external_user_id="UTOMBSTONE").exists()


@pytest.mark.django_db
def test_authoritative_terminal_tombstone_blocks_an_older_active_event(installation):
    snapshot_started_at = timezone.now()
    terminal_payload = slack_user("USNAPSHOTTERMINAL", deleted=True)
    terminal_payload["updated"] = int(snapshot_started_at.timestamp()) - 100
    sync_slack_user(
        installation,
        terminal_payload,
        authoritative=True,
        authoritative_started_at=snapshot_started_at,
    )
    delayed_active = slack_user("USNAPSHOTTERMINAL")
    delayed_active["updated"] = int(snapshot_started_at.timestamp()) + 100

    result = sync_slack_user(
        installation,
        delayed_active,
        source_timestamp=snapshot_started_at.timestamp() - 1,
    )

    assert result is None
    tombstone = SlackUserTombstone.objects.get(external_user_id="USNAPSHOTTERMINAL")
    assert tombstone.snapshot_terminal_at == snapshot_started_at


@pytest.mark.django_db
def test_old_generation_tombstone_does_not_block_reconnected_projection(installation):
    sync_slack_user(
        installation,
        slack_user("URECONNECTED", deleted=True),
        source_timestamp=timezone.now().timestamp(),
    )
    installation.generation += 1
    installation.save(update_fields=["generation", "updated_at"])

    identity = sync_slack_user(
        installation,
        slack_user("URECONNECTED"),
        source_timestamp=1,
    )

    assert identity is not None
    assert identity.source_generation == installation.generation
    assert not SlackUserTombstone.objects.filter(external_user_id="URECONNECTED").exists()


@pytest.mark.django_db
def test_revoked_installation_cannot_reactivate_a_member(installation):
    installation.status = IdentitySource.Status.REVOKED
    installation.save(update_fields=["status", "updated_at"])

    with pytest.raises(SlackClientError):
        sync_slack_user(installation, slack_user())

    assert not ExternalIdentity.objects.exists()


@pytest.mark.django_db
@patch("plane.bgtasks.slack_sync.reconcile_installation")
def test_terminal_bot_auth_failure_revokes_access_without_erasing_project_role(
    mock_reconcile,
    installation,
):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None
    project = Project.objects.create(
        name="Preserved project",
        identifier="PRESERVE",
        workspace=installation.workspace,
    )
    project_member = ProjectMember.objects.create(
        project=project,
        workspace=installation.workspace,
        member=identity.user,
        role=15,
    )
    mock_reconcile.side_effect = SlackAuthenticationError(
        "Slack API error: invalid_auth",
        error_code="invalid_auth",
    )

    reconcile_slack_installation.run(str(installation.id))

    installation.refresh_from_db()
    identity.refresh_from_db()
    identity.user.refresh_from_db()
    membership = WorkspaceMember.objects.get(
        workspace=installation.workspace,
        member=identity.user,
    )
    project_member.refresh_from_db()
    assert installation.status == IdentitySource.Status.REVOKED
    assert installation.encrypted_access_token == ""
    assert identity.is_active is False
    assert identity.user.is_active is False
    assert membership.is_active is False
    assert project_member.is_active is True


@pytest.mark.django_db
@patch("plane.bgtasks.slack_sync.reconcile_installation")
def test_current_generation_auth_failure_revokes_after_a_concurrent_success(
    mock_reconcile,
    installation,
):
    def fail_after_success(_installation):
        IdentitySource.objects.filter(pk=installation.pk).update(
            last_synced_at=timezone.now(),
            updated_at=timezone.now(),
        )
        raise SlackAuthenticationError(
            "Slack API error: invalid_auth",
            error_code="invalid_auth",
        )

    mock_reconcile.side_effect = fail_after_success

    reconcile_slack_installation.run(str(installation.id))

    installation.refresh_from_db()
    assert installation.status == IdentitySource.Status.REVOKED
    assert installation.encrypted_access_token == ""


@pytest.mark.django_db
def test_stale_generation_cannot_revoke_a_reconnected_installation(installation):
    previous_generation = installation.generation
    installation.generation += 1
    installation.set_access_token("xoxb-reconnected")
    installation.save()

    revoked = revoke_installation(
        installation,
        "stale invalid_auth",
        expected_generation=previous_generation,
    )

    installation.refresh_from_db()
    assert revoked is False
    assert installation.status == IdentitySource.Status.ACTIVE
    assert installation.get_access_token() == "xoxb-reconnected"


@pytest.mark.django_db
def test_stale_failure_cannot_revoke_after_a_newer_success(installation):
    failure_started_at = timezone.now()
    installation.last_synced_at = failure_started_at + timedelta(seconds=1)
    installation.save(update_fields=["last_synced_at", "updated_at"])

    revoked = revoke_installation(
        installation,
        "stale retry exhausted",
        expected_generation=installation.generation,
        expected_no_success_since=failure_started_at,
    )

    installation.refresh_from_db()
    assert revoked is False
    assert installation.status == IdentitySource.Status.ACTIVE
    assert installation.get_access_token() == "xoxb-secret"


@pytest.mark.django_db
@patch("plane.bgtasks.slack_sync.reconcile_installation")
def test_transient_reconcile_failure_keeps_existing_identity_source_live(
    mock_reconcile,
    installation,
):
    mock_reconcile.side_effect = SlackClientError("Slack temporarily unavailable")

    with patch.object(
        reconcile_slack_installation,
        "retry",
        side_effect=Retry(),
    ) as mock_retry:
        with pytest.raises(Retry):
            reconcile_slack_installation.run(str(installation.id))

    mock_retry.assert_called_once()

    installation.refresh_from_db()
    assert installation.status == IdentitySource.Status.ACTIVE
    assert installation.sync_error == "Slack temporarily unavailable"
    assert installation.sync_error_at is not None


@pytest.mark.django_db
@patch("plane.bgtasks.slack_sync.reconcile_installation")
def test_old_reconcile_retry_chain_ignores_a_reconnected_generation(
    mock_reconcile,
    installation,
):
    old_generation = installation.generation
    installation.generation += 1
    installation.set_access_token("xoxb-reconnected")
    installation.save()

    reconcile_slack_installation.run(
        str(installation.id),
        timezone.now().isoformat(),
        old_generation,
    )

    mock_reconcile.assert_not_called()
    installation.refresh_from_db()
    assert installation.status == IdentitySource.Status.ACTIVE
    assert installation.get_access_token() == "xoxb-reconnected"


@pytest.mark.django_db
def test_authoritative_lookup_cannot_commit_an_old_generation_identity(installation):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None
    authoritative_started_at = timezone.now()
    new_generation = installation.generation + 1
    IdentitySource.objects.filter(pk=installation.pk).update(
        generation=new_generation,
        updated_at=timezone.now(),
    )

    with pytest.raises(SlackClientError, match="payload was in flight"):
        sync_slack_user(
            installation,
            slack_user(),
            authoritative=True,
            authoritative_started_at=authoritative_started_at,
        )

    identity.refresh_from_db()
    assert identity.source_generation != new_generation


@pytest.mark.django_db
def test_stale_active_user_event_cannot_undo_a_newer_deactivation(installation):
    active_payload = slack_user()
    active_payload["updated"] = 1_700_000_100
    identity = sync_slack_user(installation, active_payload)
    assert identity is not None

    deleted_payload = slack_user(deleted=True)
    deleted_payload["updated"] = 1_700_000_300
    sync_slack_user(installation, deleted_payload)

    stale_active_payload = slack_user()
    stale_active_payload["updated"] = 1_700_000_200
    sync_slack_user(installation, stale_active_payload)

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is False
    assert identity.user.is_active is False


@pytest.mark.django_db
def test_deactivate_identity_revokes_membership_and_sessions(installation):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None
    Session.objects.create(
        session_key="s" * 128,
        session_data="",
        expire_date=timezone.now() + timedelta(days=1),
        user_id=str(identity.user_id),
    )

    deactivate_identity(identity)

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    membership = WorkspaceMember.objects.get(workspace=installation.workspace, member=identity.user)
    assert identity.is_active is False
    assert identity.user.is_active is False
    assert membership.is_active is False
    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is False

    reactivated_payload = slack_user()
    reactivated_payload["updated"] += 1
    reactivated = sync_slack_user(installation, reactivated_payload)
    assert reactivated is not None
    assert reactivated.user.is_active is True
    assert (
        WorkspaceMember.objects.get(
            workspace=installation.workspace,
            member=reactivated.user,
        ).is_active
        is True
    )


class FakeSlackClient:
    def team_info(self):
        return {
            "ok": True,
            "team": {
                "id": "T123",
                "name": "Authoritative Slack",
                "domain": "authoritative",
                "icon": {"image_230": "https://avatars.slack-edge.com/team.png"},
            },
        }

    def users_list(self, cursor=None):
        assert cursor is None
        return {
            "ok": True,
            "members": [
                slack_user("UNEW", email="new@example.com"),
                slack_user("UBOT", is_bot=True),
            ],
            "response_metadata": {"next_cursor": ""},
        }


@pytest.mark.django_db
def test_older_team_snapshot_cannot_overwrite_a_newer_started_snapshot(installation):
    newer_started_at = timezone.now()
    newer_team = {
        "id": installation.external_organization_id,
        "name": "New Team",
        "domain": "new-domain",
        "icon": {},
    }
    older_team = {
        "id": installation.external_organization_id,
        "name": "Old Team",
        "domain": "old-domain",
        "icon": {},
    }

    assert sync_slack_team_metadata(
        installation,
        newer_team,
        snapshot_at=newer_started_at,
    )
    assert not sync_slack_team_metadata(
        installation,
        older_team,
        snapshot_at=newer_started_at - timedelta(seconds=1),
    )

    installation.refresh_from_db()
    installation.workspace.refresh_from_db()
    assert installation.external_organization_name == "New Team"
    assert installation.external_organization_domain == "new-domain"
    assert installation.workspace.name == "New Team"


@pytest.mark.django_db
def test_older_reconcile_success_cannot_suppress_a_newer_auth_failure(installation):
    class FailureStartsDuringSnapshotClient(FakeSlackClient):
        failure_started_at = None

        def team_info(self):
            self.failure_started_at = timezone.now()
            return super().team_info()

    client = FailureStartsDuringSnapshotClient()
    reconcile_installation(installation, client=client)
    assert client.failure_started_at is not None

    revoked = revoke_installation(
        installation,
        "newer authentication failure",
        expected_generation=installation.generation,
        expected_no_success_since=client.failure_started_at,
    )

    installation.refresh_from_db()
    assert revoked is True
    assert installation.status == IdentitySource.Status.REVOKED


@pytest.mark.django_db
def test_older_reconcile_cannot_rewind_a_newer_success_watermark(installation):
    newer_success_at = timezone.now() + timedelta(minutes=1)
    installation.last_synced_at = newer_success_at
    installation.sync_error = "newer transient failure"
    installation.save(update_fields=["last_synced_at", "sync_error", "updated_at"])

    reconcile_installation(installation, client=FakeSlackClient())

    installation.refresh_from_db()
    assert installation.last_synced_at == newer_success_at
    assert installation.sync_error == "newer transient failure"


@pytest.mark.django_db
def test_older_reconcile_success_cannot_clear_a_newer_failure_watermark(installation):
    class FailureRecordedDuringSnapshotClient(FakeSlackClient):
        failure_recorded_at = None

        def team_info(self):
            self.failure_recorded_at = timezone.now()
            IdentitySource.objects.filter(pk=installation.pk).update(
                sync_error="newer transient failure",
                sync_error_at=self.failure_recorded_at,
                updated_at=self.failure_recorded_at,
            )
            return super().team_info()

    client = FailureRecordedDuringSnapshotClient()
    reconcile_installation(installation, client=client)

    installation.refresh_from_db()
    assert client.failure_recorded_at is not None
    assert installation.last_synced_at is not None
    assert installation.last_synced_at < client.failure_recorded_at
    assert installation.sync_error == "newer transient failure"
    assert installation.sync_error_at == client.failure_recorded_at


@pytest.mark.django_db
def test_newer_reconcile_success_clears_an_older_failure_watermark(installation):
    older_failure_at = timezone.now() - timedelta(minutes=1)
    installation.sync_error = "older transient failure"
    installation.sync_error_at = older_failure_at
    installation.save(update_fields=["sync_error", "sync_error_at", "updated_at"])

    reconcile_installation(installation, client=FakeSlackClient())

    installation.refresh_from_db()
    assert installation.sync_error == ""
    assert installation.sync_error_at is None


@pytest.mark.django_db
def test_reconcile_mirrors_team_and_deactivates_missing_identity(installation):
    instance = Instance.objects.create(
        instance_name="Old instance name",
        instance_id=uuid4().hex,
        current_version="test",
        last_checked_at=timezone.now(),
    )
    stale_identity = sync_slack_user(installation, slack_user("USTALE", email="stale@example.com"))
    assert stale_identity is not None

    reconcile_installation(installation, client=FakeSlackClient())

    installation.refresh_from_db()
    installation.workspace.refresh_from_db()
    instance.refresh_from_db()
    stale_identity.refresh_from_db()
    assert installation.external_organization_name == "Authoritative Slack"
    assert installation.external_organization_domain == "authoritative"
    assert installation.external_organization_icon_url == "https://avatars.slack-edge.com/team.png"
    assert installation.workspace.name == "Authoritative Slack"
    assert installation.workspace.logo == "https://avatars.slack-edge.com/team.png"
    assert instance.instance_name == "Authoritative Slack"
    assert installation.last_synced_at is not None
    assert stale_identity.is_active is False
    assert ExternalIdentity.objects.filter(external_user_id="UNEW", is_active=True).exists()
    assert not ExternalIdentity.objects.filter(external_user_id="UBOT").exists()
    new_identity = ExternalIdentity.objects.get(external_user_id="UNEW")
    assert Profile.objects.get(user=new_identity.user).theme == {}


@pytest.mark.django_db
def test_reconcile_does_not_remove_a_member_synced_while_snapshot_was_loading(installation):
    class JoinDuringSnapshotClient(FakeSlackClient):
        def users_list(self, cursor=None):
            assert cursor is None
            sync_slack_user(installation, slack_user("UJOINED", email="joined@example.com"))
            return {
                "ok": True,
                "members": [],
                "response_metadata": {"next_cursor": ""},
            }

    reconcile_installation(installation, client=JoinDuringSnapshotClient())

    identity = ExternalIdentity.objects.select_related("user").get(external_user_id="UJOINED")
    membership = WorkspaceMember.objects.get(
        workspace=installation.workspace,
        member=identity.user,
    )
    assert identity.is_active is True
    assert identity.user.is_active is True
    assert membership.is_active is True


@pytest.mark.django_db
def test_reconcile_overrides_an_older_event_processed_while_snapshot_was_loading(
    installation,
):
    identity = sync_slack_user(
        installation,
        slack_user("UDELAYED", email="delayed@example.com"),
    )
    assert identity is not None

    class DelayedTerminalEventClient(FakeSlackClient):
        def users_list(self, cursor=None):
            assert cursor is None
            sync_slack_user(
                installation,
                slack_user("UDELAYED", email="delayed@example.com", deleted=True),
                source_timestamp=(timezone.now() - timedelta(minutes=1)).timestamp(),
            )
            return {
                "ok": True,
                "members": [slack_user("UDELAYED", email="delayed@example.com")],
                "response_metadata": {"next_cursor": ""},
            }

    reconcile_installation(installation, client=DelayedTerminalEventClient())

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is True
    assert identity.user.is_active is True


@pytest.mark.django_db
def test_reconcile_absence_overrides_an_older_active_event_processed_during_fetch(
    installation,
):
    identity = sync_slack_user(
        installation,
        slack_user("UDELAYEDABSENCE", email="absent@example.com"),
    )
    assert identity is not None

    class DelayedActiveEventClient(FakeSlackClient):
        def users_list(self, cursor=None):
            assert cursor is None
            sync_slack_user(
                installation,
                slack_user("UDELAYEDABSENCE", email="absent@example.com"),
                source_timestamp=(timezone.now() - timedelta(minutes=1)).timestamp(),
            )
            return {
                "ok": True,
                "members": [],
                "response_metadata": {"next_cursor": ""},
            }

    reconcile_installation(installation, client=DelayedActiveEventClient())

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is False
    assert identity.user.is_active is False


@pytest.mark.django_db
def test_reconcile_absence_watermark_blocks_a_delayed_active_event(installation):
    initial_payload = slack_user("ULEFT", email="left@example.com")
    initial_payload["updated"] = timezone.now().timestamp() - 120
    identity = sync_slack_user(installation, initial_payload)
    assert identity is not None
    initial_source_updated_at = identity.source_updated_at

    class EmptySnapshotClient(FakeSlackClient):
        def users_list(self, cursor=None):
            assert cursor is None
            return {
                "ok": True,
                "members": [],
                "response_metadata": {"next_cursor": ""},
            }

    reconcile_installation(installation, client=EmptySnapshotClient())

    identity.refresh_from_db()
    assert identity.source_updated_at == initial_source_updated_at
    assert identity.snapshot_absent_at is not None
    snapshot_barrier = identity.snapshot_absent_at.timestamp()
    delayed_payload = slack_user("ULEFT", email="left@example.com")
    delayed_payload["updated"] = snapshot_barrier - 10
    sync_slack_user(
        installation,
        delayed_payload,
        source_timestamp=snapshot_barrier - 1,
    )

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is False
    assert identity.user.is_active is False

    # A current users.info/users.list snapshot is authoritative even when
    # Slack's profile `updated` second did not advance past our local clock.
    sync_slack_user(installation, initial_payload, authoritative=True)

    identity.refresh_from_db()
    identity.user.refresh_from_db()
    assert identity.is_active is True
    assert identity.snapshot_absent_at is None
    assert identity.user.is_active is True


@pytest.mark.django_db
def test_reconnect_snapshot_absence_records_the_current_generation(installation):
    identity = sync_slack_user(installation, slack_user("UMISSING"))
    assert identity is not None
    installation.generation += 1
    installation.save(update_fields=["generation", "updated_at"])

    class EmptySnapshotClient(FakeSlackClient):
        def users_list(self, cursor=None):
            assert cursor is None
            return {
                "ok": True,
                "members": [],
                "response_metadata": {"next_cursor": ""},
            }

    reconcile_installation(installation, client=EmptySnapshotClient())

    identity.refresh_from_db()
    assert identity.is_active is False
    assert identity.source_generation == installation.generation


@pytest.mark.django_db
def test_installation_encrypts_bot_token(installation):
    installation.refresh_from_db()
    assert installation.encrypted_access_token != "xoxb-secret"
    assert installation.access_token == "xoxb-secret"


@pytest.mark.django_db
def test_identity_source_records_cannot_be_soft_deleted(installation):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            ExternalIdentity.objects.filter(pk=identity.pk).delete()
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            IdentitySource.objects.filter(pk=installation.pk).delete()

    assert ExternalIdentity.objects.filter(pk=identity.pk).exists()
    assert IdentitySource.objects.filter(pk=installation.pk).exists()


@pytest.mark.django_db
def test_bootstrap_user_can_be_bound_without_duplicate_user(installation):
    bootstrap_user = User.objects.create(
        email=f"bootstrap-{uuid4().hex}@example.com",
        username=f"bootstrap-{uuid4().hex}",
    )
    Profile.objects.create(user=bootstrap_user)
    user_count = User.objects.count()

    identity = sync_slack_user(installation, slack_user("UADMIN", is_admin=True), user=bootstrap_user)

    assert identity is not None
    assert identity.user_id == bootstrap_user.id
    assert User.objects.count() == user_count
    assert WorkspaceMember.objects.get(member=bootstrap_user, workspace=installation.workspace).role == 20


@pytest.mark.django_db
def test_old_slack_event_receipts_are_hard_deleted():
    old_receipt = SlackEventReceipt.objects.create(
        event_id="EvOld",
        team_id="T123",
        event_type="user_change",
        received_at=timezone.now() - timedelta(days=31),
    )
    current_receipt = SlackEventReceipt.objects.create(
        event_id="EvCurrent",
        team_id="T123",
        event_type="user_change",
    )

    delete_old_slack_event_receipts.run()

    assert not SlackEventReceipt.all_objects.filter(pk=old_receipt.pk).exists()
    assert SlackEventReceipt.all_objects.filter(pk=current_receipt.pk).exists()


@pytest.mark.django_db
def test_deactivation_enqueues_live_user_revocation_after_commit(
    installation,
    django_capture_on_commit_callbacks,
):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None

    with patch(
        "plane.bgtasks.slack_sync.publish_live_user_revocation.apply_async"
    ) as apply_async:
        with django_capture_on_commit_callbacks(execute=True):
            deactivate_identity(identity)

    apply_async.assert_called_once()
    assert apply_async.call_args.kwargs["args"][0] == str(identity.user_id)
    assert isinstance(apply_async.call_args.kwargs["args"][1], str)
    assert apply_async.call_args.kwargs["retry"] is False


@pytest.mark.django_db
def test_workspace_role_change_enqueues_live_user_revocation_after_commit(
    installation,
    django_capture_on_commit_callbacks,
):
    identity = sync_slack_user(installation, slack_user())
    assert identity is not None
    promoted_payload = slack_user(is_admin=True)
    promoted_payload["updated"] += 1

    with patch(
        "plane.bgtasks.slack_sync.publish_live_user_revocation.apply_async"
    ) as apply_async:
        with django_capture_on_commit_callbacks(execute=True):
            sync_slack_user(installation, promoted_payload)

    apply_async.assert_called_once()
    assert apply_async.call_args.kwargs["args"][0] == str(identity.user_id)
    assert apply_async.call_args.kwargs["retry"] is False


def test_publish_live_user_revocation_uses_hocuspocus_server_channel():
    with patch("plane.bgtasks.slack_sync.redis_instance") as redis_factory:
        redis_client = redis_factory.return_value

        publish_live_user_revocation.run(
            "user-id",
            "2026-08-24T00:00:00+00:00",
        )

    redis_client.publish.assert_called_once()
    channel, raw_payload = redis_client.publish.call_args.args
    payload = json.loads(raw_payload)
    assert channel == "hocuspocus:server"
    assert payload["command"] == "revoke_user"
    assert payload["userId"] == "user-id"
    assert payload["accessChangedAt"] == "2026-08-24T00:00:00+00:00"
    redis_client.close.assert_called_once_with()
