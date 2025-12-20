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
from utils.permissions import IsDoctor, IsAdminOrAdminDoctor, IsSystemAdmin
from django.utils import timezone
from rest_framework.exceptions import NotFound


# 审核状态与用户状态映射
AUDIT_TO_USER_STATUS = {
    'pending': 'pending',
    'approved': 'active',
    'rejected': 'inactive',
}

DOCTOR_NOT_FOUND = '医生不存在'
DOCTOR_INFO_NOT_FOUND = '医生信息不存在'


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
        """获取医生详情（含评价列表）"""
        try:
            instance = self.get_object()
        except Doctor.DoesNotExist:
            return error_response(DOCTOR_NOT_FOUND, 404)
        
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # 获取该医生的评价列表（已评价的病历）
        from records.models import Record
        from .review_serializers import DoctorReviewSerializer
        
        reviews = Record.objects.filter(
            doctor=instance,
            rated=True
        ).select_related('user').order_by('-created_at')
        
        # 分页处理评价
        page = int(request.query_params.get('review_page', 1))
        page_size = int(request.query_params.get('review_page_size', 10))
        total_reviews = reviews.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_reviews = reviews[start:end]
        
        review_serializer = DoctorReviewSerializer(page_reviews, many=True)
        
        data['reviews_data'] = {
            'count': total_reviews,
            'page': page,
            'page_size': page_size,
            'results': review_serializer.data
        }
        
        return success_response(data)


class UpdateDoctorProfile(generics.UpdateAPIView):
    """医生端更新个人信息"""
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsDoctor]
    
    def get_object(self):
        """获取当前登录用户的医生信息"""
        try:
            return self.request.user.doctor_profile
        except Doctor.DoesNotExist:
            raise NotFound(DOCTOR_INFO_NOT_FOUND)
    
    def update(self, request, *args, **kwargs):
        """更新个人信息"""
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response(DOCTOR_INFO_NOT_FOUND, 404)
        
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
            return error_response(DOCTOR_INFO_NOT_FOUND, 404)
        
        is_online = request.data.get('is_online')
        if is_online is None:
            return error_response('is_online参数必填', 400)
        
        doctor.is_online = bool(is_online)
        doctor.save()
        return success_response({'is_online': doctor.is_online}, '状态更新成功')


