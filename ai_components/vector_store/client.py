# ai_components/vector_store/client.py
import os
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import json
from sqlalchemy import create_engine, Column, Integer, String, Float, text, BLOB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 더미 상태를 위한 변수 (실제 구현에서는 DB 연결 사용)
DUMMY_MODE = True

# SQLAlchemy 모델 설정
Base = declarative_base()

class DocumentVector(Base):
    """
    벡터 DB(MySQL)에 저장되는 문서 벡터 모델
    """
    __tablename__ = "document_vectors"
    
    id = Column(Integer, primary_key=True)
    content = Column(String(2048), nullable=False)  # 문서 텍스트
    metadata = Column(String(1024))  # JSON 형태의 메타데이터 (출처, 날짜 등)
    embedding_blob = Column(BLOB)  # 벡터 데이터 (MySQL BLOB 타입으로 저장)
    
    def __repr__(self):
        return f"<DocumentVector(id={self.id}, content_preview='{self.content[:30]}...', metadata={self.metadata})>"


def get_vector_db_connection():
    """
    벡터 DB(MySQL)에 연결
    
    Returns:
        session: SQLAlchemy 세션 객체
    """
    if DUMMY_MODE:
        logger.info("더미 벡터 DB 연결 모드 사용 중")
        return "dummy_session"
    
    # 실제 연결 정보는 환경 변수에서 가져옴
    db_url = os.getenv("VECTOR_DB_URL")
    if not db_url:
        raise ValueError("VECTOR_DB_URL 환경 변수가 설정되지 않았습니다.")
    
    # 엔진 생성 및 세션 생성
    try:
        engine = create_engine(db_url)
        
        # 테이블 생성
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        logger.info("벡터 DB 연결 성공")
        return session
    except Exception as e:
        logger.error(f"벡터 DB 연결 실패: {e}")
        raise


def close_vector_db_connection(session):
    """
    벡터 DB 연결 종료
    
    Args:
        session: 벡터 DB 세션 객체
    """
    if DUMMY_MODE:
        logger.info("더미 벡터 DB 연결 종료")
        return
    
    try:
        session.close()
        logger.info("벡터 DB 연결 종료됨")
    except Exception as e:
        logger.error(f"벡터 DB 연결 종료 중 오류 발생: {e}")


def search_similar_vectors(session, query_vector: List[float], limit: int = 5) -> List[Tuple[str, float]]:
    """
    쿼리 벡터와 유사한 문서 검색
    
    Args:
        session: 벡터 DB 세션
        query_vector: 검색할 쿼리 벡터
        limit: 반환할 최대 문서 수
        
    Returns:
        List[Tuple[str, float]]: 검색된 문서와 유사도 점수 리스트
    """
    if DUMMY_MODE:
        logger.info(f"더미 벡터 검색: 쿼리 벡터 길이 {len(query_vector)}, 제한 {limit}")
        # 더미 결과 반환
        return [
            ("AAPL의 2023년 3분기 실적은 예상치를 상회했습니다. 주당 순이익(EPS)은 $1.46로, 애널리스트 예상($1.39)보다 높았습니다.", 0.92),
            ("애플(AAPL)은 최근 AI 기술 투자를 확대하고 있으며, 차기 iOS에 AI 기능을 탑재할 계획을 발표했습니다.", 0.87),
            ("투자자들은 경기침체 우려에도 불구하고 AAPL, MSFT와 같은 대형 기술주의 안정적인 수익성에 주목하고 있습니다.", 0.82)
        ]
    
    # 실제 구현에서는 MySQL에서 유사도 계산 구현
    # (MySQL은 pgvector와 달리 네이티브 벡터 연산을 지원하지 않으므로 애플리케이션 레벨에서 유사도 계산 필요)
    # query = session.query(DocumentVector).all()
    # results = []
    # for doc in query:
    #     # BLOB에서 벡터 역직렬화
    #     doc_vector = np.frombuffer(doc.embedding_blob, dtype=np.float32)
    #     # 코사인 유사도 계산
    #     similarity = cosine_similarity(query_vector, doc_vector)
    #     results.append((doc.content, similarity))
    # 
    # # 유사도로 정렬하고 상위 limit개 반환
    # results.sort(key=lambda x: x[1], reverse=True)
    # return results[:limit]
    raise NotImplementedError("실제 벡터 검색 기능은 아직 구현되지 않았습니다.")


def store_document_vector(session, content: str, embedding: List[float], metadata: Optional[Dict[str, Any]] = None):
    """
    문서 벡터를 DB에 저장
    
    Args:
        session: 벡터 DB 세션
        content: 문서 텍스트
        embedding: 문서의 임베딩 벡터
        metadata: 문서 메타데이터 (출처, 날짜 등)
    """
    if DUMMY_MODE:
        logger.info(f"더미 문서 벡터 저장: {content[:30]}...")
        return
    
    # 실제 구현에서는 DB에 저장
    # # 벡터를 바이너리로 직렬화
    # embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
    # 
    # doc_vector = DocumentVector(
    #     content=content,
    #     embedding_blob=embedding_bytes,
    #     metadata=json.dumps(metadata) if metadata else None
    # )
    # session.add(doc_vector)
    # session.commit()
    raise NotImplementedError("실제 문서 벡터 저장 기능은 아직 구현되지 않았습니다.")


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    두 벡터 간의 코사인 유사도 계산
    
    Args:
        vec1: 첫 번째 벡터
        vec2: 두 번째 벡터
        
    Returns:
        float: 코사인 유사도 (-1 ~ 1 범위)
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm_vec1 = np.linalg.norm(vec1)
    norm_vec2 = np.linalg.norm(vec2)
    
    return dot_product / (norm_vec1 * norm_vec2) 