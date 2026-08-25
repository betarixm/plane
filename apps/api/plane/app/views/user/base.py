# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control
from django.views.decorators.vary import vary_on_cookie

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.app.serializers import (
    IssueActivitySerializer,
    ProfileSerializer,
    UserMeSerializer,
    UserMeSettingsSerializer,
)
from plane.app.views.base import BaseAPIView, BaseViewSet
from plane.db.models import (
    IssueActivity,
    Profile,
    User,
)
from plane.utils.order_queryset import ACTIVITY_ORDER_BY_ALLOWLIST, sanitize_order_by
from plane.utils.paginator import BasePaginator


class UserEndpoint(BaseViewSet):
    serializer_class = UserMeSerializer
    model = User
    use_read_replica = True

    def get_object(self):
        return self.request.user

    @method_decorator(cache_control(private=True, max_age=12))
    @method_decorator(vary_on_cookie)
    def retrieve(self, request):
        serialized_data = UserMeSerializer(request.user).data
        return Response(serialized_data, status=status.HTTP_200_OK)

    @method_decorator(cache_control(private=True, max_age=12))
    @method_decorator(vary_on_cookie)
    def retrieve_user_settings(self, request):
        serialized_data = UserMeSettingsSerializer(request.user).data
        return Response(serialized_data, status=status.HTTP_200_OK)

class UserActivityEndpoint(BaseAPIView, BasePaginator):
    def get(self, request):
        queryset = IssueActivity.objects.filter(actor=request.user).select_related(
            "actor", "workspace", "issue", "project"
        )

        return self.paginate(
            order_by=sanitize_order_by(
                request.GET.get("order_by", "-created_at"),
                ACTIVITY_ORDER_BY_ALLOWLIST,
                "-created_at",
            ),
            request=request,
            queryset=queryset,
            on_results=lambda issue_activities: IssueActivitySerializer(issue_activities, many=True).data,
        )


class ProfileEndpoint(BaseAPIView):
    @method_decorator(cache_control(private=True, max_age=12))
    @method_decorator(vary_on_cookie)
    def get(self, request):
        profile = Profile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        profile = Profile.objects.get(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
