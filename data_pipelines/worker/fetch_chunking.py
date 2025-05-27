import os
import sys
import uuid
import time
import json
from datetime import datetime
from openai import OpenAI
from sqlalchemy import text, desc
from dotenv import load_dotenv
import tiktoken

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
from sqlalchemy import Column, Text, DateTime, Integer

# ──────────────── 파라미터 ──────────────────────
CHUNK_SIZE = 500  # 청크 크기 (토큰 단위)
CHUNK_OVERLAP = 200  # 청크 간 겹치는 부분 (토큰 단위)
BATCH_SIZE = 100  # 한 번에 처리할 뉴스 개수
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI 임베딩 모델
ENCODING_NAME = "cl100k_base"  # OpenAI 임베딩 모델용 인코딩

# OpenAI API 키 설정
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
print(f"OPENAI_API_KEY: {OPENAI_API_KEY}")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일에 OPENAI_API_KEY를 추가해주세요.")

# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OPENAI_API_KEY)

# 토크나이저 초기화
encoding = tiktoken.get_encoding(ENCODING_NAME)

# 기존 뉴스 임베딩 모델 (읽기용)
class NewsEmbedding(NewsBase):
    __tablename__ = 'news_vectors'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1536))
    published_at = Column(DateTime)
    
    def __repr__(self):
        return f"<NewsEmbedding(id='{self.id}', title='{self.title[:30]}...')>"

# 청킹된 뉴스 임베딩 모델 (저장용)
class NewsChunkEmbedding(NewsBase):
    __tablename__ = 'news_chunks'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    news_id = Column(UUID(as_uuid=True), nullable=False)  # 원본 뉴스 ID
    title = Column(Text, nullable=False)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # 청크 순서
    embedding = Column(Vector(1536))
    published_at = Column(DateTime)
    
    def __repr__(self):
        return f"<NewsChunkEmbedding(id='{self.id}', chunk_index={self.chunk_index}, title='{self.title[:30]}...')>"

def init_db():
    """데이터베이스 연결 초기화 및 pgvector 확장 확인"""
    session = NewsSessionLocal()
    
    try:
        # pgvector 확장이 존재하는지 확인
        result = session.execute(text("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'vector')"))
        extension_exists = result.scalar()
        
        if not extension_exists:
            session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            print("pgvector 확장 생성 완료")
            session.commit()
            
    except Exception as e:
        print(f"데이터베이스 초기화 중 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

def get_embedding(text):
    """OpenAI API를 사용하여 텍스트에 대한 임베딩 생성"""
    try:
        response = client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"임베딩 생성 중 오류 발생: {e}")
        return None

def chunk_text(text, max_tokens=CHUNK_SIZE, overlap_tokens=CHUNK_OVERLAP):
    """텍스트를 토큰 단위로 청킹"""
    # 텍스트를 토큰으로 변환
    tokens = encoding.encode(text)
    
    if len(tokens) <= max_tokens:
        # 텍스트가 청크 크기보다 작으면 그대로 반환
        return [text]
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        # 청크 끝 위치 계산
        end = min(start + max_tokens, len(tokens))
        
        # 토큰을 텍스트로 변환
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        
        # 다음 청크 시작 위치 (겹치는 부분 고려)
        if end == len(tokens):
            break
        start = end - overlap_tokens
    
    return chunks

def fetch_existing_news_batch(session, offset=0, batch_size=BATCH_SIZE):
    """기존 뉴스 데이터를 배치 단위로 가져옴"""
    query = session.query(NewsEmbedding).order_by(desc(NewsEmbedding.published_at))
    return query.offset(offset).limit(batch_size).all()

def get_total_news_count(session):
    """전체 뉴스 개수를 가져옴"""
    return session.query(NewsEmbedding).count()

def save_chunk_embeddings(session, chunk_embeddings):
    """청킹된 임베딩을 데이터베이스에 저장"""
    try:
        session.add_all(chunk_embeddings)
        session.commit()
        print(f"✅ {len(chunk_embeddings)}개의 청크 임베딩 저장 완료")
    except Exception as e:
        print(f"청크 임베딩 저장 중 오류 발생: {e}")
        session.rollback()
        raise

