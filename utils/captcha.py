"""
验证码工具函数
"""
from django.core.cache import cache


def verify_captcha(captcha_id, captcha_answer):
    """
    验证验证码
    
    Args:
        captcha_id: 验证码ID
        captcha_answer: 用户输入的验证码答案
    
    Returns:
        bool: 验证是否通过
    """
    if not captcha_id or not captcha_answer:
        return False
    
    # 从缓存中获取验证码
    cached_captcha = cache.get(f'captcha_{captcha_id}')
    
    if cached_captcha is None:
        return False  # 验证码已过期或不存在
    
    # 验证码不区分大小写
    if cached_captcha.lower() == captcha_answer.lower():
        # 验证成功后删除验证码（防止重复使用）
        cache.delete(f'captcha_{captcha_id}')
        return True
    
    return False

