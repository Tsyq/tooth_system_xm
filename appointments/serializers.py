"""
预约序列化器
"""
from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    """预约序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']

