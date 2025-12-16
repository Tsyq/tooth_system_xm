"""
病历序列化器
"""
from rest_framework import serializers
from .models import Record
from django.contrib.auth import get_user_model

User = get_user_model()


class RecordSerializer(serializers.ModelSerializer):
    """病历序列化器（用于列表和详情展示）"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    user_name = serializers.CharField(source='user.name', read_only=True)
    doctor_id = serializers.IntegerField(source='doctor.id', read_only=True)
    doctor_name = serializers.CharField(source='doctor.name', read_only=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    hospital_name = serializers.CharField(source='hospital.name', read_only=True)
    appointment_id = serializers.IntegerField(source='appointment.id', read_only=True, allow_null=True)
    
    class Meta:
        model = Record
        fields = [
            'id', 'user_id', 'user_name', 'doctor_id', 'doctor_name',
            'hospital_id', 'hospital_name', 'appointment_id',
            'date', 'diagnosis', 'content', 'treatment', 'medications',
            'result_image', 'rated', 'rating', 'comment',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'rated', 'rating', 'comment']


class RecordCreateSerializer(serializers.ModelSerializer):
    """病历创建序列化器（医生端使用）"""
    user_id = serializers.IntegerField(write_only=True)
    hospital_id = serializers.IntegerField(write_only=True)
    appointment_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    medications = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    
    class Meta:
        model = Record
        fields = [
            'user_id', 'hospital_id', 'appointment_id',
            'date', 'diagnosis', 'content', 'treatment',
            'medications', 'result_image'
        ]
    
    def validate_user_id(self, value):
        """验证患者用户ID"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError('患者用户不存在')
        return value
    
    def validate_hospital_id(self, value):
        """验证医院ID"""
        from hospitals.models import Hospital
        try:
            Hospital.objects.get(id=value)
        except Hospital.DoesNotExist:
            raise serializers.ValidationError('医院不存在')
        return value
    
    def validate_appointment_id(self, value):
        """验证预约ID"""
        if value is None:
            return value
        from appointments.models import Appointment
        try:
            Appointment.objects.get(id=value)
        except Appointment.DoesNotExist:
            raise serializers.ValidationError('预约不存在')
        return value
    
    def create(self, validated_data):
        """创建病历"""
        user_id = validated_data.pop('user_id')
        hospital_id = validated_data.pop('hospital_id')
        appointment_id = validated_data.pop('appointment_id', None)
        
        # 获取当前医生
        doctor = self.context['request'].user.doctor_profile
        
        # 获取关联对象
        from hospitals.models import Hospital
        from appointments.models import Appointment
        
        user = User.objects.get(id=user_id)
        hospital = Hospital.objects.get(id=hospital_id)
        appointment = Appointment.objects.get(id=appointment_id) if appointment_id else None
        
        # 创建病历
        record = Record.objects.create(
            user=user,
            doctor=doctor,
            hospital=hospital,
            appointment=appointment,
            **validated_data
        )
        return record


class RecordUpdateSerializer(serializers.ModelSerializer):
    """病历更新序列化器（医生端使用）"""
    medications = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
    
    class Meta:
        model = Record
        fields = [
            'date', 'diagnosis', 'content', 'treatment',
            'medications', 'result_image'
        ]


class RecordRatingSerializer(serializers.Serializer):
    """病历评价序列化器（患者端使用）"""
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, attrs):
        """验证评价"""
        record = self.context.get('record')
        if record and record.rated:
            raise serializers.ValidationError('该病历已评价过')
        return attrs

