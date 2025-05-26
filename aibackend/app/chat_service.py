from sqlalchemy.orm import Session
from aibackend.app.models import ChatHistory, ChatRole, User
from datetime import datetime
from aibackend.app.database import get_db
from fastapi import HTTPException

# 채팅 내용 저장 기능
def save_chat(userID: str, stock_code: str, role: ChatRole, chat_content: str):
    db: Session = next(get_db())
    
    # userID로 사용자 테이블 ID 조회
    user = db.query(User).filter(User.userID == userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다")
    
    chat_history = ChatHistory(
        user_id = user.id,
        stock_code = stock_code,
        role = role,
        chat = chat_content,
        created_at = datetime.now()
    )
    db.add(chat_history)
    db.commit()
    db.refresh(chat_history)
    return chat_history
    
# 채팅 내용 불러오기 기능
def get_recent_chats(userID: str, stock_code: str, limit: int = 100):
    db: Session = next(get_db())
    
    # userID로 사용자 테이블 ID 조회
    user = db.query(User).filter(User.userID == userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다")
    
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.user_id == user.id,
                ChatHistory.stock_code == stock_code)
        .order_by(ChatHistory.created_at.asc())
        .limit(limit)
        .all()
    )
    
#채팅 내용 삭제하기 기능
def delete_chats(userID: str, stock_code: str):
    db: Session = next(get_db())
    
    # userID로 사용자 테이블 ID 조회
    user = db.query(User).filter(User.userID == userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다")
    
    db.query(ChatHistory).filter(
        ChatHistory.user_id == user.id,
        ChatHistory.stock_code == stock_code
    ).delete()
    db.commit()