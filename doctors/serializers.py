"""
医生序列化器
"""
from rest_framework import serializers
from .models import Doctor, Schedule


class DoctorSerializer(serializers.ModelSerializer):
    """医生序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    name = serializers.CharField(required=False)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    
    class Meta:
        model = Doctor
        fields = ['id', 'user_id', 'name', 'title', 'specialty', 'hospital_id', 'avatar', 
                  'score', 'reviews', 'introduction', 'education', 'experience', 'is_online', 
                  'is_admin', 'audit_status', 'applied_at', 'audited_at', 'rejected_reason',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'user_id', 'hospital_id', 'score', 'reviews', 'is_admin', 
                            'audit_status', 'applied_at', 'audited_at', 'created_at', 'updated_at']


class ScheduleSerializer(serializers.ModelSerializer):
    """排班序列化器"""
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    created_by_id = serializers.IntegerField(source='created_by.id', read_only=True, allow_null=True)

    class Meta:
        model = Schedule
        fields = ['id', 'hospital_id', 'doctor_id', 'doctor_name', 'date', 
                  'status', 'created_by_id', 'created_at', 'updated_at']
        read_only_fields = ['id', 'hospital_id', 'doctor_id', 'doctor_name', 'created_by_id', 'created_at', 'updated_at']

