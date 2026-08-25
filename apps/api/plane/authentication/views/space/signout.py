# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.views import View
from django.contrib.auth import logout
from django.http import HttpResponseRedirect

# Module imports
from plane.utils.host import base_host
from plane.utils.path_validator import get_safe_redirect_url


class SignOutAuthSpaceEndpoint(View):
    def post(self, request):
        next_path = request.POST.get("next_path")

        logout(request)
        url = get_safe_redirect_url(base_url=base_host(request=request, is_space=True), next_path=next_path)
        return HttpResponseRedirect(url)
