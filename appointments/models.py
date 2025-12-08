"""
预约模型
"""
from django.db import models
from user.models import User
from doctors.models import Doctor
from hospitals.models import Hospital


class Appointment(models.Model):
    """预约模型"""
    STATUS_CHOICES = [
        ('upcoming', '待就诊'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('checked-in', '已签到'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='appointments')
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='appointments')
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='appointments')
    appointment_date = models.DateField('预约日期')
    appointment_time = models.CharField('预约时间', max_length=5)  # HH:mm格式
    symptoms = models.TextField('症状描述', blank=True, null=True)
    patient_name = models.CharField('患者姓名', max_length=50)
    patient_phone = models.CharField('患者电话', max_length=11)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='upcoming')
    checkin_time = models.DateTimeField('签到时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'appointment'
        verbose_name = '预约'
        verbose_name_plural = '预约'
        ordering = ['-appointment_date', '-appointment_time']
        unique_together = [['doctor', 'appointment_date', 'appointment_time']]  # 防止时间冲突
    
    def __str__(self):
        return f'{self.user.name} - {self.doctor.name} - {self.appointment_date}'

