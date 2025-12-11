"""
医生视图
"""
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Doctor
from .serializers import DoctorSerializer
from utils.response import success_response, error_response
from utils.permissions import IsDoctor


class DoctorList(generics.ListAPIView):
    """医生列表视图"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]
    
    def list(self, request, *args, **kwargs):
        """获取医生列表"""
        queryset = self.get_queryset()
        
        # 支持按医院ID过滤
        hospital_id = request.query_params.get('hospital_id')
        if hospital_id:
            queryset = queryset.filter(hospital_id=hospital_id)
        
        # 支持按专科过滤
        specialty = request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty=specialty)
        
        # 支持视图类型（list 或 rank）
        view_type = request.query_params.get('view', 'list')
        if view_type == 'rank':
            # rank 视图按评分和评价数降序排列
            queryset = queryset.order_by('-score', '-reviews')
        
        # 手动分页
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        
        total_count = queryset.count()
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        paginated_data = queryset[start_index:end_index]
        serializer = self.get_serializer(paginated_data, many=True)
        
        response_data = {
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        }
        
        return success_response(response_data)


class DoctorDetail(generics.RetrieveAPIView):
    """医生详情视图"""
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]
    lookup_field = 'pk'
    
    def retrieve(self, request, *args, **kwargs):
        """获取医生详情"""
        try:
            instance = self.get_object()
        except Doctor.DoesNotExist:
            return error_response('医生不存在', 404)
        
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)


class UpdateDoctorProfile(generics.UpdateAPIView):
    """医生端更新个人信息"""
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsDoctor]
    
    def get_object(self):
        """获取当前登录用户的医生信息"""
        try:
            return self.request.user.doctor_profile
        except Doctor.DoesNotExist:
            raise None
    
    def update(self, request, *args, **kwargs):
        """更新个人信息"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)
        
        serializer = self.get_serializer(doctor, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return success_response(serializer.data, '更新成功')
        return error_response(serializer.errors, 400)


class SetDoctorOnlineStatus(APIView):
    """医生端设置在线状态"""
    permission_classes = [IsAuthenticated, IsDoctor]
    
    def post(self, request):
        """设置在线状态"""
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

