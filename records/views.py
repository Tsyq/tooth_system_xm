"""
病历视图
"""
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Record
from .serializers import RecordSerializer
from utils.response import success_response, error_response
from utils.permissions import IsDoctor


class RecordViewSet(viewsets.ModelViewSet):
    """病历视图集"""
    queryset = Record.objects.all()
    serializer_class = RecordSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        """获取病历列表"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return success_response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """获取病历详情"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='rating')
    def rating(self, request, pk=None):
        """评价就诊"""
        record = self.get_object()
        # 具体业务逻辑待实现
        return success_response(None, '评价成功')



