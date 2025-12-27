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
    # 向量字段：存储文本的向量表示（JSON格式，存储为列表）
    embedding = models.JSONField(
        verbose_name='文本向量',
        help_text='存储文本的向量表示，用于语义检索',
        blank=True,
        null=True
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


class UserBehavior(models.Model):
    """用户行为记录模型（用于智能推荐）"""
    ACTION_CHOICES = [
        ('search', '搜索'),
        ('click_doctor', '点击医生'),
        ('view_doctor_detail', '查看医生详情'),
        ('make_appointment', '预约医生'),
        ('cancel_appointment', '取消预约'),
        ('rate_doctor', '评价医生'),
        ('click_recommendation', '点击推荐医生'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='behaviors',
        verbose_name='用户'
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        verbose_name='行为类型'
    )
    doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.CASCADE,
        related_name='user_behaviors',
        null=True,
        blank=True,
        verbose_name='相关医生'
    )
    # 上下文信息：记录行为发生时的上下文
    context = models.JSONField(
        verbose_name='上下文信息',
        help_text='记录行为发生时的上下文，如搜索关键词、推荐来源等',
        default=dict,
        blank=True
    )
    # 行为评分：用于推荐算法（如评价的评分、点击的权重等）
    score = models.FloatField(
        verbose_name='行为评分',
        help_text='行为的评分，用于推荐算法计算',
        default=1.0
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    
    class Meta:
        db_table = 'user_behavior'
        verbose_name = '用户行为记录'
        verbose_name_plural = '用户行为记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'action', 'created_at']),
            models.Index(fields=['doctor', 'action']),
        ]
    
    def __str__(self):
        return f'{self.user_id} - {self.get_action_display()} - {self.created_at}'


class UserProfile(models.Model):
    """用户画像模型（用于个性化推荐）"""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='用户'
    )
    # 专科偏好：{"正畸": 0.8, "种植": 0.2}，数值表示偏好强度（0-1）
    specialty_preference = models.JSONField(
        verbose_name='专科偏好',
        help_text='用户对不同专科的偏好程度',
        default=dict,
        blank=True
    )
    # 医院偏好：{"医院A": 0.6, "医院B": 0.4}
    hospital_preference = models.JSONField(
        verbose_name='医院偏好',
        help_text='用户对不同医院的偏好程度',
        default=dict,
        blank=True
    )
    # 价格敏感度：0-1，0表示不敏感，1表示非常敏感
    price_sensitivity = models.FloatField(
        verbose_name='价格敏感度',
        default=0.5,
        help_text='0-1，0表示不敏感，1表示非常敏感'
    )
    # 时间偏好：morning, afternoon, evening
    time_preference = models.CharField(
        max_length=20,
        verbose_name='时间偏好',
        blank=True,
        null=True,
        help_text='morning, afternoon, evening'
    )
    # 医生特征偏好：偏好高评分还是高评价数
    doctor_feature_preference = models.JSONField(
        verbose_name='医生特征偏好',
        help_text='{"score_weight": 0.6, "reviews_weight": 0.4}',
        default=dict,
        blank=True
    )
    # 最后更新时间
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'user_profile'
        verbose_name = '用户画像'
        verbose_name_plural = '用户画像'
    
    def __str__(self):
        return f'{self.user_id} - 用户画像'

