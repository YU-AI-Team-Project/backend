from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from dotenv import load_dotenv
from typing import List,Tuple
from openai import OpenAI
import os

load_dotenv()

pg_user = os.getenv("NEWS_DB_USER")
pg_passwd = os.getenv("NEWS_DB_PASSWORD")
pg_host = os.getenv("NEWS_DB_HOST")
pg_port = os.getenv("NEWS_DB_PORT")
pg_db = os.getenv("NEWS_DB_NAME")

NEWS_DB_URL = f'postgresql+psycopg2://{pg_user}:{pg_passwd}@{pg_host}:{pg_port}/{pg_db}'

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

NewsEngine = create_engine(NEWS_DB_URL,echo=True)
NewsSessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=NewsEngine)
NewsBase = declarative_base()


from contextlib import contextmanager

@contextmanager
def get_news_db():
    db: Session = NewsSessionLocal()
    try:
        yield db
    finally:
        db.close()
        
    
def save_news_vectors(session: Session, news_list: List):
    if not news_list:
        return
    session.add_all(news_list)
    session.commit()
    
    
import torch

# ------------------------------------------------------
# db에서 임베딩된 뉴스 벡터값 가져오는 메서드
# ------------------------------------------------------

def load_news_embeddings(session: Session, limit: int = 1000) -> Tuple[List[str], torch.Tensor]:
    from news_vector import NewsVector
    records = session.query(NewsVector).filter(NewsVector.embedding != None).limit(limit).all()
    contents = [r.content for r in records]
    embeddings = torch.stack([torch.tensor(r.embedding) for r in records])
    return contents, embeddings



# ----------------------------
# OpenAI 임베딩 함수
# ----------------------------
def get_openai_embedding(text: str) -> torch.Tensor:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    embedding = response.data[0].embedding
    return torch.tensor(embedding)


# -------------------------------------------------------------
# 키워드와 유사도 높은 뉴스를 골라 k개 반환하는 메서드
# k 입력으로 가져올 가장 비슷한 뉴스 개수 조정(디폴트 5)
# limit 값 입력으로 db에서 가져올 뉴스 개수 조정 가능(디폴트 1000)
# -------------------------------------------------------------

def find_similar_news(keywords: List[str], k: int = 5, limit: int = 1000) -> List[str]:
    keyword_embeddings = [get_openai_embedding(k) for k in keywords]
    keyword_embeddings = torch.stack(keyword_embeddings)
    query_vector = torch.mean(keyword_embeddings, dim=0)
    
    with get_news_db() as session:
        news_contents, news_vectors = load_news_embeddings(session,limit=limit)
        similarities = torch.nn.functional.cosine_similarity(query_vector.unsqueeze(0), news_vectors)
        top_k = torch.topk(similarities, k=k)
        indices = top_k.indices.tolist()
        return [news_contents[i] for i in indices]
        

# ---------
# 예시 실행
# ---------

if __name__ == "__main__":
    sample_keywords = ["삼성전자", "금리", "경제","대한민국"]
    top_news = find_similar_news(sample_keywords, k=5)
    print("ENV DEBUG:", pg_user, pg_host, pg_port, pg_db)
    print("🔍 키워드 기반 유사 뉴스:")
    for i, news in enumerate(top_news, 1):
        print(f"{i}. {news[:100]}...")  # 100자만 미리보기