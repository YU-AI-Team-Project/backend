from sqlalchemy import Integer, String, Boolean, ForeignKey, Text, BigInteger, Float, Date, DateTime, DECIMAL
from sqlalchemy.orm import mapped_column, relationship
from .database import Base

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
    industry = mapped_column(String(100))
    sector = mapped_column(String(100))
    business_summary = mapped_column(Text)
    
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
    report_type = mapped_column(String(15), nullable=False)
    revenue = mapped_column(BigInteger)
    operating_income = mapped_column(BigInteger)
    net_income = mapped_column(BigInteger)
    assets = mapped_column(BigInteger)
    liabilities = mapped_column(BigInteger)
    equity = mapped_column(BigInteger)
    gross_profits = mapped_column(BigInteger)
    ebitda = mapped_column(BigInteger)
    operating_cashflow = mapped_column(BigInteger)
    free_cashflow = mapped_column(BigInteger)
    revenue_per_share = mapped_column(DECIMAL(10, 3))
    gross_margins = mapped_column(DECIMAL(10, 5))
    ebitda_margins = mapped_column(DECIMAL(10, 5))
    operating_margins = mapped_column(DECIMAL(10, 5))
    return_on_assets = mapped_column(DECIMAL(10, 5))
    return_on_equity = mapped_column(DECIMAL(10, 5))
    debt_to_equity = mapped_column(DECIMAL(10, 3))
    quick_ratio = mapped_column(DECIMAL(10, 3))
    current_ratio = mapped_column(DECIMAL(10, 3))
    earnings_growth = mapped_column(DECIMAL(10, 5))
    revenue_growth = mapped_column(DECIMAL(10, 5))
    enterprise_value = mapped_column(BigInteger)
    enterprise_to_revenue = mapped_column(DECIMAL(10, 3))
    enterprise_to_ebitda = mapped_column(DECIMAL(10, 3))

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
    market = mapped_column(String(50))
    exchange = mapped_column(String(50))
    currency = mapped_column(String(10))
    previous_close = mapped_column(DECIMAL(10, 2))
    open = mapped_column(DECIMAL(10, 2))
    current_price = mapped_column(DECIMAL(10, 4))
    day_low = mapped_column(DECIMAL(10, 2))
    day_high = mapped_column(DECIMAL(10, 2))
    volume = mapped_column(BigInteger)
    average_volume = mapped_column(BigInteger)
    pe_ratio_trailing = mapped_column(DECIMAL(10, 4))
    pe_ratio_forward = mapped_column(DECIMAL(10, 4))
    eps_forward = mapped_column(DECIMAL(10, 4))
    eps_current_year = mapped_column(DECIMAL(10, 5))
    price_eps_current_year = mapped_column(DECIMAL(10, 5))
    beta = mapped_column(DECIMAL(10, 3))
    dividend_rate = mapped_column(DECIMAL(10, 2))
    dividend_date = mapped_column(Date)
    ex_dividend_date = mapped_column(Date)
    payout_ratio = mapped_column(DECIMAL(10, 4))
    book_value = mapped_column(DECIMAL(10, 3))
    fifty_two_week_low = mapped_column(DECIMAL(10, 2))
    fifty_two_week_high = mapped_column(DECIMAL(10, 2))
    fifty_two_week_change_percent = mapped_column(DECIMAL(10, 5))

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