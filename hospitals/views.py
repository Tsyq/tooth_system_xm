"""
医院视图
"""
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
        queryset = self.get_queryset()
        filter_type = request.query_params.get('filter', 'all')

        # 处理附近筛选（按距离排序）
        if filter_type == 'near':
            try:
                user_lat = float(request.query_params.get('latitude'))
                user_lon = float(request.query_params.get('longitude'))
            except (TypeError, ValueError):
                return error_response('latitude和longitude参数必须为有效的浮点数', code=400)

            hospitals_with_distance = []
            for h in queryset:
                if h.latitude is not None and h.longitude is not None:
                    dist = self.haversine(user_lat, user_lon, h.latitude, h.longitude)
                    hospitals_with_distance.append((h, dist))
            # 按距离排序（由近到远）
            hospitals_with_distance.sort(key=lambda x: x[1])
            # 为后续非 nearby 分支保留基于 id 的 queryset（如果需要）
            hospitals_ids = [h[0].id for h in hospitals_with_distance]
            queryset = Hospital.objects.filter(id__in=hospitals_ids)

        # 手动分页：从 query params 读取 page 和 page_size
        try:
            page_num = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page_num = 1

        try:
            page_size = request.query_params.get('page_size')
            page_size = int(page_size) if page_size is not None and page_size != '' else None
        except (TypeError, ValueError):
            page_size = None

        if filter_type == 'near':
            # hospitals_with_distance 已按距离排序，使用列表切片保证顺序，并在结果中加入距离信息（公里，保留两位小数）
            total = len(hospitals_with_distance)
            if page_size is None or page_size <= 0:
                page_size = total if total > 0 else 0
            if page_num <= 0:
                page_num = 1
            start = (page_num - 1) * page_size
            end = start + page_size
            page_items = hospitals_with_distance[start:end]  # 切片后仍保持 (hospital, distance)
            hospitals = [item[0] for item in page_items]
            serializer = self.get_serializer(hospitals, many=True)
            results = serializer.data
            # 将距离信息插入对应序列化对象，按相同顺序
            for idx, item in enumerate(page_items):
                _, dist_km = item
                # 保留两位小数
                try:
                    results[idx]['distance_km'] = round(dist_km, 2)
                except Exception:
                    # 兼容性保护：如果 serializer 返回不包含 dict，则跳过
                    pass

            return success_response({
                'count': total,
                'page': page_num,
                'page_size': page_size,
                'results': results
            })

        # 非 nearby 的普通分页（在数据库层切片）
        total = queryset.count()
        if page_size is None or page_size <= 0:
            page_size = 9
        if page_num <= 0:
            page_num = 1
        start = (page_num - 1) * page_size
        end = start + page_size
        page_qs = queryset[start:end]
        serializer = self.get_serializer(page_qs, many=True)
        return success_response({
            'count': total,
            'page': page_num,
            'page_size': page_size,
            'results': serializer.data
        })


class HospitalDetail(generics.RetrieveAPIView):
    """获取医院详情"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [AllowAny]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)


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

