"""
文件上传视图
"""
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
import os
import uuid
from utils.response import success_response, error_response


class ImageUploadView(APIView):
    """图片上传视图"""
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        """上传图片，返回可访问URL；可选地更新当前用户的头像字段"""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return error_response('未找到文件，表单键应为 file', 400)

        # 校验文件类型（简单基于内容类型和扩展名）
        allowed_content_types = {'image/jpeg', 'image/png', 'image/gif', 'image/webp'}
        if file_obj.content_type not in allowed_content_types:
            return error_response('不支持的图片类型', 400)

        # 限制大小：5MB
        max_size = 5 * 1024 * 1024
        if file_obj.size > max_size:
            return error_response('文件过大，最大5MB', 400)

        # 构建保存路径：media/uploads/avatars/YYYY/MM/<uuid>.<ext>
        today = timezone.now()
        ext = os.path.splitext(file_obj.name)[1].lower() or '.jpg'
        filename = f"{uuid.uuid4().hex}{ext}"
        relative_dir = os.path.join('uploads', 'avatars', today.strftime('%Y'), today.strftime('%m'))
        relative_path = os.path.join(relative_dir, filename).replace('\\', '/')
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # 保存文件
        saved_path = default_storage.save(relative_path, ContentFile(file_obj.read()))
        media_url = f"{settings.MEDIA_URL}{saved_path}".replace('//', '/').replace(':/', '://')
        
        # 构建完整的绝对 URL（包含协议和域名）
        request_host = request.build_absolute_uri('/').rstrip('/')
        full_url = f"{request_host}{media_url}"

        # 是否更新用户头像
        update_avatar = request.data.get('update_avatar', 'false').lower() in ('true', '1')
        if update_avatar:
            user = request.user
            user.avatar = full_url
            user.save(update_fields=['avatar'])

        return success_response({'url': full_url}, '上传成功')


class FileUploadView(APIView):
    """通用文件上传视图（图片/PDF/文档等）

    - 表单键：file
    - 可选参数：purpose 用途目录，可选 avatars/doctors/hospitals/records/others（默认 others）
    - 返回：文件可访问 URL 及元信息
    """
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    IMAGE_TYPES = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    DOC_TYPES = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt'}
    MAX_SIZE_IMAGE = 5 * 1024 * 1024  # 5MB
    MAX_SIZE_FILE = 10 * 1024 * 1024  # 10MB

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return error_response('未找到文件，表单键应为 file', 400)

        orig_name = file_obj.name or 'unnamed'
        ext = os.path.splitext(orig_name)[1].lower()
        if not ext:
            return error_response('无法识别文件扩展名', 400)

        # 校验扩展名并限制大小
        is_image = ext in self.IMAGE_TYPES
        is_doc = ext in self.DOC_TYPES
        if not (is_image or is_doc):
            return error_response('不支持的文件类型', 400)

        if is_image and file_obj.size > self.MAX_SIZE_IMAGE:
            return error_response('图片过大，最大5MB', 400)
        if is_doc and file_obj.size > self.MAX_SIZE_FILE:
            return error_response('文件过大，最大10MB', 400)

        purpose = (request.data.get('purpose') or 'others').strip().lower()
        if purpose not in {'avatars', 'doctors', 'hospitals', 'records', 'others'}:
            purpose = 'others'

        # 保存路径：media/uploads/{purpose}/YYYY/MM/uuid.ext
        today = timezone.now()
        filename = f"{uuid.uuid4().hex}{ext}"
        relative_dir = os.path.join('uploads', purpose, today.strftime('%Y'), today.strftime('%m'))
        relative_path = os.path.join(relative_dir, filename).replace('\\', '/')
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        saved_path = default_storage.save(relative_path, ContentFile(file_obj.read()))
        media_url = f"{settings.MEDIA_URL}{saved_path}".replace('//', '/').replace(':/', '://')
        
        # 构建完整的绝对 URL（包含协议和域名）
        request_host = request.build_absolute_uri('/').rstrip('/')
        full_url = f"{request_host}{media_url}"

        return success_response({
            'url': full_url,
            'filename': orig_name,
            'ext': ext,
            'size': file_obj.size,
            'purpose': purpose,
        }, '上传成功')
