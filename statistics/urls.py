"""
统计数据URL配置
"""
from django.urls import path
from .views import HomeStatisticsView

urlpatterns = [
    path('home/', HomeStatisticsView.as_view(), name='home_statistics'),
    # GET /statistics/home/ - 获取首页统计数据
]

