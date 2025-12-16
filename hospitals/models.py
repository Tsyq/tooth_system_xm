"""
医院模型
"""
from django.db import models


class Hospital(models.Model):
    """医院模型"""
    name = models.CharField('医院名称', max_length=100)
    address = models.CharField('地址', max_length=200)
    phone = models.CharField('联系电话', max_length=20)
    latitude = models.FloatField('纬度', null=True, blank=True)
    longitude = models.FloatField('经度', null=True, blank=True)
    image = models.URLField('图片URL', blank=True, null=True)
    rating = models.FloatField('评分', default=0.0)
    review_count = models.IntegerField('评价数量', default=0)
    description = models.TextField('简介', blank=True)
    business_hours = models.CharField('营业时间', max_length=100, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'hospital'
        verbose_name = '医院'
        verbose_name_plural = '医院'
        ordering = ['-rating', '-review_count']
    
    def __str__(self):
        return self.name

