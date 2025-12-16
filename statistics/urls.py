"""
统计数据URL配置
"""
from django.urls import path
from .views import HomeStatisticsView

urlpatterns = [
    path('home/', HomeStatisticsView.as_view(), name='home_statistics'),
]

"""
API端点说明：
1. GET /statistics/home/ - 获取首页统计数据
   
   响应示例:
   {
       "code": 200,
       "message": "success",
       "data": {
           "cooperation_clinics": 10,              # 合作诊所数
           "appointment_efficiency": 85.50,       # 预约完成率(%)
           "revenue_growth": 12.30,                # 预约增长率(%)
           "patient_satisfaction": 4.85,          # 患者满意度(0-5分)
           "today_patients": 25,                  # 今日预约数
           "online_doctors": 15,                  # 在线医生数
           "total_doctors": 50,                   # 总医生数
           "total_appointments": 1250,            # 总预约数
           "total_users": 500,                    # 总用户数
           "today_completed": 21,                 # 今日已完成预约
           "top_hospitals": [                     # 热门医院前5
               {
                   "id": 1,
                   "name": "北京口腔医院",
                   "rating": 4.8,
                   "visit_count": 500,
                   "image": "http://..."
               }
           ],
           "top_doctors": [                       # 热门医生前5
               {
                   "id": 1,
                   "name": "李医生",
                   "title": "主任医师",
                   "specialty": "牙周病",
                   "avatar": "http://...",
                   "score": 4.9,
                   "reviews": 200
               }
           ]
       }
   }
"""

