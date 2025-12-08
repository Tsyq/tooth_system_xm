"""
AI问询视图
"""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Inquiry
from .serializers import InquirySerializer
from utils.response import success_response


class InquiryViewSet(viewsets.ModelViewSet):
    """AI问询视图集"""
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    permission_classes = [IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        """创建AI问询"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(serializer.data, '问询成功')

