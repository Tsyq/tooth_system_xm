from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decouple import config


class Command(BaseCommand):
    help = 'Create a single default admin if none exists (idempotent).'

    def handle(self, *args, **options):
        User = get_user_model()
        # Check if an admin exists
        if User.objects.filter(role='admin').exists():
            self.stdout.write(self.style.WARNING('Admin already exists. No action taken.'))
            return
        # 从 .env 读取，提供默认值以避免缺失
        phone = config('ADMIN_PHONE', default='19300000000')
        password = config('ADMIN_PASSWORD', default='admin@123')
        name = config('ADMIN_NAME', default='系统管理员')
        # Create as superuser (will have is_staff/is_superuser)
        user = User.objects.create_superuser(phone=phone, password=password, name=name)
        self.stdout.write(self.style.SUCCESS(f'Created admin: {user.phone}'))
