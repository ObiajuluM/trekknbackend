from rest_framework import serializers
from .models import TrekknUser, DailyActivity, Mission, UserMission, UserEventLog


class TrekknUserSerializer(serializers.ModelSerializer):
    # invited_by = serializers.SerializerMethodField()

    # def get_invited_by(self, obj):
    #     if obj.invited_by:
    #         return obj.invited_by
    #     return None

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
            "name",
            "username",
            "goal",
            "balance",
            "aura",
            "level",
            "streak",
            # "invite_code",
            "invited_by",
            # "device_id",
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
            # "device_id",
            # "invite_code",
            # "invited_by",
            "invite_url",
        ]


class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = "__all__"


class MissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Mission
        fields = "__all__"


class UserMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserMission
        fields = "__all__"


class UserEventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserEventLog
        fields = "__all__"
