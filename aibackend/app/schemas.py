from pydantic import BaseModel
from typing import List, Optional
from datetime import date

class StockBase(BaseModel):
    code: str
    company_name: str
    financial_info: Optional[str]
    report_url: Optional[str]

class FinancialStatementBase(BaseModel):
    report_period: str
    report_type: str
    revenue: Optional[float]
    operating_income: Optional[float]
    net_income: Optional[float]
    assets: Optional[float]
    liabilities: Optional[float]
    equity: Optional[float]

class MarketIndicatorBase(BaseModel):
    date: date
    market_cap: Optional[float]
    per: Optional[float]
    pbr: Optional[float]
    eps: Optional[float]
    bps: Optional[float]
    dividend_yield: Optional[float]
    close_price: Optional[float]

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