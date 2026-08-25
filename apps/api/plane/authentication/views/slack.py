# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import hashlib
import logging
import re
import secrets
from typing import Any
from urllib.parse import urlencode, urljoin

import jwt
from django.contrib.auth import login
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views import View

from plane.authentication.errors import identity_error_payload
from plane.utils.host import base_host
from plane.bgtasks.slack_sync import reconcile_slack_installation
from plane.db.models import (
    Profile,
    IdentitySource,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.integrations.slack import (
    SlackAuthenticationError,
    SlackClient,
    SlackClientError,
    get_slack_credentials,
    revoke_installation,
    sync_slack_user,
)
from plane.integrations.identity import configured_identity_provider
from plane.license.models import Instance
from plane.utils.cache import invalidate_cache_directly
from plane.utils.constants import RESTRICTED_WORKSPACE_SLUGS
from plane.utils.path_validator import get_safe_redirect_url, validate_next_path
from plane.utils.identity_access import (
    IDENTITY_SOURCE_GENERATION_SESSION_KEY,
    IDENTITY_SOURCE_ID_SESSION_KEY,
    WORKSPACE_ADMIN_ROLE,
    lock_current_session_identity,
)

logger = logging.getLogger("plane")

SLACK_INSTALL_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OPENID_AUTHORIZE_URL = "https://slack.com/openid/connect/authorize"
SLACK_OPENID_ISSUER = "https://slack.com"
SLACK_OPENID_JWKS_URL = "https://slack.com/openid/connect/keys"
SLACK_TEAM_ID_CLAIM = "https://slack.com/team_id"
SLACK_USER_ID_CLAIM = "https://slack.com/user_id"
SLACK_INSTALL_SCOPES = ("team:read", "users:read", "users:read.email")
SLACK_OPENID_SCOPES = ("openid", "profile", "email")
SLACK_JWKS_CLIENT = jwt.PyJWKClient(
    SLACK_OPENID_JWKS_URL,
    cache_keys=True,
    lifespan=300,
    timeout=5,
)

_INSTALL_STATE_SESSION_KEY = "slack_install_state"
_LOGIN_STATE_SESSION_KEY = "slack_login_state"
_LOGIN_NONCE_SESSION_KEY = "slack_login_nonce"
_LOGIN_NEXT_PATH_SESSION_KEY = "slack_login_next_path"
_LOGIN_ORIGIN_SESSION_KEY = "slack_login_origin"

_APP_ORIGIN = "app"
_SPACE_ORIGIN = "space"
_LOGIN_ORIGINS = {_APP_ORIGIN, _SPACE_ORIGIN}
_BOOTSTRAP_INSTALL_MODE = "bootstrap"
_RECONNECT_INSTALL_MODE = "reconnect"


def _callback_uri(request, route_name: str) -> str:
    return request.build_absolute_uri(reverse(route_name))


def _error_redirect(
    request,
    error_name: str,
    *,
    origin: str = _APP_ORIGIN,
    next_path: str = "",
) -> HttpResponseRedirect:
    return HttpResponseRedirect(
        get_safe_redirect_url(
            base_url=base_host(
                request=request,
                is_app=origin == _APP_ORIGIN,
                is_space=origin == _SPACE_ORIGIN,
            ),
            next_path=next_path,
            params=identity_error_payload(error_name),
        )
    )


def _credentials_are_configured() -> bool:
    if configured_identity_provider() != IdentitySource.Provider.SLACK:
        return False
    credentials = get_slack_credentials()
    return bool(credentials.client_id and credentials.client_secret and credentials.signing_secret)


def _setup_is_available(instance: Instance | None) -> bool:
    return bool(
        instance is not None
        and not instance.is_setup_done
        and not User.objects.exists()
        and not Workspace.all_objects.exists()
        and not IdentitySource.all_objects.exists()
    )


def _install_mode(
    instance: Instance | None,
    installation: IdentitySource | None = None,
) -> str | None:
    if _setup_is_available(instance):
        return _BOOTSTRAP_INSTALL_MODE

    installation = installation or IdentitySource.objects.select_related("workspace").first()
    if not (
        instance is not None
        and instance.is_setup_done
        and installation is not None
        and installation.provider == IdentitySource.Provider.SLACK
        and installation.status
        in {IdentitySource.Status.REVOKED, IdentitySource.Status.ERROR}
        and IdentitySource.all_objects.count() == 1
        and Workspace.all_objects.filter(pk=installation.workspace_id).count() == 1
        and Workspace.all_objects.count() == 1
    ):
        return None
    return _RECONNECT_INSTALL_MODE


def _one_shot_session_value(request, key: str) -> str:
    value = request.session.pop(key, "")
    return value if isinstance(value, str) else ""


def _login_origin(value: Any) -> str:
    return value if isinstance(value, str) and value in _LOGIN_ORIGINS else _APP_ORIGIN


def _state_matches(expected: str, supplied: Any) -> bool:
    return bool(
        expected
        and isinstance(supplied, str)
        and secrets.compare_digest(expected, supplied)
    )


def _mapping(value: Any) -> dict[str, Any] | None:
    return value if isinstance(value, dict) else None


def _scope_list(raw_scopes: Any) -> list[str]:
    if isinstance(raw_scopes, list):
        scopes = [str(scope).strip() for scope in raw_scopes]
    elif isinstance(raw_scopes, str):
        scopes = re.split(r"[\s,]+", raw_scopes)
    else:
        scopes = []
    return sorted({scope for scope in scopes if scope})


def _team_icon_url(team: dict[str, Any]) -> str:
    icon = _mapping(team.get("icon")) or {}
    for key in ("image_original", "image_230", "image_132", "image_102", "image_68"):
        value = icon.get(key)
        if value:
            return str(value)
    return ""


def _is_active_human(member: dict[str, Any], *, team_id: str) -> bool:
    external_user_id = str(member.get("id") or "").strip()
    return bool(
        external_user_id
        and str(member.get("team_id") or "") == team_id
        and not member.get("deleted")
        and not member.get("suspended")
        and not member.get("is_forgotten")
        and not member.get("is_invited_user")
        and not member.get("is_profile_only_user")
        and not member.get("is_bot")
        and not member.get("is_app_user")
        and not member.get("is_workflow_bot")
        and not member.get("is_agentforce_bot")
        and not member.get("is_stranger")
        and not member.get("is_external")
        and external_user_id != "USLACKBOT"
        and str(member.get("name") or "").lower() != "slackbot"
    )


def _is_slack_admin(member: dict[str, Any]) -> bool:
    return bool(
        not member.get("is_restricted")
        and not member.get("is_ultra_restricted")
        and (
            member.get("is_admin")
            or member.get("is_owner")
            or member.get("is_primary_owner")
        )
    )


def _workspace_slug(team: dict[str, Any], team_id: str) -> str:
    source = str(team.get("domain") or team.get("name") or "")
    value = slugify(source)[:48]
    if not value or value in RESTRICTED_WORKSPACE_SLUGS:
        value = slugify(f"slack-{team_id}")[:48]
    return value or "slack-workspace"


def _profile_text(profile: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = profile.get(key)
        if value:
            return str(value)
    return ""


def _profile_email(profile: dict[str, Any]) -> str | None:
    raw_email = str(profile.get("email") or "").strip().lower()
    if raw_email:
        try:
            validate_email(raw_email)
        except ValidationError:
            pass
        else:
            return raw_email
    return None


def _create_bootstrap_user(team_id: str, member: dict[str, Any]) -> User:
    external_user_id = str(member["id"])
    profile = _mapping(member.get("profile")) or {}
    email = _profile_email(profile)
    display_name = _profile_text(
        profile,
        "display_name_normalized",
        "display_name",
        "real_name_normalized",
        "real_name",
    ) or str(member.get("real_name") or member.get("name") or external_user_id)
    avatar = _profile_text(
        profile,
        "image_original",
        "image_512",
        "image_192",
        "image_72",
        "image_48",
    )
    username_digest = hashlib.sha256(f"{team_id}:{external_user_id}".encode()).hexdigest()[:32]
    user = User(
        email=email,
        username=f"slack-{username_digest}",
        display_name=display_name,
        first_name=_profile_text(profile, "first_name"),
        last_name=_profile_text(profile, "last_name"),
        avatar=avatar,
        is_active=True,
    )
    user.save()
    Profile.objects.create(user=user)
    return user


def _validate_openid_id_token(id_token: str, *, client_id: str, nonce: str) -> dict[str, Any]:
    if not id_token:
        raise jwt.InvalidTokenError("Slack did not return an ID token")

    signing_key = SLACK_JWKS_CLIENT.get_signing_key_from_jwt(id_token)
    claims = jwt.decode(
        id_token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=SLACK_OPENID_ISSUER,
        options={"require": ["aud", "exp", "iss", "nonce", "sub"]},
    )
    token_nonce = claims.get("nonce")
    if not (
        isinstance(token_nonce, str)
        and nonce
        and secrets.compare_digest(token_nonce, nonce)
    ):
        raise jwt.InvalidTokenError("Slack ID token nonce does not match")
    return claims


def _claim_id(claims: dict[str, Any], namespaced_key: str, fallback_key: str) -> str:
    return str(claims.get(namespaced_key) or claims.get(fallback_key) or "").strip()


def _login_current_external_identity(
    request,
    *,
    source_id,
    expected_generation: int,
    user_id,
) -> bool:
    """Persist a session while holding the authoritative source fence."""

    with transaction.atomic():
        identity = lock_current_session_identity(
            source_id=source_id,
            expected_generation=expected_generation,
            user_id=user_id,
        )
        if identity is None:
            return False

        login(request=request, user=identity.user)
        request.session[IDENTITY_SOURCE_ID_SESSION_KEY] = str(source_id)
        request.session[IDENTITY_SOURCE_GENERATION_SESSION_KEY] = expected_generation
        request.session.save()
        request._identity_session_fence = {
            "source_id": str(source_id),
            "expected_generation": expected_generation,
            "user_id": str(user_id),
            "session_key": request.session.session_key,
        }
    return True


class SlackInstallEndpoint(View):
    """Bootstrap or reconnect the singleton Slack identity source."""

    def get(self, request):
        instance = Instance.objects.first()
        installation = IdentitySource.objects.select_related("workspace").first()
        install_mode = _install_mode(instance, installation)
        if install_mode is None:
            return _error_redirect(request, "IDENTITY_SOURCE_SETUP_NOT_ALLOWED")
        if not _credentials_are_configured():
            return _error_redirect(request, "IDENTITY_SOURCE_NOT_CONFIGURED")

        state = secrets.token_urlsafe(32)
        request.session[_INSTALL_STATE_SESSION_KEY] = state
        credentials = get_slack_credentials()
        query_params = {
            "client_id": credentials.client_id,
            "scope": ",".join(SLACK_INSTALL_SCOPES),
            "redirect_uri": _callback_uri(request, "slack-install-callback"),
            "state": state,
        }
        if install_mode == _RECONNECT_INSTALL_MODE and installation is not None:
            query_params["team"] = installation.external_organization_id
        query = urlencode(query_params)
        return HttpResponseRedirect(f"{SLACK_INSTALL_AUTHORIZE_URL}?{query}")


class SlackInstallCallbackEndpoint(View):
    """Bind or reconnect the Slack team and singleton workspace atomically."""

    def get(self, request):
        expected_state = _one_shot_session_value(request, _INSTALL_STATE_SESSION_KEY)
        if not _state_matches(expected_state, request.GET.get("state")):
            return _error_redirect(request, "IDENTITY_SOURCE_OAUTH_STATE_INVALID")

        code = request.GET.get("code")
        if request.GET.get("error") or not code:
            return _error_redirect(request, "IDENTITY_SOURCE_OAUTH_ERROR")
        if not _credentials_are_configured():
            return _error_redirect(request, "IDENTITY_SOURCE_NOT_CONFIGURED")

        instance = Instance.objects.first()
        existing_installation = IdentitySource.objects.select_related("workspace").first()
        if _install_mode(instance, existing_installation) is None:
            return _error_redirect(request, "IDENTITY_SOURCE_SETUP_NOT_ALLOWED")

        try:
            oauth_response = SlackClient().exchange_oauth_code(
                str(code),
                _callback_uri(request, "slack-install-callback"),
            )
            token_received_at = timezone.now()
            bot_token = str(oauth_response.get("access_token") or "")
            oauth_team = _mapping(oauth_response.get("team")) or {}
            authed_user = _mapping(oauth_response.get("authed_user")) or {}
            team_id = str(oauth_team.get("id") or "").strip()
            installer_id = str(authed_user.get("id") or "").strip()
            bot_user_id = str(oauth_response.get("bot_user_id") or "").strip()
            scopes = _scope_list(oauth_response.get("scope"))
            if (
                not bot_token
                or not team_id
                or not installer_id
                or not bot_user_id
                or not set(SLACK_INSTALL_SCOPES).issubset(scopes)
            ):
                raise SlackClientError("Slack OAuth response is incomplete")

            slack_client = SlackClient(bot_token)
            if existing_installation is not None and not secrets.compare_digest(
                existing_installation.external_organization_id,
                team_id,
            ):
                return _error_redirect(request, "IDENTITY_SOURCE_ORGANIZATION_MISMATCH")

            with transaction.atomic():
                locked_installation = (
                    IdentitySource.objects.select_for_update()
                    .select_related("workspace")
                    .first()
                )
                if locked_installation is None:
                    # Bootstrap has no installation row to serialize on, so use
                    # the singleton instance and then re-check the empty slot.
                    locked_instance = Instance.objects.select_for_update().get(pk=instance.pk)
                    if IdentitySource.all_objects.exists():
                        return _error_redirect(request, "IDENTITY_SOURCE_SETUP_NOT_ALLOWED")
                else:
                    # Match reconcile/event lock order: installation, workspace,
                    # then instance. This avoids reconnect deadlocks.
                    workspace = Workspace.objects.select_for_update().get(
                        pk=locked_installation.workspace_id
                    )
                    locked_instance = Instance.objects.select_for_update().get(pk=instance.pk)
                install_mode = _install_mode(locked_instance, locked_installation)
                if install_mode is None:
                    return _error_redirect(request, "IDENTITY_SOURCE_SETUP_NOT_ALLOWED")

                # Validate the token, team, and installer only after the
                # singleton installation/instance fence is held. A lifecycle or
                # user event that won the lock first is therefore reflected by
                # these commit-adjacent Slack reads; an event that arrives later
                # waits and is applied against the committed generation.
                team_snapshot_at = timezone.now()
                team_response = slack_client.team_info()
                team = _mapping(team_response.get("team"))
                installer_lookup_started_at = timezone.now()
                member_response = slack_client.users_info(installer_id)
                installer = _mapping(member_response.get("user"))
                if team is None or str(team.get("id") or "") != team_id:
                    return _error_redirect(request, "IDENTITY_SOURCE_ORGANIZATION_MISMATCH")
                if installer is None or not _is_active_human(installer, team_id=team_id):
                    return _error_redirect(request, "EXTERNAL_IDENTITY_INACTIVE")
                if not _is_slack_admin(installer):
                    return _error_redirect(request, "IDENTITY_SOURCE_ADMIN_REQUIRED")
                auth_response = slack_client.auth_test()
                if (
                    not secrets.compare_digest(
                        str(auth_response.get("team_id") or ""),
                        team_id,
                    )
                    or not secrets.compare_digest(
                        str(auth_response.get("user_id") or ""),
                        bot_user_id,
                    )
                ):
                    raise SlackClientError(
                        "Slack bot token identity does not match the installation"
                    )

                raw_team_name = str(
                    team.get("name") or oauth_team.get("name") or ""
                ).strip()
                team_name = (raw_team_name or f"Slack {team_id}")[:80]
                team_domain = str(team.get("domain") or "").strip()[:255]
                team_icon_url = _team_icon_url(team)

                if install_mode == _BOOTSTRAP_INSTALL_MODE:
                    user = _create_bootstrap_user(team_id, installer)
                    workspace = Workspace.objects.create(
                        name=team_name,
                        slug=_workspace_slug(team, team_id),
                        logo=team_icon_url,
                    )
                    WorkspaceMember.objects.create(
                        workspace=workspace,
                        member=user,
                        role=WORKSPACE_ADMIN_ROLE,
                    )
                    installation = IdentitySource(
                        workspace=workspace,
                        provider=IdentitySource.Provider.SLACK,
                        external_organization_id=team_id,
                        external_organization_name=team_name,
                        external_organization_domain=team_domain,
                        external_organization_icon_url=team_icon_url,
                        service_account_id=bot_user_id,
                        status=IdentitySource.Status.ACTIVE,
                        connected_at=token_received_at,
                        metadata_synced_at=team_snapshot_at,
                    )
                else:
                    if locked_installation is None or not secrets.compare_digest(
                        locked_installation.external_organization_id,
                        team_id,
                    ):
                        return _error_redirect(request, "IDENTITY_SOURCE_ORGANIZATION_MISMATCH")
                    installation = locked_installation
                    installation.external_organization_name = team_name
                    installation.external_organization_domain = team_domain
                    installation.external_organization_icon_url = team_icon_url
                    installation.service_account_id = bot_user_id
                    installation.status = IdentitySource.Status.ACTIVE
                    installation.generation += 1
                    installation.connected_at = token_received_at
                    installation.metadata_synced_at = team_snapshot_at
                    installation.last_synced_at = None
                    installation.sync_error = ""
                    installation.sync_error_at = None

                installation.set_access_token(bot_token)
                if not installation.encrypted_access_token:
                    raise SlackClientError("Slack bot token encryption failed")
                installation.save()

                if install_mode == _BOOTSTRAP_INSTALL_MODE:
                    identity = sync_slack_user(
                        installation,
                        installer,
                        user=user,
                        authoritative=True,
                        authoritative_started_at=installer_lookup_started_at,
                    )
                else:
                    workspace.name = team_name
                    workspace.logo = team_icon_url
                    workspace.logo_asset = None
                    workspace.save(update_fields=["name", "logo", "logo_asset", "updated_at"])
                    identity = sync_slack_user(
                        installation,
                        installer,
                        authoritative=True,
                        authoritative_started_at=installer_lookup_started_at,
                    )
                    user = identity.user if identity is not None else None

                if identity is None or user is None or identity.user_id != user.id or not identity.is_active:
                    raise ValueError("Slack installer identity could not be bound")

                locked_instance.instance_name = team_name
                locked_instance.is_setup_done = True
                locked_instance.save(update_fields=["instance_name", "is_setup_done", "updated_at"])
                transaction.on_commit(
                    lambda installation_id=str(installation.id): reconcile_slack_installation.delay(
                        installation_id
                    ),
                    robust=True,
                )

            invalidate_cache_directly(
                path="/api/instances/",
                user=False,
                request=request,
            )
            if not _login_current_external_identity(
                request,
                source_id=installation.id,
                expected_generation=installation.generation,
                user_id=user.id,
            ):
                return _error_redirect(
                    request,
                    "IDENTITY_SOURCE_OAUTH_ERROR",
                )
            return HttpResponseRedirect(
                urljoin(
                    f"{base_host(request=request, is_app=True).rstrip('/')}/",
                    f"{workspace.slug}/",
                )
            )
        except (IntegrityError, SlackClientError, ValueError, jwt.PyJWTError):
            logger.exception("Slack workspace installation failed")
            return _error_redirect(request, "IDENTITY_SOURCE_OAUTH_ERROR")


class SlackLoginEndpoint(View):
    """Start Slack OpenID Connect for the team bound during installation."""

    def get(self, request):
        next_path = validate_next_path(request.GET.get("next_path", ""))
        origin = _login_origin(request.GET.get("origin"))
        instance = Instance.objects.first()
        if instance is None or not instance.is_setup_done:
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_NOT_CONFIGURED",
                origin=origin,
                next_path=next_path,
            )
        if not _credentials_are_configured():
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_NOT_CONFIGURED",
                origin=origin,
                next_path=next_path,
            )

        installation = IdentitySource.objects.filter(
            provider=IdentitySource.Provider.SLACK,
            status=IdentitySource.Status.ACTIVE
        ).first()
        if installation is None:
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_NOT_CONFIGURED",
                origin=origin,
                next_path=next_path,
            )

        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        request.session[_LOGIN_STATE_SESSION_KEY] = state
        request.session[_LOGIN_NONCE_SESSION_KEY] = nonce
        request.session[_LOGIN_NEXT_PATH_SESSION_KEY] = next_path
        request.session[_LOGIN_ORIGIN_SESSION_KEY] = origin
        credentials = get_slack_credentials()
        query = urlencode(
            {
                "client_id": credentials.client_id,
                "scope": " ".join(SLACK_OPENID_SCOPES),
                "response_type": "code",
                "redirect_uri": _callback_uri(request, "slack-login-callback"),
                "state": state,
                "nonce": nonce,
                "team": installation.external_organization_id,
            }
        )
        return HttpResponseRedirect(f"{SLACK_OPENID_AUTHORIZE_URL}?{query}")


