# Create your views here.
from datetime import timedelta
from django.db.models import Sum
from django.db import models
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework import permissions
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers

# from django.contrib.auth.models import User
from trekkn.actions import get_referred, log_steps_and_reward_user
from trekkn.models import TrekknUser, DailyActivity, Mission, UserMission, UserEventLog
from trekkn.permissions import IsOwner
from trekkn.serializers import (
    LeaderboardUserSerializer,
    TrekknUserSerializer,
    DailyActivitySerializer,
    MissionSerializer,
    UserMissionSerializer,
    UserEventLogSerializer,
)

# from trekknbackend import settings
from django.conf import settings


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
            invite_code = request.data.get("invite_code")

            #    get inviter from invite code
            # --- Handle inviter via invite_code ---
            inviter = None
            if invite_code:
                inviter = TrekknUser.objects.filter(invite_code=invite_code).first()

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

            # 🚨 Check if device_id is already bound to another user
            existing_user_with_device = TrekknUser.objects.filter(
                device_id=device_id
            ).first()
            if existing_user_with_device and existing_user_with_device.email != email:
                return Response(
                    {"error": "This device is already linked to another account."},
                    status=status.HTTP_403_FORBIDDEN,
                )

            # Check if user already exists
            try:
                user = TrekknUser.objects.get(email=email)
                # --- check device binding ---
                if user.device_id is None:
                    # first time login from this user → bind device
                    user.device_id = device_id
                    # user.save()
                    # Reward flow: if user not invited before and valid inviter exists
                elif user.device_id != device_id:
                    return Response(
                        {"error": "This account is already bound to another device."},
                        status=status.HTTP_403_FORBIDDEN,
                    )

                if user.invited_by is None and inviter:
                    user.invited_by = inviter.invite_code
                    print("setting invited by and rewarding")
                    get_referred(inviter, user)

                user.save()
            except TrekknUser.DoesNotExist:
                # New user → create and bind device
                user = TrekknUser.objects.create_user(
                    email=email,
                    username=name if name else "",
                    device_id=device_id,
                )

                # Reward flow: as a new user, if valid inviter exists
                if inviter:
                    user.invited_by = inviter.invite_code
                    get_referred(inviter, user)
                    user.save()

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

        refresh_token = request.data.get("refresh")
        access_token = request.data.get("access")

        if not refresh_token:
            return Response(
                {"error": "Refresh token required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Blacklist refresh token
            refresh = RefreshToken(refresh_token)
            refresh.blacklist()

            # Blacklist access token
            access = AccessToken(access_token)
            # access.blacklist()

            return Response(
                {"success": "Successfully signed out"},
                status=status.HTTP_205_RESET_CONTENT,
            )

        except Exception as e:
            print(e)
            return Response(
                {"error": f"{e}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class TrekknUserListCreateView(generics.ListCreateAPIView):
    queryset = TrekknUser.objects.all()
    serializer_class = TrekknUserSerializer
    # permission_classes = [permissions.IsAuthenticated]
    # show only methods in here
    http_method_names = ["get"]

    def get_serializer_class(self):
        # If 'leaderboard' is in the query params, use the specific serializer
        if self.request.query_params.get("leaderboard"):
            return LeaderboardUserSerializer
        # Otherwise, use the default
        return super().get_serializer_class()

    def get_permissions(self):
        # if the server is not in DEBUG mode, apply the permission
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                permissions.IsAuthenticated,
            ]
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        level = self.request.query_params.get("level")
        # "day", "week", "month"
        leaderboard = self.request.query_params.get("leaderboard")

        #  handle level
        if level:
            # 1. Get all users ordered by level (descending = higher level first)
            users = TrekknUser.objects.all().order_by("-level")
            serializer = self.get_serializer(users, many=True)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK,
            )

        # Handle step leaderboards
        if leaderboard:
            now = timezone.now()
            if leaderboard == "day":
                start_date = now - timedelta(days=1)
            elif leaderboard == "week":
                start_date = now - timedelta(weeks=1)
            elif leaderboard == "month":
                start_date = now - timedelta(days=30)
            elif leaderboard == "year":
                start_date = now - timedelta(weeks=52)
            else:
                return Response(
                    {"error": "Invalid leaderboard type. Use day, week, or month."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Aggregate total steps in range
            users = (
                TrekknUser.objects.annotate(
                    total_steps=Sum(
                        "daily_activities__step_count",
                        filter=models.Q(daily_activities__timestamp__gte=start_date)
                        & models.Q(daily_activities__source="steps"),
                    )
                )
                .order_by("-total_steps")
                .exclude(total_steps=None)[:100]  # top 100 only
            )

            serializer = self.get_serializer(users, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        return super().list(request, *args, **kwargs)


class TrekknUserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TrekknUser.objects.all()
    serializer_class = TrekknUserSerializer
    # permission_classes = [
    #     IsOwner,
    #     permissions.IsAuthenticated,
    # ]
    http_method_names = ["patch", "get"]

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                permissions.IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request, *args, **kwargs):
        try:
            return Response(
                data=TrekknUserSerializer(self.request.user, many=False).data,
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # return super().get(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        # if user is authenticated
        # partial=True means we only update the fields
        # provided in the request
        try:
            serializer = TrekknUserSerializer(
                self.request.user, data=self.request.data, partial=True
            )
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        # return super().patch(request, *args, **kwargs)


class DailyActivityListCreateView(generics.ListCreateAPIView):
    queryset = DailyActivity.objects.all()
    serializer_class = DailyActivitySerializer
    # show only methods in here

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "POST":
            self.permission_classes = [
                IsOwner,
                permissions.IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request, *args, **kwargs):
        try:
            # Get all events for the authenticated user
            if self.request.user.is_authenticated:
                events = DailyActivity.objects.filter(user=self.request.user).order_by(
                    "-timestamp"
                )[:50]
                serializer = self.get_serializer(events, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            return super().get(request, *args, **kwargs)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def post(self, request, *args, **kwargs):
        try:
            now = timezone.now()
            cutoff = now - timedelta(hours=23)
            recent_activity = DailyActivity.objects.filter(
                user=self.request.user, timestamp__gte=cutoff
            ).exists()
            if recent_activity:
                return Response(
                    {"error": "You can only log activity once every 23 hours."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
            # if conditions are met, log steps and reward user
            activity = log_steps_and_reward_user(
                user=self.request.user,
                steps=self.request.data.get("steps", 0),
            )
            serializer = self.get_serializer(activity)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DailyActivityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = DailyActivity.objects.all()
    serializer_class = DailyActivitySerializer
    # show only methods in here
    http_method_names = [""]


class MissionListCreateView(generics.ListCreateAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    http_method_names = [""]


class MissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Mission.objects.all()
    serializer_class = MissionSerializer
    http_method_names = [""]


# @method_decorator(cache_page(20), name="get")
# @method_decorator(vary_on_headers("Authorization"), name="get")
class UserMissionListCreateView(generics.ListCreateAPIView):
    queryset = UserMission.objects.all()
    serializer_class = UserMissionSerializer
    http_method_names = ["get"]

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                permissions.IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request, *args, **kwargs):
        # print("called")
        try:
            # Get all events for the authenticated user
            # if self.request.user.is_authenticated:
            events = UserMission.objects.filter(user=self.request.user)
            serializer = self.get_serializer(events, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        # return super().get(request, *args, **kwargs)
        except Exception as e:

            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserMissionDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserMission.objects.all()
    serializer_class = UserMissionSerializer
    http_method_names = [""]


class UserEventLogListCreateView(generics.ListCreateAPIView):
    queryset = UserEventLog.objects.all()
    serializer_class = UserEventLogSerializer

    http_method_names = ["get"]

    def get_permissions(self):
        if not settings.DEBUG:
            # if self.request.method == "GET":
            self.permission_classes = [
                IsOwner,
                permissions.IsAuthenticated,
            ]
        return super().get_permissions()

    def get(self, request, *args, **kwargs):
        # Get all events for the authenticated user

        # if self.request.user.is_authenticated:
        #     events = UserEventLog.objects.filter(user=self.request.user).order_by(
        #         "-timestamp"
        #     )
        #     serializer = self.get_serializer(events, many=True)
        #     return Response(serializer.data, status=status.HTTP_200_OK)
        return super().get(request, *args, **kwargs)


class UserEventLogDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserEventLog.objects.all()
    serializer_class = UserEventLogSerializer
    http_method_names = [""]


class ServerHealth(generics.RetrieveAPIView):

    permission_classes = []
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        # print(self.generate_evm_account())
        # print(self.generate_solana_account())
        try:
            return Response(
                data={"status": "ok"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Configurations for production
if not settings.DEBUG:
    TrekknUserListCreateView = method_decorator(cache_page(60), name="list")(
        TrekknUserListCreateView
    )
    TrekknUserListCreateView = method_decorator(
        vary_on_headers("Authorization"), name="list"
    )(TrekknUserListCreateView)

    #
    TrekknUserDetailView = method_decorator(cache_page(20), name="get")(
        TrekknUserDetailView
    )
    TrekknUserDetailView = method_decorator(
        vary_on_headers("Authorization"), name="get"
    )(TrekknUserDetailView)

    #
    DailyActivityListCreateView = method_decorator(cache_page(60), name="get")(
        DailyActivityListCreateView
    )
    DailyActivityListCreateView = method_decorator(
        vary_on_headers("Authorization"), name="get"
    )(DailyActivityListCreateView)

    #
    UserMissionListCreateView = method_decorator(cache_page(20), name="get")(
        UserMissionListCreateView
    )
    UserMissionListCreateView = method_decorator(
        vary_on_headers("Authorization"), name="get"
    )(UserMissionListCreateView)

    #
    UserEventLogListCreateView = method_decorator(cache_page(60), name="get")(
        UserEventLogListCreateView
    )
    UserEventLogListCreateView = method_decorator(
        vary_on_headers("Authorization"), name="get"
    )(UserEventLogListCreateView)

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
