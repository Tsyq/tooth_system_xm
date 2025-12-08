"""
医院序列化器
"""
from rest_framework import serializers
from .models import Hospital


class HospitalSerializer(serializers.ModelSerializer):
    """医院序列化器"""
    
    class Meta:
        model = Hospital
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

