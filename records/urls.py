"""
病历URL配置
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RecordViewSet

router = DefaultRouter()
router.register(r'', RecordViewSet, basename='record')

urlpatterns = [
    path('', include(router.urls)),
    # 路由已通过ViewSet自动注册：
    # GET /records/ - 获取病历列表
    # POST /records/ - 医生端创建病历
    # GET /records/{record_id}/ - 获取病历详情
    # PUT /records/{record_id}/ - 医生端更新病历
    # POST /records/{record_id}/rating/ - 评价就诊
]

