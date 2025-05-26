from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from enum import Enum

from aibackend.app.database import get_db
from aibackend.app.models import ChatHistory, ChatRole
from aibackend.app.chat_service import get_recent_chats, save_chat, delete_chats
from aibackend.app.schemas import ChatRequest, ChatResponse

router = APIRouter()

@router.get("/",summary="채팅 기록 불러오기", response_model=List[ChatResponse])
def get_chats(
    user_id: int = Query(...),
    stock_code: str = Query(...),
    limit: int = 100
):
    chats = get_recent_chats(user_id,stock_code,limit)
    return chats

@router.post("/",summary="채팅 기록 저장하기", response_model=ChatResponse)
def post_chat(request: ChatRequest):
    chat = save_chat(request.user_id, request.stock_code, ChatRole(request.role), request.chat)
    return chat

@router.delete("/", summary="채팅 기록 삭제하기")
def clear_chat_history(user_id: int = Query(...), stock_code: str = Query(...)):
    delete_chats(user_id, stock_code)
    return {"message": "채팅 기록이 삭제됐습니다."}