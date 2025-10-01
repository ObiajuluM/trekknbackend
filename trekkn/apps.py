from django.apps import AppConfig


class TrekknConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trekkn'

    def ready(self):
        import trekkn.signals  # ensures signals.py runs
