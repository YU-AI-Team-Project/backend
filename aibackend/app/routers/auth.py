from fastapi import APIRouter, Request, Form, Response, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from aibackend.app import models
from aibackend.app.database import get_db


router = APIRouter()

@router.post("/signup",summary="회원가입", description="새 사용자 계정을 등록")
def signup(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(models.User).filter(models.User.userID == username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 아이디입니다"
        )
    new_user = models.User(userID=username,passwd = password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"message":"회원가입 성공"}

@router.get("/",response_class=HTMLResponse,summary="쿠키 정보 확인")
def read_root(request:Request):
    username = request.cookies.get("username")
    if username:
        return f"{username}님 환영합니다!"
    return "로그인이 필요합니다"

@router.post("/login",summary="로그인 API")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
    ):
    
    user = db.query(models.User).filter(models.User.userID == username).first()
    
    if user and user.passwd == password:
        response = JSONResponse(
            content={"message": "로그인 성공", "username": username},
            status_code=200
        )
        response.set_cookie(key="username",value=username)
        return response
    return JSONResponse(
        content={"message": "로그인 실패"},
        status_code=401
    )

@router.get("/logout",summary="로그아웃 API")
def logout():
    response = JSONResponse(
        content={"message": "로그아웃 성공"},
        status_code=200
    )
    response.delete_cookie("username")
    return response

@router.get("/check", summary="인증 상태 확인 API")
def check_auth(request: Request):
    username = request.cookies.get("username")
    if username:
        return JSONResponse(
            content={"isAuthenticated": True, "username": username},
            status_code=200
        )
    return JSONResponse(
        content={"isAuthenticated": False},
        status_code=401
    )
    