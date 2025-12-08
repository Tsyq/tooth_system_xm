"""
AI问询序列化器
"""
from rest_framework import serializers
from .models import Inquiry


class InquirySerializer(serializers.ModelSerializer):
    """AI问询序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    class Meta:
        model = Inquiry
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at']

