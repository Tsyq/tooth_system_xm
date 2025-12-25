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


class HospitalViewSet(viewsets.ModelViewSet):
    """医院视图集"""
    queryset = Hospital.objects.all()
    serializer_class = HospitalSerializer
    permission_classes = [AllowAny]  # 医院列表公开访问
    
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
        """获取医院详情"""
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

