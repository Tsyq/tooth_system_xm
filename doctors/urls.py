"""
医生URL配置
"""
from django.urls import path
from .views import (
    DoctorList,
    DoctorDetail,
    UpdateDoctorProfile,
    SetDoctorOnlineStatus,
    DoctorPatientRecordsView
)

urlpatterns = [
    path('', DoctorList.as_view(), name='doctor-list'),  # 医生列表 GET /doctors/
    path('<int:pk>/', DoctorDetail.as_view(), name='doctor-detail'),  # 医生信息 GET /doctors/<id>/
    path('me/', UpdateDoctorProfile.as_view(), name='update-doctor-profile'),  # 医生更新个人信息 PUT /doctors/me/
    path('me/online-status/', SetDoctorOnlineStatus.as_view(), name='set-online-status'),  # 医生设置在线状态 POST /doctors/me/online-status/
    path('patients/records/', DoctorPatientRecordsView.as_view(), name='doctor-patient-records'),  # 医生端获取患者病历列表 GET /doctors/patients/records/
]

