from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
from aibackend.app.news_vector_db import get_news_db
from aibackend.app.database import get_db
from aibackend.app.services.rag_service import rag_service

router = APIRouter(tags=["보고서 작성"])

@router.get("/report/{stock_code}")
async def get_stock_report(
    stock_code: str,
    main_db: Session = Depends(get_db),
    news_db: Session = Depends(get_news_db)
):
    """
    종목 보고서를 조회하거나 새로 생성합니다.
    저장된 보고서가 있으면 반환하고, 없으면 자동으로 새 보고서를 생성합니다.
    """
    try:
        if not stock_code.strip():
            raise HTTPException(status_code=400, detail="종목 코드가 필요합니다.")
        
        # DB에서 보고서 조회
        from ..models import Reports, Stock
        
        # 종목이 존재하는지 확인
        stock = main_db.query(Stock).filter(Stock.code == stock_code).first()
        if not stock:
            raise HTTPException(status_code=404, detail="해당 종목을 찾을 수 없습니다.")
        
        # 해당 종목의 가장 최근 보고서 조회
        report = main_db.query(Reports).filter(
            Reports.stock_code == stock_code
        ).order_by(Reports.created_at.desc()).first()
        
        # 보고서가 있으면 기존 보고서 반환
        if report:
            return {
                "stock_code": stock_code,
                "company_name": stock.company_name,
                "report": report.report,
                "created_at": report.created_at,
                "is_new": False,
                "success": True
            }
        
        # 보고서가 없으면 새로 생성
        print(f"보고서가 없어서 새로 생성합니다: {stock_code}")
        
        result = rag_service.generate_stock_analysis(
            stock_code=stock_code,
            news_db=news_db,
            main_db=main_db
        )
        
        if result.get('success'):
            # 새로 생성된 보고서 반환
            return {
                "stock_code": stock_code,
                "company_name": stock.company_name,
                "report": result['response'],
                "created_at": "방금 생성됨",
                "is_new": True,
                "success": True
            }
        else:
            raise HTTPException(status_code=500, detail="보고서 생성에 실패했습니다.")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"보고서 처리 중 오류 발생: {str(e)}") 