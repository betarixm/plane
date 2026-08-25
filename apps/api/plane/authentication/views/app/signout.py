# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.views import View
from django.contrib.auth import logout
from django.http import HttpResponseRedirect

# Module imports
from plane.utils.host import base_host


class SignOutAuthEndpoint(View):
    def post(self, request):
        logout(request)
        return HttpResponseRedirect(base_host(request=request, is_app=True))
