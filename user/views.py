from rest_framework import generics, status
from .serializers import UserSerializer, UserLogOutSerializer
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from utils.response import success_response, error_response


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
