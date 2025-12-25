"""
在线问诊序列化器
"""
from rest_framework import serializers
from .models import Consultation, Message


class MessageSerializer(serializers.ModelSerializer):
    """消息序列化器"""
    consultation_id = serializers.IntegerField(source='consultation.id', read_only=True)
    # 注意：这些字段在模型中是必填的，但在序列化器中设为可选
    # 因为消息创建是通过 ConsultationViewSet.send_message 直接使用 Model.objects.create
    # 而不是通过序列化器的 create 方法
    text = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    sender = serializers.CharField(required=False, allow_null=True)
    consultation = serializers.PrimaryKeyRelatedField(read_only=True)  # 明确设为只读
    
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['id', 'consultation', 'time', 'created_at']
    
    def validate(self, attrs):
        """验证消息数据（仅在通过序列化器创建时调用）"""
        # 如果 text 为空，设置为空字符串
        if 'text' not in attrs or attrs.get('text') is None:
            attrs['text'] = ''
        return attrs


class ConsultationSerializer(serializers.ModelSerializer):
    """问诊会话序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Consultation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

