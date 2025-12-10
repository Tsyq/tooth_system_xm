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
        fields = ['id', 'name', 'phone', 'email', 'role', 'avatar', 'status', 'created_at', 'updated_at', 'password']
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


class UserLoginSerializer(serializers.Serializer):
    """用户登录序列化器"""
    phone = serializers.CharField(required=True, help_text='手机号')
    password = serializers.CharField(required=True, write_only=True, help_text='密码')
    captcha_id = serializers.CharField(required=True, help_text='验证码ID')
    captcha = serializers.CharField(required=True, help_text='验证码答案')
    
    def validate(self, attrs):
        """验证登录信息"""
        from utils.captcha import verify_captcha
        from django.contrib.auth import authenticate
        
        phone = attrs.get('phone')
        password = attrs.get('password')
        captcha_id = attrs.get('captcha_id')
        captcha = attrs.get('captcha')
        
        # 1. 验证验证码
        if not verify_captcha(captcha_id, captcha):
            raise serializers.ValidationError({'captcha': '验证码错误或已过期'})
        
        # 2. 验证用户名和密码
        user = authenticate(request=self.context.get('request'), username=phone, password=password)
        
        if not user:
            raise serializers.ValidationError({'password': '手机号或密码错误'})
        
        if not user.is_active:
            raise serializers.ValidationError({'phone': '账号已被禁用'})
        
        attrs['user'] = user
        return attrs


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


class ChangePasswordSerializer(serializers.Serializer):
    """修改密码序列化器（强制校验邮箱 + 验证码）"""
    old_password = serializers.CharField(required=True, write_only=True, min_length=6)
    new_password = serializers.CharField(required=True, write_only=True, min_length=6)
    email = serializers.EmailField(required=True, write_only=True)
    code = serializers.CharField(required=True, write_only=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('原密码错误')
        return value

    def validate(self, attrs):
        user = self.context['request'].user
        email = attrs.get('email')
        code = attrs.get('code')

        # 强制校验邮箱与验证码
        if not getattr(user, 'email', None):
            raise serializers.ValidationError({'email': '当前账号未绑定邮箱，请先绑定后再获取验证码'})
        if email != getattr(user, 'email', None):
            raise serializers.ValidationError({'email': '邮箱与当前账号不一致'})
        from django.core.cache import cache
        cache_code = cache.get(f'email_code_{email}')
        if not cache_code or str(cache_code) != str(code):
            raise serializers.ValidationError({'code': '验证码错误或已过期'})

        return attrs

    def validate_new_password(self, value):
        # 可以在这里扩展密码规则，如复杂度校验
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        new_password = self.validated_data['new_password']
        user.set_password(new_password)
        user.save()
        return user