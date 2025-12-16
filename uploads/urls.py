"""
文件上传URL配置
"""
from django.urls import path
from .views import ImageUploadView, FileUploadView

urlpatterns = [
    path('image/', ImageUploadView.as_view(), name='image_upload'),
    path('file/', FileUploadView.as_view(), name='file_upload'),
    # POST /upload/image/ - 上传图片（可选更新头像）
    # POST /upload/file/  - 上传文件（图片、PDF、文档等）
]

