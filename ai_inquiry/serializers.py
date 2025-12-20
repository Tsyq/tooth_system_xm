"""
AI问询序列化器
"""
from rest_framework import serializers
from .models import Inquiry, AIChatMessage


class InquirySerializer(serializers.ModelSerializer):
    """AI问询序列化器（旧接口兼容）"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Inquiry
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']


# ==================== 新的AI对话接口序列化器 ====================

class AIChatRequestSerializer(serializers.Serializer):
    """AI对话请求序列化器"""
    message = serializers.CharField(
        max_length=2000,
        help_text='用户输入的问题或描述'
    )
    age = serializers.IntegerField(
        required=False,
        min_value=0,
        max_value=120,
        help_text='年龄'
    )
    gender = serializers.ChoiceField(
        choices=[('male', '男'), ('female', '女')],
        required=False,
        help_text='性别'
    )
    has_allergy = serializers.BooleanField(
        required=False,
        help_text='是否有过敏史'
    )


class RecommendedDoctorSerializer(serializers.Serializer):
    """推荐医生序列化器"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    department_name = serializers.CharField()
    title = serializers.CharField()
    good_at = serializers.CharField()
    next_available_time = serializers.CharField(
        allow_null=True,
        required=False
    )


class AIChatResponseSerializer(serializers.Serializer):
    """AI对话响应序列化器"""
    answer = serializers.CharField(help_text='AI 生成的回答文案')
    recommended_doctors = RecommendedDoctorSerializer(
        many=True,
        required=False
    )
    suggestion_level = serializers.ChoiceField(
        choices=[('info', '一般信息'),
                 ('normal', '建议就诊'),
                 ('urgent', '建议尽快就医')],
        required=False
    )


class AIChatMessageSerializer(serializers.ModelSerializer):
    """AI对话消息序列化器（用于历史记录和搜索）"""
    
    class Meta:
        model = AIChatMessage
        fields = ['id', 'role', 'content', 'created_at']
        read_only_fields = ['id', 'created_at']

