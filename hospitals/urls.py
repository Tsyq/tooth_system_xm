"""
医院URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HospitalViewSet

router = DefaultRouter()
router.register(r'', HospitalViewSet, basename='hospital')

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet自动注册：
    # GET /hospitals/ - 获取医院列表
    # GET /hospitals/{hospital_id}/ - 获取医院详情
]

