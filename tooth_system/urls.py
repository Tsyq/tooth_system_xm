"""
URL configuration for tooth_system project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # API文档路由
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    # API路由
    path('api/auth/', include('user.urls')),           # 用户认证模块
    path('api/hospitals/', include('hospitals.urls')), # 医院管理模块
    path('api/doctors/', include('doctors.urls')),     # 医生管理模块
    path('api/appointments/', include('appointments.urls')), # 预约管理模块
    path('api/records/', include('records.urls')),     # 病历管理模块
    path('api/consultations/', include('consultations.urls')), # 在线问诊模块
    path('api/ai/', include('ai_inquiry.urls')),      # AI问询模块
    path('api/upload/', include('uploads.urls')),      # 文件上传模块
    path('api/statistics/', include('statistics.urls')), # 统计数据模块
]

# 开发环境：提供媒体文件访问
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
