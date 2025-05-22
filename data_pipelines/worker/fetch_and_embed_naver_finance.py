import os
import sys
import uuid
import time
import random
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
from openai import OpenAI
from sqlalchemy import text
from dotenv import load_dotenv

# 경로 설정을 통해 aibackend 패키지를 import 할 수 있도록 함
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(backend_path)

# 환경 변수 로드 (루트 디렉토리의 .env 파일)
dotenv_path = os.path.join(backend_path, '.env')
load_dotenv(dotenv_path)

# aibackend에서 필요한 모듈 가져오기
from aibackend.app.news_vector_db import NewsBase, NewsSessionLocal, save_news_vectors
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Column, Text, DateTime

# ──────────────── 파라미터 ──────────────────────
START_DATE = "2025-02-21"
END_DATE = "2025-05-17"
BASE = "https://n.news.naver.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI 임베딩 모델

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 추가해주세요.")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 뉴스 임베딩을 위한 모델 정의
class NewsEmbedding(NewsBase):
    __tablename__ = 'news_vectors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    published_at = Column(DateTime)
    
    def __repr__(self):
        return f"<NewsEmbedding(id='{self.id}', title='{self.title[:30]}...')>"

def init_db():
    """데이터베이스 연결 초기화 및 pgvector 확장 확인"""
    # 세션 생성
    session = NewsSessionLocal()
    
    try:
        # pgvector 확장이 존재하는지 확인
        result = session.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        extension_exists = result.scalar()
        
        if not extension_exists:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("pgvector 확장 생성 완료")
            session.commit()
        
        print("데이터베이스 초기화 완료")
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

def get_embedding(text):
    """OpenAI API를 사용하여 텍스트에 대한 임베딩 생성"""
    try:
        # API 제한을 위해 텍스트 길이 제한
        if len(text) > 100000:
            text = text[:100000]
            
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"임베딩 생성 중 오류 발생: {e}")
        return None

def daterange(start_date: str, end_date: str):
    d0 = datetime.fromisoformat(start_date)
    d1 = datetime.fromisoformat(end_date)
    delta = timedelta(days=1)
    while d0 <= d1:
        yield d0.strftime("%Y-%m-%d")
        d0 += delta

def news_read_to_mnews(url: str) -> str:
    """
    '/news/news_read.naver?article_id=0001209610&office_id=215&…'
        → 'https://n.news.naver.com/mnews/article/215/0001209610'
    """
    if "/news/news_read" not in url:
        return url                          # 대상이 아니면 그대로

    qs  = parse_qs(urlparse(url).query)     # 쿼리 → dict
    oid = qs.get("office_id", [""])[0]
    aid = qs.get("article_id", [""])[0]
    return f"https://n.news.naver.com/mnews/article/{oid}/{aid}" if oid and aid else url

