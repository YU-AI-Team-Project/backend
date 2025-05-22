from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from aibackend.app.database import get_db
from aibackend.app.models import User,Stock,InterestStock, FinancialStatement, MarketIndicator, EarningsForecast
from aibackend.app import schemas

router = APIRouter()

@router.get("/{stock_code}",summary="기업코드로 종목 정보(기업 정보,재무정보,시장지표,실적정망) 조회",response_model=schemas.StockDetailResponse)
def get_stock_detail(stock_code: str, db: Session = Depends(get_db)):
    # 종목 기본 정보
    stock = db.query(Stock).filter(Stock.code == stock_code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="종목 정보를 찾을 수 없습니다.")

    # 재무제표
    financials = db.query(FinancialStatement).filter(FinancialStatement.stock_code == stock_code).all()

    # 시세지표
    indicators = db.query(MarketIndicator).filter(MarketIndicator.stock_code == stock_code).order_by(MarketIndicator.date.asc()).all()

    # 실적추정
    forecasts = db.query(EarningsForecast).filter(EarningsForecast.stock_code == stock_code).all()

    return {
        "stock": {
            "code": stock.code,
            "company_name": stock.company_name,
            "financial_info": stock.financial_info,
            "report_url": stock.report_url
        },
        "financial_statements": [
            {
                "report_period": f.report_period,
                "report_type": f.report_type,
                "revenue": f.revenue,
                "operating_income": f.operating_income,
                "net_income": f.net_income,
                "assets": f.assets,
                "liabilities": f.liabilities,
                "equity": f.equity
            } for f in financials
        ],
        "market_indicators": [
            {
                "date": m.date,
                "market_cap": m.market_cap,
                "per": m.per,
                "pbr": m.pbr,
                "eps": m.eps,
                "bps": m.bps,
                "dividend_yield": m.dividend_yield,
                "close_price": m.close_price
            } for m in indicators
        ],
        "earnings_forecasts": [
            {
                "fiscal_year": e.fiscal_year,
                "expected_eps": e.expected_eps,
                "expected_revenue": e.expected_revenue,
                "expected_operating_income": e.expected_operating_income,
                "source": e.source
            } for e in forecasts
        ]
    }
    
@router.get("/interests/{userID}",summary="사용자 관심종목 조회",response_model=schemas.InterestStockResponse)
def get_my_interest_stocks(userID:str, db: Session = Depends(get_db)):
    #1 userID로 사용자 테이블 ID 조회
    user = db.query(User).filter(User.userID == userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다")
    
    print("userID는"+str(user.id))
    # 2. 사용자 ID로 관심종목 조회
    interests = (
        db.query(InterestStock)
        .join(User)
        .filter(InterestStock.user_id == user.id)
        .all()
    )
    
    if not interests:
        raise HTTPException(status_code=404, detail="관심 종목이 없습니다")
    
    result = [
        schemas.InterestStockInfo(
            stock_code=i.stock_code,
            company_name=i.stock.company_name
        )
        for i in interests
    ]
    
    return {"interests":result}