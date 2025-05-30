import openai
import os
import csv
import pandas as pd
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text, create_engine
from dotenv import load_dotenv
from datetime import datetime, date

load_dotenv()

class HistoricalReportGenerator:
    def __init__(self):
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60.0
        )
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4o"
        
        # MySQL 연결 설정 (주식/재무 데이터)
        mysql_user = os.getenv("DB_USER")
        mysql_passwd = os.getenv("DB_PASSWORD")
        mysql_host = os.getenv("DB_HOST")
        mysql_port = os.getenv("DB_PORT")
        mysql_db = os.getenv("DB_NAME")
        
        if mysql_user and mysql_passwd and mysql_host and mysql_port and mysql_db:
            mysql_url = f"mysql+pymysql://{mysql_user}:{mysql_passwd}@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
            self.mysql_engine = create_engine(mysql_url)
        else:
            print("❌ MySQL 연결 정보가 부족합니다.")
            self.mysql_engine = None
        
        # PostgreSQL 연결 설정 (뉴스 데이터)
        pg_user = os.getenv("NEWS_DB_USER")
        pg_passwd = os.getenv("NEWS_DB_PASSWORD")
        pg_host = os.getenv("NEWS_DB_HOST")
        pg_port = os.getenv("NEWS_DB_PORT")
        pg_db = os.getenv("NEWS_DB_NAME")
        
        if pg_user and pg_passwd and pg_host and pg_port and pg_db:
            pg_url = f'postgresql+psycopg2://{pg_user}:{pg_passwd}@{pg_host}:{pg_port}/{pg_db}'
            self.postgres_engine = create_engine(pg_url)
        else:
            # 대체 방식: DATABASE_URL 환경변수 사용
            pg_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/dbname")
            self.postgres_engine = create_engine(pg_url)
        
        # 2024년 이전 데이터 기준일 설정
        self.cutoff_date = date(2024, 1, 1)
        
    def get_embedding(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환 (rag_service.py 참고)"""
        if os.getenv("OPENAI_API_KEY") is None:
            print("❌ OPENAI_API_KEY is None")
        try:
            print("임베딩 시작")
            response = self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_model,
                timeout=30
            )
            print("임베딩 완료")
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            return []
    
    def _generate_diverse_queries(self, stock_code: str, stock_info=None) -> List[Dict[str, Any]]:
        """주식 분석을 위한 다양한 검색 쿼리 생성 (과거 데이터용)"""
        queries = []
        
        # 1. 기본 종목 코드 검색 (높은 정확도)
        queries.append({
            "query": stock_code,
            "type": "stock_code",
            "top_k": 15,
            "threshold": 0.5
        })
        
        if stock_info:
            # 2. 회사명 검색 (중간 정확도)
            if stock_info.get("company_name"):
                queries.append({
                    "query": stock_info["company_name"],
                    "type": "company_name", 
                    "top_k": 12,
                    "threshold": 0.4
                })
                
                # 3. 회사명 + 주요 키워드 조합
                company_keywords = [
                    f"{stock_info['company_name']} 실적",
                    f"{stock_info['company_name']} 전망",
                    f"{stock_info['company_name']} 투자",
                    f"{stock_info['company_name']} 주가"
                ]
                for keyword in company_keywords:
                    queries.append({
                        "query": keyword,
                        "type": "company_keyword",
                        "top_k": 8,
                        "threshold": 0.3
                    })
            
            # 4. 업종/섹터 관련 검색
            if stock_info.get("industry"):
                queries.append({
                    "query": f"{stock_info['industry']} 업종",
                    "type": "industry",
                    "top_k": 8,
                    "threshold": 0.25
                })
                
            if stock_info.get("sector"):
                queries.append({
                    "query": f"{stock_info['sector']} 섹터",
                    "type": "sector", 
                    "top_k": 8,
                    "threshold": 0.25
                })
            
            # 5. 사업 영역 관련 검색
            if stock_info.get("business_summary"):
                business_keywords = self._extract_business_keywords(stock_info["business_summary"])
                for keyword in business_keywords[:2]:  # 상위 2개만
                    queries.append({
                        "query": keyword,
                        "type": "business_keyword",
                        "top_k": 6,
                        "threshold": 0.25
                    })
        
        # 6. 일반적인 주식 관련 키워드
        general_keywords = [
            f"{stock_code} 분석",
            f"{stock_code} 리포트"
        ]
        for keyword in general_keywords:
            queries.append({
                "query": keyword,
                "type": "analysis_keyword",
                "top_k": 5,
                "threshold": 0.3
            })
        
        return queries
    
    def _extract_business_keywords(self, business_summary: str) -> List[str]:
        """사업 요약에서 주요 키워드 추출"""
        if not business_summary:
            return []
        
        # 주요 사업 관련 키워드들
        business_terms = [
            "반도체", "메모리", "디스플레이", "스마트폰", "전자", "IT", "소프트웨어",
            "바이오", "제약", "화학", "석유", "자동차", "조선", "건설", "금융",
            "은행", "증권", "보험", "통신", "게임", "엔터테인먼트", "유통",
            "식품", "음료", "의류", "화장품", "항공", "물류", "에너지",
            "AI", "인공지능", "빅데이터", "클라우드", "5G", "IoT", "블록체인",
            "technology", "software", "hardware", "semiconductor", "biotech",
            "pharmaceutical", "automotive", "financial", "banking", "insurance"
        ]
        
        found_keywords = []
        business_lower = business_summary.lower()
        
        for term in business_terms:
            if term in business_summary or term.lower() in business_lower:
                found_keywords.append(term)
        
        return found_keywords[:5]  # 최대 5개까지

    def get_historical_news(self, stock_code: str, db_session: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """2024년 이전 뉴스 데이터 검색 (다양한 쿼리 사용)"""
        try:
            # 1. 기업 기본 정보 가져오기 (MySQL에서)
            stock_info = None
            with Session(self.mysql_engine) as mysql_session:
                stock_query = text("SELECT * FROM stocks WHERE code = :stock_code")
                stock_result = mysql_session.execute(stock_query, {"stock_code": stock_code}).fetchone()
                if stock_result:
                    stock_info = dict(stock_result._mapping)
            
            # 2. 다양한 검색 쿼리 생성
            search_queries = self._generate_diverse_queries(stock_code, stock_info)
            print(f"생성된 검색 쿼리 수: {len(search_queries)} for {stock_code}")
            
            # 3. 각 쿼리로 검색하여 결과 수집
            all_docs = []
            for i, query_info in enumerate(search_queries):
                print(f"🔍 검색 {i+1}/{len(search_queries)}: {query_info['query']} (타입: {query_info['type']})")
                
                # 2024년 이전 뉴스 청크 검색 with 벡터 유사도
                query_text = text("""
                    SELECT id, title, chunk_text, published_at,
                           1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                    FROM news_chunks
                    WHERE published_at < :cutoff_date
                    AND 1 - (embedding <=> CAST(:query_embedding AS vector)) > :threshold
                    ORDER BY embedding <=> CAST(:query_embedding AS vector)
                    LIMIT :limit
                """)
                
                # 쿼리 임베딩 생성
                query_embedding = self.get_embedding(query_info["query"])
                if not query_embedding:
                    continue
                
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                result = db_session.execute(
                    query_text,
                    {
                        "query_embedding": embedding_str,
                        "cutoff_date": self.cutoff_date,
                        "threshold": query_info["threshold"],
                        "limit": query_info["top_k"]
                    }
                )
                
                docs = []
                for row in result:
                    docs.append({
                        "id": str(row.id),
                        "title": row.title,
                        "content": row.chunk_text,
                        "published_at": row.published_at.isoformat() if row.published_at else None,
                        "similarity": float(row.similarity),
                        "query_type": query_info["type"]
                    })
                
                print(f"   ✅ 검색 결과: {len(docs)}개")
                if docs:
                    print(f"   📊 유사도: {min([d['similarity'] for d in docs]):.3f} ~ {max([d['similarity'] for d in docs]):.3f}")
                
                all_docs.extend(docs)
            
            print(f"전체 검색 완료 - 총 문서: {len(all_docs)}개")
            
            # 4. 중복 제거 (ID 기준)
            seen_ids = set()
            historical_news = []
            for doc in all_docs:
                if doc["id"] not in seen_ids:
                    seen_ids.add(doc["id"])
                    historical_news.append(doc)
            
            # 5. 유사도 기준으로 정렬하고 상위 limit개만 선택
            historical_news = sorted(historical_news, key=lambda x: x["similarity"], reverse=True)[:limit]
            
            print(f"2024년 이전 뉴스 검색 완료: {len(historical_news)}개 (중복 제거 후)")
            if historical_news:
                print(f"최종 유사도 범위: {min([d['similarity'] for d in historical_news]):.3f} ~ {max([d['similarity'] for d in historical_news]):.3f}")
                
                # 쿼리 타입별 분포 확인
                type_counts = {}
                for doc in historical_news:
                    query_type = doc.get("query_type", "unknown")
                    type_counts[query_type] = type_counts.get(query_type, 0) + 1
                print(f"쿼리 타입별 분포: {type_counts}")
            
            return historical_news
            
        except Exception as e:
            print(f"과거 뉴스 검색 실패: {e}")
            # 실패시 기본 방식으로 대체
            return self._fallback_news_search(stock_code, db_session, limit)
    
    def _fallback_news_search(self, stock_code: str, db_session: Session, limit: int = 50) -> List[Dict[str, Any]]:
        """벡터 검색 실패시 기본 텍스트 검색"""
        try:
            query_text = text("""
                SELECT id, title, chunk_text, published_at
                FROM news_chunks
                WHERE published_at < :cutoff_date
                AND (title ILIKE :stock_pattern OR chunk_text ILIKE :stock_pattern)
                ORDER BY published_at DESC
                LIMIT :limit
            """)
            
            result = db_session.execute(
                query_text,
                {
                    "cutoff_date": self.cutoff_date,
                    "stock_pattern": f"%{stock_code}%",
                    "limit": limit
                }
            )
            
            historical_news = []
            for row in result:
                historical_news.append({
                    "id": str(row.id),
                    "title": row.title,
                    "content": row.chunk_text,
                    "published_at": row.published_at.isoformat() if row.published_at else None,
                    "similarity": 0.5,  # 기본값
                    "query_type": "fallback"
                })
            
            print(f"대체 검색 결과: {len(historical_news)}개")
            return historical_news
            
        except Exception as e:
            print(f"대체 검색도 실패: {e}")
            return []
    
    def get_historical_financial_data(self, stock_code: str, db_session: Session) -> Dict[str, Any]:
        """2024년 이전 재무 데이터 가져오기 (MySQL)"""
        try:
            financial_data = {}
            
            # MySQL 세션 사용
            with Session(self.mysql_engine) as mysql_session:
                # 종목 기본 정보
                stock_query = text("SELECT * FROM stocks WHERE code = :stock_code")
                stock_result = mysql_session.execute(stock_query, {"stock_code": stock_code}).fetchone()
                
                if stock_result:
                    financial_data["basic_info"] = dict(stock_result._mapping)
                
                # 2024년 이전 재무제표 데이터
                financial_query = text("""
                    SELECT * FROM financial_statements 
                    WHERE stock_code = :stock_code 
                    AND report_period < :cutoff_date
                    ORDER BY report_period DESC
                    LIMIT 8
                """)
                
                financial_results = mysql_session.execute(
                    financial_query, 
                    {"stock_code": stock_code, "cutoff_date": "2024-01-01"}
                ).fetchall()
                
                financial_data["statements"] = [dict(row._mapping) for row in financial_results]
            
            print(f"과거 재무 데이터 수집 완료: {stock_code}")
            return financial_data
            
        except Exception as e:
            print(f"과거 재무 데이터 수집 실패: {e}")
            return {}
    
    def generate_historical_report(self, stock_code: str) -> Dict[str, Any]:
        """2024년 이전 데이터를 사용한 주식 분석 보고서 생성"""
        try:
            with Session(self.postgres_engine) as db_session:
                # 1. 과거 뉴스 데이터 수집
                historical_news = self.get_historical_news(stock_code, db_session)
                
                # 2. 과거 재무 데이터 수집
                financial_data = self.get_historical_financial_data(stock_code, db_session)
                
                # 3. 과거 데이터 분석용 시스템 프롬프트
                analysis_prompt = """당신은 월스트리트 출신의 전문 기업 분석가입니다.

2024년 이전의 과거 뉴스 데이터와 재무 데이터를 바탕으로 해당 기업에 대한 과거 시점 기준 종합적인 분석 보고서를 작성하세요.

📌 주어지는 데이터:
- 2024년 이전 기업 관련 뉴스 기사들
- 2024년 이전 상세한 재무 정보 (재무제표, 시장지표)

🎯 분석 보고서 구성:

## 📊 기업 개요
- 사업 분야 및 주요 사업
- 업계 내 위치

## 📈 재무 상황 분석 (2024년 이전 기준)
- 수익성 지표 (매출, 영업이익, 순이익, 마진률 등)
- 수익성 지표 설명: 초보자도 이해할 수 있도록 수치의 의미, 기준선, 업계 평균 비교 등 자세한 해설 포함
- 재무건전성 (부채비율, 유동비율, ROE/ROA 등)
- 재무건전성 설명: 각 지표의 개념, 수치 해석, 리스크 여부 등 초보자 시각에서 자세한 설명 추가
- 성장성 (매출/이익 증가율)
- 성장성 설명: 성장성 수치 해석, 시장 내 성장 위치, 향후 전망 등 상세하게 기술
- 밸류에이션 (PER, PBR, EV/EBITDA 등)
- 밸루에이션 설명: 해당 지표의 의미, 고평가/저평가 여부, 투자 매력도 관점 설명

## 📰 과거 주요 동향 및 이슈 (2024년 이전)
- 주요 뉴스 이벤트 요약
- 긍정적/부정적 요인 분석
- 시장 반응 및 영향도
- 과거 동향 및 이슈 설명: 기업에 영향을 준 과거 뉴스, 정책, 기술 동향을 초보자 관점에서 상세히 해석

## 🔮 과거 시점 기준 전망 및 리스크
- 과거 데이터 기준 실적 패턴
- 성장 동력 및 기회요인
- 주요 리스크 요인
- 전망 및 리스크 설명: 과거 데이터 기준 긍정/부정 패턴 근거를 제시하고, 주요 리스크는 초보자가 쉽게 이해할 수 있도록 해설

## 💡 종합 의견 (과거 데이터 기준)
- 투자 매력도: ⭐⭐⭐⭐⭐ (5점 만점)
- 투자 포인트 요약
- 주의 사항
- 과거 데이터 한계점 명시

⚠️ 작성 원칙:
- 객관적이고 균형잡힌 시각 유지
- 구체적인 수치와 근거 제시
- 과거 데이터 기반 분석임을 명시
- 정보 제공 중심 (구체적 매매 조언 지양)
- 모든 분석은 2024년 이전 데이터에만 기반"""
                
                # 4. 뉴스 컨텍스트 구성
                news_content = ""
                if historical_news:
                    news_summaries = []
                    for doc in historical_news:
                        news_summaries.append(f"• {doc['title']}: {doc['content'][:200]}...")
                    news_content = "\n".join(news_summaries)
                
                # 5. 재무 데이터 컨텍스트 구성
                financial_content = ""
                if financial_data:
                    if financial_data.get("basic_info"):
                        basic_info = financial_data["basic_info"]
                        financial_content += f"◆ 기업 기본 정보:\n"
                        for key, value in basic_info.items():
                            if value is not None:
                                financial_content += f"  - {key}: {value}\n"
                    
                    if financial_data.get("statements"):
                        financial_content += f"\n◆ 과거 재무제표 (2024년 이전):\n"
                        for stmt in financial_data["statements"]:
                            financial_content += f"  - 보고기간: {stmt.get('report_period', 'N/A')}\n"
                            for key, value in stmt.items():
                                if key not in ['id', 'stock_code', 'report_period'] and value is not None:
                                    financial_content += f"    {key}: {value}\n"
                            financial_content += "\n"
                
                # 6. 사용자 프롬프트 구성
                user_content = f"""
[분석 대상 종목]: {stock_code}
[분석 기간]: 2024년 이전 데이터

[과거 뉴스 기사들]:
{news_content if news_content else "관련 과거 뉴스 없음"}

[과거 재무 정보]:
{financial_content if financial_content else "관련 과거 재무 데이터 없음"}

[분석 요청]: {stock_code} 기업에 대한 2024년 이전 데이터 기반 과거 분석 보고서를 작성해주세요.
"""
                
                # 7. GPT 분석 실행
                messages = [
                    {"role": "system", "content": analysis_prompt},
                    {"role": "user", "content": user_content}
                ]
                
                print(f"GPT 과거 분석 시작: {stock_code}")
                response = self.openai_client.chat.completions.create(
                    model=self.chat_model,
                    messages=messages,
                    temperature=0,  # 최대 일관성
                    max_tokens=12000
                )
                print(f"GPT 과거 분석 완료: {stock_code}")
                
                report_content = response.choices[0].message.content
                
                return {
                    "stock_code": stock_code,
                    "analysis_type": "historical_analysis",
                    "data_period": "pre_2024",
                    "report": report_content,
                    "news_count": len(historical_news),
                    "financial_periods": len(financial_data.get("statements", [])),
                    "generated_at": datetime.now().isoformat(),
                    "success": True
                }
                
        except Exception as e:
            print(f"과거 분석 보고서 생성 실패: {e}")
            import traceback
            print(f"상세 오류: {traceback.format_exc()}")
            
            return {
                "stock_code": stock_code,
                "analysis_type": "historical_analysis",
                "data_period": "pre_2024",
                "report": "분석 중 오류가 발생했습니다.",
                "news_count": 0,
                "financial_periods": 0,
                "generated_at": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    def save_report_to_csv(self, report_data: Dict[str, Any], output_dir: str = "data"):
        """보고서를 CSV 파일로 저장"""
        try:
            # 현재 스크립트 파일 위치 기준으로 절대경로 생성
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(script_dir, output_dir)
            
            # 출력 디렉토리 생성
            os.makedirs(output_dir, exist_ok=True)
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"historical_report_{report_data['stock_code']}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            # CSV로 저장
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'stock_code', 'analysis_type', 'data_period', 'report',
                    'news_count', 'financial_periods', 'generated_at', 'success'
                ]
                
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # 에러 정보 제외하고 저장
                save_data = {k: v for k, v in report_data.items() if k != 'error'}
                writer.writerow(save_data)
            
            print(f"보고서 CSV 저장 완료: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"CSV 저장 실패: {e}")
            return None
    
    def batch_generate_reports(self, stock_codes: List[str], output_dir: str = "data"):
        """여러 종목에 대한 일괄 보고서 생성"""
        results = []
        
        for i, stock_code in enumerate(stock_codes, 1):
            print(f"보고서 생성 진행: {i}/{len(stock_codes)} - {stock_code}")
            
            # 보고서 생성
            report_data = self.generate_historical_report(stock_code)
            
            # CSV 저장
            csv_path = self.save_report_to_csv(report_data, output_dir)
            report_data["csv_path"] = csv_path
            
            results.append(report_data)
            
            # 진행상황 로그
            if report_data["success"]:
                print(f"✅ {stock_code} 보고서 생성 완료")
            else:
                print(f"❌ {stock_code} 보고서 생성 실패")
        
        # 전체 결과 요약 CSV 생성
        self.save_batch_summary(results, output_dir)
        
        return results
    
    def save_batch_summary(self, results: List[Dict[str, Any]], output_dir: str):
        """일괄 처리 결과 요약 CSV 저장"""
        try:
            # 현재 스크립트 파일 위치 기준으로 절대경로 생성
            script_dir = os.path.dirname(os.path.abspath(__file__))
            if not os.path.isabs(output_dir):
                output_dir = os.path.join(script_dir, output_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            summary_filename = f"historical_reports_summary_{timestamp}.csv"
            summary_filepath = os.path.join(output_dir, summary_filename)
            
            # 요약 데이터 준비
            summary_data = []
            for result in results:
                summary_data.append({
                    "stock_code": result["stock_code"],
                    "success": result["success"],
                    "news_count": result["news_count"],
                    "financial_periods": result["financial_periods"],
                    "generated_at": result["generated_at"],
                    "csv_path": result.get("csv_path", ""),
                    "error": result.get("error", "")
                })
            
            # DataFrame으로 변환하여 저장
            df = pd.DataFrame(summary_data)
            df.to_csv(summary_filepath, index=False, encoding='utf-8')
            
            print(f"일괄 처리 요약 저장 완료: {summary_filepath}")
            
            # 통계 정보 출력
            total_count = len(results)
            success_count = sum(1 for r in results if r["success"])
            total_news = sum(r["news_count"] for r in results)
            total_financial_periods = sum(r["financial_periods"] for r in results)
            
            print(f"📊 처리 완료 통계:")
            print(f"  - 전체 종목: {total_count}개")
            print(f"  - 성공: {success_count}개")
            print(f"  - 실패: {total_count - success_count}개")
            print(f"  - 총 뉴스 수: {total_news}개")
            print(f"  - 총 재무 기간 수: {total_financial_periods}개")
            
        except Exception as e:
            print(f"요약 CSV 저장 실패: {e}")


def main():
    """메인 실행 함수"""
    # 보고서 생성기 초기화
    generator = HistoricalReportGenerator()
    
    # config에서 랜덤 SP500 종목 50개 가져오기
    from config_historical import get_random_sp500_tickers
    
    # SP500에서 랜덤 250개 종목 선택
    test_stock_codes = get_random_sp500_tickers(250)
    
    print("과거 데이터 기반 보고서 생성 시작")
    print(f"대상 종목: 랜덤 SP500 250개")
    print(f"선택된 종목 처음 10개: {test_stock_codes[:10]}")
    print(f"분석 기준: 2024년 이전 데이터")
    
    # 현재 스크립트 파일과 같은 위치에 data 폴더 생성
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, "data", "historical_reports")
    
    print(f"출력 위치: {output_dir}")
    
    # 일괄 보고서 생성
    results = generator.batch_generate_reports(
        stock_codes=test_stock_codes,
        output_dir=output_dir
    )
    
    print("과거 데이터 기반 보고서 생성 완료")

if __name__ == "__main__":
    main() 