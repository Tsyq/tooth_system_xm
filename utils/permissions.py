"""
自定义权限类
"""
from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    """检查是否为医生"""
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'doctor'


class IsOwnerOrDoctor(permissions.BasePermission):
    """检查是否为资源所有者或医生"""
    
    def has_object_permission(self, request, view, obj):
        # 医生可以访问
        if request.user.role == 'doctor':
            return True
        # 资源所有者可以访问
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsAdminDoctor(permissions.BasePermission):
    """检查是否为管理员医生"""
    
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.role == 'doctor'):
            return False
        try:
            return request.user.doctor_profile.is_admin
        except Exception:
            return False


class IsAdminOrAdminDoctor(permissions.BasePermission):
    """管理员(系统)或管理员医生权限"""
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if getattr(user, 'role', None) == 'admin':
            return True
        try:
            return user.role == 'doctor' and user.doctor_profile.is_admin
        except Exception:
            return False


class IsSystemAdmin(permissions.BasePermission):
    """仅允许系统唯一管理员访问"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and getattr(user, 'role', None) == 'admin')

