"""
医生模型
"""
from django.db import models
from user.models import User
from hospitals.models import Hospital


class Doctor(models.Model):
    """医生模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    name = models.CharField('姓名', max_length=50)
    title = models.CharField('职称', max_length=50)
    specialty = models.CharField('专科', max_length=50)
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctors', null=True, blank=True)
    avatar = models.URLField('头像', blank=True, null=True)
    score = models.FloatField('评分', default=0.0)
    reviews = models.IntegerField('评价数量', default=0)
    introduction = models.TextField('简介', blank=True)
    education = models.CharField('学历', max_length=100, blank=True)
    experience = models.CharField('经验', max_length=200, blank=True)
    is_online = models.BooleanField('是否在线', default=False)
    is_admin = models.BooleanField('是否为管理员', default=False)
    # 审核相关字段
    AUDIT_STATUS_CHOICES = [
        ('pending', '待审核'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]
    audit_status = models.CharField('审核状态', max_length=10, choices=AUDIT_STATUS_CHOICES, default='pending')
    applied_at = models.DateTimeField('申请时间', auto_now_add=True)
    audited_at = models.DateTimeField('审核时间', blank=True, null=True)
    rejected_reason = models.CharField('拒绝原因', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'doctor'
        verbose_name = '医生'
        verbose_name_plural = '医生'
        ordering = ['-score', '-reviews']
    
    def __str__(self):
        return f'{self.name} - {self.hospital.name}'


class Schedule(models.Model):
    """医生排班（按时间段）"""
    STATUS_CHOICES = [
        ('active', '有效'),
        ('cancelled', '已取消'),
    ]

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='schedules')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    date = models.DateField('排班日期')
    start_time = models.CharField('开始时间', max_length=5, help_text='格式：HH:mm，如 08:00', default='08:00')
    end_time = models.CharField('结束时间', max_length=5, help_text='格式：HH:mm，如 08:30', default='08:30')
    max_appointments = models.IntegerField('该时间段最多预约数', default=3)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='active')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_schedules')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'doctor_schedule'
        verbose_name = '排班'
        verbose_name_plural = '排班'
        constraints = [
            models.UniqueConstraint(fields=['doctor', 'date', 'start_time'], name='unique_doctor_schedule_per_day'),
        ]
        ordering = ['-date', 'start_time', '-created_at']

    def __str__(self):
        return f'{self.date} {self.start_time}-{self.end_time} {self.doctor.name} ({self.hospital.name}) {self.status}'

