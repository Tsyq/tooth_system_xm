"""
医院URL配置（显式路由，风格与 `user/urls.py` 保持一致）
"""
from django.urls import path
from .views import HospitalList, HospitalDetail

urlpatterns = [
    path('', HospitalList.as_view(), name='hospital-list'),
    path('<int:pk>/', HospitalDetail.as_view(), name='hospital-detail'),
]

