import os
import json
import glob
import sys
import uuid
from datetime import datetime
from openai import OpenAI
from sqlalchemy import Column, Integer, String, Text, DateTime, text
from sqlalchemy.dialects.postgresql import ARRAY, FLOAT
from sqlalchemy.sql import func
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

# 설정
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "naverfinanceNews")
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

def read_news_files():
    """naverfinanceNews 디렉토리의 모든 JSONL 파일 읽기"""
    news_items = []
    
    # JSONL 파일 읽기
    json_files = glob.glob(os.path.join(DATA_DIR, "*.jsonl"))
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:  # 빈 줄이 아닌지 확인
                        try:
                            news_data = json.loads(line)
                            news_items.append(news_data)
                        except json.JSONDecodeError as e:
                            print(f"JSON 파싱 오류 (파일: {file_path}): {e}")
        except Exception as e:
            print(f"파일 {file_path} 읽기 오류: {e}")
    
    print(f"naverfinanceNews 디렉토리에서 {len(news_items)}개의 뉴스 항목을 읽었습니다")
    return news_items

def store_embeddings(news_items):
    """뉴스 항목에 대한 임베딩 생성 및 데이터베이스에 저장"""
    session = NewsSessionLocal()
    
    count = 0
    news_embeddings_to_save = []
    
    try:
        for item in news_items:
            try:
                # 네이버 금융 뉴스 형식에서 필드 추출
                news_id = item.get('id')
                try:
                    # 기존 ID를 사용하되, 없거나 변환 불가능한 경우 새 UUID 생성
                    if news_id:
                        news_id = uuid.UUID(str(news_id))
                    else:
                        news_id = uuid.uuid4()
                except (ValueError, TypeError):
                    # UUID로 변환할 수 없는 경우 새로 생성
                    news_id = uuid.uuid4()
                
                title = item.get('title', '')
                content = item.get('content', '')
                
                # 네이버 금융 뉴스 형식의 published_at 처리
                published_at = None
                pub_date = item.get('time')
                if pub_date:
                    try:
                        if isinstance(pub_date, str):
                            published_at = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                        elif isinstance(pub_date, (int, float)):
                            published_at = datetime.fromtimestamp(pub_date)
                    except:
                        print(f"날짜 파싱 실패: {pub_date}")
                        published_at = datetime.now()
                else:
                    published_at = datetime.now()
                
                # 뉴스 내용에 대한 임베딩 생성
                # 더 포괄적인 임베딩을 위해 제목과 내용 결합
                embedding_text = f"{title}\n{content}"
                if not embedding_text.strip():
                    print(f"뉴스 ID {news_id}의 내용이 비어있어 건너뜁니다")
                    continue
                    
                embedding = get_embedding(embedding_text)
                if not embedding:
                    print(f"뉴스 ID {news_id}의 임베딩 생성 실패, 건너뜁니다")
                    continue
                
                # 기존 항목이 있는지 확인
                existing_news = session.query(NewsEmbedding).filter_by(id=news_id).first()
                
                if existing_news:
                    # 기존 항목 업데이트
                    existing_news.title = title
                    existing_news.content = content
                    existing_news.published_at = published_at
                    existing_news.embedding = embedding
                else:
                    # 새 항목 생성
                    news_embedding = NewsEmbedding(
                        id=news_id,
                        title=title,
                        content=content,
                        published_at=published_at,
                        embedding=embedding
                    )
                    news_embeddings_to_save.append(news_embedding)
                
                # 주기적으로 커밋하여 메모리 관리
                count += 1
                if count % 10 == 0:
                    save_news_vectors(session, news_embeddings_to_save)
                    news_embeddings_to_save = []
                    print(f"{count}개의 뉴스 항목 처리 완료")
                    
            except Exception as e:
                print(f"뉴스 항목 처리 중 오류 발생: {e}")
                session.rollback()
        
        # 남은 항목 커밋
        if news_embeddings_to_save:
            save_news_vectors(session, news_embeddings_to_save)
            
        print(f"총 {count}개의 뉴스 항목 처리 완료")
        
    except Exception as e:
        print(f"데이터베이스 저장 중 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

def main():
    """워크플로우를 조정하는 메인 함수"""
    try:
        print("뉴스 임베딩 프로세스 시작")
        
        # 데이터베이스 초기화
        init_db()
        
        # 뉴스 파일 읽기
        news_items = read_news_files()
        
        if not news_items:
            print("처리할 뉴스 항목이 없습니다")
            return
        
        # 임베딩 생성 및 데이터베이스에 저장
        store_embeddings(news_items)
        
        print("뉴스 임베딩 프로세스 성공적으로 완료")
    except Exception as e:
        print(f"메인 프로세스 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
