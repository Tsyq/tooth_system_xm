from rest_framework import generics, status
from .serializers import UserSerializer, UserLogOutSerializer, UserLoginSerializer
from .serializers import ChangePasswordSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.settings import api_settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from utils.response import success_response, error_response
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import uuid
from utils.permissions import IsSystemAdmin
from appointments.models import Appointment
from datetime import datetime, timedelta


class CreateUser(generics.CreateAPIView):
    """
    用户注册接口
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        # 验证数据，异常由全局异常处理返回
        serializer.is_valid(raise_exception=True)

        # 创建用户
        user = serializer.save()

        # 构建返回数据（符合接口文档格式）
        response_data = {
            'user_id': user.id,
            'name': user.name,
            'phone': user.phone,
            'role': user.role,
            'status': user.status,
        }

        # 使用统一响应格式
        return success_response(
            data=response_data,
            message='注册成功',
            code=200
        )


class LoginView(APIView):
    """
    用户登录接口
    支持验证码验证和JWT Token生成
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        """
        用户登录
        """
        serializer = UserLoginSerializer(data=request.data, context={'request': request})
        
        try:
            # 验证数据（包括验证码和用户名密码）
            serializer.is_valid(raise_exception=True)
            
            # 获取用户
            user = serializer.validated_data['user']
            
            # 生成JWT Token
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            # 计算过期时间（秒）
            expires_in = int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds())
            
            # 构建用户信息（使用序列化器确保格式一致）
            from .serializers import UserSerializer
            user_serializer = UserSerializer(user)
            user_data = user_serializer.data
            
            # 构建返回数据（符合接口文档格式）
            response_data = {
                'token': access_token,
                'refresh_token': refresh_token,
                'user': user_data,
                'expires_in': expires_in
            }

            # 若有登录提示（医生待审核/被拒绝），追加到响应
            login_notice = serializer.validated_data.get('login_notice')
            rejected_reason = serializer.validated_data.get('rejected_reason')
            if login_notice:
                response_data['login_notice'] = login_notice
            if rejected_reason:
                response_data['rejected_reason'] = rejected_reason

            # 登录成功后清理验证码键，避免二次请求误判
            captcha_id = serializer.validated_data.get('captcha_id')
            if captcha_id:
                cache.delete_many([
                    f'captcha_{captcha_id}',
                    f'captcha_used_{captcha_id}',
                ])
            
            return success_response(
                data=response_data,
                message='登录成功',
                code=200
            )
            
        except Exception as e:
            # 处理异常情况
            error_message = str(e)
            
            # 如果是验证错误，提取更友好的错误信息
            if hasattr(e, 'detail'):
                if isinstance(e.detail, dict):
                    # 提取第一个字段错误
                    first_error = list(e.detail.values())[0]
                    if isinstance(first_error, list):
                        error_message = first_error[0]
                    else:
                        error_message = str(first_error)
                else:
                    error_message = str(e.detail)
            
            return error_response(
                message=error_message,
                code=400,
                data=None
            )


