from fastapi import FastAPI
from app import models
from app.database import engine
from app.routers import auth, stock_info

app = FastAPI()

#router폴더 생성해서 기능별 API 관리
app.include_router(auth.router)
app.include_router(stock_info.router)


#서버 실행 시 DB에 테이블이 없다면 models.py에 있는 정보 토대로 자동생성
models.Base.metadata.create_all(bind=engine)