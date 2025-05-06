# data_pipelines/workers/__init__.py
from .fetch_naver_news import NaverNewsCollector
from .fetch_naver_news_api import NaverNewsAPIClient

__all__ = ['NaverNewsCollector', 'NaverNewsAPIClient'] 