class RefreshTokenView(TokenRefreshView):
    """
    刷新Access Token并轮换Refresh Token
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_data = serializer.validated_data
        access_token = token_data.get('access')
        refresh_token = token_data.get('refresh') or request.data.get('refresh')

        response_data = {
            'token': access_token,
            'refresh_token': refresh_token,
            'expires_in': int(api_settings.ACCESS_TOKEN_LIFETIME.total_seconds()),
        }

        return success_response(
            data=response_data,
            message='刷新成功',
            code=200
        )


class UpdateRetrieveUser(generics.RetrieveUpdateAPIView):
    """An endpoint for updating and retrieving users"""
    authentication_classes = [JWTAuthentication, ]
    permission_classes = [IsAuthenticated, ]
    serializer_class = UserSerializer
    # 兼容两种前端提交方式：
    # - application/json（仅更新 name/email 等）
    # - multipart/form-data（包含 avatar 文件上传）
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_object(self):
        return self.request.user

    def _save_avatar_if_present(self, request):
        avatar_file = request.FILES.get('avatar')
        if not avatar_file:
            return None

        allowed_content_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if avatar_file.content_type not in allowed_content_types:
            raise ValueError('不支持的图片类型')
        max_size = 5 * 1024 * 1024
        if avatar_file.size > max_size:
            raise ValueError('文件过大，最大5MB')

        today = timezone.now()
        ext = os.path.splitext(avatar_file.name)[1].lower() or '.jpg'
        filename = f"{uuid.uuid4().hex}{ext}"
        relative_dir = os.path.join('uploads', 'avatars', today.strftime('%Y'), today.strftime('%m'))
        relative_path = os.path.join(relative_dir, filename).replace('\\', '/')
        saved_path = default_storage.save(relative_path, ContentFile(avatar_file.read()))
        url = f"{settings.MEDIA_URL}{saved_path}".replace('//', '/').replace(':/', '://')
        return url

    def put(self, request, *args, **kwargs):
        user = self.get_object()
        # 手工提取表单字段，避免 multipart 数据中的文件对象
        update_data = {}
        if 'name' in request.data:
            update_data['name'] = request.data.get('name')
        if 'email' in request.data:
            update_data['email'] = request.data.get('email')
        
        # 处理头像文件
        try:
            avatar_url = self._save_avatar_if_present(request)
            if avatar_url:
                update_data['avatar'] = avatar_url
        except ValueError as e:
            return error_response(str(e), 400)

        # 只传入提取的字段给序列化器
        serializer = self.get_serializer(user, data=update_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(serializer.data, '更新成功', 200)

    def patch(self, request, *args, **kwargs):
        # 与 PUT 相同逻辑
        return self.put(request, *args, **kwargs)


class Logout(APIView):
    """An endpoint to logout a user"""
    authentication_classes = [JWTAuthentication, ]
    permission_classes = [IsAuthenticated, ]

    def post(self, request):
        serializer = UserLogOutSerializer(
            data=request.data, context={'access_token': request.auth})
        serializer.is_valid(raise_exception=True)
        refresh_token_string = serializer.validated_data['refresh']
        try:
            refresh_token = RefreshToken(refresh_token_string)
            refresh_token.blacklist()
            return success_response(
                data=None,
                message='退出成功',
                code=200
            )
        except Exception as e:
            return error_response(
                message=f'退出失败: {str(e)}',
                code=400,
                data=None
            )


# 管理端：用户列表 & 拉黑/解锁




class AdminUserList(APIView):
    """管理员获取用户列表，附带未按时签到次数"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def get(self, request):
        user_model = get_user_model()
        users = user_model.objects.exclude(role='admin').order_by('-created_at')
        status_filter = request.query_params.get('status')
        keyword = request.query_params.get('keyword')
        if status_filter in ['active', 'pending', 'inactive']:
            users = users.filter(status=status_filter)
        if keyword:
            users = users.filter(name__icontains=keyword)

        results = []
        for user in users.filter(role='user'):
            # 直接使用数据库中的 no_show_count，避免与自动计算冲突
            data = UserSerializer(user).data
            results.append(data)

        return success_response({'count': len(results), 'results': results})


class AdminUserBlacklist(APIView):
    """管理员拉黑指定用户"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request, pk):
        try:
            user = get_user_model().objects.get(pk=pk)
        except get_user_model().DoesNotExist:
            return error_response('用户不存在', 404)
        user.status = 'inactive'
        user.is_active = False
        user.save(update_fields=['status', 'is_active'])
        return success_response(UserSerializer(user).data, '已拉黑')


class AdminUserUnblacklist(APIView):
    """管理员解除拉黑"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request, pk):
        try:
            user = get_user_model().objects.get(pk=pk)
        except get_user_model().DoesNotExist:
            return error_response('用户不存在', 404)
        user.status = 'active'
        user.is_active = True
        # 解除拉黑后重置未按时签到次数，避免继续累加影响
        user.no_show_count = 0
        user.save(update_fields=['status', 'is_active', 'no_show_count'])
        return success_response(UserSerializer(user).data, '已解除拉黑')


