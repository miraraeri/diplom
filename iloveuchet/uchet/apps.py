from django.apps import AppConfig


class UchetConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'uchet'
    verbose_name = 'Учет'

    def ready(self):
        import uchet.signals  # noqa