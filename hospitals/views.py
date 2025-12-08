"""
医院视图
"""
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Hospital
from .serializers import HospitalSerializer
from utils.response import success_response


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
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """获取医院详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

