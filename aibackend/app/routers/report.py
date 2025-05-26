from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from aibackend.app.database import get_db
from aibackend.app.models import Reports
from aibackend.app.schemas import ReportCreate, ReportRead

router = APIRouter()

@router.post("/", summary="보고서 저장하기",response_model=ReportRead)
def create_report(report: ReportCreate, db: Session = Depends(get_db)):
    db_report = Reports(
        stock_code=report.stock_code,
        report=report.report,
        created_at=datetime.now()
    )
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router.get("/{stock_code}", summary="보고서 읽어오기", response_model=List[ReportRead])
def get_reports(stock_code: str, db: Session = Depends(get_db)):
    reports = db.query(Reports).filter(Reports.stock_code == stock_code).order_by(Reports.created_at.desc()).all()
    if not reports:
        raise HTTPException(status_code=404, detail="보고서 내용이 없습니다")
    return reports