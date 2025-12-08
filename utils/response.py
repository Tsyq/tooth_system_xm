"""
统一响应格式工具
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data=None, message='success', code=200):
    """成功响应"""
    return Response({
        'code': code,
        'message': message,
        'data': data
    }, status=status.HTTP_200_OK)


def error_response(message='error', code=400, data=None):
    """错误响应"""
    return Response({
        'code': code,
        'message': message,
        'data': data
    }, status=status.HTTP_200_OK)  # 注意：业务错误也返回200，通过code区分


def custom_exception_handler(exc, context):
    """自定义异常处理器"""
    from rest_framework.views import exception_handler
    
    response = exception_handler(exc, context)
    
    if response is not None:
        custom_response_data = {
            'code': response.status_code,
            'message': str(exc),
            'data': None
        }
        response.data = custom_response_data
    
    return response

