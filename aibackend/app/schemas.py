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
    revenue: float
    operating_income: float
    net_income: float
    assets: float
    liabilities: float
    equity: float

class MarketIndicatorBase(BaseModel):
    date: date
    market_cap: float
    per: float
    pbr: float
    eps: float
    bps: float
    dividend_yield: float
    close_price: float

class EarningsForecastBase(BaseModel):
    fiscal_year: int
    expected_eps: float
    expected_revenue: float
    expected_operating_income: float
    source: str

class StockDetailResponse(BaseModel):
    stock: StockBase
    financial_statements: List[FinancialStatementBase]
    market_indicators: List[MarketIndicatorBase]
    earnings_forecasts: List[EarningsForecastBase]