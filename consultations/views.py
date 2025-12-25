"""
在线问诊视图
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Consultation, Message
from doctors.models import Doctor
from .serializers import ConsultationSerializer, MessageSerializer
from utils.response import success_response, error_response


class ConsultationViewSet(viewsets.ModelViewSet):
    """问诊会话视图集"""
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """按角色与查询参数过滤可见会话列表"""
        qs = Consultation.objects.select_related('user', 'doctor').all()
        
        # 仅普通用户看到自己的会话；医生看到自己的会话
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
        
        return qs.order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """获取问诊会话列表（手动分页）"""
        queryset = self.get_queryset()
        
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
        """获取问诊会话详情（含消息列表分页）"""
        consultation = self.get_object()
        
        # 消息列表手动分页
        try:
            msg_page = int(request.query_params.get('page', 1))
        except (TypeError, ValueError):
            msg_page = 1
        try:
            msg_page_size = int(request.query_params.get('page_size', 20))
        except (TypeError, ValueError):
            msg_page_size = 20
        if msg_page <= 0:
            msg_page = 1
        if msg_page_size <= 0:
            msg_page_size = 20
        
        messages_qs = consultation.messages.all().order_by('time')  # 按时间正序
        msg_total = messages_qs.count()
        msg_start = (msg_page - 1) * msg_page_size
        msg_end = msg_start + msg_page_size
        messages_page = messages_qs[msg_start:msg_end]
        
        # 返回结构包含会话信息和分页的消息列表
        from doctors.serializers import DoctorSerializer
        return success_response({
            'id': consultation.id,
            'doctor': DoctorSerializer(consultation.doctor).data,
            'status': consultation.status,
            'messages': {
                'count': msg_total,
                'page': msg_page,
                'page_size': msg_page_size,
                'results': MessageSerializer(messages_page, many=True).data
            },
            'created_at': consultation.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    def create(self, request, *args, **kwargs):
        """创建问诊会话：校验医生并可选初始消息"""
        user = request.user
        data = request.data
        
        doctor_id = data.get('doctor_id')
        if not doctor_id:
            return error_response('doctor_id为必填项', 400)
        
        # 获取医生并校验
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return error_response('医生不存在', 404)
        
        # 创建会话
        consultation = Consultation.objects.create(
            user=user,
            doctor=doctor,
            status='active'
        )
        
        # 如果有初始消息，创建首条消息
        initial_message = data.get('initial_message')
        if initial_message:
            Message.objects.create(
                consultation=consultation,
                sender='user',
                text=initial_message
            )
        
        return success_response(ConsultationSerializer(consultation).data, '会话创建成功')
    
    @action(detail=True, methods=['post'], url_path='messages', url_name='send-message')
    def send_message(self, request, pk=None):
        """发送消息：根据当前用户角色判断发送者"""
        consultation = self.get_object()
        
        # 校验会话状态
        if consultation.status == 'closed':
            return error_response('会话已关闭，无法发送消息', 400)
        
        text = request.data.get('text')
        if not text:
            return error_response('text为必填项', 400)
        
        # 判断发送者
        user = request.user
        if user.role == 'doctor':
            try:
                doctor = user.doctor_profile
                if consultation.doctor_id != doctor.id:
                    return error_response('无权限发送该会话消息', 403)
                sender = 'doctor'
            except Doctor.DoesNotExist:
                return error_response('医生信息不存在', 404)
        else:
            if consultation.user_id != user.id:
                return error_response('无权限发送该会话消息', 403)
            sender = 'user'
        
        # 创建消息
        message = Message.objects.create(
            consultation=consultation,
            sender=sender,
            text=text
        )
        
        return success_response(MessageSerializer(message).data, '发送成功')
    
    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """关闭问诊会话"""
        consultation = self.get_object()
        
        if consultation.status == 'closed':
            return error_response('会话已关闭', 400)
        
        consultation.status = 'closed'
        consultation.save()
        return success_response(ConsultationSerializer(consultation).data, '关闭成功')


class MessageViewSet(viewsets.ModelViewSet):
    """消息视图集（主要用于查询，不用于创建）"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']  # 禁用 POST/PUT/DELETE，只能通过 ConsultationViewSet.send_message 创建消息


