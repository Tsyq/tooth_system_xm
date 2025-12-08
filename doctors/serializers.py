"""
医生序列化器
"""
from rest_framework import serializers
from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    """医生序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    
    class Meta:
        model = Doctor
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

