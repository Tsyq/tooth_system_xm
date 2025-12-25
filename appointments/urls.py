"""
预约URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AppointmentViewSet

router = DefaultRouter()
router.register(r'', AppointmentViewSet, basename='appointment')

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet自动注册：
    # POST /appointments/ - 创建预约
    # GET /appointments/ - 获取预约列表
    # GET /appointments/{appointment_id}/ - 获取预约详情
    # PUT /appointments/{appointment_id}/ - 预约改期
    # POST /appointments/{appointment_id}/cancel/ - 取消预约
    # POST /appointments/{appointment_id}/checkin/ - 预约签到
    # POST /appointments/{appointment_id}/complete/ - 医生端完成预约
]

