from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from dotenv import load_dotenv
import os

load_dotenv()

pg_user = os.getenv("NEWS_DB_USER")
pg_passwd = os.getenv("NEWS_DB_PASSWD")
pg_host = os.getenv("NEWS_DB_HOST")
pg_port = os.getenv("NEWS_DB_PORT")
pg_db = os.getenv("NEWS_DB_NAME")

NEWS_DB_URL = f'postgresql+psycopg2://{pg_user}:{pg_passwd}@{pg_host}:{pg_port}/{pg_db}'

NewsEngine = create_engine(NEWS_DB_URL,echo=True)
NewsSessionLocal = sessionmaker(autocommit=False,autoflush=False,bind=NewsEngine)
NewsBase = declarative_base()

def get_news_db():
    db: Session = NewsSessionLocal()
    try:
        yield db
    finally:
        db.close()