# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

"""Resolve URL-scoped workspace context for the singleton deployment."""

from django.http import Http404
from django.urls import path


SINGLETON_WORKSPACE_KWARG = "_singleton_workspace_kwarg"
SUPPORTED_WORKSPACE_KWARGS = frozenset({"slug", "workspace_id"})


def singleton_workspace_path(
    route,
    view,
    kwargs=None,
    name=None,
    *,
    workspace_kwarg="slug",
):
    """Create a route whose workspace identifier is supplied by middleware."""

    if workspace_kwarg not in SUPPORTED_WORKSPACE_KWARGS:
        raise ValueError(f"Unsupported singleton workspace kwarg: {workspace_kwarg}")

    defaults = dict(kwargs or {})
    if SINGLETON_WORKSPACE_KWARG in defaults:
        raise ValueError(f"{SINGLETON_WORKSPACE_KWARG} is reserved")
    defaults[SINGLETON_WORKSPACE_KWARG] = workspace_kwarg
    return path(route, view, defaults, name=name)


class SingletonWorkspaceContextMiddleware:
    """Inject the singleton workspace into explicitly marked URL patterns."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        workspace_kwarg = view_kwargs.pop(SINGLETON_WORKSPACE_KWARG, None)
        if workspace_kwarg is None:
            return None
        if workspace_kwarg not in SUPPORTED_WORKSPACE_KWARGS:
            raise RuntimeError(f"Unsupported singleton workspace kwarg: {workspace_kwarg}")
        if workspace_kwarg in view_kwargs:
            raise RuntimeError(f"URL already supplied singleton workspace kwarg: {workspace_kwarg}")

        from plane.db.models import Workspace

        try:
            workspace = Workspace.objects.using("default").only("id", "slug").get(singleton_key=True)
        except Workspace.DoesNotExist as exc:
            raise Http404("Workspace is not configured") from exc

        request.workspace = workspace
        view_kwargs[workspace_kwarg] = workspace.slug if workspace_kwarg == "slug" else workspace.id
        return None
