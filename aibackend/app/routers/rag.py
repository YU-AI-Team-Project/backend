from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from aibackend.app.news_vector_db import get_news_db
from aibackend.app.services.rag_service import rag_service

router = APIRouter(tags=["RAG"])

# Request/Response 모델들
class RAGQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    similarity_threshold: Optional[float] = 0.7
    system_prompt: Optional[str] = None

class StockAnalysisRequest(BaseModel):
    stock_code: str
    news_query: str
    financial_data: Optional[str] = None

class NewsSource(BaseModel):
    id: str
    title: str
    content: str
    published_at: Optional[str]
    similarity: float

class RAGResponse(BaseModel):
    query: str
    response: str
    sources: list[NewsSource]
    success: bool

class StockAnalysisResponse(BaseModel):
    stock_code: str
    query: str
    response: str
    sources: list[NewsSource]
    has_financial_data: bool
    success: bool

@router.post("/query", response_model=RAGResponse)
async def rag_query(
    request: RAGQueryRequest,
    db: Session = Depends(get_news_db)
):
    """
    RAG 시스템을 사용하여 질문에 답변합니다.
    뉴스 데이터베이스에서 관련 기사를 검색하고, 이를 바탕으로 AI가 답변을 생성합니다.
    """
    try:
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="질문이 비어있습니다.")
        
        result = rag_service.rag_query(
            query=request.query,
            db=db,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            system_prompt=request.system_prompt
        )
        
        return RAGResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG 처리 중 오류 발생: {str(e)}")

@router.get("/search")
async def similarity_search(
    query: str = Query(..., description="검색할 질문"),
    top_k: int = Query(5, ge=1, le=20, description="반환할 최대 결과 수"),
    similarity_threshold: float = Query(0.7, ge=0.0, le=1.0, description="유사도 임계값"),
    db: Session = Depends(get_news_db)
):
    """
    벡터 유사도 검색만 수행합니다. (응답 생성 없이)
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="검색어가 비어있습니다.")
        
        similar_docs = rag_service.similarity_search(
            query=query,
            db=db,
            top_k=top_k,
            similarity_threshold=similarity_threshold
        )
        
        return {
            "query": query,
            "results": similar_docs,
            "count": len(similar_docs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 중 오류 발생: {str(e)}")

@router.post("/generate")
async def generate_with_context(
    request: dict,
    db: Session = Depends(get_news_db)
):
    """
    사용자가 직접 제공한 컨텍스트를 바탕으로 응답을 생성합니다.
    """
    try:
        query = request.get("query")
        context_docs = request.get("context_docs", [])
        system_prompt = request.get("system_prompt")
        
        if not query:
            raise HTTPException(status_code=400, detail="질문이 필요합니다.")
        
        if not context_docs:
            raise HTTPException(status_code=400, detail="컨텍스트 문서가 필요합니다.")
        
        response = rag_service.generate_response(
            query=query,
            context_docs=context_docs,
            system_prompt=system_prompt
        )
        
        return {
            "query": query,
            "response": response,
            "context_count": len(context_docs)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"응답 생성 중 오류 발생: {str(e)}")

@router.post("/analyze-stock", response_model=StockAnalysisResponse)
async def analyze_stock(
    request: StockAnalysisRequest,
    db: Session = Depends(get_news_db)
):
    """
    특정 종목에 대한 전문적인 투자 분석을 수행합니다.
    뉴스 기사와 재무 데이터(선택사항)를 종합하여 투자 의견을 제시합니다.
    """
    try:
        if not request.stock_code.strip():
            raise HTTPException(status_code=400, detail="종목 코드가 필요합니다.")
        
        if not request.news_query.strip():
            raise HTTPException(status_code=400, detail="분석 질문이 필요합니다.")
        
        result = rag_service.generate_stock_analysis(
            stock_code=request.stock_code,
            news_query=request.news_query,
            financial_data=request.financial_data,
            db=db
        )
        
        return StockAnalysisResponse(**result)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"주식 분석 중 오류 발생: {str(e)}")

@router.get("/health")
async def rag_health_check():
    """RAG 시스템 상태 확인"""
    try:
        # OpenAI API 키 확인
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        
        return {
            "status": "healthy",
            "openai_configured": bool(api_key and api_key != ""),
            "models": {
                "embedding": rag_service.embedding_model,
                "chat": rag_service.chat_model
            }
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        } 