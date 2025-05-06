import os
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

# 로컬 모듈 임포트
from workers.fetch_naver_news import NaverNewsCollector
from workers.fetch_naver_news_api import NaverNewsAPIClient

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 스케줄러 생성
scheduler = BackgroundScheduler()

def fetch_stock_news():
    """
    주식 관련 네이버 뉴스 수집 작업 (웹 크롤링 방식)
    """
    logger.info("Starting scheduled task: fetch_stock_news (Web Crawling)")
    
    try:
        # 수집 키워드 정의
        stock_keywords = [
            '주식', '증시', '코스피', '코스닥', '나스닥', 
            '애플', '테슬라', '삼성전자', 'LG에너지솔루션',
            '금리', '연준', 'FED'
        ]
        
        # 네이버 뉴스 수집기 초기화
        collector = NaverNewsCollector(keywords=stock_keywords, days_ago=0)
        
        # 뉴스 수집 (키워드당 최대 2페이지, 최대 5개 뉴스)
        news_data = collector.collect_news(max_pages_per_keyword=2, max_news_per_keyword=5)
        
        # 결과 저장
        if news_data:
            # data 디렉토리 생성
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # 현재 시간 포함한 파일명으로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(data_dir, f'stock_news_{timestamp}.json')
            
            collector.save_to_json(news_data, output_path)
            logger.info(f"Collected {len(news_data)} news articles. Saved to {output_path}")
        else:
            logger.warning("No news data collected")
    
    except Exception as e:
        logger.error(f"Error in fetch_stock_news task: {e}", exc_info=True)


def fetch_stock_news_api():
    """
    주식 관련 네이버 뉴스 수집 작업 (API 방식)
    """
    logger.info("Starting scheduled task: fetch_stock_news_api (Using Naver API)")
    
    try:
        # 네이버 API 키 확인
        client_id = os.getenv('NAVER_CLIENT_ID')
        client_secret = os.getenv('NAVER_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            logger.error("NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET 환경변수가 설정되지 않았습니다.")
            return
        
        # 수집 키워드 정의
        stock_keywords = [
            '주식', '증시', '코스피', '코스닥', '나스닥', 
            '애플', '테슬라', '삼성전자', 'LG에너지솔루션',
            '금리', '연준', 'FED'
        ]
        
        # 네이버 뉴스 API 클라이언트 초기화
        client = NaverNewsAPIClient(
            client_id=client_id,
            client_secret=client_secret,
            keywords=stock_keywords, 
            days_ago=0
        )
        
        # 뉴스 수집 (키워드당 최대 20개 뉴스)
        news_data = client.collect_news(max_items_per_keyword=20)
        
        # 결과 저장
        if news_data:
            # data 디렉토리 생성
            data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
            os.makedirs(data_dir, exist_ok=True)
            
            # 현재 시간 포함한 파일명으로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(data_dir, f'stock_news_api_{timestamp}.json')
            
            client.save_to_json(news_data, output_path)
            logger.info(f"API Collected {len(news_data)} news articles. Saved to {output_path}")
        else:
            logger.warning("No news data collected from API")
    
    except Exception as e:
        logger.error(f"Error in fetch_stock_news_api task: {e}", exc_info=True)


def start_scheduler():
    """
    모든 작업을 스케줄러에 등록하고 시작
    """
    # [웹 크롤링 방식] 작업 1: 주식 뉴스 수집 - 매일 오전 9시와 오후 6시에 실행
    scheduler.add_job(
        fetch_stock_news,
        CronTrigger(hour='9,18', minute='0'),
        id='stock_news_daily',
        replace_existing=True,
        coalesce=True,  # 지연된 작업이 여러개일 경우 한번만 실행
    )
    
    # [웹 크롤링 방식] 작업 2: 실시간 뉴스 업데이트 - 30분마다 실행
    scheduler.add_job(
        fetch_stock_news,
        IntervalTrigger(minutes=30),
        id='stock_news_realtime',
        replace_existing=True,
    )
    
    # [API 방식] 작업 3: API를 통한 뉴스 수집 - 매시간 15분에 실행
    scheduler.add_job(
        fetch_stock_news_api,
        CronTrigger(minute='15'),
        id='stock_news_api_hourly',
        replace_existing=True,
    )
    
    # [API 방식] 작업 4: API를 통한 주요 뉴스 수집 - 아침 8시와 오후 4시에 실행
    scheduler.add_job(
        fetch_stock_news_api,
        CronTrigger(hour='8,16', minute='0'),
        id='stock_news_api_main',
        replace_existing=True,
    )
    
    # 서버 시작 시 즉시 한 번 실행 (API 방식)
    scheduler.add_job(
        fetch_stock_news_api,
        'date',
        run_date=datetime.now(),
        id='stock_news_api_immediate',
    )
    
    # 스케줄러 시작
    scheduler.start()
    logger.info("Scheduler started. Jobs registered:")
    for job in scheduler.get_jobs():
        logger.info(f"- {job.id}: Next run at {job.next_run_time}")


if __name__ == "__main__":
    logger.info("Initializing data pipeline scheduler...")
    
    try:
        # 스케줄러 시작
        start_scheduler()
        
        # 스케줄러가 백그라운드에서 실행되므로 메인 스레드 유지
        try:
            # 무한 루프로 실행 상태 유지
            while True:
                pass
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler shutdown requested")
            scheduler.shutdown()
            logger.info("Scheduler shut down")
    
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}", exc_info=True) 