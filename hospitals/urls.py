"""
医院URL配置

"""
from django.urls import path
from .views import HospitalList, HospitalDetail

urlpatterns = [
    path('', HospitalList.as_view(), name='hospital-list'),#  医院列表 GET  /hospitals/   - （filter: all|near|frequent）-权限：AllowAny
    path('<int:pk>/', HospitalDetail.as_view(), name='hospital-detail'),#医院详情 GET  /hospitals/<id>/   - 详情（访问计数） -权限：AllowAny
]

