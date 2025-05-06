# ai_components/services/rag_engine.py
from typing import List, Tuple, Dict, Any, Optional
import os
import json
import logging
from openai import OpenAI
import numpy as np

# 로컬 임포트
from ..vector_store.client import (
    get_vector_db_connection,
    close_vector_db_connection,
    search_similar_vectors
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 더미 모드 설정 (실제 구현에서는 실제 OpenAI API 호출)
DUMMY_MODE = True

# OpenAI 클라이언트 초기화
client = None
if not DUMMY_MODE:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다. 더미 모드로 전환합니다.")
        DUMMY_MODE = True
    else:
        client = OpenAI(api_key=api_key)


def get_embedding(text: str) -> List[float]:
    """
    텍스트 임베딩 생성
    
    Args:
        text: 임베딩할 텍스트
        
    Returns:
        List[float]: 텍스트 임베딩 벡터
    """
    if DUMMY_MODE:
        logger.info(f"더미 임베딩 생성: '{text[:30]}...'")
        # 더미 임베딩 (1536차원, OpenAI text-embedding-ada-002 크기)
        return [0.1] * 1536
    
    # OpenAI API를 통한 임베딩 생성
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"임베딩 생성 중 오류 발생: {e}")
        # 오류 발생 시 더미 임베딩 반환
        return [0.0] * 1536


def get_llm_completion(prompt: str, context: str = "", temperature: float = 0.3) -> str:
    """
    LLM을 통한 텍스트 생성
    
    Args:
        prompt: LLM에 전달할 프롬프트
        context: 검색된 컨텍스트 (RAG)
        temperature: 생성 온도 (낮을수록 결정적)
        
    Returns:
        str: 생성된 텍스트
    """
    if DUMMY_MODE:
        logger.info(f"더미 LLM 응답 생성: 프롬프트 '{prompt[:30]}...'")
        return f"Dummy LLM response for query '{prompt}'. 검색된 정보에 따르면, AAPL의 실적이 양호하며 AI 투자를 확대하고 있습니다. 투자자들은 대형 기술주의 안정성에 주목하고 있습니다."
    
    # 실제 OpenAI API 호출
    try:
        full_prompt = f"""
        다음은 미국 주식에 관한 질문입니다:
        
        {prompt}
        
        다음은 관련 정보입니다:
        {context}
        
        위 정보를 바탕으로 질문에 답변해주세요. 정보가 부족하면 솔직히 모른다고 답변하세요.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "당신은 미국 주식 시장 전문가입니다. 정확하고 객관적인 정보만 제공합니다."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=temperature
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"LLM 응답 생성 중 오류 발생: {e}")
        return f"답변을 생성하는 중 오류가 발생했습니다: {str(e)}"


def retrieve_and_generate(query: str, top_k: int = 3) -> str:
    """
    RAG (Retrieval-Augmented Generation) 파이프라인
    
    Args:
        query: 사용자 질의
        top_k: 검색할 상위 문서 수
        
    Returns:
        str: 생성된 응답
    """
    try:
        # 1. 쿼리 임베딩 생성
        query_embedding = get_embedding(query)
        
        # 2. 벡터 DB 연결
        db_session = get_vector_db_connection()
        
        # 3. 유사 문서 검색
        search_results = search_similar_vectors(db_session, query_embedding, limit=top_k)
        
        # 4. 벡터 DB 연결 종료
        close_vector_db_connection(db_session)
        
        # 5. 검색 결과를 컨텍스트로 구성
        if search_results:
            context = "\n\n".join([f"문서 {i+1} (유사도: {score:.2f}):\n{doc}" 
                                 for i, (doc, score) in enumerate(search_results)])
        else:
            context = "관련 정보를 찾을 수 없습니다."
        
        # 6. LLM으로 응답 생성
        response = get_llm_completion(query, context)
        
        return response
    except Exception as e:
        logger.error(f"RAG 파이프라인 실행 중 오류 발생: {e}")
        return f"죄송합니다. 질문에 답변하는 과정에서 오류가 발생했습니다: {str(e)}"


def batch_process_documents(documents: List[Dict[str, Any]]) -> None:
    """
    여러 문서를 벡터 DB에 일괄 처리하여 저장
    
    Args:
        documents: 처리할 문서 리스트 (텍스트와 메타데이터 포함)
    """
    # 실제 구현에서는 이 함수를 사용하여 문서를 벡터 DB에 저장
    if DUMMY_MODE:
        logger.info(f"더미 문서 배치 처리: {len(documents)}개 문서")
        return
    
    # 실제 구현 코드...
    raise NotImplementedError("실제 배치 처리 기능은 아직 구현되지 않았습니다.") 