def process_news_chunking(limit=None):
    """기존 뉴스를 배치 단위로 청킹하여 임베딩 생성 및 저장"""
    session = NewsSessionLocal()
    
    try:
        # 전체 뉴스 개수 확인
        total_news_count = get_total_news_count(session)
        print(f"총 {total_news_count:,}개의 뉴스가 데이터베이스에 있습니다.")
        
        if limit:
            total_news_count = min(total_news_count, limit)
            print(f"처리 제한으로 인해 {total_news_count:,}개만 처리합니다.")
        
        # 이미 처리된 뉴스 ID 확인
        processed_news_ids = set()
        existing_chunks = session.query(NewsChunkEmbedding.news_id).distinct().all()
        for (news_id,) in existing_chunks:
            processed_news_ids.add(news_id)
        
        print(f"이미 처리된 뉴스: {len(processed_news_ids):,}개")
        
        chunk_embeddings_to_save = []
        processed_count = 0
        batch_count = 0
        offset = 0
        
        # 배치 단위로 처리
        while offset < total_news_count:
            batch_count += 1
            current_batch_size = min(BATCH_SIZE, total_news_count - offset)
            
            print(f"\n📦 배치 {batch_count} 처리 중 (뉴스 {offset+1}~{offset+current_batch_size})...")
            
            # 배치 단위로 뉴스 로드
            news_batch = fetch_existing_news_batch(session, offset, current_batch_size)
            
            if not news_batch:
                print("더 이상 처리할 뉴스가 없습니다.")
                break
            
            batch_processed = 0
            for news in news_batch:
                # 이미 처리된 뉴스는 건너뛰기
                if news.id in processed_news_ids:
                    continue
                
                print(f"🔄 뉴스 처리 중: {news.title[:50]}...")
                
                # 제목과 내용을 합쳐서 청킹
                full_text = f"{news.title}\n\n{news.content}"
                chunks = chunk_text(full_text)
                
                print(f"📄 {len(chunks)}개의 청크로 분할됨")
                
                # 각 청크에 대해 임베딩 생성
                for chunk_index, chunk_content in enumerate(chunks):
                    print(f"  🔄 청크 {chunk_index + 1}/{len(chunks)} 임베딩 생성 중...")
                    
                    # 임베딩 생성
                    embedding = get_embedding(chunk_content)
                    if not embedding:
                        print(f"  ❌ 청크 {chunk_index + 1} 임베딩 생성 실패, 건너뛰기")
                        continue
                    
                    # 청크 임베딩 엔티티 생성
                    chunk_embedding = NewsChunkEmbedding(
                        id=uuid.uuid4(),
                        news_id=news.id,
                        title=news.title,
                        chunk_text=chunk_content,
                        chunk_index=chunk_index,
                        embedding=embedding,
                        published_at=news.published_at
                    )
                    
                    chunk_embeddings_to_save.append(chunk_embedding)
                    
                    # API 레이트 리미트 방지를 위해 잠시 대기
                    time.sleep(0.1)
                
                batch_processed += 1
                processed_count += 1
                
                # 20개 청크마다 DB에 저장
                if len(chunk_embeddings_to_save) >= 20:
                    save_chunk_embeddings(session, chunk_embeddings_to_save)
                    chunk_embeddings_to_save = []
            
            print(f"✅ 배치 {batch_count} 완료: {batch_processed}개 뉴스 처리 (누적: {processed_count}개)")
            offset += current_batch_size
        
        # 남은 청크 임베딩 저장
        if chunk_embeddings_to_save:
            save_chunk_embeddings(session, chunk_embeddings_to_save)
        
        print(f"\n✅ 전체 뉴스 청킹 및 임베딩 완료: {processed_count:,}개 처리")
        
    except Exception as e:
        print(f"뉴스 청킹 처리 중 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

def get_chunk_stats():
    """청킹 통계 정보 출력"""
    session = NewsSessionLocal()
    
    try:
        # 원본 뉴스 수
        original_count = session.query(NewsEmbedding).count()
        
        # 청크 수
        chunk_count = session.query(NewsChunkEmbedding).count()
        
        # 청킹된 뉴스 수
        chunked_news_count = session.query(NewsChunkEmbedding.news_id).distinct().count()
        
        print(f"\n📊 청킹 통계:")
        print(f"  - 원본 뉴스 수: {original_count:,}개")
        print(f"  - 청킹된 뉴스 수: {chunked_news_count:,}개")
        print(f"  - 총 청크 수: {chunk_count:,}개")
        print(f"  - 평균 청크 수 (청킹된 뉴스당): {chunk_count / chunked_news_count:.1f}개" if chunked_news_count > 0 else "  - 평균 청크 수: N/A")
        
    except Exception as e:
        print(f"통계 조회 중 오류 발생: {e}")
    finally:
        session.close()

def main():
    """워크플로우를 조정하는 메인 함수"""
    try:
        print("뉴스 청킹 및 임베딩 프로세스 시작")
        print(f"청크 크기: {CHUNK_SIZE} 토큰")
        print(f"청크 겹침: {CHUNK_OVERLAP} 토큰")
        print(f"배치 크기: {BATCH_SIZE}개")
        
        # 데이터베이스 초기화
        init_db()
        
        # 현재 통계 출력
        get_chunk_stats()
        
        # 뉴스 청킹 및 임베딩 처리
        # limit 매개변수를 조정하여 처리할 뉴스 수를 제한할 수 있음 (테스트 시 유용)
        process_news_chunking(limit=None)  # None이면 모든 뉴스 처리
        
        # 최종 통계 출력
        get_chunk_stats()
        
        print("뉴스 청킹 및 임베딩 프로세스 성공적으로 완료")
        
    except Exception as e:
        print(f"메인 프로세스 중 오류 발생: {e}")

if __name__ == "__main__":
    main()
