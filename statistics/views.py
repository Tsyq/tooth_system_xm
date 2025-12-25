"""
统计数据视图
"""
from datetime import datetime, timedelta
from django.db.models import Count, Q, Avg
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from utils.response import success_response
from hospitals.models import Hospital
from doctors.models import Doctor
from appointments.models import Appointment
from user.models import User


class HomeStatisticsView(APIView):
    """首页统计数据视图"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        """获取首页统计数据"""
        # 获取各项统计数据
        cooperation_clinics = Hospital.objects.count()
        online_doctors = Doctor.objects.filter(is_online=True, audit_status='approved').count()
        total_doctors = Doctor.objects.filter(audit_status='approved').count()
        
        # 获取今日预约数
        today = datetime.now().date()
        today_appointments = Appointment.objects.filter(
            appointment_date=today
        ).count()
        
        # 获取今日完成预约数
        today_completed = Appointment.objects.filter(
            appointment_date=today,
            status='completed'
        ).count()
        
        # 计算预约完成率
        appointment_completion_rate = (
            (today_completed / today_appointments * 100) 
            if today_appointments > 0 else 0
        )
        appointment_completion_rate = round(appointment_completion_rate, 2)
        
        # 获取总预约数
        total_appointments = Appointment.objects.count()
        
        # 获取总用户数
        total_users = User.objects.count()
        
        # 计算患者满意度（基于医生评分平均值）
        avg_doctor_score = Doctor.objects.aggregate(Avg('score'))['score__avg'] or 0
        patient_satisfaction = round(avg_doctor_score, 2)
        
        # 获取最近30天预约增长率
        thirty_days_ago = today - timedelta(days=30)
        last_30_days = Appointment.objects.filter(
            created_at__date__gte=thirty_days_ago
        ).count()
        
        sixty_days_ago = today - timedelta(days=60)
        thirty_to_sixty_days = Appointment.objects.filter(
            created_at__date__gte=sixty_days_ago,
            created_at__date__lt=thirty_days_ago
        ).count()
        
        appointment_growth_rate = (
            ((last_30_days - thirty_to_sixty_days) / thirty_to_sixty_days * 100)
            if thirty_to_sixty_days > 0 else 0
        )
        appointment_growth_rate = round(appointment_growth_rate, 2)
        
        # 获取热门医院前5（按预约次数）
        top_hospitals = Hospital.objects.order_by('-appointment_count')[:5].values(
            'id', 'name', 'rating', 'appointment_count', 'image'
        )
        
        # 获取热门医生前5
        top_doctors = Doctor.objects.order_by('-score', '-reviews')[:5].values(
            'id', 'name', 'title', 'specialty', 'avatar', 'score', 'reviews'
        )
        
        data = {
            # 关键指标
            'cooperation_clinics': cooperation_clinics,
            'appointment_completion_rate': appointment_completion_rate,
            'appointment_growth_rate': appointment_growth_rate,
            'patient_satisfaction': patient_satisfaction,
            'today_patients': today_appointments,
            'online_doctors': online_doctors,
            
            # 扩展统计
            'total_doctors': total_doctors,
            'total_appointments': total_appointments,
            'total_users': total_users,
            'today_completed': today_completed,
            
            # 热门数据
            'top_hospitals': list(top_hospitals),
            'top_doctors': list(top_doctors),
        }
        return success_response(data)

