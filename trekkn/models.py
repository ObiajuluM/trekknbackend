import uuid
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
import hashlib
from django.db import models

# pip install unique-namer
import namer


class TrekknUserManager(models.Manager):

    def create_user(self, email, password=None, username=None, **extra_fields):
        if not username:
            # Auto-generate username if not provided
            username = namer.generate(separator=" ", style="title")
            # Ensure uniqueness
            for _ in range(10):
                if not TrekknUser.objects.filter(username=username).exists():
                    break
                username = namer.generate(separator=" ", style="title")
            else:
                raise ValueError(
                    "Could not generate a unique username after 10 attempts"
                )
        user = self.model(email=email, username=username, **extra_fields)
        if password:
            user.set_password(password)
        user.save(using=self._db)
        return user


# Create your models here.
class TrekknUser(AbstractUser):
    id = models.UUIDField(
        # primary_key=True,
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    device_id = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, unique=True)
    username = models.CharField(max_length=50)
    goal = models.IntegerField(default=1000)  # daily step goal
    balance = models.IntegerField(default=0)  # points balance
    aura = models.IntegerField(default=100)  # aura points
    level = models.IntegerField(default=1)  # user level
    streak = models.IntegerField(default=0)  # current streak

    #
    # solana_key = models.CharField(default=uuid.uuid4,
    #     editable=False,)
    # evm_key = models.CharField(default=uuid.uuid4,
    #     editable=False,)

    # store unique code instead of full URL
    invite_code = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        # editable=False,
    )
    invited_by = models.CharField(
        # "self",
        # on_delete=models.SET_NULL,
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        # related_name="referrals",
    )

    BASE_AURA = 100
    LEVEL_MULTIPLIER = 20

    @property
    def invite_url(self):
        # TODO: may becmoe env variable
        return f"https://walkitapp.com/invite/{self.invite_code}"

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = TrekknUserManager()

    def aura_to_next_level(self):
        """Aura needed to reach the next level."""
        return self.BASE_AURA + (self.level * self.LEVEL_MULTIPLIER)

    def update_level(self):
        """Increase/decrease level depending on aura total."""
        required = self.aura_to_next_level()
        while self.aura >= required:
            self.level += 1
            required = self.aura_to_next_level()
        while (
            self.aura < (self.BASE_AURA + ((self.level - 1) * self.LEVEL_MULTIPLIER))
            and self.level > 1
        ):
            self.level -= 1

    def add_aura(self, amount: int):
        """Add aura and adjust level accordingly."""
        self.aura += amount
        self.update_level()
        # self.save()

    def __generate_username(self) -> str:
        """method to generate display name"""
        return namer.generate(
            separator=" ",
            style="title",
        )

    def __generate_invite_code(self) -> str:
        """Generate a unique invite code."""
        base_string = f"{self.email}-{timezone.now().timestamp()}"
        return hashlib.sha256(base_string.encode()).hexdigest()[:10]

    def save(self, **kwargs):
        if not self.invite_code:
            self.invite_code = self.__generate_invite_code()  # short random code
        if not self.username:  # only if username is empty
            for _ in range(10):  # try up to 10 times
                username = self.__generate_username()
                self.username = username
                try:
                    with transaction.atomic():  # ensure atomic save
                        return super().save(**kwargs)
                except IntegrityError:
                    # username was taken by another process, retry
                    continue
            raise ValueError("Could not generate a unique username after 10 attempts")
        # else:
        return super().save(**kwargs)

    # def save(self, **kwargs):
    #     if not self.username:  # generate display name if its empty
    #         try:
    #             # try to create a unique username
    #             while True:
    #                 username = self.__generate_username()
    #                 if not TrekknUser.objects.filter(username=username).exists():
    #                     break
    #         except Exception as e:
    #             print(e)
    #         self.username = username
    #     return super().save(**kwargs)  # Call the "real" save() method.

    def __str__(self):
        return self.username

    # def calculate_streak(self):
    #     """Calculate the current streak of consecutive days with 'steps' activity."""
    #     from django.utils import timezone
    #     from datetime import timedelta

    #     activities = self.daily_activities.filter(source="steps").order_by("-timestamp")
    #     if not activities.exists():
    #         return 0

    #     streak = 0
    #     today = timezone.localdate()
    #     expected_date = today

    #     for activity in activities:
    #         activity_date = activity.timestamp.date()
    #         if activity_date == expected_date:
    #             streak += 1
    #             expected_date -= timedelta(days=1)
    #         elif activity_date < expected_date:
    #             break  # streak broken
    #         # if activity_date > expected_date, skip (future or duplicate)
    #     return streak


# When creating the new user via invite, set:
# new_user.invited_by = inviter
# new_user.save()
# Now you can query:

# python
# Copy code
# user.referrals.all()  # all users invited by this user


