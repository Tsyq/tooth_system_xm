"""
医生序列化器
"""
from rest_framework import serializers
from .models import Doctor, Schedule


class ScheduleSerializer(serializers.ModelSerializer):
    """排班序列化器"""
    
    class Meta:
        model = Schedule
        fields = ['id', 'date', 'start_time', 'end_time', 'status', 'max_appointments']
        read_only_fields = ['id']


class DoctorSerializer(serializers.ModelSerializer):
    """医生序列化器"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    hospital_id = serializers.IntegerField(source='hospital.id', read_only=True)
    
    class Meta:
        model = Doctor
        fields = '__all__'
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        """自定义序列化输出，添加排班数据和处理头像URL"""
        representation = super().to_representation(instance)
        
        # 处理头像URL：如果是相对路径，转换为完整URL
        avatar = representation.get('avatar')
        
        # 处理空值情况（None、空字符串、空白字符串）
        if avatar is None or (isinstance(avatar, str) and not avatar.strip()):
            # 如果头像为空，返回一个通用的占位图URL
            # 使用一个在线占位图服务，确保始终有有效的URL
            # 或者返回前端可以处理的相对路径（前端会使用默认头像）
            representation['avatar'] = 'https://ui-avatars.com/api/?name=' + (instance.name or 'Doctor') + '&background=1871a5&color=fff&size=128'
        elif isinstance(avatar, str):
            avatar = avatar.strip()
            # 如果已经是完整URL（http/https开头），直接使用
            if avatar.startswith('http://') or avatar.startswith('https://'):
                representation['avatar'] = avatar
            else:
                # 处理相对路径
                request = self.context.get('request')
                
                # 确保路径以/开头（除非已经是完整URL）
                if not avatar.startswith('/'):
                    avatar = '/' + avatar
                
                # 构建完整URL
                if request:
                    try:
                        # 使用request构建绝对URI
                        representation['avatar'] = request.build_absolute_uri(avatar)
                    except Exception as e:
                        # 如果构建失败，使用默认域名
                        try:
                            domain = request.get_host()
                            scheme = 'https' if request.is_secure() else 'http'
                            representation['avatar'] = f"{scheme}://{domain}{avatar}"
                        except Exception:
                            representation['avatar'] = f"http://localhost:8000{avatar}"
                else:
                    # 如果没有request上下文，使用默认域名
                    representation['avatar'] = f"http://localhost:8000{avatar}"
        else:
            # 非字符串类型，返回空字符串
            representation['avatar'] = ''
        
        # 获取该医生的所有活跃排班（未来或今天的日期）
        try:
            from django.utils import timezone
            today = timezone.now().date()
            schedules = Schedule.objects.filter(
                doctor=instance, 
                status='active',
                date__gte=today
            ).order_by('date', 'start_time')
            representation['schedules'] = ScheduleSerializer(schedules, many=True).data
        except Exception as e:
            # 如果排班查询失败，返回空数组，避免影响医生详情返回
            representation['schedules'] = []
        
        return representation

