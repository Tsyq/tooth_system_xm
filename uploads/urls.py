"""
文件上传URL配置
"""
from django.urls import path
from .views import ImageUploadView

urlpatterns = [
    path('image/', ImageUploadView.as_view(), name='image_upload'),
    # POST /upload/image/ - 上传图片
]

