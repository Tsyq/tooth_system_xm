from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    password = serializers.CharField(
        write_only=True,
        max_length=100,
        required=True,  # 改为必填
        min_length=6,   # 添加最小长度验证
        help_text='密码（至少6位）'
    )

    class Meta:
        model = get_user_model()
        fields = ['id', 'name', 'phone', 'role', 'avatar', 'status', 'created_at', 'updated_at', 'password']
        read_only_fields = ['id', 'created_at', 'updated_at', 'status']  # status 由系统根据 role 自动设置

    def validate_phone(self, value):
        """验证手机号唯一性和格式"""
        if self.instance is None:  # 创建时检查
            if get_user_model().objects.filter(phone=value).exists():
                raise serializers.ValidationError('手机号已注册')
        
        # 验证手机号格式（11位数字）
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError('手机号必须是11位数字')
        
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        
        # 设置默认角色为 user（如果未提供）
        role = validated_data.get('role', 'user')
        validated_data['role'] = role
        
        # 如果注册的是医生，状态设为待审核；普通用户为激活状态
        if role == 'doctor':
            validated_data['status'] = 'pending'
        else:
            validated_data['status'] = 'active'
        
        user = get_user_model().objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class UserLogOutSerializer(serializers.Serializer):
    "A serializer for validate data for Logging out user"
    refresh = serializers.CharField(required=True,
                                    write_only=True, trim_whitespace=True)

    def validate_refresh(self, value):
        """Validate the refresh token"""
        access_token = self.context.get('access_token')

        if not access_token:
            raise serializers.\
                ValidationError("Something wrong in the access token")

        try:
            access_user_id = access_token.payload.get('user_id')
            if access_user_id is None:
                raise serializers.ValidationError
            ("User ID is missing in the access token.")
        except Exception:
            raise serializers.ValidationError(
                "Something went rong extracting" +
                "user id from payload of access token")

        # Validate the refresh token
        try:
            refresh_token = RefreshToken(value)
            refresh_user_id = refresh_token.payload.get('user_id')
        except TokenError:
            raise serializers.ValidationError(
                "Invalid or expired refresh token.")

        # Check if the user ID in the access token matches the refresh token
        if access_user_id != refresh_user_id:
            raise serializers.ValidationError(
                "The refresh token does not belong " +
                "to the same user as the access token.")

        return value
