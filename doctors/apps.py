from django.apps import AppConfig


class DoctorsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'doctors'
    verbose_name = '医生管理'
    
    def ready(self):
        """应用启动时注册signals"""
        import doctors.signals

