# Create your views here.
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from rest_framework import permissions

# from django.contrib.auth.models import User
from trekkn.models import TrekknUser, DailyActivity, Mission, UserMission, UserEventLog
from trekkn.permissions import IsOwner
from trekkn.serializers import (
    TrekknUserSerializer,
    DailyActivitySerializer,
    MissionSerializer,
    UserMissionSerializer,
    UserEventLogSerializer,
)
from trekknbackend import settings


# eward Flow

# User A copies their invite_url (https://trekkn.page.link/?invite_code=abc123).

# User B clicks the link → Flutter app opens → extract invite_code.

# Flutter calls your API /signup?invite_code=abc123.


# Django looks up inviter and applies rewards.
class GoogleAuthView(APIView):
    def post(self, request):
        try:
            token = request.data.get("id_token")
            device_id = request.data.get("device_id")
            invited_by = request.data.get("invited_by")

            if not token:
                return Response(
                    {"error": "ID token not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not device_id:
                return Response(
                    {"error": "Device ID not provided"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            )

            email = idinfo["email"]
            name = idinfo.get("name", "")

            # Check if user already exists
            try:
                user = TrekknUser.objects.get(email=email)
                # --- check device binding ---
                if user.device_id is None:
                    # first time login from this user → bind device
                    user.device_id = device_id
                    user.save()
                elif user.device_id != device_id:
                    return Response(
                        {"error": "This account is already bound to another device."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

            except TrekknUser.DoesNotExist:
                # New user → create and bind device
                user = TrekknUser.objects.create_user(
                    email=email,
                    name=name if name else "",
                    device_id=device_id,
                )

            # TODO: handle invite code reward if invited_by is present

            # Issue JWT tokens
            refresh = RefreshToken.for_user(user)
            return Response(
                {
                    "refresh": str(refresh),
                    "access": str(refresh.access_token),
                }
            )

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SignOutView(APIView):
    def post(self, request):
        # TODO: get the user and retrieve their tokens
        refresh_token = request.data.get("refresh")
        access_token = request.data.get("access")

        if not refresh_token or not access_token:
            return Response(
                {"error": "Both refresh and access tokens are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Blacklist refresh token
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()

            # Blacklist access token
            access = AccessToken(access_token)
            access.blacklist()

            return Response(
                {"success": "Successfully signed out"},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except TokenError:
            return Response(
                {"error": "Invalid or expired token"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TrekknUserListCreateView(generics.ListCreateAPIView):
    queryset = TrekknUser.objects.all()
    serializer_class = TrekknUserSerializer
    # show only methods in here
    http_method_names = ["get"]
    # TODO: restrict to admin only


class TrekknUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrekknUser.objects.all()
    serializer_class = TrekknUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["patch", "get"]
    # TODO: restrict to owner or admin only

    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                permissions.IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request, *args, **kwargs):
        return Response(
            data=TrekknUserSerializer(self.request.user, many=False).data,
            status=status.HTTP_200_OK,
        )

        # return super().get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        # if user is authenticated
        return super().partial_update(request, *args, **kwargs)


class DailyActivityListCreateView(generics.ListCreateAPIView):
    queryset = DailyActivity.objects.all()
    serializer_class = DailyActivitySerializer
    # show only methods in here
    http_method_names = ["get"]
    # TODO: admin only
    # TODO: restrict to owner or admin only


class DailyActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DailyActivity.objects.all()
    serializer_class = DailyActivitySerializer
    # show only methods in here
    http_method_names = ["get"]


class MissionListCreateView(generics.ListCreateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer


class MissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer


class UserMissionListCreateView(generics.ListCreateAPIView):
    queryset = UserMission.objects.all()
    serializer_class = UserMissionSerializer


class UserMissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserMission.objects.all()
    serializer_class = UserMissionSerializer


class UserEventLogListCreateView(generics.ListCreateAPIView):
    queryset = UserEventLog.objects.all()
    serializer_class = UserEventLogSerializer


class UserEventLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserEventLog.objects.all()
    serializer_class = UserEventLogSerializer


# class GoogleAuthView(APIView):
#     def post(self, request):
#         try:
#             token = request.data.get("id_token")
#             device_id = request.data.get("device_id")
#             # todo: check it the invite code is valid, then reward the inviter and set the code
#             invited_by = request.data.get("invited_by")
#             if not token:
#                 return Response(
#                     {"error": "ID token not provided"},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )
#             if not device_id:
#                 return Response(
#                     {"error": "Device ID not provided"},
#                     status=status.HTTP_400_BAD_REQUEST,
#                 )

#             # Verify token with Google
#             idinfo = id_token.verify_oauth2_token(
#                 token,
#                 requests.Request(),
#                 settings.GOOGLE_CLIENT_ID,
#             )

#             email = idinfo["email"]
#             name = idinfo.get("name", "")

#             # Get or create user
#             user, _ = TrekknUser.objects.get_or_create(
#                 email=email,
#                 defaults={
#                     "email": email,
#                     "name": name if name else "",
#                     "device_id": device_id,
#                 },
#             )

#             # Issue JWT token
#             refresh = RefreshToken.for_user(user)
#             return Response(
#                 {
#                     "refresh": str(refresh),
#                     "access": str(refresh.access_token),
#                 }
#             )
#         except Exception as e:
#             print(e)
#             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
