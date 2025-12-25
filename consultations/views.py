"""
在线问诊视图
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Consultation, Message
from .serializers import ConsultationSerializer, MessageSerializer
from utils.response import success_response, error_response


class ConsultationViewSet(viewsets.ModelViewSet):
    """问诊会话视图集"""
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_serializer(self, *args, **kwargs):
        """重写get_serializer，对于send_message action不返回序列化器"""
        if self.action == 'send_message':
            # send_message action 不使用序列化器，直接返回None
            return None
        return super().get_serializer(*args, **kwargs)
    
    def list(self, request, *args, **kwargs):
        """获取问诊会话列表"""
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
        """获取问诊会话详情（含消息列表）"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='messages', url_name='send-message')
    def send_message(self, request, pk=None):
        """发送消息 - 完全绕过序列化器验证"""
        # 直接获取请求数据，不经过序列化器验证
        # 使用 request.data 而不是序列化器
        text = request.data.get('text', '').strip()
        if not text:
            return error_response('消息内容不能为空', 400)
        
        consultation = self.get_object()
        
        # 1. 验证用户权限：只能在自己的问诊会话中发送消息
        if consultation.user != request.user:
            # 检查是否是医生
            from utils.permissions import IsDoctor
            is_doctor = IsDoctor().has_permission(request, self)
            if not is_doctor or consultation.doctor.user != request.user:
                return error_response('只能在自己的问诊会话中发送消息', 403)
        
        # 2. 验证会话状态：只能向活跃的会话发送消息
        if consultation.status != 'active':
            return error_response('该问诊会话已关闭，无法发送消息', 400)
        
        # 3. 确定发送者身份
        if consultation.user == request.user:
            sender = 'user'
        else:
            # 应该是医生
            sender = 'doctor'
        
        # 4. 创建消息（直接使用 Model.objects.create，不经过序列化器验证）
        message = Message.objects.create(
            consultation=consultation,
            sender=sender,
            text=text
        )
        
        # 5. 返回创建的消息（直接构建字典，避免序列化器验证问题）
        message_data = {
            'id': message.id,
            'consultation_id': consultation.id,
            'sender': message.sender,
            'text': message.text,
            'time': message.time.isoformat() if message.time else None,
            'created_at': message.created_at.isoformat() if message.created_at else None,
        }
        return success_response(message_data, '发送成功')
    
    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """关闭问诊会话"""
        consultation = self.get_object()
        consultation.status = 'closed'
        consultation.save()
        return success_response(None, '关闭成功')


class MessageViewSet(viewsets.ModelViewSet):
    """消息视图集（主要用于查询，不用于创建）"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'head', 'options']  # 禁用 POST/PUT/DELETE，只能通过 ConsultationViewSet.send_message 创建消息

