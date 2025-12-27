"""
管理命令：更新用户画像
使用方法：python manage.py update_user_profiles
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from ai_inquiry.services.user_profile import update_user_profile

User = get_user_model()


class Command(BaseCommand):
    help = '更新所有用户的画像（用于个性化推荐）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='只更新指定用户的画像',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制更新（即使最近已更新过）',
        )

    def handle(self, *args, **options):
        if options['user_id']:
            # 只更新指定用户
            try:
                user = User.objects.get(id=options['user_id'])
                self.stdout.write(f'更新用户 {user.id} ({user.name}) 的画像...')
                update_user_profile(user, force_update=options['force'])
                self.stdout.write(self.style.SUCCESS(f'成功更新用户 {user.id} 的画像'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'用户 {options["user_id"]} 不存在'))
        else:
            # 更新所有用户
            users = User.objects.all()
            self.stdout.write(f'开始更新 {users.count()} 个用户的画像...')
            
            success_count = 0
            error_count = 0
            
            for user in users:
                try:
                    update_user_profile(user, force_update=options['force'])
                    success_count += 1
                    if success_count % 10 == 0:
                        self.stdout.write(f'已更新 {success_count} 个用户...')
                except Exception as e:
                    error_count += 1
                    self.stdout.write(self.style.WARNING(f'更新用户 {user.id} 失败: {e}'))
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'完成！成功: {success_count}, 失败: {error_count}'
                )
            )

