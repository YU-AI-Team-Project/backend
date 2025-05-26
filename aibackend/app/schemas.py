from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal

class StockBase(BaseModel):
    code: str
    company_name: str
    financial_info: Optional[str]
    report_url: Optional[str]
    industry: Optional[str]
    sector: Optional[str]
    business_summary: Optional[str]

class FinancialStatementBase(BaseModel):
    report_period: str
    report_type: str
    revenue: Optional[int]
    operating_income: Optional[int]
    net_income: Optional[int]
    assets: Optional[int]
    liabilities: Optional[int]
    equity: Optional[int]
    gross_profits: Optional[int]
    ebitda: Optional[int]
    operating_cashflow: Optional[int]
    free_cashflow: Optional[int]
    revenue_per_share: Optional[Decimal]
    gross_margins: Optional[Decimal]
    ebitda_margins: Optional[Decimal]
    operating_margins: Optional[Decimal]
    return_on_assets: Optional[Decimal]
    return_on_equity: Optional[Decimal]
    debt_to_equity: Optional[Decimal]
    quick_ratio: Optional[Decimal]
    current_ratio: Optional[Decimal]
    earnings_growth: Optional[Decimal]
    revenue_growth: Optional[Decimal]
    enterprise_value: Optional[int]
    enterprise_to_revenue: Optional[Decimal]
    enterprise_to_ebitda: Optional[Decimal]

class MarketIndicatorBase(BaseModel):
    date: date
    market_cap: Optional[float]
    per: Optional[float]
    pbr: Optional[float]
    eps: Optional[float]
    bps: Optional[float]
    dividend_yield: Optional[float]
    close_price: Optional[float]
    market: Optional[str]
    exchange: Optional[str]
    currency: Optional[str]
    previous_close: Optional[Decimal]
    open: Optional[Decimal]
    current_price: Optional[Decimal]
    day_low: Optional[Decimal]
    day_high: Optional[Decimal]
    volume: Optional[int]
    average_volume: Optional[int]
    pe_ratio_trailing: Optional[Decimal]
    pe_ratio_forward: Optional[Decimal]
    eps_forward: Optional[Decimal]
    eps_current_year: Optional[Decimal]
    price_eps_current_year: Optional[Decimal]
    beta: Optional[Decimal]
    dividend_rate: Optional[Decimal]
    dividend_date: Optional[date]
    ex_dividend_date: Optional[date]
    payout_ratio: Optional[Decimal]
    book_value: Optional[Decimal]
    fifty_two_week_low: Optional[Decimal]
    fifty_two_week_high: Optional[Decimal]
    fifty_two_week_change_percent: Optional[Decimal]

class EarningsForecastBase(BaseModel):
    fiscal_year: int
    expected_eps: Optional[float]
    expected_revenue: Optional[float]
    expected_operating_income: Optional[float]
    source: str

class StockDetailResponse(BaseModel):
    stock: StockBase
    financial_statements: List[FinancialStatementBase]
    market_indicators: List[MarketIndicatorBase]
    earnings_forecasts: List[EarningsForecastBase]
    
class InterestStockInfo(BaseModel):
    stock_code: str
    company_name: str
    
class InterestStockResponse(BaseModel):
    interests: List[InterestStockInfo]

# 관심종목 추가 요청 스키마
class InterestStockAddRequest(BaseModel):
    userID: str
    stock_code: str

# 관심종목 추가 응답 스키마  
class InterestStockAddResponse(BaseModel):
    message: str
    interest: InterestStockInfo

# 관심종목 삭제 요청 스키마
class InterestStockRemoveRequest(BaseModel):
    userID: str
    stock_code: str

# 관심종목 삭제 응답 스키마
class InterestStockRemoveResponse(BaseModel):
    message: str
    
class ReportCreate(BaseModel):
    stock_code: str
    report: str
    
class ReportRead(BaseModel):
    id: int
    stock_code: str
    report: str
    created_at: datetime