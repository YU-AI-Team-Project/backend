from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from aibackend.app import models
from aibackend.app.database import engine
from aibackend.app.routers import auth, stock_info, rag
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ CORS 설정 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080",
                   "http://0.0.0.0:8080"],  # 운영 시 ["https://yourfrontend.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#router폴더 생성해서 기능별 API 관리
app.include_router(auth.router, prefix="/auth")
app.include_router(stock_info.router, prefix="/stocks")
app.include_router(rag.router, prefix="/rag")

#--------------------------배포용--------------------------------
# React 정적 파일 제공
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# 모든 경로 index.html 반환
@app.get("/{full_path:path}")
def serve_react_app_catch_all(full_path: str):
    return FileResponse("frontend/index.html")
#----------------------------------------------------------


#서버 실행 시 DB에 테이블이 없다면 models.py에 있는 정보 토대로 자동생성
models.Base.metadata.create_all(bind=engine)