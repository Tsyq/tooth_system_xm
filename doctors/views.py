"""
医生视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Doctor
from .serializers import DoctorSerializer
from utils.response import success_response, error_response
from utils.permissions import IsDoctor
from records.models import Record
from records.serializers import RecordSerializer


class DoctorViewSet(viewsets.ModelViewSet):
    """医生视图集"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        """获取医生列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """获取医生详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated, IsDoctor])
    def me(self, request):
        """医生端更新个人信息"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)
        
        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return success_response(serializer.data, '更新成功')
    
    @action(detail=False, methods=['post'], url_path='me/online-status', permission_classes=[IsAuthenticated, IsDoctor])
    def online_status(self, request):
        """医生端设置在线状态"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)
        
        is_online = request.data.get('is_online')
        if is_online is None:
            return error_response('is_online参数必填', 400)
        
        doctor.is_online = bool(is_online)
        doctor.save()
        return success_response({'is_online': doctor.is_online}, '状态更新成功')
    
    @action(detail=False, methods=['get'], url_path='patients/records', permission_classes=[IsAuthenticated, IsDoctor])
    def patient_records(self, request):
        """医生端获取患者病历列表"""
        from rest_framework.pagination import PageNumberPagination
        
        queryset = Record.objects.all()
        # 具体过滤逻辑待实现
        
        # 手动分页
        paginator = PageNumberPagination()
        paginator.page_size = request.query_params.get('page_size', 10)
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = RecordSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        
        serializer = RecordSerializer(queryset, many=True)
        return success_response(serializer.data)

