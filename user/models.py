from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)


class UserManager(BaseUserManager):
    """用户管理器"""
    def create_user(self, phone, password=None, **extra_fields):
        """创建普通用户"""
        if not phone:
            raise ValueError('手机号是必填项')
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone, password=None, **extra_fields):
        """创建超级管理员"""
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('status', 'active')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(phone, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """用户模型"""
    ROLE_CHOICES = [
        ('user', '普通用户'),
        ('doctor', '医生'),
        ('admin', '管理员'),
    ]
    STATUS_CHOICES = [
        ('active', '激活'),
        ('pending', '待审核'),
        ('inactive', '禁用'),
    ]
    
    phone = models.CharField('手机号', max_length=11, unique=True)
    name = models.CharField('姓名', max_length=50)
    role = models.CharField('角色', max_length=10, choices=ROLE_CHOICES, default='user')
    avatar = models.URLField('头像', blank=True, null=True)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()
    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name']
    
    class Meta:
        db_table = 'user'
        verbose_name = '用户'
        verbose_name_plural = '用户'
    
    def __str__(self):
        return f'{self.name}({self.phone})'
