from sqlalchemy.orm import Session
from aibackend.app.models import ChatHistory, ChatRole
from datetime import datetime
from aibackend.app.database import get_db

# 채팅 내용 저장 기능
def save_chat(user_id: int, stock_code: str, role: ChatRole, chat: str):
    db: Session = next(get_db())
    chat = ChatHistory(
        user_id = user_id,
        stock_code = stock_code,
        role = role,
        chat = chat,
        created_at = datetime.now()
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat
    
# 채팅 내용 불러오기 기능
def get_recent_chats(user_id: int, stock_code: str, limit: int = 100):
    db: Session = next(get_db())
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user_id,
                ChatHistory.stock_code == stock_code)
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )
    
#채팅 내용 삭제하기 기능
def delete_chats(user_id: int, stock_code: str):
    db: Session = next(get_db())
    db.query(ChatHistory).filter(
        ChatHistory.user_id == user_id,
        ChatHistory.stock_code == stock_code
    ).delete()
    db.commit()