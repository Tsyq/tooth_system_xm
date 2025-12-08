"""
在线问诊模型
"""
from django.db import models
from user.models import User
from doctors.models import Doctor


class Consultation(models.Model):
    """问诊会话模型"""
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('closed', '已关闭'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultations')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='consultations')
    status = models.CharField('会话状态', max_length=10, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'consultation'
        verbose_name = '问诊会话'
        verbose_name_plural = '问诊会话'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.name} - {self.doctor.name} - {self.status}'


class Message(models.Model):
    """消息模型"""
    SENDER_CHOICES = [
        ('user', '用户'),
        ('doctor', '医生'),
    ]
    
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField('发送者', max_length=10, choices=SENDER_CHOICES)
    text = models.TextField('消息内容')
    time = models.DateTimeField('发送时间', auto_now_add=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'consultation_message'
        verbose_name = '消息'
        verbose_name_plural = '消息'
        ordering = ['-time']
    
    def __str__(self):
        return f'{self.sender} - {self.text[:20]}'

