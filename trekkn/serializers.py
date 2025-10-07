from rest_framework import serializers
from .models import TrekknUser, DailyActivity, Mission, UserMission, UserEventLog


class TrekknUserSerializer(serializers.ModelSerializer):
    # invited_by = serializers.SerializerMethodField()
    streak = serializers.IntegerField(read_only=True)

    # def get_invited_by(self, obj):
    #     if obj.invited_by:
    #         return obj.invited_by
    #     return

    def get_streak(self, obj: TrekknUser) -> int:
        """Calculate the current streak of consecutive days with 'steps' activity for the user."""
        from django.utils import timezone
        from datetime import timedelta

        activities = obj.daily_activities.filter(source="steps").order_by("-timestamp")
        if not activities.exists():
            return 0

        streak = 0
        today = timezone.localdate()
        expected_date = today

        for activity in activities:
            activity_date = activity.timestamp.date()
            if activity_date == expected_date:
                streak += 1
                expected_date -= timedelta(days=1)
            elif activity_date < expected_date:
                break  # streak broken
        return streak

    def update(self, instance, validated_data):
        # Prevent patching invited_by if already set
        if instance.invited_by is not None and "invited_by" in validated_data:
            validated_data.pop("invited_by")

        if instance.device_id is not None and "device_id" in validated_data:
            validated_data.pop("device_id")
        return super().update(instance, validated_data)

    class Meta:
        model = TrekknUser
        fields = [
            "id",
            "email",
            "displayname",
            "username",
            "goal",
            "balance",
            "aura",
            "level",
            "streak",
            # "invite_code",
            "date_joined",
            "invited_by",
            # "device_id",
            "sol_addr",
            "evm_addr",
            "invite_url",
        ]

        read_only_fields = [
            "id",
            "email",
            "name",
            "username",
            # "goal",
            "balance",
            "aura",
            "level",
            "streak",
            "date_joined",
            "sol_addr",
            "evm_addr",
            # "sol_key",
            # "evm_key"
            # "device_id",
            # "invite_code",
            # "invited_by",
            "invite_url",
        ]


# todo limit serializer writwbality to
class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = "__all__"


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = "__all__"


class UserMissionSerializer(serializers.ModelSerializer):
    # Full mission details (for GET)
    mission = MissionSerializer(read_only=True)

    # Only ID input (for POST/PUT)
    mission_id = serializers.PrimaryKeyRelatedField(
        queryset=Mission.objects.all(),
        source="mission",  # links to the Foreign Key
        write_only=True,
    )

    class Meta:
        model = UserMission
        fields = "__all__"


class UserEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEventLog
        fields = "__all__"


# --- NEW SERIALIZER FOR THE LEADERBOARD ---
class LeaderboardUserSerializer(serializers.ModelSerializer):
    # This tells the serializer: "Expect a read-only attribute named `total_steps`
    # on the objects you receive, and include it in the output."
    total_steps = serializers.ReadOnlyField()

    class Meta:
        model = TrekknUser
        # Define the fields you want in the leaderboard response
        fields = ["displayname", "username", "total_steps"]
