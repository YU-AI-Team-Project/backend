from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

from dotenv import load_dotenv
import os

#.env 파일 로드
load_dotenv()

user = os.getenv("DB_USER")
passwd = os.getenv("DB_PASSWORD")
host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
db = os.getenv("DB_NAME")
'''instance_connection_name = os.environ.get("INSTANCE_CONNECTION_NAME")

# Unix 소켓 경로 설정
unix_socket_path = f"/cloudsql/{instance_connection_name}"

DB_URL = f"mysql+pymysql://{user}:{passwd}@/{db}?unix_socket={unix_socket_path}&charset=utf8mb4"'''

DB_URL = f"mysql+pymysql://{user}:{passwd}@{host}:{port}/{db}?charset=utf8mb4"

engine = create_engine(DB_URL,echo=True)
SessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base = declarative_base()

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()