"""
预约视图
"""
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import datetime, timedelta
from math import radians, sin, cos, sqrt, atan2
from rest_framework.response import Response
from datetime import timedelta
import math
from doctors.models import Doctor, Schedule
from hospitals.models import Hospital
from .models import Appointment
from .serializers import AppointmentSerializer, CheckInSerializer
from utils.response import success_response, error_response
from utils.permissions import IsDoctor


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    计算两点之间的直线距离（单位：米）
    使用 Haversine 公式
    """
    R = 6371000  # 地球半径（米）
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    distance = R * c
    
    return distance


class AppointmentViewSet(viewsets.ModelViewSet):
    """预约视图集"""
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """只返回当前用户的预约"""
        queryset = super().get_queryset()
        # 只返回当前登录用户的预约
        queryset = queryset.filter(user=self.request.user)
        return queryset
    
    def list(self, request, *args, **kwargs):
        """获取预约列表"""
        queryset = self.get_queryset()
        
        # 手动实现状态筛选
        status = request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # 应用其他过滤（如果有）
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            # 获取分页响应并添加page和page_size字段
            paginated_data = self.get_paginated_response(serializer.data)
            # 获取当前页码和每页大小
            paginator = self.paginator
            current_page = int(request.query_params.get('page', 1))
            page_size = paginator.page_size if hasattr(paginator, 'page_size') else int(request.query_params.get('page_size', 20))
            
            # 构建符合前端期望的格式
            response_data = paginated_data.data
            response_data['page'] = current_page
            response_data['page_size'] = page_size
            return success_response(response_data)
        
        # 只检查待就诊状态的预约（全局，不限于当前用户）
        upcoming_appointments = Appointment.objects.filter(status='upcoming').select_related('user')
        
        for appointment in upcoming_appointments:
            # 计算预约时间
            appt_dt = timezone.make_aware(
                datetime.combine(
                    appointment.appointment_date,
                    datetime.strptime(appointment.appointment_time, '%H:%M').time()
                )
            )
            # 允许迟到30分钟
            latest_checkin = appt_dt + timedelta(minutes=30)
            
            # 如果超过签到时间，标记为no-show并累加爽约次数
            if now > latest_checkin:
                # 更新预约状态
                appointment.status = 'no-show'
                appointment.save(update_fields=['status', 'updated_at'])
                
                # 累加用户爽约次数（使用 F 表达式避免竞态条件）
                from django.db.models import F
                appointment.user.__class__.objects.filter(id=appointment.user.id).update(
                    no_show_count=F('no_show_count') + 1
                )

    def list(self, request, *args, **kwargs):
        """获取预约列表（手动分页，返回与接口文档一致结构）"""
        queryset = self.get_queryset()

        # 手动分页
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 10))
        except (TypeError, ValueError):
            page_size = 10
        if page <= 0:
            page = 1
        if page_size <= 0:
            page_size = 10

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = queryset[start:end]
        serializer = self.get_serializer(page_qs, many=True)
        return success_response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """获取预约详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """创建预约"""
        serializer = self.get_serializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            # 验证预约时间是否在排班范围内
            appointment_date = serializer.validated_data.get('appointment_date')
            appointment_time = serializer.validated_data.get('appointment_time')
            doctor = serializer.validated_data.get('doctor')
            hospital = serializer.validated_data.get('hospital')
            
            if appointment_date and appointment_time and doctor and hospital:
                from doctors.models import Schedule
                # 检查是否有对应的排班
                schedule = Schedule.objects.filter(
                    doctor=doctor,
                    hospital=hospital,
                    date=appointment_date,
                    start_time__lte=appointment_time,
                    end_time__gt=appointment_time,
                    status='active'
                ).first()
                
                if not schedule:
                    return error_response('该时间段没有可用的排班', 400)
                
                # 检查预约数量是否已满
                existing_count = Appointment.objects.filter(
                    doctor=doctor,
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                    status__in=['upcoming', 'checked-in']
                ).count()
                
                if existing_count >= schedule.max_appointments:
                    return error_response('该时间段预约已满，请选择其他时间', 400)
            
            # 确保 user 字段被设置
            serializer.validated_data['user'] = request.user
            
            appointment = serializer.save()
            return success_response(
                AppointmentSerializer(appointment, context={'request': request}).data,
                '预约成功'
            )
        
        return error_response(serializer.errors, 400)
    
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """取消预约：仅可取消未完成/未取消的预约"""
        appointment = self.get_object()
        
        # 1. 验证用户权限：只能取消自己的预约
        if appointment.user != request.user:
            return error_response('只能取消自己的预约', 403)
        
        # 2. 验证预约状态：只能取消 'upcoming' 或 'checked-in' 状态的预约
        if appointment.status not in ['upcoming', 'checked-in']:
            status_display = appointment.get_status_display()
            return error_response(f'该预约状态为{status_display}，无法取消', 400)
        
        # 3. 验证时间：不能取消已过期的预约（可选，根据业务需求）
        # 如果预约时间已过，可以允许取消，也可以不允许，这里选择允许
        
        # 4. 获取取消原因（可选）
        cancel_reason = request.data.get('reason', '').strip()
        
        # 5. 更新预约状态
        appointment.status = 'cancelled'
        appointment.save()
        
        # 6. 如果需要保存取消原因，可以在这里添加（需要模型支持）
        # 目前模型中没有 cancel_reason 字段，如果需要可以后续添加
        
        return success_response({
            'appointment_id': appointment.id,
            'status': appointment.status,
            'message': '预约已取消'
        }, '取消成功')
    
    @action(detail=True, methods=['post'], url_path='checkin')
    def checkin(self, request, pk=None):
        """用户根据定位签到到预约（时间窗口 + 距离校验）"""
        appointment = self.get_object()
        
        # 1. 验证用户权限：只能对自己的预约进行签到
        if appointment.user != request.user:
            return error_response('只能对自己的预约进行签到', 403)
        
        # 2. 验证预约状态：只能对 'upcoming' 状态的预约进行签到
        if appointment.status != 'upcoming':
            return error_response(f'该预约状态为{appointment.get_status_display()}，无法签到', 400)
        
        # 3. 验证时间：只能在预约时间前30分钟到后30分钟内签到
        now = timezone.now()
        appointment_date = appointment.appointment_date
        appointment_time_str = appointment.appointment_time  # HH:mm格式
        
        # 解析预约时间
        try:
            time_parts = appointment_time_str.split(':')
            if len(time_parts) != 2:
                return error_response('预约时间格式错误', 400)
            hour = int(time_parts[0])
            minute = int(time_parts[1])
            appointment_datetime = timezone.make_aware(
                datetime.combine(appointment_date, datetime.min.time().replace(hour=hour, minute=minute))
            )
        except (ValueError, IndexError) as e:
            return error_response('预约时间格式错误', 400)
        
        # 计算允许签到的时间窗口（预约时间前30分钟到后30分钟）
        checkin_start = appointment_datetime - timedelta(minutes=30)
        checkin_end = appointment_datetime + timedelta(minutes=30)
        
        if now < checkin_start:
            return error_response(f'签到时间未到，请在预约时间前30分钟内签到（最早{checkin_start.strftime("%Y-%m-%d %H:%M")}）', 400)
        if now > checkin_end:
            return error_response(f'签到时间已过，请在预约时间后30分钟内签到（最晚{checkin_end.strftime("%Y-%m-%d %H:%M")}）', 400)
        
        # 4. 验证地理位置：用户位置必须在医院500米范围内
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')
        
        if latitude is None or longitude is None:
            return error_response('请提供地理位置信息', 400)
        
        try:
            latitude = float(latitude)
            longitude = float(longitude)
        except (ValueError, TypeError):
            return error_response('地理位置信息格式错误', 400)
        
        hospital = appointment.hospital
        if not hospital.latitude or not hospital.longitude:
            # 如果医院没有设置经纬度，跳过地理位置验证（但记录警告）
            pass
        else:
            # 计算两点之间的距离（使用 Haversine 公式，单位：米）
            R = 6371000  # 地球半径（米）
            lat1 = radians(hospital.latitude)
            lat2 = radians(latitude)
            delta_lat = radians(latitude - hospital.latitude)
            delta_lon = radians(longitude - hospital.longitude)
            
            a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = R * c  # 距离（米）
            
            # 允许的签到距离：500米
            max_distance = 500
            if distance > max_distance:
                return error_response(f'您距离医院约{int(distance)}米，超过允许的签到距离（{max_distance}米），请到医院附近再签到', 400)
        
        # 5. 所有验证通过，执行签到
        appointment.status = 'checked-in'
        appointment.checkin_time = now
        appointment.save()
        
        return success_response({
            'appointment_id': appointment.id,
            'status': appointment.status,
            'checkin_time': appointment.checkin_time.strftime('%Y-%m-%d %H:%M:%S')
        }, '签到成功')
    
    @action(detail=True, methods=['post'], url_path='complete', permission_classes=[IsAuthenticated, IsDoctor])
    def complete(self, request, pk=None):
        """医生端完成预约：仅该预约对应医生可操作"""
        appointment = self.get_object()
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)

        if appointment.doctor_id != doctor.id:
            return error_response('无权限操作该预约', 403)
        if appointment.status == 'cancelled':
            return error_response('已取消预约不可完成', 400)
        if appointment.status == 'completed':
            return error_response('预约已完成', 400)

        appointment.status = 'completed'
        appointment.save()
        return success_response(None, '完成成功')

    @action(detail=True, methods=['get', 'post'], url_path='route')
    def route(self, request, pk=None):
        # 已废弃：路线规划改为基于医院ID的接口，请使用 /hospitals/<id>/route/
        return error_response('路线接口已迁移至医院模块：/hospitals/<id>/route/', 410)

