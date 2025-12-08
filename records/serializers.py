"""
病历序列化器
"""
from rest_framework import serializers
from .models import Record


class RecordSerializer(serializers.ModelSerializer):
    """病历序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    
    class Meta:
        model = Record
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

