import openai
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv
from tqdm import tqdm

from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. 환경 변수 로드 및 OpenAI API 키 설정
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 2. 데이터베이스 연결 설정 
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# 3. news_vectors 테이블 정의 
class NewsVector(Base):
    __tablename__ = "news_vectors"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    content = Column(String, nullable=False)
    embedding = Column(ARRAY(String), nullable=False)
    published_at = Column(DateTime, nullable=False)

# 4. OpenAI API를 사용한 임베딩 함수
def get_embedding(text, model="text-embedding-ada-002"):
    try:
        response = openai.Embedding.create(input=[text], model=model)
        return response["data"][0]["embedding"]
    except Exception as e:
        print(f"임베딩 실패: {e}")
        return []

# 5. 뉴스 벡터화 및 DB 저장 함수
def embed_and_store_news(input_path):
    session = SessionLocal()
    inserted_count = 0

    with open(input_path, "r", encoding="utf-8") as f:
        for line in tqdm(f, desc="뉴스 임베딩 및 저장 중"):
            try:
                news = json.loads(line.strip())
                title = news.get("title", "")
                content = news.get("content", "")
                published_at = news.get("published_at") or news.get("time")

                if not content or not published_at:
                    continue

                embedding = get_embedding(content)

                published_at = (
                    datetime.fromisoformat(published_at)
                    if "T" in published_at
                    else datetime.strptime(published_at, "%Y-%m-%d %H:%M:%S")
                )

                news_vector = NewsVector(
                    title=title,
                    content=content,
                    embedding=[str(x) for x in embedding],  # VECTOR(1536) 사용 시 float[]로 변환 가능
                    published_at=published_at
                )

                session.add(news_vector)
                inserted_count += 1

            except Exception as e:
                print(f"뉴스 파싱 실패: {e}")
                continue

    session.commit()
    session.close()
    print(f"총 {inserted_count}개의 뉴스가 DB에 저장되었습니다.")

# 6. 실행 진입점
if __name__ == "__main__":
    INPUT = "path/to/naverfinance_mainnews_2025-02-06.jsonl"  # 실제 파일 경로로 수정
    Base.metadata.create_all(bind=engine)
    embed_and_store_news(INPUT)
