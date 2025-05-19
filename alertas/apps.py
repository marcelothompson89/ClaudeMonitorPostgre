from django.apps import AppConfig


class AlertasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alertas'

    def ready(self):
        import alertas.signals  # Importar las señales cuando la app esté lista