class SlackLoginCallbackEndpoint(View):
    """Validate Slack OIDC and refresh the Slack-owned local user projection."""

    def get(self, request):
        expected_state = _one_shot_session_value(request, _LOGIN_STATE_SESSION_KEY)
        nonce = _one_shot_session_value(request, _LOGIN_NONCE_SESSION_KEY)
        next_path = _one_shot_session_value(request, _LOGIN_NEXT_PATH_SESSION_KEY)
        origin = _login_origin(_one_shot_session_value(request, _LOGIN_ORIGIN_SESSION_KEY))
        if not _state_matches(expected_state, request.GET.get("state")) or not nonce:
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_OAUTH_STATE_INVALID",
                origin=origin,
                next_path=next_path,
            )

        code = request.GET.get("code")
        if request.GET.get("error") or not code:
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_OAUTH_ERROR",
                origin=origin,
                next_path=next_path,
            )
        if not _credentials_are_configured():
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_NOT_CONFIGURED",
                origin=origin,
                next_path=next_path,
            )

        installation = (
            IdentitySource.objects.select_related("workspace")
            .filter(
                provider=IdentitySource.Provider.SLACK,
                status=IdentitySource.Status.ACTIVE,
            )
            .first()
        )
        if installation is None:
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_NOT_CONFIGURED",
                origin=origin,
                next_path=next_path,
            )

        try:
            credentials = get_slack_credentials()
            oidc_response = SlackClient().exchange_openid_code(
                str(code),
                _callback_uri(request, "slack-login-callback"),
            )
            access_token = str(oidc_response.get("access_token") or "")
            id_token = str(oidc_response.get("id_token") or "")
            if not access_token or not id_token:
                raise SlackClientError("Slack OIDC response is incomplete")

            id_claims = _validate_openid_id_token(
                id_token,
                client_id=credentials.client_id,
                nonce=nonce,
            )
            userinfo = SlackClient().openid_userinfo(access_token)
            id_subject = str(id_claims.get("sub") or "")
            info_subject = str(userinfo.get("sub") or "")
            id_team_id = _claim_id(id_claims, SLACK_TEAM_ID_CLAIM, "team_id")
            info_team_id = _claim_id(userinfo, SLACK_TEAM_ID_CLAIM, "team_id")
            id_user_id = _claim_id(id_claims, SLACK_USER_ID_CLAIM, "user_id")
            info_user_id = _claim_id(userinfo, SLACK_USER_ID_CLAIM, "user_id")
            if (
                not id_subject
                or not secrets.compare_digest(id_subject, info_subject)
                or not id_team_id
                or not secrets.compare_digest(id_team_id, info_team_id)
                or not id_user_id
                or not secrets.compare_digest(id_user_id, info_user_id)
            ):
                return _error_redirect(
                    request,
                    "EXTERNAL_IDENTITY_INVALID",
                    origin=origin,
                    next_path=next_path,
                )
            if not secrets.compare_digest(
                installation.external_organization_id,
                id_team_id,
            ):
                return _error_redirect(
                    request,
                    "IDENTITY_SOURCE_ORGANIZATION_MISMATCH",
                    origin=origin,
                    next_path=next_path,
                )

            try:
                try:
                    bot_token = installation.get_access_token()
                except ValueError as exc:
                    raise SlackAuthenticationError(
                        "Slack bot token could not be decrypted",
                        error_code="bot_token_decryption_failed",
                    ) from exc
                slack_client = SlackClient(bot_token)
                member_lookup_started_at = timezone.now()
                member_response = slack_client.users_info(id_user_id)
            except SlackAuthenticationError as exc:
                error_code = exc.error_code or "unknown_auth_error"
                revoke_installation(
                    installation,
                    f"Slack bot authentication failed: {error_code}",
                    expected_generation=installation.generation,
                )
                raise
            member = _mapping(member_response.get("user"))
            if (
                member is None
                or not secrets.compare_digest(str(member.get("id") or ""), id_user_id)
                or not secrets.compare_digest(
                    str(member.get("team_id") or ""),
                    installation.external_organization_id,
                )
            ):
                return _error_redirect(
                    request,
                    "EXTERNAL_IDENTITY_INVALID",
                    origin=origin,
                    next_path=next_path,
                )
            if not _is_active_human(
                member,
                team_id=installation.external_organization_id,
            ):
                sync_slack_user(
                    installation,
                    member,
                    authoritative=True,
                    authoritative_started_at=member_lookup_started_at,
                )
                return _error_redirect(
                    request,
                    "EXTERNAL_IDENTITY_INACTIVE",
                    origin=origin,
                    next_path=next_path,
                )

            identity = sync_slack_user(
                installation,
                member,
                authoritative=True,
                authoritative_started_at=member_lookup_started_at,
            )
            if (
                identity is None
                or identity.source_id != installation.id
                or not identity.is_active
                or not identity.user.is_active
            ):
                return _error_redirect(
                    request,
                    "EXTERNAL_IDENTITY_NOT_FOUND",
                    origin=origin,
                    next_path=next_path,
                )

            user = identity.user
            if not _login_current_external_identity(
                request,
                source_id=installation.id,
                expected_generation=installation.generation,
                user_id=user.id,
            ):
                return _error_redirect(
                    request,
                    "EXTERNAL_IDENTITY_NOT_FOUND",
                    origin=origin,
                    next_path=next_path,
                )
            destination = validate_next_path(next_path) or f"/{installation.workspace.slug}/"
            destination_base = base_host(
                request=request,
                is_app=origin == _APP_ORIGIN,
                is_space=origin == _SPACE_ORIGIN,
            )
            return HttpResponseRedirect(
                urljoin(
                    f"{destination_base.rstrip('/')}/",
                    destination.lstrip("/"),
                )
            )
        except (IntegrityError, SlackClientError, ValueError, jwt.PyJWTError):
            logger.exception("Slack login failed")
            return _error_redirect(
                request,
                "IDENTITY_SOURCE_OAUTH_ERROR",
                origin=origin,
                next_path=next_path,
            )
