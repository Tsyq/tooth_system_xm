"""
AI问询URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InquiryViewSet

router = DefaultRouter()
router.register(r'inquiry', InquiryViewSet, basename='inquiry')

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet自动注册：
    # POST /ai/inquiry/ - AI问询
]

