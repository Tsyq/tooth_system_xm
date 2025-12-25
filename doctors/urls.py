"""
医生URL配置
"""
from django.urls import path
from .views import (
    DoctorList,
    DoctorDetail,
    UpdateDoctorProfile,
    SetDoctorOnlineStatus,
    DoctorPatientRecordsView,
    DoctorAuditList,
    DoctorAuditApprove,
    DoctorAuditReject,
    DoctorApply,
    ScheduleView,
    SetDoctorAsAdmin,
)

urlpatterns = [
    path('', DoctorList.as_view(), name='doctor-list'),  # 医生列表 GET /doctors/
    path('<int:pk>/', DoctorDetail.as_view(), name='doctor-detail'),  # 医生信息 GET /doctors/<id>/
    path('me/', UpdateDoctorProfile.as_view(), name='update-doctor-profile'),  # 医生更新个人信息 PUT /doctors/me/
    path('me/online-status/', SetDoctorOnlineStatus.as_view(), name='set-online-status'),  # 医生设置在线状态 POST /doctors/me/online-status/
    path('patients/records/', DoctorPatientRecordsView.as_view(), name='doctor-patient-records'),  # 医生端获取患者病历列表 GET /doctors/patients/records/
    path('schedules/', ScheduleView.as_view(), name='doctor-schedules'),  # 排班管理与查询
    # 审核相关
    path('audits/', DoctorAuditList.as_view(), name='doctor-audit-list'),  # 管理端获取审核列表 GET /doctors/audits/?status=pending|approved|rejected
    path('audits/<int:pk>/approve/', DoctorAuditApprove.as_view(), name='doctor-audit-approve'),  # 管理端审核通过 POST /doctors/audits/<id>/approve/
    path('audits/<int:pk>/reject/', DoctorAuditReject.as_view(), name='doctor-audit-reject'),  # 管理端审核拒绝 POST /doctors/audits/<id>/reject/
    # 申请入口
    path('apply/', DoctorApply.as_view(), name='doctor-apply'),  # 医生申请 POST /doctors/apply/
    # 设置管理员医生
    path('<int:pk>/set-admin/', SetDoctorAsAdmin.as_view(), name='set-doctor-as-admin'),  # 管理端设置医生为管理员医生 POST /doctors/<id>/set-admin/
]

