# data_pipelines/workers/fetch_naver_news_api.py
import os
import time
import datetime
import logging
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import List, Dict, Any, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 1일 기준 뉴스 수집 (오늘 = 0, 어제 = 1, ...)
DEFAULT_DAYS_AGO = 0

# 주식 관련 키워드 (예시)
STOCK_KEYWORDS = [
    '주식', '증시', '코스피', '코스닥', '나스닥', '다우', 'S&P500', 
    '금융시장', '애플', '테슬라', '삼성전자', 'LG에너지솔루션',
    '투자', '주가', '실적', '배당', '테크주', '금리', '연준', 'FED'
]

class NaverNewsAPIClient:
    """네이버 뉴스 API 클라이언트"""
    
    def __init__(self, 
                 client_id: str = None, 
                 client_secret: str = None, 
                 keywords: List[str] = None, 
                 days_ago: int = DEFAULT_DAYS_AGO):
        """
        초기화
        
        Args:
            client_id: 네이버 API 클라이언트 ID (환경변수: NAVER_CLIENT_ID)
            client_secret: 네이버 API 클라이언트 시크릿 (환경변수: NAVER_CLIENT_SECRET)
            keywords: 검색할 키워드 목록 (기본: 주식 관련 키워드)
            days_ago: 몇 일 전 뉴스를 수집할지 (기본: 오늘)
        """
        # API 인증 정보 설정
        self.client_id = client_id or os.getenv('NAVER_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('NAVER_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError("네이버 API 키가 필요합니다. "
                             "NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경변수를 설정하거나 "
                             "초기화 시 매개변수로 전달하세요.")
        
        self.keywords = keywords or STOCK_KEYWORDS
        self.days_ago = days_ago
        
        # 날짜 설정
        self.now = datetime.datetime.now() - datetime.timedelta(days=days_ago)
        # 네이버 검색 API는 YYYY-mm-dd 형식 사용
        self.date_str = self.now.strftime('%Y-%m-%d')
    
    def search_news(self, keyword: str, start: int = 1, display: int = 100) -> Dict[str, Any]:
        """
        네이버 뉴스 API를 사용하여 뉴스 검색
        
        Args:
            keyword: 검색 키워드
            start: 검색 시작 위치 (1부터 시작)
            display: 한 번에 가져올 검색 결과 개수 (최대 100)
            
        Returns:
            Dict[str, Any]: API 응답 데이터
        """
        # 네이버 검색 API URL
        url = "https://openapi.naver.com/v1/search/news.json"
        
        # 쿼리 파라미터 설정
        query_params = {
            "query": keyword,
            "display": display,
            "start": start,
            "sort": "date",  # 최신순 정렬
        }
        
        # URL 인코딩
        query_string = urllib.parse.urlencode(query_params)
        request_url = f"{url}?{query_string}"
        
        # API 요청 헤더 설정
        request = urllib.request.Request(request_url)
        request.add_header("X-Naver-Client-Id", self.client_id)
        request.add_header("X-Naver-Client-Secret", self.client_secret)
        
        try:
            # API 호출
            logger.info(f"Requesting news search for '{keyword}' (start={start}, display={display})")
            response = urllib.request.urlopen(request)
            response_code = response.getcode()
            
            if response_code == 200:
                # 응답 파싱
                response_body = response.read()
                response_data = json.loads(response_body.decode('utf-8'))
                logger.info(f"Found {response_data.get('total', 0)} results for '{keyword}'")
                return response_data
            else:
                logger.error(f"API request failed with code {response_code}")
                return {"items": []}
        
        except urllib.error.HTTPError as e:
            logger.error(f"HTTPError: {e.code} - {e.reason}")
            return {"items": []}
        except urllib.error.URLError as e:
            logger.error(f"URLError: {e.reason}")
            return {"items": []}
        except Exception as e:
            logger.error(f"Error fetching news for '{keyword}': {e}")
            return {"items": []}
    
    def clean_html_tags(self, text: str) -> str:
        """
        HTML 태그 제거
        
        Args:
            text: HTML 태그가 포함된 텍스트
            
        Returns:
            str: 태그가 제거된 텍스트
        """
        import re
        return re.sub(r'<.*?>', '', text)
    
    def collect_news(self, max_items_per_keyword: int = 30) -> List[Dict[str, Any]]:
        """
        키워드별로 뉴스 수집
        
        Args:
            max_items_per_keyword: 키워드당 최대 뉴스 수
            
        Returns:
            List[Dict[str, Any]]: 수집된 뉴스 목록
        """
        all_news = []
        collected_urls = set()  # 중복 제거를 위한 URL 저장소
        
        for keyword in self.keywords:
            logger.info(f"Collecting news for keyword: {keyword}")
            start = 1
            display = min(100, max_items_per_keyword)  # 최대 100개까지 한 번에 요청 가능
            
            while start <= max_items_per_keyword:
                # API 호출하여 뉴스 검색
                search_result = self.search_news(keyword, start, display)
                
                # 검색 결과가 없으면 중단
                items = search_result.get('items', [])
                if not items:
                    break
                
                # 각 뉴스 항목 처리
                for item in items:
                    # URL 기준으로 중복 건너뛰기
                    if item['link'] in collected_urls:
                        continue
                    
                    # HTML 태그 제거
                    title = self.clean_html_tags(item['title'])
                    description = self.clean_html_tags(item['description'])
                    
                    # 결과 저장
                    news_item = {
                        'title': title,
                        'description': description,
                        'url': item['link'],
                        'original_link': item.get('originallink', ''),
                        'pub_date': item['pubDate'],
                        'keyword': keyword,
                        'collected_date': datetime.datetime.now().isoformat()
                    }
                    
                    all_news.append(news_item)
                    collected_urls.add(item['link'])
                
                # 다음 페이지로 이동
                start += display
                
                # API 호출 제한 준수 (초당 10회)
                time.sleep(0.1)
                
                # 요청한 개수만큼 다 모았으면 중단
                if len(collected_urls) >= max_items_per_keyword:
                    break
        
        logger.info(f"Total news collected: {len(all_news)}")
        return all_news
    
    def save_to_json(self, news_data: List[Dict[str, Any]], output_path: str = None) -> str:
        """
        수집한 뉴스를 JSON 파일로 저장
        
        Args:
            news_data: 뉴스 데이터 목록
            output_path: 저장할 경로 (기본값: ./data/news_api_{날짜}.json)
            
        Returns:
            str: 저장된 파일 경로
        """
        if not output_path:
            # 기본 저장 경로
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            output_path = os.path.join(data_dir, f'news_api_{self.now.strftime("%Y%m%d")}.json')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(news_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"News data saved to {output_path}")
        return output_path


# 모듈 직접 실행 시 테스트
if __name__ == "__main__":
    # 환경 변수에서 API 키를 가져와 테스트
    if os.getenv('NAVER_CLIENT_ID') and os.getenv('NAVER_CLIENT_SECRET'):
        # 테스트 실행
        client = NaverNewsAPIClient(keywords=['삼성전자', 'LG에너지솔루션'], days_ago=0)
        news_data = client.collect_news(max_items_per_keyword=10)
        client.save_to_json(news_data)
    else:
        print("테스트하려면 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경변수를 설정하세요.")
        print("https://developers.naver.com/apps/#/register 에서 애플리케이션을 등록하고 API 키를 발급받을 수 있습니다.") 