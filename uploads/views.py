"""
文件上传视图
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from utils.response import success_response, error_response


class ImageUploadView(APIView):
    """图片上传视图"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        """上传图片"""
        # 框架结构，具体实现待补充
        return error_response('图片上传功能待实现', 400)

