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



