"""
病历视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from .models import Record
from .serializers import (
    RecordSerializer,
    RecordCreateSerializer,
    RecordUpdateSerializer,
    RecordRatingSerializer
)
from utils.response import success_response, error_response
from utils.permissions import IsDoctor, IsOwnerOrDoctor


class RecordViewSet(viewsets.ModelViewSet):
    """病历视图集"""
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """根据操作类型返回不同的序列化器"""
        if self.action == 'create':
            return RecordCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return RecordUpdateSerializer
        elif self.action == 'rating':
            return RecordRatingSerializer
        return RecordSerializer
    
    def get_permissions(self):
        """根据操作类型返回不同的权限"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            # 只有医生可以创建、更新、删除病历
            return [IsAuthenticated(), IsDoctor()]
        elif self.action == 'rating':
            # 只有患者本人可以评价
            return [IsAuthenticated()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """根据用户角色过滤病历"""
        user = self.request.user
        queryset = Record.objects.all()
        
        # 普通用户只能看自己的病历
        if user.role == 'user':
            queryset = queryset.filter(user=user)
        # 医生可以看自己创建的病历
        elif user.role == 'doctor':
            try:
                doctor = user.doctor_profile
                queryset = queryset.filter(doctor=doctor)
            except:
                queryset = Record.objects.none()
        # 管理员可以看所有
        
        # 应用筛选参数
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        patient_name = self.request.query_params.get('patient_name')
        doctor_name = self.request.query_params.get('doctor_name')
        
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if patient_name:
            queryset = queryset.filter(user__name__icontains=patient_name)
        if doctor_name:
            queryset = queryset.filter(doctor__name__icontains=doctor_name)
        
        return queryset.select_related('user', 'doctor', 'hospital', 'appointment')
    
    def list(self, request, *args, **kwargs):
        """获取病历列表"""
        queryset = self.filter_queryset(self.get_queryset())
        
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
        
        try:
            page = int(page)
            page_size = int(page_size)
        except ValueError:
            page = 1
            page_size = 10
        
        # 计算分页
        total_count = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        
        records = queryset[start:end]
        serializer = self.get_serializer(records, many=True)
        
        return success_response(
            data={
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'results': serializer.data
            },
            message='获取成功'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """获取病历详情"""
        try:
            instance = self.get_object()
        except:
            return error_response(message='病历不存在', code=404)
        
        # 检查权限：只有患者本人、创建病历的医生或管理员可以查看
        user = request.user
        if user.role == 'user' and instance.user != user:
            return error_response(message='无权限查看该病历', code=403)
        elif user.role == 'doctor':
            try:
                if instance.doctor != user.doctor_profile:
                    return error_response(message='无权限查看该病历', code=403)
            except:
                return error_response(message='无权限查看该病历', code=403)
        
        serializer = self.get_serializer(instance)
        return success_response(data=serializer.data, message='获取成功')
    
    def create(self, request, *args, **kwargs):
        """医生端创建病历"""
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            record = serializer.save()
            
            # 返回完整的病历数据
            output_serializer = RecordSerializer(record)
            return success_response(
                data=output_serializer.data,
                message='创建成功',
                code=200
            )
        except Exception as e:
            return error_response(message=str(e), code=400)
    
    def update(self, request, *args, **kwargs):
        """医生端更新病历"""
        try:
            instance = self.get_object()
        except:
            return error_response(message='病历不存在', code=404)
        
        # 检查权限：只有创建病历的医生可以更新
        try:
            if instance.doctor != request.user.doctor_profile:
                return error_response(message='无权限更新该病历', code=403)
        except:
            return error_response(message='无权限更新该病历', code=403)
        
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        
        try:
            serializer.is_valid(raise_exception=True)
            record = serializer.save()
            
            # 返回完整的病历数据
            output_serializer = RecordSerializer(record)
            return success_response(
                data=output_serializer.data,
                message='更新成功',
                code=200
            )
        except Exception as e:
            return error_response(message=str(e), code=400)
    
    def destroy(self, request, *args, **kwargs):
        """删除病历（医生端）"""
        try:
            instance = self.get_object()
        except:
            return error_response(message='病历不存在', code=404)
        
        # 检查权限：只有创建病历的医生可以删除
        try:
            if instance.doctor != request.user.doctor_profile:
                return error_response(message='无权限删除该病历', code=403)
        except:
            return error_response(message='无权限删除该病历', code=403)
        
        instance.delete()
        return success_response(data=None, message='删除成功')
    
    @action(detail=True, methods=['post'], url_path='rating')
    def rating(self, request, pk=None):
        """评价就诊"""
        try:
            record = self.get_object()
        except:
            return error_response(message='病历不存在', code=404)
        
        # 检查权限：只有患者本人可以评价
        if record.user != request.user:
            return error_response(message='只能评价自己的病历', code=403)
        
        # 检查是否已评价
        if record.rated:
            return error_response(message='该病历已评价过', code=400)
        
        serializer = RecordRatingSerializer(
            data=request.data,
            context={'record': record}
        )
        
        try:
            serializer.is_valid(raise_exception=True)
            
            # 更新病历评价信息
            record.rating = serializer.validated_data['rating']
            record.comment = serializer.validated_data.get('comment', '')
            record.rated = True
            record.save()
            
            # 更新医生评分
            doctor = record.doctor
            total_reviews = doctor.reviews + 1
            new_score = (doctor.score * doctor.reviews + record.rating) / total_reviews
            doctor.score = round(new_score, 1)
            doctor.reviews = total_reviews
            doctor.save()
            
            return success_response(data=None, message='评价成功')
        except Exception as e:
            return error_response(message=str(e), code=400)



