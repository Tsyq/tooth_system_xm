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
        read_only_fields = ['id', 'user', 'doctor','hospital','created_at', 'updated_at']


class CheckInSerializer(serializers.Serializer):
    """用户签到序列化器"""
    latitude = serializers.FloatField(
        required=True,
        help_text='用户当前位置的纬度'
    )
    longitude = serializers.FloatField(
        required=True,
        help_text='用户当前位置的经度'
    )
    
    def validate(self, attrs):
        """验证经纬度范围"""
        lat = attrs.get('latitude')
        lon = attrs.get('longitude')
        
        # 基本范围检查（地球坐标范围）
        if not (-90 <= lat <= 90):
            raise serializers.ValidationError({'latitude': '纬度必须在 -90 到 90 之间'})
        if not (-180 <= lon <= 180):
            raise serializers.ValidationError({'longitude': '经度必须在 -180 到 180 之间'})
        
        return attrs
