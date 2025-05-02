from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer,primary_key=True, autoincrement=True)
    userID =  mapped_column(String(13), nullable=False)
    passwd = mapped_column(String(50),nullable=False)
    
    interests = relationship("InterestStock",back_populates="user",cascade="all, delete-orphan")
    
class Stock(Base):
    __tablename__ = "stocks"
    id = mapped_column(String(4),primary_key=True)
    company_name = mapped_column(String(100),nullable=False)
    financial_info = mapped_column(Text)
    report_url = mapped_column(String(255))
    
    interests = relationship("InterestStock", back_populates="stock", cascade="all, delete-orphan")
    
class InterestStock(Base):
    __tablename__ = "interest_stocks"
    id = mapped_column(Integer,primary_key=True,autoincrement=True)
    user_id = mapped_column(Integer,ForeignKey("users.id"),nullable=False)
    stock_id = mapped_column(String(4),ForeignKey("stocks.id"),nullable=False)
    
    user = relationship("User", back_populates="interests")
    stock = relationship("Stock", back_populates="interests")
    
    
    