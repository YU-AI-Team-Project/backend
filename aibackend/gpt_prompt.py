
import openai
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from uuid import uuid4
from datetime import datetime

#환경 설정
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")

#DB 설정
Base = declarative_base()
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

#모델 정의
class GPTAnalysisResult(Base):
    __tablename__ = "gpt_analysis_results"
    id = Column(String, primary_key=True)
    stock_code = Column(String)
    news_id = Column(String)
    result_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

#FastAPI 초기화
app = FastAPI()

#프롬프트
system_prompt = """당신은 월스트리트 출신의 전문 주식 분석가입니다.

다음으로 주어질 뉴스 기사와 재무 데이터를 바탕으로, 해당 기업의 투자 적합성 여부를 전문가 관점에서 분석하세요.

📌 주어지는 데이터:
- 뉴스 기사 (제목 + 본문)
- 재무 정보: 최근 분기 기준 아래 8가지 주요 지표
    1. 매출액
    2. 영업이익
    3. 순이익
    4. 부채비율 (%)
    5. ROE (%)
    6. PER (주가수익비율)
    7. PBR (주가순자산비율)
    8. 배당수익률 (%)

🎯 당신의 분석 작업:
1. 뉴스 기사 분석 및 긍/부정 판단 (요약하지 말고 내용 정리)
2. 재무 지표 분석
3. 최종 판단 제시 (매수 추천 / 관망 / 주의 요망)

🧾 출력 형식 (엄수):

[뉴스 분석]:
- 핵심 내용 정리:
- 투자 관점 판단: ✅ / ⚠️
- 판단 근거:

[재무 분석]:
- 수익성 분석:
- 재무건전성:
- 시장지표 해석:

[종합 판단]:
- 판단:
- 근거:

⚠️ 작성 조건:
- 분석은 전문가 시점에서 정확하고 간결하게 작성
- 수치를 인용해 구체적으로 설명
"""

#요청 스키마
class AnalyzeRequest(BaseModel):
    stock_code: str
    news_id: str
    news: str
    financials: str

#GPT 분석 API
@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    session = SessionLocal()
    try:
        user_prompt = f"뉴스: {request.news}\n재무: {request.financials}"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        result_text = response["choices"][0]["message"]["content"]
        result_id = str(uuid4())

        # 결과 DB 저장
        result = GPTAnalysisResult(
            id=result_id,
            stock_code=request.stock_code,
            news_id=request.news_id,
            result_text=result_text
        )
        session.add(result)
        session.commit()

        return {
            "status": "success",
            "analysis_id": result_id,
            "gpt_report": result_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()
