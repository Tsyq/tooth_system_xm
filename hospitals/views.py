"""
医院视图
"""
from math import radians, sin, asin, sqrt
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.db.models import F
from .models import Hospital
from .serializers import HospitalSerializer
from utils.response import success_response, error_response


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
            # 使用 review_count 排序以代表常用医院
            qs = qs.order_by('-review_count', '-rating')
        else:
            qs = qs.order_by('-rating', '-review_count')
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
            hospitals_with_distance.sort(key=lambda x: x[1])
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
            # hospitals_with_distance 已按距离排序，使用列表切片保证顺序
            total = len(hospitals_with_distance)
            if page_size is None or page_size <= 0:
                page_size = total if total > 0 else 0
            if page_num <= 0:
                page_num = 1
            start = (page_num - 1) * page_size
            end = start + page_size
            page_list = [h[0] for h in hospitals_with_distance][start:end]
            serializer = self.get_serializer(page_list, many=True)
            return success_response({
                'count': total,
                'page': page_num,
                'page_size': page_size,
                'results': serializer.data
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

