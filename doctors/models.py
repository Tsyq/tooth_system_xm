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
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='doctors')
    avatar = models.URLField('头像', blank=True, null=True)
    score = models.FloatField('评分', default=0.0)
    reviews = models.IntegerField('评价数量', default=0)
    introduction = models.TextField('简介', blank=True)
    education = models.CharField('学历', max_length=100, blank=True)
    experience = models.CharField('经验', max_length=200, blank=True)
    is_online = models.BooleanField('是否在线', default=False)
    is_super_doctor = models.BooleanField('是否为超级医生', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'doctors_doctor'
        verbose_name = '医生'
        verbose_name_plural = '医生'
        ordering = ['-score', '-reviews']
    
    def __str__(self):
        return f'{self.name} - {self.hospital.name}'

