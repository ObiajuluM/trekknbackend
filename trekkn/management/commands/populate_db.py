import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import uuid
from trekkn.models import TrekknUser, DailyActivity, Mission, UserMission, UserEventLog


class Command(BaseCommand):
    help = "Seed the database with fake data using Faker"

    def handle(self, *args, **kwargs):
        fake = Faker()

        # --- Create Users ---
        self.stdout.write(self.style.SUCCESS("Creating users..."))
        users = []
        for _ in range(10):  # create 10 users
            user = TrekknUser.objects.create(
                email=fake.unique.email(),
                username=fake.user_name(),
                displayname=fake.name(),
                device_id=fake.unique.uuid4(),
                goal=random.choice([1000, 2000, 5000, 10000]),
                balance=random.randint(0, 5000),
                aura=random.randint(50, 500),
                level=random.randint(1, 5),
                streak=random.randint(0, 10),
            )
            users.append(user)

        # --- Create Missions ---
        self.stdout.write(self.style.SUCCESS("Creating missions..."))
        missions = []
        for i in range(5):
            mission = Mission.objects.create(
                # id=uuid.uuid4(),
                name=f"Mission {i+1} {fake.name()}",
                description=fake.sentence(),
                requirement_steps=random.choice([1000, 2000, 5000, 10000]),
                aura_reward=random.randint(10, 100),
            )
            missions.append(mission)

        # --- Assign missions to users ---
        self.stdout.write(self.style.SUCCESS("Assigning missions..."))
        for user in users:
            for mission in random.sample(missions, k=3):  # give each user 3 missions
                UserMission.objects.get_or_create(user=user, mission=mission)

        # --- Create Activities ---
        self.stdout.write(self.style.SUCCESS("Creating activities..."))
        for user in users:
            for _ in range(random.randint(5, 15)):  # random activities per user
                DailyActivity.objects.create(
                    user=user,
                    step_count=random.randint(100, 10000),
                    timestamp=fake.date_time_this_year(
                        tzinfo=timezone.get_current_timezone()
                    ),
                    conversion_rate=0.05,
                    source=random.choice(["steps", "referral", "bonus"]),
                )

        # --- Create Event Logs ---
        self.stdout.write(self.style.SUCCESS("Creating event logs..."))
        for user in users:
            for _ in range(random.randint(3, 7)):
                UserEventLog.objects.create(
                    # id=uuid.uuid4(),
                    user=user,
                    event_type=random.choice(["steps", "referral", "bonus"]),
                    description=fake.text(),
                    timestamp=fake.date_time_this_year(
                        tzinfo=timezone.get_current_timezone()
                    ),
                    metadata={"ip": fake.ipv4(), "device": fake.word()},
                )

        self.stdout.write(
            self.style.SUCCESS("Database successfully seeded with fake data!")
        )
