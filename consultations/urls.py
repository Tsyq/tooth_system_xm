"""
在线问诊URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConsultationViewSet

router = DefaultRouter()
router.register(r'', ConsultationViewSet, basename='consultation')
# 注意：不再注册 MessageViewSet，因为：
# 1. 消息创建必须通过 ConsultationViewSet.send_message action
# 2. 消息列表可以通过 ConsultationViewSet.retrieve 获取（ConsultationSerializer 包含 messages 字段）

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet自动注册：
    # POST /consultations/ - 创建问诊会话
    # GET /consultations/ - 获取问诊会话列表
    # GET /consultations/{consultation_id}/ - 获取问诊会话详情（含消息列表）
    # POST /consultations/{consultation_id}/messages/ - 发送消息（ConsultationViewSet.send_message）
    # POST /consultations/{consultation_id}/close/ - 关闭问诊会话
]

