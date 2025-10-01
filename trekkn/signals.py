# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver

# from django.conf import settings

from .models import TrekknUser, UserMission, Mission


@receiver(post_save, sender=TrekknUser)
def create_user_missions(sender, instance, created, **kwargs):
    """
    Auto-create UserMission entries for every Mission when a new user is created.
    """
    if created:  # only when the user is first created
        missions = Mission.objects.all()
        for mission in missions:
            UserMission.objects.get_or_create(user=instance, mission=mission)


@receiver(post_save, sender=Mission)
def assign_mission_to_existing_users(sender, instance, created, **kwargs):
    """
    When a new mission is created, assign it to all existing users.
    """
    if created:
        # from trekkn.models import TrekknUser  # avoid circular import

        users = TrekknUser.objects.all()
        for user in users:
            UserMission.objects.get_or_create(user=user, mission=instance)
