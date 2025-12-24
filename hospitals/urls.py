"""
医院URL配置

"""
from django.urls import path
from .views import HospitalList, HospitalDetail, AdminHospitalCreate, AssignDoctorHospital, HospitalRoute

urlpatterns = [
    path('', HospitalList.as_view(), name='hospital-list'),#  医院列表 GET  /hospitals/   - （filter: all|near|frequent）-权限：AllowAny
    path('<int:pk>/', HospitalDetail.as_view(), name='hospital-detail'),#医院详情 GET  /hospitals/<id>/   - 详情（访问计数） -权限：AllowAny
    path('<int:pk>/route/', HospitalRoute.as_view(), name='hospital-route'),  # 路线信息 GET/POST /hospitals/<id>/route/
    # 管理端
    path('admin/create/', AdminHospitalCreate.as_view(), name='hospital-create'),  # POST /hospitals/admin/create/
    path('admin/assign-doctor/', AssignDoctorHospital.as_view(), name='assign-doctor-hospital'),  # POST /hospitals/admin/assign-doctor/
]

