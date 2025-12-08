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
    
    def list(self, request, *args, **kwargs):
        """获取问诊会话列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """获取问诊会话详情（含消息列表）"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='messages')
    def send_message(self, request, pk=None):
        """发送消息"""
        consultation = self.get_object()
        # 具体业务逻辑待实现
        return success_response(None, '发送成功')
    
    @action(detail=True, methods=['post'], url_path='close')
    def close(self, request, pk=None):
        """关闭问诊会话"""
        consultation = self.get_object()
        consultation.status = 'closed'
        consultation.save()
        return success_response(None, '关闭成功')


class MessageViewSet(viewsets.ModelViewSet):
    """消息视图集"""
    queryset = Message.objects.all()
    serializer_class = MessageSerializer
    permission_classes = [IsAuthenticated]

