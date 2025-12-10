from rest_framework import generics, status
from .serializers import UserSerializer, UserLogOutSerializer, UserLoginSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.settings import api_settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from utils.response import success_response, error_response
from django.contrib.auth import get_user_model


class CreateUser(generics.CreateAPIView):
    """
    用户注册接口
    """
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        
        try:
            # 验证数据
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
        try:
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
        except Exception as e:
            error_message = str(e)
            if hasattr(e, 'detail'):
                detail = e.detail
                if isinstance(detail, dict) and detail:
                    error_message = next(iter(detail.values()))
                else:
                    error_message = str(detail)

            return error_response(
                message=error_message,
                code=400,
                data=None
            )


class UpdateRetrieveUser(generics.RetrieveUpdateAPIView):
    """An endpoint for updating and retrieving users"""
    authentication_classes = [JWTAuthentication, ]
    permission_classes = [IsAuthenticated, ]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


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
            return Response({'message': 'Successfully logged out'}, status=200)
        except Exception:
            return Response({'error': 'Failed to blacklist token'}, status=400)


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
            except:
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