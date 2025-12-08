"""
医生URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DoctorViewSet

router = DefaultRouter()
router.register(r'', DoctorViewSet, basename='doctor')

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet的@action装饰器自动注册：
    # GET /doctors/ - 获取医生列表
    # GET /doctors/{doctor_id}/ - 获取医生详情
    # PUT /doctors/me/ - 医生端更新个人信息
    # POST /doctors/me/online-status/ - 医生端设置在线状态
    # GET /doctors/patients/records/ - 医生端获取患者病历列表
]

