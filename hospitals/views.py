"""
医院视图
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from math import radians, sin, cos, sqrt, atan2
from .models import Hospital
from .serializers import HospitalSerializer
from utils.response import success_response, error_response
from math import radians, sin, asin, sqrt
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView
from django.db.models import F
from .models import Hospital
from .serializers import HospitalSerializer
from utils.response import success_response, error_response
from utils.permissions import IsSystemAdmin
from doctors.models import Doctor
from appointments.serializers import CheckInSerializer
import math


class HospitalList(generics.ListAPIView):
    """获取医院列表（支持 filter=all|near|frequent，及分页）"""
    serializer_class = HospitalSerializer
    permission_classes = [AllowAny]
    # 不使用 DRF 的分页器文件，采用简单的手动分页实现

    def haversine(self, lat1, lon1, lat2, lon2):
        """计算两点之间的距离（公里）"""
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + __import__('math').cos(lat1) * __import__('math').cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        r = 6371
        return c * r

    def get_queryset(self):
        filter_type = self.request.query_params.get('filter', 'all')
        qs = Hospital.objects.all()
        if filter_type == 'near':
            qs = qs.filter(latitude__isnull=False, longitude__isnull=False)
        elif filter_type == 'frequent':
            # 使用预约次数排序代表常用医院
            qs = qs.order_by('-appointment_count')
        else:
            qs = qs.order_by('-appointment_count')
        return qs

    def list(self, request, *args, **kwargs):
        """获取医院列表"""
        queryset = self.filter_queryset(self.get_queryset())
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
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='route', permission_classes=[IsAuthenticated])
    def route(self, request, pk=None):
        """路线规划：获取医院位置信息和距离计算"""
        hospital = self.get_object()
        
        # 获取用户当前位置（可选）
        user_latitude = request.data.get('latitude')
        user_longitude = request.data.get('longitude')
        
        # 构建响应数据
        response_data = {
            'hospital': {
                'id': hospital.id,
                'name': hospital.name,
                'address': hospital.address,
                'latitude': hospital.latitude,
                'longitude': hospital.longitude,
                'phone': hospital.phone,
            }
        }
        
        # 如果提供了用户位置，计算距离
        if user_latitude is not None and user_longitude is not None:
            try:
                user_lat = float(user_latitude)
                user_lng = float(user_longitude)
                
                if hospital.latitude and hospital.longitude:
                    # 使用 Haversine 公式计算距离（单位：米）
                    R = 6371000  # 地球半径（米）
                    lat1 = radians(hospital.latitude)
                    lat2 = radians(user_lat)
                    delta_lat = radians(user_lat - hospital.latitude)
                    delta_lon = radians(user_lng - hospital.longitude)
                    
                    a = sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2
                    c = 2 * atan2(sqrt(a), sqrt(1 - a))
                    distance = R * c  # 距离（米）
                    distance_km = distance / 1000
                    
                    response_data['distance'] = distance
                    response_data['distance_km'] = round(distance_km, 2)
                    response_data['user_location'] = {
                        'latitude': user_lat,
                        'longitude': user_lng
                    }
                    
                    # 添加路线规划建议
                    # 高德地图路线规划距离限制：
                    # - 步行：通常限制在50公里以内
                    # - 骑行：通常限制在100公里以内
                    # - 驾车：通常限制在500公里以内
                    # - 公交：通常限制在100公里以内
                    route_suggestions = []
                    
                    if distance_km > 500:
                        route_suggestions.append({
                            'mode': 'driving',
                            'message': '距离较远（超过500公里），建议使用驾车路线规划'
                        })
                    elif distance_km > 100:
                        route_suggestions.append({
                            'mode': 'driving',
                            'message': '距离较远（超过100公里），建议使用驾车路线规划'
                        })
                    elif distance_km > 50:
                        route_suggestions.append({
                            'mode': 'driving',
                            'message': '距离较远（超过50公里），步行和骑行可能无法规划，建议使用驾车或公交'
                        })
                    
                    if route_suggestions:
                        response_data['route_suggestions'] = route_suggestions
                        response_data['warning'] = f'您距离医院约{round(distance_km, 1)}公里，部分路线规划方式可能无法使用，建议选择驾车或公交方式'
                else:
                    response_data['distance'] = None
                    response_data['warning'] = '医院未设置位置信息，无法计算距离'
            except (ValueError, TypeError):
                return error_response('地理位置信息格式错误', 400)
        else:
            response_data['distance'] = None
            response_data['info'] = '未提供用户位置，无法计算距离'
        
        return success_response(response_data, '路线规划信息获取成功')


class HospitalRoute(APIView):
    """基于医院ID的路线信息接口：返回医院位置、用户位置、两者距离（米）"""
    permission_classes = [AllowAny]

    def _haversine_distance(self, lat1, lon1, lat2, lon2):
        R = 6371000
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        return R * c

    def get(self, request, pk: int):
        return self._handle(request, pk)

    def post(self, request, pk: int):
        return self._handle(request, pk)

    def _handle(self, request, pk: int):
        try:
            hospital = Hospital.objects.get(pk=pk)
        except Hospital.DoesNotExist:
            return error_response('医院不存在', 404)

        if hospital.latitude is None or hospital.longitude is None:
            return error_response('医院位置信息不完整', 500)

        if request.method.upper() == 'POST':
            raw_lat = request.data.get('latitude')
            raw_lon = request.data.get('longitude')
        else:
            raw_lat = request.query_params.get('latitude')
            raw_lon = request.query_params.get('longitude')

        user_location = None
        distance_m = None

        if raw_lat is not None and raw_lon is not None:
            coord_ser = CheckInSerializer(data={'latitude': raw_lat, 'longitude': raw_lon})
            if not coord_ser.is_valid():
                return error_response(coord_ser.errors, 400)

            user_lat = coord_ser.validated_data['latitude']
            user_lon = coord_ser.validated_data['longitude']
            user_location = {'latitude': user_lat, 'longitude': user_lon}

            distance_m = self._haversine_distance(
                user_lat, user_lon, hospital.latitude, hospital.longitude
            )

        data = {
            'hospital': {
                'id': hospital.id,
                'name': hospital.name,
                'address': hospital.address,
                'latitude': hospital.latitude,
                'longitude': hospital.longitude,
            },
            'user_location': user_location,
            'distance_meters': round(distance_m, 2) if distance_m is not None else None,
            'guide': {
                'message': '请在前端调用地图API（如高德JS API）显示路线',
                'example': 'AMap.Driving.search([userLon,userLat],[hosLon,hosLat])'
            }
        }

        return success_response(data, '路线信息获取成功', 200)

class AdminHospitalCreate(generics.CreateAPIView):
    """管理员添加医院"""
    serializer_class = HospitalSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return error_response(serializer.errors, 400)
        hospital = serializer.save()
        return success_response(HospitalSerializer(hospital).data, '创建成功')


class AssignDoctorHospital(APIView):
    """管理员为医生分配或变更医院"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request, *args, **kwargs):
        doctor_id = request.data.get('doctor_id')
        hospital_id = request.data.get('hospital_id')  # 允许为空表示取消分配
        if not doctor_id:
            return error_response('doctor_id必填', 400)
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return error_response('医生不存在', 404)

        if hospital_id:
            try:
                hospital = Hospital.objects.get(id=hospital_id)
            except Hospital.DoesNotExist:
                return error_response('医院不存在', 404)
            doctor.hospital = hospital
        else:
            doctor.hospital = None
        doctor.save(update_fields=['hospital'])
        from doctors.serializers import DoctorSerializer
        return success_response(DoctorSerializer(doctor).data, '分配成功')

