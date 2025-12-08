"""
在线问诊URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultationViewSet, MessageViewSet

router = DefaultRouter()
router.register(r'', ConsultationViewSet, basename='consultation')
router.register(r'messages', MessageViewSet, basename='message')

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet自动注册：
    # POST /consultations/ - 创建问诊会话
    # GET /consultations/ - 获取问诊会话列表
    # GET /consultations/{consultation_id}/ - 获取问诊会话详情（含消息列表）
    # POST /consultations/{consultation_id}/messages/ - 发送消息
    # POST /consultations/{consultation_id}/close/ - 关闭问诊会话
]