class DoctorPatientRecordsView(APIView):
    """医生端获取患者病历列表"""
    permission_classes = [IsAuthenticated, IsDoctor]
    
    def get(self, request):
        """获取患者病历列表"""
        from records.models import Record
        from records.serializers import RecordSerializer
        
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)
        
        # 获取该医生创建的所有病历
        queryset = Record.objects.filter(doctor=doctor)
        
        # 筛选参数
        patient_id = request.query_params.get('patient_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        patient_name = request.query_params.get('patient_name')
        doctor_name = request.query_params.get('doctor_name')
        
        if patient_id:
            queryset = queryset.filter(user_id=patient_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)
        if patient_name:
            queryset = queryset.filter(user__name__icontains=patient_name)
        if doctor_name:
            queryset = queryset.filter(doctor__name__icontains=doctor_name)
        
        queryset = queryset.select_related('user', 'doctor', 'hospital', 'appointment')
        
        # 分页参数
        page = request.query_params.get('page', 1)
        page_size = request.query_params.get('page_size', 10)
        
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
        serializer = RecordSerializer(records, many=True)
        
        return success_response(
            data={
                'count': total_count,
                'page': page,
                'page_size': page_size,
                'results': serializer.data
            },
            message='获取成功'
        )


class DoctorAuditList(generics.ListAPIView):
    """医生审核列表（管理员视角）"""
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    queryset = Doctor.objects.all()

    def list(self, request, *args, **kwargs):
        status_q = request.query_params.get('status', 'pending')
        qs = self.get_queryset()
        if status_q in ['pending', 'approved', 'rejected']:
            qs = qs.filter(audit_status=status_q)

        # 支持按专科/医院过滤
        hospital_id = request.query_params.get('hospital_id')
        specialty = request.query_params.get('specialty')
        if hospital_id:
            qs = qs.filter(hospital_id=hospital_id)
        if specialty:
            qs = qs.filter(specialty=specialty)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        total_count = qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        serializer = self.get_serializer(qs[start:end], many=True)
        return success_response({
            'count': total_count,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })


class DoctorAuditApprove(APIView):
    """审核通过某位医生"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request, pk):
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return error_response(DOCTOR_NOT_FOUND, 404)
        if doctor.audit_status == 'approved':
            return success_response(DoctorSerializer(doctor).data, '已是通过状态')
        doctor.audit_status = 'approved'
        doctor.audited_at = timezone.now()
        doctor.rejected_reason = ''
        doctor.save()
        # 同步医生用户状态为激活
        try:
            user = doctor.user
            user.role = 'doctor'
            user.status = AUDIT_TO_USER_STATUS['approved']
            user.is_active = True
            user.save(update_fields=['role', 'status', 'is_active', 'updated_at'])
        except Exception:
            pass
        return success_response(DoctorSerializer(doctor).data, '审核通过')


class DoctorAuditReject(APIView):
    """审核拒绝某位医生"""
    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request, pk):
        reason = request.data.get('reason', '')
        try:
            doctor = Doctor.objects.get(pk=pk)
        except Doctor.DoesNotExist:
            return error_response(DOCTOR_NOT_FOUND, 404)
        doctor.audit_status = 'rejected'
        doctor.rejected_reason = reason
        doctor.audited_at = timezone.now()
        doctor.save()
        # 将医生用户标记为禁用
        try:
            user = doctor.user
            user.role = 'doctor'
            user.status = AUDIT_TO_USER_STATUS['rejected']
            user.is_active = False
            user.save(update_fields=['role', 'status', 'is_active', 'updated_at'])
        except Exception:
            pass
        return success_response(DoctorSerializer(doctor).data, '审核拒绝')


class DoctorApply(generics.CreateAPIView):
    """医生申请入驻（提交/更新申请资料并进入待审核）。无需登录，通过手机号定位账号。"""
    serializer_class = DoctorSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        from django.contrib.auth import get_user_model
        data = request.data.copy()

        # 需要手机号以定位用户
        phone = data.get('phone')
        if not phone:
            return error_response('phone为必填项', 400)

        # 必填：姓名/职称/专科；医院由管理员分配（可选）
        for field in ['name', 'title', 'specialty']:
            if not data.get(field):
                return error_response(f'{field}为必填项', 400)

        user = get_user_model().objects.filter(phone=phone).first()
        if not user:
            return error_response('用户不存在', 404)

        # 若为普通用户，切换为医生角色；若已是医生，继续更新资料
        doctor = getattr(user, 'doctor_profile', None)
        try:
            if doctor is None:
                doctor = Doctor.objects.create(
                    user=user,
                    name=data.get('name'),
                    title=data.get('title'),
                    specialty=data.get('specialty'),
                    avatar=data.get('avatar') or None,
                    introduction=data.get('introduction') or '',
                    education=data.get('education') or '',
                    experience=data.get('experience') or '',
                    hospital_id=data.get('hospital_id') or data.get('hospital') or None,
                    audit_status='pending'
                )
            else:
                doctor.name = data.get('name') or doctor.name
                doctor.title = data.get('title') or doctor.title
                doctor.specialty = data.get('specialty') or doctor.specialty
                if 'avatar' in data:
                    doctor.avatar = data.get('avatar') or None
                if 'introduction' in data:
                    doctor.introduction = data.get('introduction') or ''
                if 'education' in data:
                    doctor.education = data.get('education') or ''
                if 'experience' in data:
                    doctor.experience = data.get('experience') or ''
                if data.get('hospital_id') or data.get('hospital'):
                    doctor.hospital_id = data.get('hospital_id') or data.get('hospital')
                doctor.audit_status = 'pending'
                doctor.rejected_reason = ''
                doctor.audited_at = None
                doctor.save()
        except Exception as e:
            return error_response(f'提交失败: {e}', 400)

        # 同步用户角色/状态为待审核并禁用登录
        try:
            user.role = 'doctor'
            user.status = AUDIT_TO_USER_STATUS['pending']
            user.is_active = False
            user.save(update_fields=['role', 'status', 'is_active', 'updated_at'])
        except Exception:
            pass

        return success_response(DoctorSerializer(doctor).data, '申请已提交')

