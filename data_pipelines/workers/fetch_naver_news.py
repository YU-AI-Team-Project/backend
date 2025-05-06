# data_pipelines/workers/fetch_naver_news.py
import os
import time
import datetime
import logging
import json
import random
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional, Tuple

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 상수 설정
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
}

# 1일 기준 뉴스 수집 (오늘 = 0, 어제 = 1, ...)
DEFAULT_DAYS_AGO = 0

# 주식 관련 키워드 (예시)
STOCK_KEYWORDS = [
    '주식', '증시', '코스피', '코스닥', '나스닥', '다우', 'S&P500', 
    '금융시장', '애플', '테슬라', '삼성전자', 'LG에너지솔루션',
    '투자', '주가', '실적', '배당', '테크주', '금리', '연준', 'FED'
]

class NaverNewsCollector:
    """네이버 뉴스 수집기"""
    
    def __init__(self, keywords: List[str] = None, days_ago: int = DEFAULT_DAYS_AGO):
        """
        초기화
        
        Args:
            keywords: 검색할 키워드 목록 (기본: 주식 관련 키워드)
            days_ago: 몇 일 전 뉴스를 수집할지 (기본: 오늘)
        """
        self.keywords = keywords or STOCK_KEYWORDS
        self.days_ago = days_ago
        
        # 날짜 설정
        self.now = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        self.date_str = self.now.strftime('%Y.%m.%d')
    
    def get_news_list(self, keyword: str, page: int = 1) -> Tuple[List[Dict[str, str]], bool]:
        """
        네이버 뉴스 목록 페이지에서 뉴스 링크 및 기본 정보 수집
        
        Args:
            keyword: 검색 키워드
            page: 페이지 번호
            
        Returns:
            Tuple[List[Dict[str, str]], bool]: 뉴스 목록과 다음 페이지 존재 여부
        """
        news_list = []
        
        # 네이버 뉴스 검색 URL
        url = (
            f"https://search.naver.com/search.naver?where=news"
            f"&query={keyword}"
            f"&pd=3"  # 기간 검색
            f"&ds={self.date_str}"  # 시작일
            f"&de={self.date_str}"  # 종료일
            f"&start={(page-1)*10 + 1}"  # 페이지 시작점
        )
        
        try:
            logger.info(f"Requesting news list for '{keyword}' page {page} on {self.date_str}")
            response = requests.get(url, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 뉴스 항목 추출
            news_items = soup.select('div.info_group')
            
            for item in news_items:
                # 네이버 뉴스 링크만 추출 (다른 언론사 사이트 링크 제외)
                naver_news_link = item.select_one('a.info[href*="news.naver.com"]')
                if not naver_news_link:
                    continue
                
                news_url = naver_news_link.get('href')
                
                # 상위 뉴스 컨테이너에서 제목 추출
                title_elem = item.find_previous('a', class_='news_tit')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # 뉴스 항목 저장
                news_list.append({
                    'title': title,
                    'url': news_url,
                    'keyword': keyword,
                    'date': self.date_str
                })
            
            # 다음 페이지 존재 여부 확인
            next_page_exists = bool(soup.select_one('a.btn_next'))
            
            return news_list, next_page_exists
            
        except Exception as e:
            logger.error(f"Error fetching news list for '{keyword}' page {page}: {e}")
            return [], False
    
    def get_news_content(self, news_url: str) -> Optional[Dict[str, Any]]:
        """
        네이버 뉴스 페이지에서 상세 내용 추출
        
        Args:
            news_url: 네이버 뉴스 URL
            
        Returns:
            Optional[Dict[str, Any]]: 뉴스 상세 정보 (추출 실패 시 None)
        """
        try:
            # 무작위 지연 (0.5~1.5초)
            time.sleep(random.uniform(0.5, 1.5))
            
            logger.info(f"Fetching news content: {news_url}")
            response = requests.get(news_url, headers=DEFAULT_HEADERS)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 네이버 뉴스 본문 추출
            title = soup.select_one('h2.media_end_head_headline')
            title = title.get_text(strip=True) if title else ''
            
            content_elem = soup.select_one('div#newsct_article')
            content = content_elem.get_text(strip=True) if content_elem else ''
            
            # 본문이 너무 짧으면 다른 컨테이너 시도
            if not content or len(content) < 50:
                content_elem = soup.select_one('div.article_body') or soup.select_one('div#articleBodyContents')
                content = content_elem.get_text(strip=True) if content_elem else ''
            
            # 작성일시 추출
            date_elem = soup.select_one('span.media_end_head_info_datestamp_time')
            date_text = date_elem.get_text(strip=True) if date_elem else ''
            
            # 언론사 추출
            press_elem = soup.select_one('a.media_end_head_top_logo')
            press = press_elem.get('title') if press_elem else ''
            
            # 결과가 비어있으면 None 반환
            if not content:
                logger.warning(f"Failed to extract content from {news_url}")
                return None
            
            return {
                'title': title,
                'content': content,
                'date': date_text,
                'press': press,
                'url': news_url
            }
            
        except Exception as e:
            logger.error(f"Error fetching news content from {news_url}: {e}")
            return None
    
    def collect_news(self, max_pages_per_keyword: int = 2, max_news_per_keyword: int = 10) -> List[Dict[str, Any]]:
        """
        키워드별로 뉴스 수집
        
        Args:
            max_pages_per_keyword: 키워드당 최대 페이지 수
            max_news_per_keyword: 키워드당 최대 뉴스 수
            
        Returns:
            List[Dict[str, Any]]: 수집된 뉴스 목록
        """
        all_news = []
        
        for keyword in self.keywords:
            logger.info(f"Collecting news for keyword: {keyword}")
            news_count = 0
            page = 1
            
            while page <= max_pages_per_keyword and news_count < max_news_per_keyword:
                news_list, has_next = self.get_news_list(keyword, page)
                
                for news_item in news_list:
                    if news_count >= max_news_per_keyword:
                        break
                    
                    # 중복 건너뛰기 (URL 기준)
                    if any(n['url'] == news_item['url'] for n in all_news):
                        continue
                    
                    # 상세 내용 가져오기
                    news_content = self.get_news_content(news_item['url'])
                    if not news_content:
                        continue
                    
                    # 수집된 상세 정보와 기본 정보 병합
                    full_news = {**news_item, **news_content}
                    all_news.append(full_news)
                    news_count += 1
                
                if not has_next:
                    break
                
                page += 1
                # 페이지 간 딜레이 (1~2초)
                time.sleep(random.uniform(1, 2))
        
        logger.info(f"Total news collected: {len(all_news)}")
        return all_news
    
    def save_to_json(self, news_data: List[Dict[str, Any]], output_path: str = None) -> str:
        """
        수집한 뉴스를 JSON 파일로 저장
        
        Args:
            news_data: 뉴스 데이터 목록
            output_path: 저장할 경로 (기본값: ./data/news_{날짜}.json)
            
        Returns:
            str: 저장된 파일 경로
        """
        if not output_path:
            # 기본 저장 경로
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            output_path = os.path.join(data_dir, f'news_{self.now.strftime("%Y%m%d")}.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"News data saved to {output_path}")
        return output_path


# 모듈 직접 실행 시 테스트
if __name__ == "__main__":
    # 테스트 실행
    collector = NaverNewsCollector(keywords=['삼성전자', 'LG에너지솔루션'], days_ago=0)
    news_data = collector.collect_news(max_pages_per_keyword=1, max_news_per_keyword=3)
    collector.save_to_json(news_data) 