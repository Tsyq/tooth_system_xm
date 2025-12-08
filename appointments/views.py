"""
预约视图
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Appointment
from .serializers import AppointmentSerializer
from utils.response import success_response, error_response
from utils.permissions import IsDoctor


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
        """预约签到"""
        appointment = self.get_object()
        # 具体业务逻辑待实现
        return success_response(None, '签到成功')
    
    @action(detail=True, methods=['post'], url_path='complete', permission_classes=[IsAuthenticated, IsDoctor])
    def complete(self, request, pk=None):
        """医生端完成预约"""
        appointment = self.get_object()
        # 具体业务逻辑待实现
        return success_response(None, '完成成功')

