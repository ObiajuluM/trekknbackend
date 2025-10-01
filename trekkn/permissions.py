# for permissions to decorate views

from rest_framework.permissions import BasePermission


class APIPermission(BasePermission):
    allow_read_only = False

    @staticmethod
    def is_safe(request):
        return request.method in ["GET", "HEAD", "OPTIONS"]


class IsOwner(APIPermission):
    def has_object_permission(self, request, view, obj):
        return request.user and obj.owner == request.user
