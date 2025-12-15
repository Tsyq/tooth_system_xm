"""
预约视图
"""
from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Appointment
from doctors.models import Doctor
from hospitals.models import Hospital
from .serializers import AppointmentSerializer
from utils.response import success_response, error_response
from utils.permissions import IsDoctor


class AppointmentViewSet(viewsets.ModelViewSet):
    """预约视图集"""
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """按角色与查询参数过滤可见预约列表"""
        qs = Appointment.objects.select_related('user', 'doctor', 'hospital').all()

        # 仅普通用户看到自己的预约；医生看到自己的预约；管理员可见全部
        user = self.request.user
        if getattr(user, 'role', 'user') == 'user':
            qs = qs.filter(user=user)
        elif user.role == 'doctor':
            try:
                doctor = user.doctor_profile
                qs = qs.filter(doctor=doctor)
            except Doctor.DoesNotExist:
                qs = qs.none()

        # 按状态过滤（可选）
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)

        return qs.order_by('-appointment_date', '-appointment_time')

    def list(self, request, *args, **kwargs):
        """获取预约列表（手动分页，返回与接口文档一致结构）"""
        queryset = self.get_queryset()

        # 手动分页
        try:
            page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get('page_size', 10))
        except (TypeError, ValueError):
            page_size = 10
        if page <= 0:
            page = 1
        if page_size <= 0:
            page_size = 10

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_qs = queryset[start:end]
        serializer = self.get_serializer(page_qs, many=True)
        return success_response({
            'count': total,
            'page': page,
            'page_size': page_size,
            'results': serializer.data
        })

    def retrieve(self, request, *args, **kwargs):
        """获取预约详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)

    def create(self, request, *args, **kwargs):
        """创建预约：校验冲突、默认患者信息、校验医生与医院关系"""
        user = request.user
        data = request.data.copy()

        # 必填校验
        required_fields = ['doctor_id', 'hospital_id', 'appointment_date', 'appointment_time']
        for f in required_fields:
            if not data.get(f):
                return error_response(f'{f}为必填项', 400)

        # 获取医生与医院并校验归属
        try:
            doctor = Doctor.objects.get(id=data.get('doctor_id'))
        except Doctor.DoesNotExist:
            return error_response('医生不存在', 404)
        try:
            hospital = Hospital.objects.get(id=data.get('hospital_id'))
        except Hospital.DoesNotExist:
            return error_response('医院不存在', 404)
        if doctor.hospital_id != hospital.id:
            return error_response('医生与医院不匹配', 400)

        # 时间冲突校验（同医生、同日同时间不可重复）
        appt_date = data.get('appointment_date')
        appt_time = data.get('appointment_time')
        conflict = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appt_date,
            appointment_time=appt_time,
        ).exists()
        if conflict:
            return error_response('该时间段已被占用', 409)

        # 默认患者信息
        data.setdefault('patient_name', getattr(user, 'name', ''))
        data.setdefault('patient_phone', getattr(user, 'phone', ''))

        # 组装保存
        serializer = self.get_serializer(data={
            'appointment_date': appt_date,
            'appointment_time': appt_time,
            'symptoms': data.get('symptoms'),
            'patient_name': data.get('patient_name'),
            'patient_phone': data.get('patient_phone'),
            'status': 'upcoming',
        })
        serializer.is_valid(raise_exception=False)
        if serializer.errors:
            return error_response(serializer.errors, 400)
        instance = serializer.save(user=user, doctor=doctor, hospital=hospital)
        return success_response(AppointmentSerializer(instance).data, '预约成功')

    def update(self, request, *args, **kwargs):
        """预约改期：仅允许修改日期与时间并校验冲突与状态"""
        appointment = self.get_object()

        if appointment.status in ['cancelled', 'completed']:
            return error_response('当前状态不允许改期', 400)

        new_date = request.data.get('appointment_date', appointment.appointment_date)
        new_time = request.data.get('appointment_time', appointment.appointment_time)

        # 如果无任何变化，直接返回
        if str(new_date) == str(appointment.appointment_date) and str(new_time) == str(appointment.appointment_time):
            return success_response(AppointmentSerializer(appointment).data, '改期成功')

        # 冲突校验（排除自身）
        conflict = Appointment.objects.filter(
            doctor=appointment.doctor,
            appointment_date=new_date,
            appointment_time=new_time,
        ).exclude(id=appointment.id).exists()
        if conflict:
            return error_response('新时间段已被占用', 409)

        appointment.appointment_date = new_date
        appointment.appointment_time = new_time
        appointment.save()
        return success_response(AppointmentSerializer(appointment).data, '改期成功')

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """取消预约：仅可取消未完成/未取消的预约"""
        appointment = self.get_object()
        if appointment.status == 'cancelled':
            return error_response('预约已取消', 400)
        if appointment.status == 'completed':
            return error_response('已完成预约不可取消', 400)

        # 可选：读取取消原因（目前不入库）
        # reason = request.data.get('reason')

        appointment.status = 'cancelled'
        appointment.save()
        return success_response(None, '取消成功')

    @action(detail=True, methods=['post'], url_path='checkin')
    def checkin(self, request, pk=None):
        """预约签到：设置状态为已签到并记录时间"""
        appointment = self.get_object()
        if appointment.status == 'cancelled':
            return error_response('已取消预约不可签到', 400)
        if appointment.status == 'completed':
            return error_response('已完成预约不可签到', 400)

        appointment.status = 'checked-in'
        appointment.checkin_time = timezone.now()
        appointment.save()
        return success_response(None, '签到成功')

    @action(detail=True, methods=['post'], url_path='complete', permission_classes=[IsAuthenticated, IsDoctor])
    def complete(self, request, pk=None):
        """医生端完成预约：仅该预约对应医生可操作"""
        appointment = self.get_object()
        try:
            doctor = request.user.doctor_profile
        except Doctor.DoesNotExist:
            return error_response('医生信息不存在', 404)

        if appointment.doctor_id != doctor.id:
            return error_response('无权限操作该预约', 403)
        if appointment.status == 'cancelled':
            return error_response('已取消预约不可完成', 400)
        if appointment.status == 'completed':
            return error_response('预约已完成', 400)

        appointment.status = 'completed'
        appointment.save()
        return success_response(None, '完成成功')

