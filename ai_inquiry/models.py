"""
AI问询模型
"""
from django.db import models
from user.models import User


class Inquiry(models.Model):
    """AI问询记录模型"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inquiries')
    question = models.TextField('问题内容')
    answer = models.TextField('回答内容', blank=True)
    suggestions = models.JSONField('建议列表', default=list, blank=True)  # 存储建议数组
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'ai_inquiry'
        verbose_name = 'AI问询'
        verbose_name_plural = 'AI问询'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.name} - {self.question[:20]}'

