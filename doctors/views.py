"""
医生视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Doctor, Schedule
from .serializers import DoctorSerializer, ScheduleSerializer
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
        queryset = self.get_queryset()
        
        # 手动实现过滤逻辑（因为DRF默认过滤可能不支持这些字段）
        hospital_id = request.query_params.get('hospital_id')
        if hospital_id:
            try:
                queryset = queryset.filter(hospital_id=int(hospital_id))
            except (ValueError, TypeError):
                pass
        
        specialty = request.query_params.get('specialty')
        if specialty:
            queryset = queryset.filter(specialty=specialty)
        
        # 应用DRF的其他过滤（如果有）
        queryset = self.filter_queryset(queryset)
        
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True, context={'request': request})
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
        
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """获取医生详情"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, context={'request': request})
            return success_response(serializer.data)
        except Doctor.DoesNotExist:
            return error_response('医生不存在', 404)
        except Exception as e:
            return error_response(f'获取医生详情失败: {str(e)}', 500)
    
    @action(detail=False, methods=['put'], permission_classes=[IsAuthenticated, IsDoctor])
    def me(self, request):
        """医生端更新个人信息"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)
        
        serializer = self.get_serializer(doctor, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # 重新序列化以应用to_representation中的头像URL处理
        updated_serializer = self.get_serializer(doctor, context={'request': request})
        return success_response(updated_serializer.data, '更新成功')
    
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
        paginator.page_size = int(request.query_params.get('page_size', 10))
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = RecordSerializer(page, many=True)
            paginated_data = paginator.get_paginated_response(serializer.data)
            # 获取当前页码和每页大小
            current_page = int(request.query_params.get('page', 1))
            page_size = paginator.page_size
            
            # 构建符合前端期望的格式
            response_data = paginated_data.data
            response_data['page'] = current_page
            response_data['page_size'] = page_size
            return success_response(response_data)
        
        serializer = RecordSerializer(queryset, many=True)
        return success_response(serializer.data)
    
    @action(detail=False, methods=['get', 'post'], url_path='schedules', permission_classes=[AllowAny])
    def schedules(self, request):
        """获取或创建排班"""
        if request.method == 'GET':
            """获取排班列表"""
            doctor_id = request.query_params.get('doctor_id')
            hospital_id = request.query_params.get('hospital_id')
            start = request.query_params.get('start')
            end = request.query_params.get('end')
            status_filter = request.query_params.get('status', 'active')
            
            queryset = Schedule.objects.all()
            
            if doctor_id:
                queryset = queryset.filter(doctor_id=doctor_id)
            if hospital_id:
                queryset = queryset.filter(hospital_id=hospital_id)
            if start:
                try:
                    start_date = datetime.strptime(start, '%Y-%m-%d').date()
                    queryset = queryset.filter(date__gte=start_date)
                except ValueError:
                    pass
            if end:
                try:
                    end_date = datetime.strptime(end, '%Y-%m-%d').date()
                    queryset = queryset.filter(date__lte=end_date)
                except ValueError:
                    pass
            if status_filter:
                queryset = queryset.filter(status=status_filter)
            
            # 只返回未来或今天的排班
            today = timezone.now().date()
            queryset = queryset.filter(date__gte=today)
            
            serializer = ScheduleSerializer(queryset.order_by('date', 'start_time'), many=True)
            return success_response(serializer.data)
        
        elif request.method == 'POST':
            """创建排班（需要认证）"""
            if not request.user.is_authenticated:
                return error_response('需要登录', 401)
            
            # 检查是否是医生或管理员
            try:
                doctor = request.user.doctor_profile
                if not doctor.is_admin:
                    return error_response('只有管理员医生可以创建排班', 403)
            except Doctor.DoesNotExist:
                return error_response('只有医生可以创建排班', 403)
            
            serializer = ScheduleSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return success_response(serializer.data, '排班创建成功')
            return error_response(serializer.errors, 400)

