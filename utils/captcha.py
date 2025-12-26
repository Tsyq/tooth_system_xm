"""
验证码工具函数
"""
from django.core.cache import cache


def verify_captcha(captcha_id, captcha_answer):
    """验证验证码，允许短时间内的二次校验并防止并发误删。"""
    if not captcha_id or not captcha_answer:
        return False

    cache_key = f'captcha_{captcha_id}'
    used_key = f'captcha_used_{captcha_id}'

    cached_captcha = cache.get(cache_key)
    # 并发场景：验证码键被删除但标记存在，仍允许通过
    if cached_captcha is None:
        return bool(cache.get(used_key, False))

    if cached_captcha.lower() == str(captcha_answer).lower():
        # 记录已使用标记，短暂容忍二次验证，避免前后端重复校验导致误判
        cache.set(used_key, True, timeout=15)
        return True

    return False

