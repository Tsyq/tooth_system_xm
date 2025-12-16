"""
预约视图
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
import math
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
    
    def list(self, request, *args, **kwargs):
        """获取预约列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """获取预约详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """取消预约"""
        appointment = self.get_object()
        # 具体业务逻辑待实现
        return success_response(None, '取消成功')
    
    @action(detail=True, methods=['post'], url_path='checkin')
    def checkin(self, request, pk=None):
        """用户根据定位签到到预约"""
        appointment = self.get_object()
        
        # 验证预约属于当前用户
        if appointment.user != request.user:
            return error_response('无权操作该预约', 403)
        
        # 验证预约状态
        if appointment.status == 'cancelled':
            return error_response('预约已取消，无法签到', 400)
        if appointment.status == 'checked-in':
            return error_response('已签到，请勿重复签到', 400)
        if appointment.status == 'completed':
            return error_response('预约已完成，无法签到', 400)
        
        # 反序列化并验证经纬度
        serializer = CheckInSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, 400)
        
        user_latitude = serializer.validated_data['latitude']
        user_longitude = serializer.validated_data['longitude']
        
        # 先校验时间（预约时间至预约后30分钟内可签到）
        now = timezone.now()
        appointment_datetime = timezone.make_aware(
            timezone.datetime.combine(
                appointment.appointment_date,
                timezone.datetime.strptime(appointment.appointment_time, '%H:%M').time()
            )
        )

        earliest_checkin = appointment_datetime
        latest_checkin = appointment_datetime + timedelta(minutes=30)

        if now < earliest_checkin:
            time_remaining = (earliest_checkin - now).total_seconds() / 60
            return error_response(
                f'签到时间未到，请在预约时间开始后再签到（还需等待 {time_remaining:.0f} 分钟）',
                400
            )

        if now > latest_checkin:
            return error_response(
                '签到时间已过期，签到失败',
                400
            )

        # 再校验医院位置与距离
        hospital = appointment.hospital
        if not hospital.latitude or not hospital.longitude:
            return error_response('医院位置信息不完整，无法签到', 500)

        distance = haversine_distance(
            user_latitude,
            user_longitude,
            hospital.latitude,
            hospital.longitude
        )

        CHECKIN_RADIUS = 500  # 签到半径：500m
        if distance > CHECKIN_RADIUS:
            return error_response(
                f'距离医院过远，当前距离 {distance:.0f}m，需在 {CHECKIN_RADIUS}m 范围内',
                400
            )
        
        # 签到成功
        appointment.status = 'checked-in'
        appointment.checkin_time = now
        appointment.save(update_fields=['status', 'checkin_time', 'updated_at'])
        
        response_data = {
            'appointment_id': appointment.id,
            'status': appointment.status,
            'checkin_time': appointment.checkin_time,
            'distance': f'{distance:.2f}m',
            'message': f'签到成功！距医院 {distance:.0f}m'
        }
        
        return success_response(response_data, '签到成功', 200)
    
    @action(detail=True, methods=['post'], url_path='complete', permission_classes=[IsAuthenticated, IsDoctor])
    def complete(self, request, pk=None):
        """医生端完成预约"""
        appointment = self.get_object()
        # 具体业务逻辑待实现
        return success_response(None, '完成成功')

    @action(detail=True, methods=['get', 'post'], url_path='route')
    def route(self, request, pk=None):
        """获取路线规划所需的位置信息（仅查看路线，不做实时导航）"""
        appointment = self.get_object()

        # 仅允许本人查询
        if appointment.user != request.user:
            return error_response('无权操作该预约', 403)

        # 获取医院位置
        hospital = appointment.hospital
        if not hospital.latitude or not hospital.longitude:
            return error_response('医院位置信息不完整', 500)

        # 可选：获取用户当前位置（用于计算距离）
        # 支持两种传参方式：
        # GET: /route/?latitude=..&longitude=..
        # POST(JSON): { "latitude": .., "longitude": .. }
        if request.method.upper() == 'POST':
            raw_lat = request.data.get('latitude')
            raw_lon = request.data.get('longitude')
        else:
            raw_lat = request.query_params.get('latitude')
            raw_lon = request.query_params.get('longitude')
        user_location = None
        distance_m = None

        if raw_lat is not None and raw_lon is not None:
            # 校验经纬度格式
            coord_ser = CheckInSerializer(data={'latitude': raw_lat, 'longitude': raw_lon})
            if not coord_ser.is_valid():
                return error_response(coord_ser.errors, 400)
            
            user_lat = coord_ser.validated_data['latitude']
            user_lon = coord_ser.validated_data['longitude']
            user_location = {'latitude': user_lat, 'longitude': user_lon}
            
            # 计算距离
            distance_m = haversine_distance(
                user_lat, user_lon,
                hospital.latitude, hospital.longitude
            )

        # 返回位置信息，供前端调用地图API显示路线
        data = {
            'appointment': {
                'id': appointment.id,
                'date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'time': appointment.appointment_time,
                'status': appointment.status
            },
            'hospital': {
                'name': hospital.name,
                'address': hospital.address,
                'latitude': hospital.latitude,
                'longitude': hospital.longitude
            },
            'user_location': user_location,
            'distance_meters': round(distance_m, 2) if distance_m is not None else None,
            'guide': {
                'message': '请在前端调用地图API（如高德JS API）显示从用户位置到医院的路线规划',
                'example': '使用 AMap.Driving.search(起点坐标, 终点坐标) 进行路线规划'
            }
        }

        return success_response(data, '路线信息获取成功', 200)

