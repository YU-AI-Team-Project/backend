from sqlalchemy import Integer, String, Boolean, ForeignKey, Text, BigInteger, Float, Date, DateTime,Enum
from sqlalchemy.orm import mapped_column, relationship
from .database import Base
import enum

# 보고서 종류 Enum
class ReportType(str, enum.Enum):
    annual = "annual"
    quarter = "quarter"

# 사용자 테이블
class User(Base):
    __tablename__ = "users"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    userID = mapped_column(String(13), nullable=False)
    passwd = mapped_column(String(50), nullable=False)
    
    interests = relationship("InterestStock", back_populates="user", cascade="all, delete-orphan")

# 종목 테이블
class Stock(Base):
    __tablename__ = "stocks"
    code = mapped_column(String(20), primary_key=True)
    company_name = mapped_column(String(100), nullable=False)
    financial_info = mapped_column(Text)
    report_url = mapped_column(String(255))
    
    interests = relationship("InterestStock", back_populates="stock", cascade="all, delete-orphan")
    financial_statements = relationship("FinancialStatement", back_populates="stock", cascade="all, delete-orphan")
    market_indicators = relationship("MarketIndicator", back_populates="stock", cascade="all, delete-orphan")
    earnings_forecasts = relationship("EarningsForecast", back_populates="stock", cascade="all, delete-orphan")

# 관심종목 테이블
class InterestStock(Base):
    __tablename__ = "interest_stocks"
    id = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    stock_code = mapped_column(String(20), ForeignKey("stocks.code"), nullable=False)
    
    user = relationship("User", back_populates="interests")
    stock = relationship("Stock", back_populates="interests")

# 재무제표 테이블
class FinancialStatement(Base):
    __tablename__ = "financial_statements"

    id = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = mapped_column(String(20), ForeignKey("stocks.code"), nullable=False)
    report_period = mapped_column(String(10), nullable=False)
    report_type = mapped_column(Enum(ReportType), nullable=False)
    revenue = mapped_column(BigInteger)
    operating_income = mapped_column(BigInteger)
    net_income = mapped_column(BigInteger)
    assets = mapped_column(BigInteger)
    liabilities = mapped_column(BigInteger)
    equity = mapped_column(BigInteger)

    stock = relationship("Stock", back_populates="financial_statements")

# 시가/지표 테이블
class MarketIndicator(Base):
    __tablename__ = "market_indicators"

    id = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = mapped_column(String(20), ForeignKey("stocks.code"), nullable=False)
    date = mapped_column(Date, nullable=False)
    market_cap = mapped_column(BigInteger)
    per = mapped_column(Float)
    pbr = mapped_column(Float)
    eps = mapped_column(Float)
    bps = mapped_column(Float)
    dividend_yield = mapped_column(Float)
    close_price = mapped_column(Float)
    created_at = mapped_column(DateTime)

    stock = relationship("Stock", back_populates="market_indicators")

# 실적 전망 테이블
class EarningsForecast(Base):
    __tablename__ = "earnings_forecasts"

    id = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_code = mapped_column(String(20), ForeignKey("stocks.code"), nullable=False)
    fiscal_year = mapped_column(Integer, nullable=False)
    expected_eps = mapped_column(Float)
    expected_revenue = mapped_column(BigInteger)
    expected_operating_income = mapped_column(BigInteger)
    source = mapped_column(String(100))
    created_at = mapped_column(DateTime)

    stock = relationship("Stock", back_populates="earnings_forecasts")