from django.contrib import admin
from .models import TrekknUser, DailyActivity, Mission, UserMission, UserEventLog

admin.site.register(TrekknUser)
admin.site.register(DailyActivity)
admin.site.register(Mission)
admin.site.register(UserMission)
admin.site.register(UserEventLog)

# Register your models here.
