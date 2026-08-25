# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework.test import APIClient
from pytest_django.fixtures import django_db_setup

from plane.db.models import (
    ExternalIdentity,
    IdentitySource,
    User,
    Workspace,
    WorkspaceMember,
)
from plane.db.models.api import APIToken


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup):  # noqa: F811
    """Set up the Django database for the test session"""
    pass


@pytest.fixture
def api_client():
    """Return an unauthenticated API client"""
    return APIClient()


@pytest.fixture
def create_user(db):
    """Create and return a user instance"""
    user = User.objects.create(
        email="test@plane.so",
        username="test-user",
        first_name="Test",
        last_name="User",
    )
    return user


@pytest.fixture
def api_token(db, create_user):
    """Create and return an API token for testing the external API"""
    token = APIToken.objects.create(
        user=create_user,
        label="Test API Token",
        token="test-api-token-12345",
    )
    return token


@pytest.fixture
def api_key_client(api_client, api_token, external_identity_source):
    """Return an API key authenticated client for external API testing"""
    api_client.credentials(HTTP_X_API_KEY=api_token.token)
    return api_client


@pytest.fixture
def session_client(api_client, create_user, external_identity_source):
    """Return a session authenticated API client for app API testing, which is what plane.app uses"""
    api_client.force_authenticate(user=create_user)
    return api_client


@pytest.fixture
def api_token_data():
    """Return sample API token data for testing"""
    from django.utils import timezone
    from datetime import timedelta

    return {
        "label": "Test API Token",
        "description": "Test description for API token",
        "expired_at": (timezone.now() + timedelta(days=30)).isoformat(),
    }


@pytest.fixture
def create_api_token_for_user(db, create_user):
    """Create and return an API token for a specific user"""
    return APIToken.objects.create(
        label="Test Token",
        description="Test token description",
        user=create_user,
    )


@pytest.fixture
def plane_server(live_server):
    """
    Renamed version of live_server fixture to avoid name clashes.
    Returns a live Django server for testing HTTP requests.
    """
    return live_server


@pytest.fixture
def workspace(create_user):
    """
    Create a new workspace and return the
    corresponding Workspace model instance.
    """
    # Create the workspace using the model
    created_workspace = Workspace.objects.create(
        name="Test Workspace",
        slug="test-workspace",
    )

    WorkspaceMember.objects.create(workspace=created_workspace, member=create_user, role=20)

    return created_workspace


@pytest.fixture
def external_identity_source(workspace, create_user):
    """Create the active Slack projection required by human authentication."""

    installation = IdentitySource.objects.create(
        workspace=workspace,
        provider=IdentitySource.Provider.SLACK,
        external_organization_id="TTEST",
        external_organization_name="Test Slack",
    )
    identity = ExternalIdentity.objects.create(
        user=create_user,
        source=installation,
        external_user_id="UTEST",
        source_generation=installation.generation,
    )
    return identity


@pytest.fixture
def bind_external_identity(external_identity_source):
    """Bind an additional test user to the singleton Slack generation."""

    def bind(user, *, external_user_id=None):
        from uuid import uuid4

        return ExternalIdentity.objects.create(
            user=user,
            source=external_identity_source.source,
            external_user_id=external_user_id or f"U{uuid4().hex[:12].upper()}",
            source_generation=external_identity_source.source.generation,
        )

    return bind
