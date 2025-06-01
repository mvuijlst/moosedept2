from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'news'
    
    def ready(self):
        # Import the wagtail_hooks module to ensure it's loaded
        import news.wagtail_hooks
