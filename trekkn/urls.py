from django.urls import path
from .views import (
    GoogleAuthView,
    ServerHealth,
    SignOutView,
    TrekknUserListCreateView,
    TrekknUserDetailView,
    DailyActivityListCreateView,
    DailyActivityDetailView,
    MissionListCreateView,
    MissionDetailView,
    UserMissionListCreateView,
    UserMissionDetailView,
    UserEventLogListCreateView,
    UserEventLogDetailView,
)

from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("auth/sign-in/", GoogleAuthView.as_view()),
    path("auth/sign-out/", SignOutView.as_view()),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("users/", TrekknUserListCreateView.as_view(), name="user-list-create"),
    path(
        "users/me/",
        TrekknUserDetailView.as_view(
            # lookup_field="id",
        ),
        name="user-detail",
    ),
    path(
        "activities/",
        DailyActivityListCreateView.as_view(),
        name="activity-list-create",
    ),
    path(
        "activities/<str:id>/",
        DailyActivityDetailView.as_view(
            lookup_field="id",
        ),
        name="activity-detail",
    ),
    path("missions/", MissionListCreateView.as_view(), name="mission-list-create"),
    path(
        "missions/<str:id>/",
        MissionDetailView.as_view(
            lookup_field="id",
        ),
        name="mission-detail",
    ),
    path(
        "user-missions/",
        UserMissionListCreateView.as_view(),
        name="usermission-list-create",
    ),
    path(
        "user-missions/<str:id>/",
        UserMissionDetailView.as_view(
            lookup_field="id",
        ),
        name="usermission-detail",
    ),
    path(
        "event-logs/", UserEventLogListCreateView.as_view(), name="eventlog-list-create"
    ),
    path(
        "event-logs/<str:id>/",
        UserEventLogDetailView.as_view(
            lookup_field="id",
        ),
        name="eventlog-detail",
    ),
    path("health/", ServerHealth.as_view(), name="health"),
]
