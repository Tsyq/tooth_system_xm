"""
预约序列化器
"""
from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, date
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    """预约序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    patient_name = serializers.CharField(required=False, allow_blank=True, max_length=50)
    patient_phone = serializers.CharField(required=False, allow_blank=True, max_length=11)
    
    class Meta:
        model = Appointment
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def validate_appointment_date(self, value):
        """验证预约日期不能是过去"""
        today = timezone.now().date()
        if value < today:
            raise serializers.ValidationError('不能预约过去的日期')
        return value
    
    def validate(self, attrs):
        """验证预约时间不能是过去的时间"""
        appointment_date = attrs.get('appointment_date')
        appointment_time = attrs.get('appointment_time')
        
        if appointment_date and appointment_time:
            # 获取当前时间
            now = timezone.now()
            today = now.date()
            current_time = now.time()
            
            # 如果预约日期是今天，检查时间是否已过
            if appointment_date == today:
                try:
                    # 解析预约时间 (HH:mm格式)
                    time_parts = appointment_time.split(':')
                    if len(time_parts) == 2:
                        hour = int(time_parts[0])
                        minute = int(time_parts[1])
                        from datetime import time as dt_time
                        appointment_time_obj = dt_time(hour=hour, minute=minute)
                        
                        # 如果预约时间已过，不允许预约
                        if appointment_time_obj < current_time:
                            raise serializers.ValidationError({
                                'appointment_time': '不能预约已过去的时间段'
                            })
                except (ValueError, IndexError):
                    raise serializers.ValidationError({
                        'appointment_time': '时间格式错误，应为 HH:mm 格式'
                    })
        
        return attrs
    
    def create(self, validated_data):
        """创建预约时，如果未提供患者信息，从当前用户自动填充"""
        request = self.context.get('request')
        user = request.user if request else None
        
        # 如果未提供患者姓名，使用当前用户的姓名
        if not validated_data.get('patient_name') and user:
            validated_data['patient_name'] = user.name
        
        # 如果未提供患者电话，使用当前用户的电话
        if not validated_data.get('patient_phone') and user:
            validated_data['patient_phone'] = user.phone
        
        # 确保 user 字段被设置
        if 'user' not in validated_data and user:
            validated_data['user'] = user
        
        return super().create(validated_data)

