"""
在线问诊序列化器
"""
from rest_framework import serializers
from .models import Consultation, Message


class MessageSerializer(serializers.ModelSerializer):
    """消息序列化器"""
    
    class Meta:
        model = Message
        fields = '__all__'
        read_only_fields = ['id', 'time', 'created_at']


class ConsultationSerializer(serializers.ModelSerializer):
    """问诊会话序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Consultation
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

