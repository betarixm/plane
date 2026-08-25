# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import jwt
import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed

from plane.api.middleware.api_authentication import APIKeyAuthentication
from plane.api.serializers import ProjectMemberSerializer, ProjectUpdateSerializer
from plane.api.serializers.cycle import (
    CycleCreateSerializer as APICycleCreateSerializer,
    CycleUpdateSerializer as APICycleUpdateSerializer,
)
from plane.api.serializers.issue import IssueSerializer as APIIssueSerializer
from plane.api.serializers.module import ModuleCreateSerializer as APIModuleCreateSerializer
from plane.app.serializers import ProjectSerializer as AppProjectSerializer
from plane.app.serializers.draft import DraftIssueCreateSerializer
from plane.app.serializers.issue import (
    IssueCreateSerializer as AppIssueCreateSerializer,
    IssueSubscriberSerializer,
)
from plane.app.serializers.module import ModuleWriteSerializer
from plane.authentication.middleware.session import SessionMiddleware
from plane.db.models import (
    APIToken,
    Cycle,
    FileAsset,
    IssueAssignee,
    Project,
    ProjectMember,
    Session,
    ExternalIdentity,
    IdentitySource,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.integrations.slack import revoke_installation, sync_slack_user
from plane.license.models import Instance
from plane.utils.identity_access import (
    IDENTITY_SOURCE_GENERATION_SESSION_KEY,
    IDENTITY_SOURCE_ID_SESSION_KEY,
    active_project_members,
)

pytestmark = [pytest.mark.contract, pytest.mark.django_db]


SLACK_CREDENTIALS = SimpleNamespace(
    client_id="123.456",
    client_secret="client-secret",
    signing_secret="signing-secret",
)


def _workspace_admin(workspace):
    """Return the role-backed administrator without a Workspace owner field."""

    cached = getattr(workspace, "_test_workspace_admin", None)
    if cached is None:
        cached = WorkspaceMember.objects.get(workspace=workspace, role=20).member
        workspace._test_workspace_admin = cached
    return cached


def slack_member(external_user_id="UADMIN", *, is_admin=True, deleted=False, is_bot=False):
    return {
        "id": external_user_id,
        "team_id": "T123",
        "name": "owner",
        "real_name": "Slack Owner",
        "deleted": deleted,
        "is_bot": is_bot,
        "is_app_user": False,
        "is_admin": is_admin,
        "is_owner": False,
        "is_primary_owner": False,
        "is_restricted": False,
        "is_ultra_restricted": False,
        "updated": 1_700_000_000,
        "tz": "Asia/Seoul",
        "profile": {
            "email": "owner@example.com",
            "display_name": "slack-owner",
            "real_name": "Slack Owner",
            "first_name": "Slack",
            "last_name": "Owner",
            "image_192": "https://avatars.slack-edge.com/owner.png",
        },
    }


class FakeSlackClient:
    member = slack_member()

    def __init__(self, bot_token=None):
        self.bot_token = bot_token

    def exchange_oauth_code(self, code, redirect_uri):
        assert code == "install-code"
        assert redirect_uri.endswith("/auth/slack/install/callback/")
        return {
            "ok": True,
            "access_token": "xoxb-secret",
            "scope": "users:read,users:read.email,team:read",
            "team": {"id": "T123", "name": "Acme Slack"},
            "authed_user": {"id": "UADMIN"},
            "bot_user_id": "UBOT",
            "app_id": "A123",
        }

    def team_info(self):
        return {
            "ok": True,
            "team": {
                "id": "T123",
                "name": "Acme Slack",
                "domain": "acme",
                "icon": {"image_230": "https://avatars.slack-edge.com/team.png"},
            },
        }

    def users_info(self, user_id):
        assert user_id == self.member["id"]
        return {"ok": True, "user": self.member}

    def auth_test(self):
        return {
            "ok": True,
            "team_id": "T123",
            "user_id": "UBOT",
        }

    def exchange_openid_code(self, code, redirect_uri):
        assert code == "login-code"
        assert redirect_uri.endswith("/auth/slack/callback/")
        return {
            "ok": True,
            "access_token": "xoxp-oidc",
            "id_token": "signed-id-token",
        }

    def openid_userinfo(self, access_token):
        assert access_token == "xoxp-oidc"
        return {
            "ok": True,
            "sub": "https://slack.com/T123-UADMIN",
            "https://slack.com/team_id": "T123",
            "https://slack.com/user_id": self.member["id"],
        }


class FakeWrongTeamSlackClient(FakeSlackClient):
    member = {**slack_member(), "team_id": "T999"}

    def exchange_oauth_code(self, code, redirect_uri):
        response = super().exchange_oauth_code(code, redirect_uri)
        response["team"] = {"id": "T999", "name": "Other Slack"}
        return response

    def team_info(self):
        return {
            "ok": True,
            "team": {
                "id": "T999",
                "name": "Other Slack",
                "domain": "other",
                "icon": {},
            },
        }


class FakeRevokedDuringInstallSlackClient(FakeSlackClient):
    def auth_test(self):
        from plane.integrations.slack import SlackAuthenticationError

        raise SlackAuthenticationError("revoked", error_code="token_revoked")


@pytest.fixture
def unconfigured_instance():
    return Instance.objects.create(
        instance_name="Plane Community Edition",
        instance_id=uuid4().hex,
        current_version="test",
        last_checked_at=timezone.now(),
    )


def _initiate(client, path):
    response = client.get(path)
    assert response.status_code == 302
    return parse_qs(urlparse(response.url).query)


@override_settings(
    APP_BASE_URL="https://app.example.com",
    WEB_URL="https://api.example.com",
)
@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack.reconcile_slack_installation.delay")
def test_install_bootstraps_singleton_from_slack_identity(
    mock_reconcile,
    _mock_credentials,
    client,
    django_capture_on_commit_callbacks,
    unconfigured_instance,
):
    query = _initiate(client, "/auth/slack/install/")
    assert query["scope"] == ["team:read,users:read,users:read.email"]
    assert "client-secret" not in str(query)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.get(
            "/auth/slack/install/callback/",
            {"state": query["state"][0], "code": "install-code"},
        )

    assert response.status_code == 302
    assert response.url == "https://app.example.com/acme/"
    workspace = Workspace.objects.get()
    installation = IdentitySource.objects.get()
    identity = ExternalIdentity.objects.select_related("user").get()
    membership = WorkspaceMember.objects.get(workspace=workspace, member=identity.user)
    assert workspace.name == "Acme Slack"
    assert workspace.slug == "acme"
    assert _workspace_admin(workspace).id == identity.user_id
    assert membership.role == 20
    assert identity.user.email == "owner@example.com"
    assert identity.user.display_name == "slack-owner"
    assert User.objects.count() == 1
    assert installation.encrypted_access_token != "xoxb-secret"
    assert installation.get_access_token() == "xoxb-secret"
    assert installation.external_organization_id == "T123"
    assert installation.external_organization_icon_url == "https://avatars.slack-edge.com/team.png"
    unconfigured_instance.refresh_from_db()
    assert unconfigured_instance.is_setup_done is True
    assert client.session.get("_auth_user_id") == str(identity.user_id)
    assert client.get("/api/users/me/").status_code == 200
    mock_reconcile.assert_called_once_with(str(installation.id))

    replay = client.get(
        "/auth/slack/install/callback/",
        {"state": query["state"][0], "code": "install-code"},
    )
    assert replay.status_code == 302
    assert replay.url.startswith("https://app.example.com")
    assert "IDENTITY_SOURCE_OAUTH_STATE_INVALID" in replay.url


@override_settings(
    APP_BASE_URL="https://app.example.com",
    WEB_URL="https://api.example.com",
)
@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack.reconcile_slack_installation.delay")
def test_install_callback_does_not_create_a_session_after_lifecycle_revocation(
    _mock_reconcile,
    _mock_credentials,
    client,
    unconfigured_instance,
):
    query = _initiate(client, "/auth/slack/install/")

    def revoke_before_login(**_kwargs):
        installation = IdentitySource.objects.get()
        revoke_installation(
            installation,
            "Slack app was uninstalled",
            expected_generation=installation.generation,
        )

    with patch(
        "plane.authentication.views.slack.invalidate_cache_directly",
        side_effect=revoke_before_login,
    ):
        response = client.get(
            "/auth/slack/install/callback/",
            {"state": query["state"][0], "code": "install-code"},
        )

    installation = IdentitySource.objects.get()
    identity = ExternalIdentity.objects.get()
    assert response.status_code == 302
    assert "IDENTITY_SOURCE_OAUTH_ERROR" in response.url
    assert installation.status == IdentitySource.Status.REVOKED
    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is False
    assert client.session.get("_auth_user_id") is None


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
def test_install_requires_active_slack_admin(_mock_credentials, client, unconfigured_instance):
    query = _initiate(client, "/auth/slack/install/")
    FakeSlackClient.member = slack_member(is_admin=False)
    try:
        response = client.get(
            "/auth/slack/install/callback/",
            {"state": query["state"][0], "code": "install-code"},
        )
    finally:
        FakeSlackClient.member = slack_member()

    assert response.status_code == 302
    assert "IDENTITY_SOURCE_ADMIN_REQUIRED" in response.url
    assert not User.objects.exists()
    assert not Workspace.objects.exists()
    assert not IdentitySource.objects.exists()
    unconfigured_instance.refresh_from_db()
    assert unconfigured_instance.is_setup_done is False


@override_settings(
    APP_BASE_URL="https://app.example.com",
    WEB_URL="https://api.example.com",
)
@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack.reconcile_slack_installation.delay")
def test_revoked_installation_can_be_reconnected_only_to_the_bound_team(
    mock_reconcile,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
    django_capture_on_commit_callbacks,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    previous_generation = installation.generation
    installation.status = IdentitySource.Status.REVOKED
    installation.encrypted_access_token = ""
    installation.sync_error = "Slack app was uninstalled"
    installation.save()
    identity = ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UADMIN",
        is_active=False,
    )
    membership = WorkspaceMember.objects.get(workspace=workspace, member=_workspace_admin(workspace))
    membership.is_active = False
    membership.save(update_fields=["is_active", "updated_at"])
    _workspace_admin(workspace).is_active = False
    _workspace_admin(workspace).save(update_fields=["is_active", "updated_at"])

    query = _initiate(client, "/auth/slack/install/")
    assert query["team"] == ["T123"]
    with django_capture_on_commit_callbacks(execute=True):
        response = client.get(
            "/auth/slack/install/callback/",
            {"state": query["state"][0], "code": "install-code"},
        )

    assert response.status_code == 302
    assert response.url == "https://app.example.com/test-workspace/"
    installation.refresh_from_db()
    identity.refresh_from_db()
    membership.refresh_from_db()
    _workspace_admin(workspace).refresh_from_db()
    assert installation.status == IdentitySource.Status.ACTIVE
    assert installation.generation == previous_generation + 1
    assert installation.get_access_token() == "xoxb-secret"
    assert installation.sync_error == ""
    assert installation.sync_error_at is None
    assert identity.is_active is True
    assert _workspace_admin(workspace).is_active is True
    assert membership.is_active is True
    assert client.session.get("_auth_user_id") == str(_workspace_admin(workspace).id)
    mock_reconcile.assert_called_once_with(str(installation.id))


@override_settings(
    APP_BASE_URL="https://app.example.com",
    WEB_URL="https://api.example.com",
)
@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeWrongTeamSlackClient)
def test_reconnect_rejects_a_different_slack_team(
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    installation.status = IdentitySource.Status.REVOKED
    installation.encrypted_access_token = ""
    installation.save()
    query = _initiate(client, "/auth/slack/install/")

    response = client.get(
        "/auth/slack/install/callback/",
        {"state": query["state"][0], "code": "install-code"},
    )

    assert response.status_code == 302
    assert response.url.startswith("https://app.example.com")
    assert "IDENTITY_SOURCE_ORGANIZATION_MISMATCH" in response.url
    installation.refresh_from_db()
    assert installation.status == IdentitySource.Status.REVOKED
    assert installation.encrypted_access_token == ""


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeRevokedDuringInstallSlackClient)
def test_reconnect_does_not_activate_a_token_revoked_during_oauth_validation(
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    installation.status = IdentitySource.Status.REVOKED
    installation.encrypted_access_token = ""
    installation.save(update_fields=["status", "encrypted_access_token", "updated_at"])
    query = _initiate(client, "/auth/slack/install/")

    response = client.get(
        "/auth/slack/install/callback/",
        {"state": query["state"][0], "code": "install-code"},
    )

    assert response.status_code == 302
    assert "IDENTITY_SOURCE_OAUTH_ERROR" in response.url
    installation.refresh_from_db()
    assert installation.status == IdentitySource.Status.REVOKED
    assert installation.encrypted_access_token == ""
    assert client.session.get("_auth_user_id") is None


def _installed_slack_workspace(workspace, instance):
    instance.is_setup_done = True
    instance.save(update_fields=["is_setup_done", "updated_at"])
    installation = IdentitySource(
        workspace=workspace,
        provider=IdentitySource.Provider.SLACK,
        external_organization_id="T123",
        external_organization_name="Acme Slack",
        external_organization_domain="acme",
    )
    installation.set_access_token("xoxb-secret")
    installation.save()
    return installation


def _force_slack_session(client, user, installation):
    client.force_login(user)
    session = client.session
    session[IDENTITY_SOURCE_ID_SESSION_KEY] = str(installation.id)
    session[IDENTITY_SOURCE_GENERATION_SESSION_KEY] = installation.generation
    session.save()
    return session.session_key


def _stale_slack_project_roster(workspace, instance):
    installation = _installed_slack_workspace(workspace, instance)
    installation.generation += 1
    installation.save(update_fields=["generation", "updated_at"])
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UCURRENT",
        source_generation=installation.generation,
    )
    stale_user = User.objects.create(
        email="stale-slack-target@example.com",
        username="stale-slack-target",
        is_active=True,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=stale_user,
        role=15,
        is_active=True,
    )
    ExternalIdentity.objects.create(
        user=stale_user,
        source=installation,
        external_user_id="USTALE",
        source_generation=installation.generation - 1,
    )
    project = Project.objects.create(
        workspace=workspace,
        name="Current external roster enforcement",
        identifier="ROSTER",
        module_view=True,
        cycle_view=True,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=_workspace_admin(workspace),
        role=20,
        is_active=True,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=stale_user,
        role=15,
        is_active=True,
    )
    return installation, project, stale_user


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack._validate_openid_id_token")
def test_oidc_login_pins_team_refreshes_full_member_and_consumes_state(
    mock_validate_token,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    mock_validate_token.return_value = {
        "sub": "https://slack.com/T123-UADMIN",
        "https://slack.com/team_id": "T123",
        "https://slack.com/user_id": "UADMIN",
    }

    query = _initiate(client, "/auth/slack/?next_path=/test-workspace/issues")
    assert query["scope"] == ["openid profile email"]
    assert query["team"] == [installation.external_organization_id]
    response = client.get(
        "/auth/slack/callback/",
        {"state": query["state"][0], "code": "login-code"},
    )

    assert response.status_code == 302
    assert response.url == "https://app.example.com/test-workspace/issues"
    identity = ExternalIdentity.objects.select_related("user").get(external_user_id="UADMIN")
    assert identity.source_id == installation.id
    assert identity.user.display_name == "slack-owner"
    assert client.session.get("_auth_user_id") == str(identity.user_id)
    mock_validate_token.assert_called_once()

    replay = client.get(
        "/auth/slack/callback/",
        {"state": query["state"][0], "code": "login-code"},
    )
    assert replay.status_code == 302
    assert "IDENTITY_SOURCE_OAUTH_STATE_INVALID" in replay.url

    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is True
    revoke_installation(
        installation,
        "Slack app was uninstalled",
        expected_generation=installation.generation,
    )
    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is False


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack._validate_openid_id_token")
def test_oidc_login_does_not_create_a_session_after_identity_revocation(
    mock_validate_token,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    mock_validate_token.return_value = {
        "sub": "https://slack.com/T123-UADMIN",
        "https://slack.com/team_id": "T123",
        "https://slack.com/user_id": "UADMIN",
    }
    query = _initiate(client, "/auth/slack/")

    def sync_then_revoke(current_installation, member, **kwargs):
        identity = sync_slack_user(current_installation, member, **kwargs)
        revoke_installation(
            current_installation,
            "Slack app was uninstalled",
            expected_generation=current_installation.generation,
        )
        return identity

    with patch(
        "plane.authentication.views.slack.sync_slack_user",
        side_effect=sync_then_revoke,
    ):
        response = client.get(
            "/auth/slack/callback/",
            {"state": query["state"][0], "code": "login-code"},
        )

    installation.refresh_from_db()
    identity = ExternalIdentity.objects.get(external_user_id="UADMIN")
    assert response.status_code == 302
    assert "EXTERNAL_IDENTITY_NOT_FOUND" in response.url
    assert installation.status == IdentitySource.Status.REVOKED
    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is False
    assert client.session.get("_auth_user_id") is None


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack._validate_openid_id_token")
def test_oidc_response_save_cannot_resurrect_a_revoked_session(
    mock_validate_token,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    mock_validate_token.return_value = {
        "sub": "https://slack.com/T123-UADMIN",
        "https://slack.com/team_id": "T123",
        "https://slack.com/user_id": "UADMIN",
    }
    query = _initiate(client, "/auth/slack/")
    response_save = SessionMiddleware._save_identity_fenced_session

    def revoke_before_response_save(request):
        current_installation = IdentitySource.objects.get(pk=installation.pk)
        revoke_installation(
            current_installation,
            "Slack app was uninstalled",
            expected_generation=current_installation.generation,
        )
        return response_save(request)

    with patch.object(
        SessionMiddleware,
        "_save_identity_fenced_session",
        side_effect=revoke_before_response_save,
    ):
        response = client.get(
            "/auth/slack/callback/",
            {"state": query["state"][0], "code": "login-code"},
        )

    installation.refresh_from_db()
    identity = ExternalIdentity.objects.get(external_user_id="UADMIN")
    assert response.status_code == 302
    assert installation.status == IdentitySource.Status.REVOKED
    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is False
    assert client.session.get("_auth_user_id") is None


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack._validate_openid_id_token")
def test_authenticated_response_save_cannot_resurrect_a_revoked_session(
    mock_validate_token,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    mock_validate_token.return_value = {
        "sub": "https://slack.com/T123-UADMIN",
        "https://slack.com/team_id": "T123",
        "https://slack.com/user_id": "UADMIN",
    }
    query = _initiate(client, "/auth/slack/")
    login_response = client.get(
        "/auth/slack/callback/",
        {"state": query["state"][0], "code": "login-code"},
    )
    assert login_response.status_code == 302

    response_save = SessionMiddleware._save_identity_fenced_session

    def revoke_before_authenticated_save(request):
        current_installation = IdentitySource.objects.get(pk=installation.pk)
        revoke_installation(
            current_installation,
            "Slack app was uninstalled",
            expected_generation=current_installation.generation,
        )
        return response_save(request)

    with (
        override_settings(SESSION_SAVE_EVERY_REQUEST=True),
        patch.object(
            SessionMiddleware,
            "_save_identity_fenced_session",
            side_effect=revoke_before_authenticated_save,
        ),
    ):
        response = client.get("/api/users/me/")

    installation.refresh_from_db()
    identity = ExternalIdentity.objects.get(external_user_id="UADMIN")
    assert response.status_code == 200
    assert installation.status == IdentitySource.Status.REVOKED
    assert Session.objects.filter(user_id=str(identity.user_id)).exists() is False
    assert client.session.get("_auth_user_id") is None


@override_settings(
    APP_BASE_URL="https://app.example.com",
    SPACE_BASE_URL="https://space.example.com",
    SPACE_BASE_PATH="/spaces/",
)
@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack._validate_openid_id_token")
def test_oidc_login_preserves_space_origin_across_callback(
    mock_validate_token,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    _installed_slack_workspace(workspace, unconfigured_instance)
    mock_validate_token.return_value = {
        "sub": "https://slack.com/T123-UADMIN",
        "https://slack.com/team_id": "T123",
        "https://slack.com/user_id": "UADMIN",
    }

    query = _initiate(client, "/auth/slack/?origin=space&next_path=/issues/123")
    response = client.get(
        "/auth/slack/callback/",
        {"state": query["state"][0], "code": "login-code"},
    )

    assert response.status_code == 302
    assert response.url == "https://space.example.com/spaces/issues/123"


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.authentication.views.slack.SlackClient", FakeSlackClient)
@patch("plane.authentication.views.slack._validate_openid_id_token")
def test_oidc_login_rejects_a_different_team(
    mock_validate_token,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    _installed_slack_workspace(workspace, unconfigured_instance)
    mock_validate_token.return_value = {
        "sub": "https://slack.com/T999-UADMIN",
        "https://slack.com/team_id": "T999",
        "https://slack.com/user_id": "UADMIN",
    }
    query = _initiate(client, "/auth/slack/")

    response = client.get(
        "/auth/slack/callback/",
        {"state": query["state"][0], "code": "login-code"},
    )

    assert response.status_code == 302
    assert "EXTERNAL_IDENTITY_INVALID" in response.url or "IDENTITY_SOURCE_ORGANIZATION_MISMATCH" in response.url
    assert ExternalIdentity.objects.count() == 0


@patch("plane.authentication.views.slack.jwt.decode")
@patch("plane.authentication.views.slack.SLACK_JWKS_CLIENT")
def test_id_token_validation_requires_slack_issuer_audience_expiry_and_nonce(
    mock_jwks_client,
    mock_decode,
):
    from plane.authentication.views.slack import _validate_openid_id_token

    mock_jwks_client.get_signing_key_from_jwt.return_value.key = "public-key"
    mock_decode.return_value = {"sub": "subject", "nonce": "expected-nonce"}

    claims = _validate_openid_id_token(
        "signed-token",
        client_id="123.456",
        nonce="expected-nonce",
    )

    assert claims["sub"] == "subject"
    mock_decode.assert_called_once_with(
        "signed-token",
        "public-key",
        algorithms=["RS256"],
        audience="123.456",
        issuer="https://slack.com",
        options={"require": ["aud", "exp", "iss", "nonce", "sub"]},
    )

    mock_decode.return_value = {"sub": "subject", "nonce": "wrong-nonce"}
    with pytest.raises(jwt.InvalidTokenError):
        _validate_openid_id_token(
            "signed-token",
            client_id="123.456",
            nonce="expected-nonce",
        )


def test_external_identity_profile_and_workspace_assets_are_read_only(
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    _force_slack_session(client, _workspace_admin(workspace), installation)
    assert client.patch(
        "/api/users/me/",
        {"display_name": "Locally changed"},
        content_type="application/json",
    ).status_code == 405
    assert client.delete("/api/users/me/").status_code == 405
    assert (
        client.post(
            f"/api/assets/v2/workspaces/{workspace.slug}/",
            {"entity_type": FileAsset.EntityTypeContext.WORKSPACE_LOGO},
            content_type="application/json",
        ).status_code
        == 403
    )

    local_logo = FileAsset.objects.create(
        attributes={"name": "local-logo.png", "type": "image/png", "size": 1},
        asset=f"{workspace.id}/local-logo.png",
        size=1,
        workspace=workspace,
        created_by=_workspace_admin(workspace),
        entity_type=FileAsset.EntityTypeContext.WORKSPACE_LOGO,
    )
    local_logo_url = f"/api/assets/v2/workspaces/{workspace.slug}/{local_logo.id}/"
    assert client.patch(local_logo_url, {}, content_type="application/json").status_code == 403
    assert client.delete(local_logo_url).status_code == 403
    local_logo.refresh_from_db()
    assert local_logo.is_deleted is False


def test_deactivated_slack_member_is_hidden_and_cannot_be_added_to_a_project(
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    inactive_user = User.objects.create(
        email="removed-from-slack@example.com",
        username="removed-from-slack",
        is_active=False,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=inactive_user,
        role=15,
        is_active=False,
    )
    _force_slack_session(client, _workspace_admin(workspace), installation)

    response = client.get(f"/api/workspaces/{workspace.slug}/members/")

    assert response.status_code == 200
    returned_user_ids = {str(item["member"]["id"]) for item in response.json()}
    assert str(inactive_user.id) not in returned_user_ids

    serializer = ProjectMemberSerializer(
        data={"member": str(inactive_user.id), "role": 5},
        context={"slug": workspace.slug},
    )
    assert serializer.is_valid() is False
    assert "member" in serializer.errors

    guest_user = User.objects.create(
        email="slack-guest@example.com",
        username="slack-guest",
        is_active=True,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=guest_user,
        role=5,
        is_active=True,
    )
    ExternalIdentity.objects.create(
        user=guest_user,
        source=installation,
        external_user_id="UGUEST",
        source_generation=installation.generation,
    )
    guest_serializer = ProjectMemberSerializer(
        data={"member": str(guest_user.id), "role": 20},
        context={"slug": workspace.slug},
    )
    assert guest_serializer.is_valid() is False
    assert "role" in guest_serializer.errors


def test_legacy_local_session_and_api_key_are_rejected_without_external_identity(
    client,
    workspace,
):
    client.force_login(_workspace_admin(workspace))
    response = client.get("/api/users/me/")

    assert response.status_code in {401, 403}
    assert client.session.get("_auth_user_id") is None

    token = APIToken.objects.create(user=_workspace_admin(workspace), token="legacy-local-token")
    with pytest.raises(AuthenticationFailed, match="active external identity"):
        APIKeyAuthentication().validate_api_token(token.token)


def test_session_authentication_flushes_live_identity_without_slack_fence(
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    client.force_login(_workspace_admin(workspace))
    session_key = client.session.session_key
    assert Session.objects.filter(pk=session_key).exists() is True

    response = client.get("/api/users/me/")

    assert response.status_code in {401, 403}
    assert Session.objects.filter(pk=session_key).exists() is False
    assert client.session.get("_auth_user_id") is None


def test_session_authentication_flushes_previous_generation_after_reconnect(
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    identity = ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    previous_generation = installation.generation
    session_key = _force_slack_session(client, _workspace_admin(workspace), installation)
    assert Session.objects.filter(pk=session_key).exists() is True

    installation.generation = previous_generation + 1
    installation.save(update_fields=["generation", "updated_at"])
    identity.source_generation = installation.generation
    identity.save(update_fields=["source_generation", "updated_at"])
    assert Session.objects.filter(pk=session_key).exists() is True

    response = client.get("/api/users/me/")

    assert response.status_code in {401, 403}
    assert Session.objects.filter(pk=session_key).exists() is False
    assert client.session.get("_auth_user_id") is None


def test_session_authentication_flushes_inactive_session_user(
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    session_key = _force_slack_session(client, _workspace_admin(workspace), installation)
    assert Session.objects.filter(pk=session_key).exists() is True
    _workspace_admin(workspace).is_active = False
    _workspace_admin(workspace).save(update_fields=["is_active", "updated_at"])
    assert Session.objects.filter(pk=session_key).exists() is True

    response = client.get("/api/users/me/")

    assert response.status_code in {401, 403}
    assert Session.objects.filter(pk=session_key).exists() is False
    assert client.session.get("_auth_user_id") is None


def test_issue_and_draft_assignees_intersect_the_current_slack_project_roster(
    workspace,
    unconfigured_instance,
):
    _installation, project, stale_user = _stale_slack_project_roster(
        workspace, unconfigured_instance
    )
    requested_ids = [_workspace_admin(workspace).id, stale_user.id]

    app_issue = AppIssueCreateSerializer(
        data={"name": "App roster issue", "assignee_ids": requested_ids},
        context={"project_id": project.id},
    )
    draft_issue = DraftIssueCreateSerializer(
        data={"name": "Draft roster issue", "assignee_ids": requested_ids},
        context={"project_id": project.id},
    )
    api_issue = APIIssueSerializer(
        data={"name": "API roster issue", "assignees": requested_ids},
        context={"project_id": project.id, "workspace_id": workspace.id},
    )

    assert app_issue.is_valid(), app_issue.errors
    assert draft_issue.is_valid(), draft_issue.errors
    assert api_issue.is_valid(), api_issue.errors
    assert list(app_issue.validated_data["assignee_ids"]) == [_workspace_admin(workspace).id]
    assert list(draft_issue.validated_data["assignee_ids"]) == [_workspace_admin(workspace).id]
    assert list(api_issue.validated_data["assignees"]) == [_workspace_admin(workspace).id]
    assert set(
        active_project_members()
        .filter(project=project)
        .values_list("member_id", flat=True)
    ) == {_workspace_admin(workspace).id}


def test_stale_slack_default_assignee_is_not_reapplied(
    workspace,
    unconfigured_instance,
):
    _installation, project, stale_user = _stale_slack_project_roster(
        workspace, unconfigured_instance
    )
    context = {
        "project_id": project.id,
        "workspace_id": workspace.id,
        "default_assignee_id": stale_user.id,
    }
    app_issue = AppIssueCreateSerializer(
        data={"name": "App default roster issue"},
        context=context,
    )
    api_issue = APIIssueSerializer(
        data={"name": "API default roster issue"},
        context=context,
    )

    assert app_issue.is_valid(), app_issue.errors
    assert api_issue.is_valid(), api_issue.errors
    created_issues = [app_issue.save(), api_issue.save()]

    assert IssueAssignee.objects.filter(issue__in=created_issues).exists() is False


def test_module_targets_intersect_the_current_slack_project_roster(
    workspace,
    unconfigured_instance,
):
    _installation, project, stale_user = _stale_slack_project_roster(
        workspace, unconfigured_instance
    )
    requested_ids = [_workspace_admin(workspace).id, stale_user.id]
    app_members = ModuleWriteSerializer(
        data={"name": "App roster module", "member_ids": requested_ids},
        context={"project": project},
    )
    api_members = APIModuleCreateSerializer(
        data={"name": "API roster module", "members": requested_ids},
        context={"project_id": project.id, "workspace_id": workspace.id},
    )

    assert app_members.is_valid(), app_members.errors
    assert api_members.is_valid(), api_members.errors
    assert [member.id for member in app_members.validated_data["member_ids"]] == [
        _workspace_admin(workspace).id
    ]
    assert list(api_members.validated_data["members"]) == [_workspace_admin(workspace).id]

    app_lead = ModuleWriteSerializer(
        data={"name": "Stale app lead", "lead_id": stale_user.id},
        context={"project": project},
    )
    api_lead = APIModuleCreateSerializer(
        data={"name": "Stale API lead", "lead": stale_user.id},
        context={"project_id": project.id, "workspace_id": workspace.id},
    )
    assert app_lead.is_valid() is False
    assert "lead_id" in app_lead.errors
    assert api_lead.is_valid() is False
    assert "lead" in api_lead.errors


def test_subscriber_and_cycle_owner_require_the_current_slack_project_roster(
    workspace,
    unconfigured_instance,
):
    _installation, project, stale_user = _stale_slack_project_roster(
        workspace, unconfigured_instance
    )
    subscriber = IssueSubscriberSerializer(
        data={"subscriber": stale_user.id},
        context={"project_id": project.id},
    )
    stale_owner = APICycleCreateSerializer(
        data={"name": "Stale owner cycle", "owned_by": stale_user.id},
        context={
            "request": SimpleNamespace(user=_workspace_admin(workspace)),
            "project_id": project.id,
        },
    )
    current_owner = APICycleCreateSerializer(
        data={"name": "Current owner cycle"},
        context={
            "request": SimpleNamespace(user=_workspace_admin(workspace)),
            "project_id": project.id,
        },
    )

    assert subscriber.is_valid() is False
    assert "subscriber" in subscriber.errors
    assert stale_owner.is_valid() is False
    assert "owned_by" in stale_owner.errors
    assert current_owner.is_valid(), current_owner.errors
    assert current_owner.validated_data["owned_by"] == _workspace_admin(workspace)


def test_cycle_update_preserves_omitted_owner_and_maps_explicit_null_to_requester(
    workspace,
    unconfigured_instance,
):
    installation, project, _stale_user = _stale_slack_project_roster(
        workspace, unconfigured_instance
    )
    preserved_owner = User.objects.create(
        email="current-cycle-owner@example.com",
        username="current-cycle-owner",
        is_active=True,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=preserved_owner,
        role=15,
        is_active=True,
    )
    ExternalIdentity.objects.create(
        user=preserved_owner,
        source=installation,
        external_user_id="UCYCLEOWNER",
        source_generation=installation.generation,
    )
    ProjectMember.objects.create(
        workspace=workspace,
        project=project,
        member=preserved_owner,
        role=15,
        is_active=True,
    )
    cycle = Cycle.objects.create(
        workspace=workspace,
        project=project,
        name="Roster-owned cycle",
        owned_by=preserved_owner,
    )
    context = {
        "request": SimpleNamespace(user=_workspace_admin(workspace)),
        "project_id": project.id,
    }

    omitted_owner = APICycleUpdateSerializer(
        cycle,
        data={"name": "Renamed roster-owned cycle"},
        partial=True,
        context=context,
    )
    assert omitted_owner.is_valid(), omitted_owner.errors
    assert "owned_by" not in omitted_owner.validated_data
    omitted_owner.save()
    cycle.refresh_from_db()
    assert cycle.owned_by_id == preserved_owner.id

    explicit_null = APICycleUpdateSerializer(
        cycle,
        data={"owned_by": None},
        partial=True,
        context=context,
    )
    assert explicit_null.is_valid(), explicit_null.errors
    assert explicit_null.validated_data["owned_by"] == _workspace_admin(workspace)
    explicit_null.save()
    cycle.refresh_from_db()
    assert cycle.owned_by_id == _workspace_admin(workspace).id


def test_api_key_requires_and_accepts_a_live_slack_projection(
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )
    token = APIToken.objects.create(user=_workspace_admin(workspace), token="slack-backed-token")

    user, authenticated_token = APIKeyAuthentication().validate_api_token(token.token)

    assert user == _workspace_admin(workspace)
    assert authenticated_token == token.token


@pytest.mark.parametrize(
    "serializer_class",
    [AppProjectSerializer, ProjectUpdateSerializer],
)
def test_project_lead_cannot_be_a_slack_guest(
    serializer_class,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    guest = User.objects.create(
        email="lead-guest@example.com",
        username="lead-guest",
        is_active=True,
    )
    WorkspaceMember.objects.create(
        workspace=workspace,
        member=guest,
        role=5,
        is_active=True,
    )
    ExternalIdentity.objects.create(
        user=guest,
        source=installation,
        external_user_id="ULEADGUEST",
        source_generation=installation.generation,
    )
    project = Project.objects.create(
        workspace=workspace,
        name="Slack lead boundary",
        identifier="SLACKLEAD",
    )

    serializer = serializer_class(
        project,
        data={"project_lead": str(guest.id)},
        context={"workspace_id": workspace.id},
        partial=True,
    )

    assert serializer.is_valid() is False
    assert "project_lead" in serializer.errors


@patch("plane.authentication.views.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
@patch("plane.integrations.slack.get_slack_credentials", return_value=SLACK_CREDENTIALS)
def test_instance_config_exposes_only_safe_slack_status(
    _instance_credentials,
    _mock_credentials,
    client,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    installation.status = IdentitySource.Status.ACTIVE
    installation.last_synced_at = timezone.now()
    installation.sync_error = "users.list temporarily failed"
    installation.external_organization_icon_url = "https://avatars.slack-edge.com/team.png"
    installation.save()
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
        source_generation=installation.generation,
    )

    public_response = client.get("/api/instances/")
    assert public_response.status_code == 200
    public_config = public_response.json()["config"]
    identity_source = public_config["identity_source"]
    assert identity_source["provider"] == "slack"
    assert identity_source["configured"] is True
    assert identity_source["connected"] is True
    assert identity_source["organization"] == {
        "name": "Acme Slack",
        "domain": "acme",
        "icon_url": "https://avatars.slack-edge.com/team.png",
    }
    assert identity_source["last_synced_at"] is not None
    assert identity_source["auth_url"] == "/auth/slack/"
    assert identity_source["install_url"] == "/auth/slack/install/"
    assert "sync_error" not in identity_source
    assert "T123" not in str(public_config)
    assert "xoxb-secret" not in str(public_config)
    assert client.get("/auth/slack/").url.startswith("https://slack.com/openid/connect/authorize")

    _force_slack_session(client, _workspace_admin(workspace), installation)
    admin_response = client.get("/api/instances/")
    assert admin_response.status_code == 200
    assert (
        admin_response.json()["config"]["identity_source"]["sync_error"]
        == installation.sync_error
    )


def test_instance_config_reports_environment_credentials(
    monkeypatch,
    client,
    unconfigured_instance,
):
    monkeypatch.setenv("SLACK_CLIENT_ID", "environment-client-id")
    monkeypatch.setenv("SLACK_CLIENT_SECRET", "environment-client-secret")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "environment-signing-secret")
    response = client.get("/api/instances/")

    assert response.status_code == 200
    identity_source = response.json()["config"]["identity_source"]
    assert identity_source == {
        "provider": "slack",
        "configured": True,
        "connected": False,
        "organization": None,
        "last_synced_at": None,
        "auth_url": "/auth/slack/",
        "install_url": "/auth/slack/install/",
    }


@patch("builtins.input")
def test_dummy_data_command_cannot_add_a_non_slack_workspace_member(
    mock_input,
    workspace,
    unconfigured_instance,
):
    installation = _installed_slack_workspace(workspace, unconfigured_instance)
    ExternalIdentity.objects.create(
        user=_workspace_admin(workspace),
        source=installation,
        external_user_id="UOWNER",
    )
    outsider = User.objects.create(
        email="outsider@example.com",
        username="outsider",
        is_active=True,
    )
    mock_input.side_effect = [_workspace_admin(workspace).email, outsider.email]

    call_command("create_dummy_data")

    assert not WorkspaceMember.objects.filter(workspace=workspace, member=outsider).exists()