def fetch_and_embed_news():
    """네이버 금융 뉴스를 크롤링하고 임베딩하여 데이터베이스에 저장"""
    # 데이터베이스 세션 생성
    session = NewsSessionLocal()
    
    # 날짜별로 크롤링
    for date in daterange(START_DATE, END_DATE):
        time.sleep(random.uniform(1.5, 3.0))
        print(f"📅 {date} 뉴스 수집 시작")

        first_url = f"https://finance.naver.com/news/mainnews.naver?date={date}"
        first_resp = requests.get(first_url, headers=HEADERS, timeout=10)
        soup_first = BeautifulSoup(first_resp.text, "lxml")

        # 최대 페이지 수 확인
        a = soup_first.select_one("td.pgRR a[href]")
        if not a:
            print("페이지 정보를 찾을 수 없습니다.")
            continue
            
        qs = parse_qs(urlparse(a["href"]).query)
        max_page = int(qs.get("page", [1])[0])
        print(f"최대 페이지: {max_page}")

        articles = []
        news_embeddings_to_save = []
        count = 0

        # 페이지별로 뉴스 목록 수집
        for page_no in range(1, max_page + 1):
            time.sleep(random.uniform(1.5, 3.0))
            url = f"https://finance.naver.com/news/mainnews.naver?date={date}&page={page_no}"
            response = requests.get(url, headers=HEADERS, timeout=10)
            if response.status_code != 200:
                print(f"❌ 요청 실패: {url}")
                continue
                
            soup = BeautifulSoup(response.text, "lxml")
            print(f"\n🔄 [목록] page {page_no} 요청 → {url}")

            # 뉴스 항목 추출
            for li in soup.select("div.mainNewsList li.block1"):
                time.sleep(random.uniform(1.5, 3.0))
                title_a = li.select_one("dd.articleSubject > a[href]")
                press = li.select_one("dd.articleSummary span.press")
                wdate = li.select_one("dd.articleSummary span.wdate")
                if not title_a:
                    continue

                url = news_read_to_mnews(title_a["href"])
                
                # 뉴스 기사 본문 수집
                try:
                    time.sleep(random.uniform(1.5, 3.0))
                    print(f"🔄 [본문] 요청 → {url}")
                    res = requests.get(url, headers=HEADERS, timeout=10)
                    if res.status_code != 200:
                        print(f"❌ 본문 요청 실패: {url}")
                        continue
                        
                    page = BeautifulSoup(res.text, "html.parser")
                    body = page.select_one("#dic_area, .go_trans._article_content")
                    
                    title = title_a.get_text(strip=True)
                    content = body.get_text(strip=True) if body else ""
                    
                    # 임베딩 생성
                    print(f"🔄 [임베딩] 생성 중...")
                    embedding_text = f"{title}\n{content}"
                    if not embedding_text.strip():
                        print(f"뉴스 '{title}'의 내용이 비어있어 건너뜁니다")
                        continue
                        
                    embedding = get_embedding(embedding_text)
                    if not embedding:
                        print(f"뉴스 '{title}'의 임베딩 생성 실패, 건너뜁니다")
                        continue
                    
                    # 발행일 파싱
                    published_at = None
                    time_str = wdate.get_text(strip=True) if wdate else ""
                    if time_str:
                        try:
                            if isinstance(time_str, str):
                                published_at = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                            elif isinstance(time_str, (int, float)):
                                published_at = datetime.fromtimestamp(time_str)
                        except:
                            print(f"날짜 파싱 실패: {time_str}")
                            published_at = datetime.now()
                    else:
                        published_at = datetime.now()
                    
                    # 뉴스 엔티티 생성
                    news_id = uuid.uuid4()
                    news_embedding = NewsEmbedding(
                        id=news_id,
                        title=title,
                        content=content,
                        published_at=published_at,
                        embedding=embedding
                    )
                    
                    news_embeddings_to_save.append(news_embedding)
                    count += 1
                    print(f"✅ {len(news_embeddings_to_save)}개의 뉴스 저장 완료 (총 {count}개)")
                    
                    # 10개마다 DB에 저장
                    if len(news_embeddings_to_save) >= 10:
                        try:
                            save_news_vectors(session, news_embeddings_to_save)
                            print(f"✅ {len(news_embeddings_to_save)}개의 뉴스 저장 완료 (총 {count}개)")
                            news_embeddings_to_save = []
                        except Exception as e:
                            print(f"데이터베이스 저장 중 오류 발생: {e}")
                            session.rollback()
                
                except Exception as e:
                    print(f"뉴스 처리 중 오류 발생: {e}")
                    continue
            
            print(f"📄 page {page_no} 수집 및 임베딩 완료")
        
        # 남은 뉴스 저장
        if news_embeddings_to_save:
            try:
                save_news_vectors(session, news_embeddings_to_save)
                print(f"✅ 남은 {len(news_embeddings_to_save)}개의 뉴스 저장 완료 (총 {count}개)")
            except Exception as e:
                print(f"데이터베이스 저장 중 오류 발생: {e}")
                session.rollback()
        
        print(f"📅 {date} 뉴스 수집 및 임베딩 완료 (총 {count}개)")
    
    # 세션 종료
    session.close()

def main():
    """워크플로우를 조정하는 메인 함수"""
    try:
        print("네이버 금융 뉴스 크롤링 및 임베딩 프로세스 시작")
        
        # 데이터베이스 초기화
        init_db()
        
        # 뉴스 크롤링 및 임베딩 저장
        fetch_and_embed_news()
        
        print("네이버 금융 뉴스 크롤링 및 임베딩 프로세스 성공적으로 완료")
    except Exception as e:
        print(f"메인 프로세스 중 오류 발생: {e}")

if __name__ == "__main__":
    main() 