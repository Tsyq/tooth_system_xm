from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

user_creation_logger = logging.getLogger('user_creation_logger')
User = get_user_model()


@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """仅记录用户创建，医生档案由注册流程显式创建"""
    try:
        if created:
            user_creation_logger.info(f"User Created with name '{instance.name}'.")
    except Exception as e:
        logging.getLogger(__name__).error(f"记录用户创建失败: {e}")
