from trekkn.models import DailyActivity, TrekknUser, UserEventLog


def log_steps_and_reward_user(user: TrekknUser, steps: int):
    try:
        # log daily activity
        DailyActivity.objects.create(
            user=user,
            step_count=steps,
            # conversion_rate=0.5,
            source="steps",
        )
        # log event
        UserEventLog.objects.create(
            user=user,
            event_type="steps",
            description=f"Logged {steps} steps and rewarded {'do rewards here'}",
        )
        return True
    except Exception as e:
        raise e


def get_referred(referrer: TrekknUser, referred: TrekknUser):
    try:
        #  get referrer and show him love
        DailyActivity.objects.create(
            user=referrer,
            source="referral",
        )
        UserEventLog.objects.create(
            user=referrer,
            event_type="referral",
            description=f"Reffered: {referred.username}",
        )
        #
        #  get referred and show him love
        DailyActivity.objects.create(
            user=referred,
            source="referral",
        )
        UserEventLog.objects.create(
            
            user=referred,
            event_type="referral",
            description=f"I was reffered by {referrer.username}",
        )

        return True
    except Exception as e:
        raise e
