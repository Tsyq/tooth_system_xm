"""
医生信号处理
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Doctor
from user.models import User


@receiver(post_save, sender=Doctor)
def sync_doctor_to_user(sender, instance, created, **kwargs):
    """
    当Doctor模型保存时，同步医生信息到对应的User模型
    """
    try:
        user = instance.user
        
        # 同步基本信息
        user.name = instance.name
        user.avatar = instance.avatar
        user.role = 'doctor'
        
        # 保存用户信息，但不触发signals
        user.save(update_fields=['name', 'avatar', 'role', 'updated_at'])
        
    except User.DoesNotExist:
        pass
    except Exception as e:
        print(f"同步医生信息到用户失败: {e}")


@receiver(post_delete, sender=Doctor)
def handle_doctor_delete(sender, instance, **kwargs):
    """
    当Doctor被删除时，重置User的role为普通用户
    """
    try:
        user = instance.user
        user.role = 'user'
        user.save(update_fields=['role', 'updated_at'])
    except User.DoesNotExist:
        pass
    except Exception as e:
        print(f"处理医生删除失败: {e}")
