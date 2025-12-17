"""
AI问询模型
"""
from django.db import models
from django.conf import settings
from user.models import User


class Inquiry(models.Model):
    """AI问询记录模型（旧表，保留兼容）"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inquiries')
    question = models.TextField('问题内容')
    answer = models.TextField('回答内容', blank=True)
    suggestions = models.JSONField('建议列表', default=list, blank=True)  # 存储建议数组
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'ai_inquiry'
        verbose_name = 'AI问询（旧）'
        verbose_name_plural = 'AI问询（旧）'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.user.name} - {self.question[:20]}'


class AIChatMessage(models.Model):
    """AI对话消息模型"""
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_chat_messages',
        verbose_name='用户'
    )
    role = models.CharField(
        max_length=16,
        choices=ROLE_CHOICES,
        verbose_name='角色'
    )
    content = models.TextField(verbose_name='内容')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间'
    )
    
    class Meta:
        db_table = 'ai_chat_message'
        ordering = ['created_at']
        verbose_name = 'AI 对话消息'
        verbose_name_plural = 'AI 对话消息'
    
    def __str__(self):
        return f'{self.user_id}-{self.role}: {self.content[:20]}'


class DentalKnowledgeArticle(models.Model):
    """牙科知识文章模型"""
    title = models.CharField(max_length=255, verbose_name='标题')
    question_pattern = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='用于简单检索的关键词或典型问句',
        verbose_name='典型问题模式'
    )
    content = models.TextField(verbose_name='内容')
    tags = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text='逗号分隔，如：龋齿,根管治疗',
        verbose_name='标签（逗号分隔，如：龋齿,根管治疗）'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'dental_knowledge_article'
        verbose_name = '牙科知识文章'
        verbose_name_plural = '牙科知识文章'
    
    def __str__(self):
        return self.title


class AIRecommendationLog(models.Model):
    """AI推荐记录模型"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_recommendation_logs',
        verbose_name='用户'
    )
    raw_question = models.TextField(verbose_name='原始问题')
    structured_intent = models.JSONField(
        verbose_name='解析后意图',
        help_text='例如 {"disease_category": "龋齿", "recommended_department": "口腔内科"}',
        blank=True,
        null=True
    )
    recommended_doctors = models.JSONField(
        verbose_name='推荐医生列表',
        help_text='存 doctor_id 列表及关键字段，方便后续分析',
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'ai_recommendation_log'
        verbose_name = 'AI 推荐记录'
        verbose_name_plural = 'AI 推荐记录'
    
    def __str__(self):
        return f'{self.user_id} - {self.raw_question[:30]}'