class AdminUserBulkBlacklist(APIView):
    """管理员批量拉黑：no_show_count 超过阈值的用户"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request):
        """
        请求体可选参数：
        - threshold: int，默认为 5（表示 no_show_count > threshold）
        返回：affected_count 与 affected_ids
        """
        from django.utils import timezone
        try:
            threshold = int(request.data.get('threshold', 5))
        except (TypeError, ValueError):
            return error_response('threshold 参数不合法，需为整数', 400)

        user_model = get_user_model()
        # 仅对普通用户进行处理，且排除已禁用的用户
        qs = user_model.objects.filter(
            role='user',
            status__in=['active', 'pending'],
            no_show_count__gt=threshold
        )

        ids = list(qs.values_list('id', flat=True))
        affected_count = len(ids)

        if affected_count == 0:
            return success_response({'affected_count': 0, 'affected_ids': []}, '无需处理，未找到符合条件的用户')

        # 批量更新为禁用，并更新更新时间
        user_model.objects.filter(id__in=ids).update(
            status='inactive',
            is_active=False,
            updated_at=timezone.now()
        )

        return success_response({'affected_count': affected_count, 'affected_ids': ids}, '已批量拉黑用户')


class CaptchaView(APIView):
    """
    获取图形验证码接口
    生成验证码图片并返回 base64 编码的图片和验证码ID
    """
    permission_classes = [AllowAny]
    
    def get(self, request):
        """
        生成并返回验证码
        """
        try:
            import random
            import string
            import base64
            import io
            import uuid
            from PIL import Image, ImageDraw, ImageFont
            from django.core.cache import cache
            
            # 生成4位随机验证码（数字+大写字母）
            captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
            
            # 生成唯一ID
            captcha_id = str(uuid.uuid4())
            
            # 将验证码存储到缓存中，5分钟过期
            cache.set(f'captcha_{captcha_id}', captcha_text.lower(), 300)
            
            # 创建图片
            width, height = 120, 40
            image = Image.new('RGB', (width, height), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            
            # 尝试使用系统字体，如果失败则使用默认字体
            import platform
            font = None
            try:
                if platform.system() == 'Windows':
                    # Windows 系统字体路径
                    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 24)
                elif platform.system() == 'Linux':
                    # Linux 系统字体
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
                elif platform.system() == 'Darwin':  # macOS
                    # macOS 系统字体
                    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
            except Exception:
                pass
            
            if font is None:
                # 使用默认字体
                font = ImageFont.load_default()
            
            # 绘制验证码文字（添加一些随机位置偏移）
            x = 10
            for char in captcha_text:
                y = random.randint(5, 15)
                # 随机颜色
                color = (random.randint(0, 100), random.randint(0, 100), random.randint(0, 100))
                draw.text((x, y), char, fill=color, font=font)
                x += 25
            
            # 添加干扰线
            for _ in range(3):
                start = (random.randint(0, width), random.randint(0, height))
                end = (random.randint(0, width), random.randint(0, height))
                draw.line([start, end], fill=(random.randint(150, 255), random.randint(150, 255), random.randint(150, 255)), width=1)
            
            # 添加干扰点
            for _ in range(50):
                x = random.randint(0, width)
                y = random.randint(0, height)
                draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
            
            # 将图片转换为 base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_data = buffer.getvalue()
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            captcha_image = f'data:image/png;base64,{image_base64}'
            
            # 返回数据
            response_data = {
                'captcha_id': captcha_id,
                'captcha_image': captcha_image
            }
            
            return success_response(
                data=response_data,
                message='获取验证码成功',
                code=200
            )
            
        except Exception as e:
            return error_response(
                message=f'生成验证码失败: {str(e)}',
                code=500,
                data=None
            )


class ChangePasswordView(APIView):
    """修改当前用户密码"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return success_response(
                data=None,
                message='密码修改成功',
                code=200
            )
        except Exception as e:
            message = str(e)
            if hasattr(e, 'detail'):
                detail = e.detail
                if isinstance(detail, dict) and detail:
                    message = next(iter(detail.values()))
                else:
                    message = str(detail)
            return error_response(
                message=message,
                code=400,
                data=None
            )


class SendEmailCodeView(APIView):
    """
    发送邮箱验证码（用于修改密码）
    要求已登录用户，且邮箱与账号绑定的邮箱一致
    """
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        email = request.data.get('email') or getattr(user, 'email', None)

        if not email:
            return error_response(message='邮箱不能为空', code=400)

        if not getattr(user, 'email', None):
            return error_response(message='当前账号未绑定邮箱，请先绑定后再发送验证码', code=400)

        if email != getattr(user, 'email', None):
            return error_response(message='邮箱与当前账号不一致', code=400)

        # 生成 6 位验证码
        import random
        code = f'{random.randint(0, 999999):06d}'

        # 写入缓存 5 分钟
        from django.core.cache import cache
        cache.set(f'email_code_{email}', code, timeout=300)

        # 发送邮件（需要在 settings 中配置 EMAIL_HOST 等）
        subject = '密码修改验证码'
        message = f'您的验证码是：{code}，5分钟内有效。'
        try:
            send_mail(subject, message, getattr(settings, 'DEFAULT_FROM_EMAIL', None), [email])
        except Exception as e:
            return error_response(message=f'邮件发送失败: {e}', code=400)

        return success_response(
            data={'expires_in': 300},
            message='验证码已发送',
            code=200
        )