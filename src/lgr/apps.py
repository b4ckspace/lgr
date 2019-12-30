from django.apps import AppConfig


class LgrConfig(AppConfig):
    """LgrConfig"""
    name = 'lgr'

    def ready(self):
        """Called when the application launches."""
        from lgr import signals
