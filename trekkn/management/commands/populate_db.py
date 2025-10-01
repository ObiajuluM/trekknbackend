from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
import random

from trekkn.models import DailyActivity, Mission, TrekknUser, UserMission


fake = Faker()


class Command(BaseCommand):
    help = "Seed the database with sample users, activities, missions"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.NOTICE("🌱 Seeding database..."))

        # --- Create Missions if none exist ---
        if Mission.objects.count() == 0:
            missions = [
                {
                    "name": "Walk 1000 steps",
                    "description": "Complete 1000 steps in a day",
                    "requirement_steps": 1000,
                    "aura_reward": 10,
                },
                {
                    "name": "Walk 5000 steps",
                    "description": "Complete 5000 steps in a day",
                    "requirement_steps": 5000,
                    "aura_reward": 50,
                },
                {
                    "name": "Referral bonus",
                    "description": "Invite a friend",
                    "requirement_steps": 0,
                    "aura_reward": 50,
                },
            ]
            for m in missions:
                Mission.objects.create(**m)
            self.stdout.write(self.style.SUCCESS("✅ Missions created"))

        # --- Create Users ---
        for _ in range(5):  # make 5 users
            email = fake.unique.email()
            user = TrekknUser.objects.create_user(
                email=email,
                username=fake.user_name(),
                name=fake.name(),
                password="password123",
                goal=random.choice([1000, 5000, 10000]),
                aura=random.randint(50, 200),
                level=random.randint(1, 3),
            )

            # Assign all missions
            for mission in Mission.objects.all():
                UserMission.objects.get_or_create(user=user, mission=mission)

            self.stdout.write(self.style.SUCCESS(f"👤 Created user: {user.email}"))

            # --- Add Daily Activities ---
            for _ in range(random.randint(3, 7)):  # 3–7 activities per user
                steps = random.randint(500, 8000)
                activity = DailyActivity.objects.create(
                    user=user,
                    step_count=steps,
                    conversion_rate=0.5,
                    source="steps",
                )
                self.stdout.write(
                    self.style.NOTICE(
                        f"   ➡ Added activity: {steps} steps → {activity.aura_gained} aura"
                    )
                )

        self.stdout.write(self.style.SUCCESS("🌟 Database seeding complete!"))
