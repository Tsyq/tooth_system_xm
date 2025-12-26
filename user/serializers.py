from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    password = serializers.CharField(
        write_only=True,
        max_length=100,
        required=False,  # 更新资料时不强制要求密码
        min_length=6,   # 添加最小长度验证
        help_text='密码（至少6位）'
    )
    # 把 avatar 改为 CharField 以避免 URLField 验证导致的文件对象错误
    avatar = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        help_text='头像URL'
    )

    class Meta:
        model = get_user_model()
        fields = ['id', 'name', 'phone', 'email', 'role', 'avatar', 'status', 'no_show_count', 'created_at', 'updated_at', 'password', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'status', 'no_show_count']  # status 由系统根据 role 自动设置

    def validate_phone(self, value):
        """验证手机号唯一性和格式"""
        if self.instance is None:  # 创建时检查
            if get_user_model().objects.filter(phone=value).exists():
                raise serializers.ValidationError('手机号已注册')
        
        # 验证手机号格式（11位数字）
        if not value.isdigit() or len(value) != 11:
            raise serializers.ValidationError('手机号必须是11位数字')
        
        return value

    def validate(self, attrs):
        return attrs

    def create(self, validated_data):
        from django.contrib.auth import get_user_model
        from django.db import IntegrityError

        password = validated_data.pop('password', None)
        if not password:
            raise serializers.ValidationError({'password': '密码为必填'})

        # 取出手机号，确保不会被误用作更新已有用户
        phone = validated_data.get('phone')
        if not phone:
            raise serializers.ValidationError({'phone': '手机号为必填'})

        # 预检手机号唯一性，防止覆盖或重复创建（并发仍由 DB 抛错保护）
        if get_user_model().objects.filter(phone=phone).exists():
            raise serializers.ValidationError({'phone': '手机号已注册'})

        # 设置默认角色和状态
        role = validated_data.get('role', 'user')
        validated_data['role'] = role
        if role == 'doctor':
            validated_data['status'] = 'pending'
            validated_data['is_active'] = False
        else:
            validated_data['status'] = 'active'

        # 调用自定义 manager 创建用户，传入 phone 与 password
        try:
            user = get_user_model().objects.create_user(phone=phone, password=password, **{k: v for k, v in validated_data.items() if k != 'phone'})
        except IntegrityError:
            # 并发场景下若仍然违反唯一性约束，返回友好错误
            raise serializers.ValidationError({'phone': '手机号已注册'})

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
        from django.contrib.auth import get_user_model
        
        phone = attrs.get('phone')
        password = attrs.get('password')
        captcha_id = attrs.get('captcha_id')
        captcha = attrs.get('captcha')
        
        # 1. 验证验证码
        if not verify_captcha(captcha_id, captcha):
            raise serializers.ValidationError({'captcha': '验证码错误或已过期'})
        
        # 2. 根据手机号获取用户（即便 is_active=False 也要拿到，便于给出明确提示）
        user = get_user_model().objects.filter(phone=phone).first()
        if not user or not user.check_password(password):
            raise serializers.ValidationError({'password': '手机号或密码错误'})

        # 登录拦截：医生与普通用户都在非激活或非active状态下拒绝登录
        user_status = getattr(user, 'status', None)
        user_role = getattr(user, 'role', None)

        if (not user.is_active) or (user_status in ['pending', 'inactive', 'rejected']):
            # 针对医生返回更具体的审核提示/拒绝原因
            if user_role == 'doctor':
                audit_status = None
                reason = ''
                try:
                    audit_status = getattr(user.doctor_profile, 'audit_status', None)
                    reason = getattr(user.doctor_profile, 'rejected_reason', '') or ''
                except Exception:
                    audit_status = None
                    reason = ''

                # 只要医生档案处于 rejected，或用户状态为 rejected，都返回拒绝原因
                if (audit_status == 'rejected') or (user_status == 'rejected'):
                    msg = f"审核未通过：{reason or '请重新提交资料'}"
                else:
                    # 其他情况视为待审核
                    msg = '账号未通过审核，请等待管理员审核'
                raise serializers.ValidationError({'phone': msg})
            else:
                raise serializers.ValidationError({'phone': '账号被拉黑，如有问题请联系后台管理员'})

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