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
            "report_url": stock.report_url,
            "industry": stock.industry,
            "sector": stock.sector,
            "business_summary": stock.business_summary
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
                "equity": f.equity,
                "gross_profits": f.gross_profits,
                "ebitda": f.ebitda,
                "operating_cashflow": f.operating_cashflow,
                "free_cashflow": f.free_cashflow,
                "revenue_per_share": f.revenue_per_share,
                "gross_margins": f.gross_margins,
                "ebitda_margins": f.ebitda_margins,
                "operating_margins": f.operating_margins,
                "return_on_assets": f.return_on_assets,
                "return_on_equity": f.return_on_equity,
                "debt_to_equity": f.debt_to_equity,
                "quick_ratio": f.quick_ratio,
                "current_ratio": f.current_ratio,
                "earnings_growth": f.earnings_growth,
                "revenue_growth": f.revenue_growth,
                "enterprise_value": f.enterprise_value,
                "enterprise_to_revenue": f.enterprise_to_revenue,
                "enterprise_to_ebitda": f.enterprise_to_ebitda
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
                "close_price": m.close_price,
                "market": m.market,
                "exchange": m.exchange,
                "currency": m.currency,
                "previous_close": m.previous_close,
                "open": m.open,
                "current_price": m.current_price,
                "day_low": m.day_low,
                "day_high": m.day_high,
                "volume": m.volume,
                "average_volume": m.average_volume,
                "pe_ratio_trailing": m.pe_ratio_trailing,
                "pe_ratio_forward": m.pe_ratio_forward,
                "eps_forward": m.eps_forward,
                "eps_current_year": m.eps_current_year,
                "price_eps_current_year": m.price_eps_current_year,
                "beta": m.beta,
                "dividend_rate": m.dividend_rate,
                "dividend_date": m.dividend_date,
                "ex_dividend_date": m.ex_dividend_date,
                "payout_ratio": m.payout_ratio,
                "book_value": m.book_value,
                "fifty_two_week_low": m.fifty_two_week_low,
                "fifty_two_week_high": m.fifty_two_week_high,
                "fifty_two_week_change_percent": m.fifty_two_week_change_percent
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
        .join(Stock, InterestStock.stock_code == Stock.code)
        .filter(InterestStock.user_id == user.id)
        .all()
    )
    
    # 관심종목이 없어도 빈 배열 반환
    result = []
    for i in interests:
        # 각 관심종목의 최신 시장지표 정보 가져오기
        latest_indicator = (
            db.query(MarketIndicator)
            .filter(MarketIndicator.stock_code == i.stock_code)
            .order_by(MarketIndicator.date.desc())
            .first()
        )
        
        # 기본 정보
        stock_info = schemas.InterestStockInfo(
            stock_code=i.stock_code,
            company_name=i.stock.company_name
        )
        
        # 시장지표 정보가 있으면 추가
        if latest_indicator:
            stock_info.current_price = latest_indicator.current_price
            stock_info.previous_close = latest_indicator.previous_close
            stock_info.day_change = latest_indicator.current_price - latest_indicator.previous_close if latest_indicator.current_price and latest_indicator.previous_close else 0
            stock_info.day_change_percent = round(((latest_indicator.current_price - latest_indicator.previous_close) / latest_indicator.previous_close * 100), 2) if latest_indicator.current_price and latest_indicator.previous_close else 0
            stock_info.volume = latest_indicator.volume
            stock_info.market_cap = latest_indicator.market_cap
        
        result.append(stock_info)
    
    return {"interests": result}

@router.post("/interests",summary="관심종목 추가",response_model=schemas.InterestStockAddResponse)
def add_interest_stock(request: schemas.InterestStockAddRequest, db: Session = Depends(get_db)):
    # 1. userID로 사용자 조회
    user = db.query(User).filter(User.userID == request.userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다")
    
    # 2. stock_code로 종목 조회
    stock = db.query(Stock).filter(Stock.code == request.stock_code).first()
    if not stock:
        raise HTTPException(status_code=404, detail="해당 종목을 찾을 수 없습니다")
    
    # 3. 이미 관심종목으로 등록되어 있는지 확인
    existing_interest = db.query(InterestStock).filter(
        InterestStock.user_id == user.id,
        InterestStock.stock_code == request.stock_code
    ).first()
    
    if existing_interest:
        raise HTTPException(status_code=400, detail="이미 관심종목으로 등록된 종목입니다")
    
    # 4. 관심종목 추가
    new_interest = InterestStock(
        user_id=user.id,
        stock_code=request.stock_code
    )
    
    db.add(new_interest)
    db.commit()
    db.refresh(new_interest)
    
    return {
        "message": "관심종목이 성공적으로 추가되었습니다",
        "interest": {
            "stock_code": stock.code,
            "company_name": stock.company_name
        }
    }

@router.delete("/interests",summary="관심종목 삭제",response_model=schemas.InterestStockRemoveResponse)
def remove_interest_stock(request: schemas.InterestStockRemoveRequest, db: Session = Depends(get_db)):
    # 1. userID로 사용자 조회
    user = db.query(User).filter(User.userID == request.userID).first()
    if not user:
        raise HTTPException(status_code=404, detail="해당 사용자를 찾을 수 없습니다")
    
    # 2. 관심종목이 존재하는지 확인
    existing_interest = db.query(InterestStock).filter(
        InterestStock.user_id == user.id,
        InterestStock.stock_code == request.stock_code
    ).first()
    
    if not existing_interest:
        raise HTTPException(status_code=404, detail="관심종목으로 등록되지 않은 종목입니다")
    
    # 3. 관심종목 삭제
    db.delete(existing_interest)
    db.commit()
    
    return {
        "message": "관심종목이 성공적으로 삭제되었습니다"
    }