# activity
class DailyActivity(models.Model):
    id = models.UUIDField(
        # primary_key=True,
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    user = models.ForeignKey(
        TrekknUser,
        on_delete=models.CASCADE,
        related_name="daily_activities",
    )
    step_count = models.IntegerField(default=0)  # steps logged in this activity
    timestamp = models.DateTimeField(default=timezone.now)  # when logged
    amount_rewarded = models.FloatField(default=0.0)  # reward points earned
    # TODO: will load from env
    conversion_rate = models.FloatField(default=0.05)  # steps → reward ratio
    aura_gained = models.IntegerField(default=0)  # aura earned from this activity
    source = models.CharField(max_length=50, default="steps")
    # e.g. "steps", "referral", "bonus"

    def calculate_rewards(self):
        """Calculate reward points from steps and conversion rate."""
        if self.source == "steps":
            return self.step_count * self.conversion_rate
        elif self.source == "referral":
            return 100  # flat reward for referral
        else:
            return 0

    def calculate_aura(self):
        """Basic rule: +10 Aura per 1000 rewardable steps."""
        if self.source == "steps":
            return (self.step_count // 1000) * 10
        elif self.source == "referral":
            return 50  # for example, flat reward
        # TODO: may modify
        return 0

    def save(self, *args, **kwargs):
        # calculate rewards if missing
        if self.amount_rewarded == 0 and self.conversion_rate > 0:
            self.amount_rewarded = self.calculate_rewards()

        # calculate aura if missing
        if self.aura_gained == 0:
            self.aura_gained = self.calculate_aura()

        super().save(*args, **kwargs)  # save activity first so values exist

        # --- update user ---
        self.user.balance += int(self.amount_rewarded)  # add reward to balance
        self.user.add_aura(self.aura_gained)  # handles aura + level update
        self.user.save()

        # after saving, check missions
        self.check_missions()
        return super().save(**kwargs)

    def check_missions(self):
        """Check and complete missions if requirements are met."""
        user_missions = self.user.missions.filter(is_completed=False)

        for user_mission in user_missions.select_related("mission"):
            mission = user_mission.mission
            total_steps = (
                self.user.daily_activities.aggregate(models.Sum("step_count"))[
                    "step_count__sum"
                ]
                or 0
            )
            if total_steps >= mission.requirement_steps:
                user_mission.complete()

    def __str__(self):
        return f"{self.user.email} - activity: {self.source} on {self.timestamp.date()}"


# Example flow
# # User takes 2500 steps
# activity = UserActivity.objects.create(
#     user=obi,
#     step_count=2500,
#     conversion_rate=0.5,
#     source="steps"
# )

# obi.add_aura(activity.aura_gained)

# print(obi.aura)   # e.g. 20 aura
# print(obi.level)  # maybe still Level 1, depending on formula

#
# obi = TrekknUser.objects.get(email="obi@example.com")

# activity = DailyActivity.objects.create(
#     user=obi,
#     step_count=2500,
#     conversion_rate=0.5,
#     source="steps"
# )

# print(obi.balance)  # balance increased
# print(obi.aura)     # aura increased
# print(obi.level)    # maybe still 1 or increased


# missions
class Mission(models.Model):
    id = models.UUIDField(
        # primary_key=True,
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    # badge image
    asset = models.ImageField(upload_to="missions/", null=True, blank=True)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    requirement_steps = models.PositiveIntegerField(default=0)  # e.g., 1000 steps
    aura_reward = models.PositiveIntegerField(default=0)  # Aura points gained

    def __str__(self):
        return self.name


class UserMission(models.Model):
    id = models.UUIDField(
        # primary_key=True,
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    user = models.ForeignKey(
        TrekknUser, on_delete=models.CASCADE, related_name="missions"
    )
    mission = models.ForeignKey(
        Mission, on_delete=models.CASCADE, related_name="user_missions"
    )
    achieved = models.DateTimeField(null=True, blank=True)  # when user completed
    is_completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "mission")

    def complete(self):
        if not self.is_completed:
            self.is_completed = True
            self.achieved = timezone.now()
            self.user.aura += self.mission.aura_reward  # add aura reward
            self.user.save()
            self.save()

    def __str__(self):
        return self.user.email + " - " + self.mission.name


# # create a mission
# m = Mission.objects.create(
#     name="Walk 1000 steps",
#     description="Complete 1000 steps in a day",
#     requirement_steps=1000,
#     aura_reward=10
# )

# # assign mission to user
# user_mission = UserMission.objects.create(user=some_user, mission=m)

# # mark as completed
# user_mission.complete()


class UserEventLog(models.Model):
    id = models.UUIDField(
        # primary_key=True,
        default=uuid.uuid4,
        editable=False,
        primary_key=True,
    )
    user = models.ForeignKey(
        TrekknUser, on_delete=models.CASCADE, related_name="event_logs"
    )
    event_type = models.CharField(max_length=20)
    description = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)

    # optional: store metadata
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.event_type} on {self.timestamp.date()}"


# UserEventLog.objects.create(
#     user=self.user,
#     event_type="mission",
#     description=f"Completed mission: {self.mission.name}",
#     metadata={"mission_id": self.mission.id, "aura_reward": self.mission.aura_reward}
# )


# logs = user.event_logs.order_by("-timestamp")
