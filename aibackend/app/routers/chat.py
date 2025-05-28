from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from enum import Enum

from aibackend.app.database import get_db
from aibackend.app.models import ChatHistory, ChatRole
from aibackend.app.chat_service import get_recent_chats, save_chat, delete_chats
from aibackend.app.schemas import ChatRequest, ChatResponse
from aibackend.app.services.rag_service import rag_service
from aibackend.app.news_vector_db import get_news_db

router = APIRouter()

# RAG 채팅용 스키마
class RagChatRequest(BaseModel):
    userID: str
    stock_code: Optional[str] = None
    message: str

class RagChatResponse(BaseModel):
    user_query: str
    response: str
    sources: List[dict]
    source_count: int
    success: bool
    error: Optional[str] = None

@router.post("/rag", summary="RAG 기반 채팅 응답", response_model=RagChatResponse)
def chat_with_rag(
    request: RagChatRequest,
    news_db: Session = Depends(get_news_db),
    main_db: Session = Depends(get_db)
):
    """사용자 질문에 대해 뉴스 기반 RAG 응답 생성"""
    try:
        # RAG 서비스로 응답 생성 (DB에서 직접 채팅 내역과 보고서 가져옴)
        result = rag_service.chat_with_rag(
            user_query=request.message,
            user_id=request.userID,
            stock_code=request.stock_code,
            news_db=news_db,
            main_db=main_db,
            top_k=25,
            similarity_threshold=0.2
        )
        
        # 채팅 기록 저장 (사용자 메시지)
        if request.stock_code:
            save_chat(request.userID, request.stock_code, ChatRole.USER, request.message)
            # AI 응답도 저장
            save_chat(request.userID, request.stock_code, ChatRole.GPT, result["response"])
        
        return RagChatResponse(**result)
        
    except Exception as e:
        print(f"RAG 채팅 오류: {e}", flush=True)
        return RagChatResponse(
            user_query=request.message,
            response="죄송합니다. 응답 생성 중 오류가 발생했습니다.",
            sources=[],
            source_count=0,
            success=False,
            error=str(e)
        )

@router.get("/{userID}/{stock_code}",summary="채팅 기록 불러오기", response_model=List[ChatResponse])
def get_chats(
    userID: str,
    stock_code: str,
    limit: int = Query(100)
):
    chats = get_recent_chats(userID,stock_code,limit)
    return chats

@router.post("/",summary="채팅 기록 저장하기", response_model=ChatResponse)
def post_chat(request: ChatRequest):
    chat = save_chat(request.userID, request.stock_code, ChatRole(request.role), request.chat)
    return chat

@router.delete("/{userID}/{stock_code}", summary="채팅 기록 삭제하기")
def clear_chat_history(userID: str, stock_code: str):
    delete_chats(userID, stock_code)
    return {"message": "채팅 기록이 삭제됐습니다."}