from django.urls import path
from .views import (
    CreateUser,
    UpdateRetrieveUser,
    Logout,
    CaptchaView,
    LoginView,
    RefreshTokenView,
    ChangePasswordView,
    SendEmailCodeView,
)

urlpatterns = [
    # 用户认证相关路由（符合API文档规范）
    path('register/', CreateUser.as_view(), name='register'),           # 用户注册
    path('login/', LoginView.as_view(), name='login'),                  # 用户登录（自定义，支持验证码）
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),       # 刷新Token
    path('logout/', Logout.as_view(), name='logout'),                   # 用户登出
    path('me/', UpdateRetrieveUser.as_view(), name='me'),               # 获取/更新当前用户信息
    path('captcha/', CaptchaView.as_view(), name='captcha'),          # 获取图形验证码
    path('change-password/', ChangePasswordView.as_view(), name='change_password'), # 修改密码
    path('send-email-code/', SendEmailCodeView.as_view(), name='send_email_code'), # 发送邮箱验证码
]
