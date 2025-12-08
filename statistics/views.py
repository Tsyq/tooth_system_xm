"""
统计数据视图
"""
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from utils.response import success_response


class HomeStatisticsView(APIView):
    """首页统计数据视图"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取首页统计数据"""
        # 框架结构，具体实现待补充
        data = {
            'cooperation_clinics': 0,
            'appointment_efficiency': 0,
            'revenue_growth': 0,
            'patient_satisfaction': 0,
            'today_patients': 0,
            'online_doctors': 0,
        }
        return success_response(data)

