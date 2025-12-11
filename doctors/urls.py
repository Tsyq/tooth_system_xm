"""
医生URL配置





"""
from django.urls import path
from .views import DoctorList, DoctorDetail, UpdateDoctorProfile, SetDoctorOnlineStatus

urlpatterns = [
    path('', DoctorList.as_view(), name='doctor-list'),#医生列表 GET   /doctors/    - 列表（filter: hospital_id, specialty, view=rank）
    path('<int:pk>/', DoctorDetail.as_view(), name='doctor-detail'),#医生信息 GET    /doctors/<id>/             - 详情
    path('me/', UpdateDoctorProfile.as_view(), name='update-doctor-profile'),#医生更新个人信息 PUT    /doctors/me/   -需IsDoctor认证
    path('me/online-status/', SetDoctorOnlineStatus.as_view(), name='set-online-status'),#医生设置在线状态 POST   /doctors/me/online-status/ - 需IsDoctor认证
]

