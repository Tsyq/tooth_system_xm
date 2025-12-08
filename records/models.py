"""
病历模型
"""
from django.db import models
from user.models import User
from doctors.models import Doctor
from hospitals.models import Hospital
from appointments.models import Appointment


class Record(models.Model):
    """病历模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='records')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='records')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='records')
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='record')
    date = models.DateField('就诊日期')
    diagnosis = models.TextField('诊断')
    content = models.TextField('病历内容')
    treatment = models.TextField('治疗方案', blank=True, null=True)
    medications = models.JSONField('药物列表', default=list, blank=True)  # 存储药物数组
    result_image = models.URLField('结果图片URL', blank=True, null=True)
    rated = models.BooleanField('是否已评价', default=False)
    rating = models.IntegerField('评分', null=True, blank=True)  # 1-5分
    comment = models.TextField('评价内容', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'record'
        verbose_name = '病历'
        verbose_name_plural = '病历'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.name} - {self.diagnosis[:20]}'

