import openai
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from dotenv import load_dotenv
from aibackend.app.news_vector import chunkVector
from aibackend.app.news_vector_db import get_news_db

load_dotenv()

class RAGService:
    def __init__(self):
        self.openai_client = openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=60.0
        )
        self.embedding_model = "text-embedding-3-small"
        self.chat_model = "gpt-4o"
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        if os.getenv("OPENAI_API_KEY") is None:
            print("❌ OPENAI_API_KEY is None", flush=True)
        try:
            print("임베딩 시작", flush=True)
            response = self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_model,
                timeout=30
            )
            print("임베딩 완료", flush=True)
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 실패: {e}", flush=True)
            return []
    
    def similarity_search(
        self, 
        query: str, 
        db: Session, 
        top_k: int = 100,
        similarity_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """쿼리와 유사한 뉴스 기사들을 벡터 검색으로 찾기"""
        try:
            # 쿼리 임베딩
            print(f"벡터 검색 시작 - 쿼리: {query}", flush=True)
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                print("임베딩 결과가 비어있음", flush=True)
                return []
            
            print(f"벡터 검색 시작 - 임베딩 길이: {len(query_embedding)}", flush=True)
            
            # 먼저 데이터베이스에 데이터가 있는지 확인
            count_query = text("SELECT COUNT(*) as total FROM news_chunks")
            count_result = db.execute(count_query).fetchone()
            total_chunks = count_result.total if count_result else 0
            print(f"데이터베이스 총 청크 수: {total_chunks}", flush=True)
            
            if total_chunks == 0:
                print("❌ news_chunks 테이블에 데이터가 없습니다!", flush=True)
                return []
            
            # pgvector의 코사인 유사도 검색
            # 벡터를 문자열로 변환하여 전달
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            print(f"벡터 문자열 생성 완료 - 길이: {len(embedding_str)}", flush=True)
            
            # 먼저 임계값 없이 상위 결과들 확인
            debug_query = text("""
                SELECT id, title, chunk_text, published_at,
                       1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM news_chunks
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT 5
            """)
            
            print("디버그용 상위 5개 결과 확인 시작", flush=True)
            debug_result = db.execute(debug_query, {"query_embedding": embedding_str})
            
            debug_docs = []
            for row in debug_result:
                debug_docs.append({
                    "similarity": float(row.similarity),
                    "title": row.title[:100] + "..." if len(row.title) > 100 else row.title
                })
            
            print(f"상위 5개 결과의 유사도: {[doc['similarity'] for doc in debug_docs]}", flush=True)
            print(f"상위 5개 결과의 제목: {[doc['title'] for doc in debug_docs]}", flush=True)
            
            # 동적 임계값 조정
            if debug_docs:
                max_similarity = max([doc['similarity'] for doc in debug_docs])
                print(f"최고 유사도: {max_similarity}", flush=True)
                
                # 최고 유사도가 임계값보다 낮으면 임계값을 낮춤
                if max_similarity < similarity_threshold:
                    adjusted_threshold = max(0.1, max_similarity - 0.1)
                    print(f"임계값 조정: {similarity_threshold} -> {adjusted_threshold}", flush=True)
                    similarity_threshold = adjusted_threshold
            
            # 실제 검색 쿼리
            query_text = text("""
                SELECT id, title, chunk_text, published_at,
                       1 - (embedding <=> CAST(:query_embedding AS vector)) as similarity
                FROM news_chunks
                WHERE 1 - (embedding <=> CAST(:query_embedding AS vector)) > :threshold
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :limit
            """)
            
            print(f"SQL 쿼리 실행 시작 - 임계값: {similarity_threshold}", flush=True)
            result = db.execute(
                query_text,
                {
                    "query_embedding": embedding_str,
                    "threshold": similarity_threshold,
                    "limit": top_k
                }
            )
            print("SQL 쿼리 실행 완료", flush=True)
            
            similar_docs = []
            row_count = 0
            for row in result:
                row_count += 1
                similar_docs.append({
                    "id": str(row.id),
                    "title": row.title,
                    "content": row.chunk_text,
                    "published_at": row.published_at.isoformat() if row.published_at else None,
                    "similarity": float(row.similarity)
                })
            
            print(f"최종 결과 처리 완료 - {row_count}개 행, 임계값: {similarity_threshold}", flush=True)
            if similar_docs:
                print(f"반환된 결과의 유사도 범위: {min([doc['similarity'] for doc in similar_docs]):.3f} ~ {max([doc['similarity'] for doc in similar_docs]):.3f}", flush=True)
            
            return similar_docs
            
        except Exception as e:
            print(f"유사도 검색 실패: {e}", flush=True)
            import traceback
            print(f"상세 오류: {traceback.format_exc()}", flush=True)
            return []
    
    def _generate_diverse_queries(self, stock_code: str, stock=None) -> List[Dict[str, Any]]:
        """주식 분석을 위한 다양한 검색 쿼리 생성"""
        queries = []
        
        # 1. 기본 종목 코드 검색 (높은 정확도)
        queries.append({
            "query": stock_code,
            "type": "stock_code",
            "top_k": 25,  # 10 → 25
            "threshold": 0.6  # 0.7 → 0.6
        })
        
        if stock:
            # 2. 회사명 검색 (중간 정확도)
            if stock.company_name:
                queries.append({
                    "query": stock.company_name,
                    "type": "company_name", 
                    "top_k": 20,  # 8 → 20
                    "threshold": 0.5  # 0.6 → 0.5
                })
                
                # 3. 회사명 + 주요 키워드 조합
                company_keywords = [
                    f"{stock.company_name} 실적",
                    f"{stock.company_name} 전망",
                    f"{stock.company_name} 투자",
                    f"{stock.company_name} 주가"
                ]
                for keyword in company_keywords:
                    queries.append({
                        "query": keyword,
                        "type": "company_keyword",
                        "top_k": 15,  # 5 → 15
                        "threshold": 0.4  # 0.5 → 0.4
                    })
            
            # 4. 업종/섹터 관련 검색 (낮은 정확도, 넓은 범위)
            if stock.industry:
                queries.append({
                    "query": f"{stock.industry} 업종",
                    "type": "industry",
                    "top_k": 12,  # 5 → 12
                    "threshold": 0.3  # 0.4 → 0.3
                })
                
            if stock.sector:
                queries.append({
                    "query": f"{stock.sector} 섹터",
                    "type": "sector", 
                    "top_k": 12,  # 5 → 12
                    "threshold": 0.3  # 0.4 → 0.3
                })
            
            # 5. 사업 영역 관련 검색
            if stock.business_summary:
                # 사업 요약에서 주요 키워드 추출
                business_keywords = self._extract_business_keywords(stock.business_summary)
                for keyword in business_keywords[:3]:  # 상위 3개만
                    queries.append({
                        "query": keyword,
                        "type": "business_keyword",
                        "top_k": 10,  # 4 → 10
                        "threshold": 0.3  # 0.4 → 0.3
                    })
        
        # 6. 일반적인 주식 관련 키워드 (종목코드와 함께)
        general_keywords = [
            f"{stock_code} 분석",
            f"{stock_code} 리포트", 
            f"{stock_code} 목표가",
            f"{stock_code} 추천"
        ]
        for keyword in general_keywords:
            queries.append({
                "query": keyword,
                "type": "analysis_keyword",
                "top_k": 8,  # 3 → 8
                "threshold": 0.4  # 0.5 → 0.4
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
            "AI", "인공지능", "빅데이터", "클라우드", "5G", "IoT", "블록체인"
        ]
        
        found_keywords = []
        business_lower = business_summary.lower()
        
        for term in business_terms:
            if term in business_summary or term.lower() in business_lower:
                found_keywords.append(term)
        
        return found_keywords[:5]  # 최대 5개까지

    
    def generate_stock_analysis(
        self,
        stock_code: str,
        news_db: Session = None,
        main_db: Session = None
    ) -> Dict[str, Any]:
        """주식 분석용 특화 RAG (뉴스 + 재무 데이터)"""
        try:
            # 1. 다양한 검색 쿼리로 관련 뉴스 수집
            similar_docs = []
            if news_db and main_db:
                # 기업 정보 가져오기
                from ..models import Stock
                stock = main_db.query(Stock).filter(Stock.code == stock_code).first()
                
                # 다채로운 검색 쿼리 생성
                print(f"검색 쿼리 생성 시작: {stock_code}", flush=True)
                search_queries = self._generate_diverse_queries(stock_code, stock)
                print(f"생성된 쿼리 수: {len(search_queries)}", flush=True)
                
                # 각 쿼리로 검색하여 결과 수집
                all_docs = []
                for i, query_info in enumerate(search_queries):
                    print(f"검색 {i+1}/{len(search_queries)}: {query_info['query']}", flush=True)
                    docs = self.similarity_search(
                        query=query_info["query"],
                        db=news_db,
                        top_k=query_info["top_k"],
                        similarity_threshold=query_info["threshold"]
                    )
                    print(f"검색 결과: {len(docs)}개", flush=True)
                    # 쿼리 타입 정보 추가
                    for doc in docs:
                        doc["query_type"] = query_info["type"]
                    all_docs.extend(docs)
                
                # 중복 제거 (ID 기준)
                seen_ids = set()
                similar_docs = []
                for doc in all_docs:
                    if doc["id"] not in seen_ids:
                        seen_ids.add(doc["id"])
                        similar_docs.append(doc)
                
                # 유사도 기준으로 정렬하고 상위 40개만 선택 (청크 기반이므로 더 많이)
                similar_docs = sorted(similar_docs, key=lambda x: x["similarity"], reverse=True)[:40]
                print(similar_docs)
            
            elif news_db:
                # DB 정보가 없을 때는 기본 검색
                similar_docs = self.similarity_search(
                    query=stock_code,
                    db=news_db,
                    top_k=30,  # 15 → 30
                    similarity_threshold=0.4  # 0.5 → 0.4
                )
            
            # 뉴스가 없어도 재무 데이터만으로 분석 진행
            news_content = ""
            if similar_docs:
                # 뉴스 내용을 하나의 문자열로 결합
                news_summaries = []
                for doc in similar_docs:
                    news_summaries.append(f"• {doc['title']}: {doc['content'][:200]}...")
                print(news_summaries)
                news_content = "\n".join(news_summaries)
            
            # 2. 기업 종합 분석용 시스템 프롬프트
            analysis_prompt = """당신은 월스트리트 출신의 전문 기업 분석가입니다.

뉴스 데이터와 재무 데이터를 바탕으로 해당 기업에 대한 종합적인 분석 보고서를 작성하세요.

📌 주어지는 데이터:
- 기업 관련 뉴스 기사들
- 상세한 재무 정보 (재무제표, 시장지표, 실적전망)

🎯 분석 보고서 구성:

## 📊 기업 개요
- 사업 분야 및 주요 사업
- 업계 내 위치

## 📈 재무 상황 분석
- 수익성 지표 (매출, 영업이익, 순이익, 마진률 등)
- 재무건전성 (부채비율, 유동비율, ROE/ROA 등)
- 성장성 (매출/이익 증가율)
- 밸류에이션 (PER, PBR, EV/EBITDA 등)

## 📰 최근 동향 및 이슈
- 주요 뉴스 이벤트 요약
- 긍정적/부정적 요인 분석
- 시장 반응 및 영향도

## 🔮 전망 및 리스크
- 실적 전망
- 성장 동력 및 기회요인
- 주요 리스크 요인

## 💡 종합 의견
- 투자 매력도: ⭐⭐⭐⭐⭐ (5점 만점)
- 투자 포인트 요약
- 주의 사항

⚠️ 작성 원칙:
- 객관적이고 균형잡힌 시각 유지
- 구체적인 수치와 근거 제시
- 투자 위험성 명시
- 정보 제공 중심 (구체적 매매 조언 지양)"""
            
            # 3. 컨텍스트 구성
            context_text = "\n\n".join([
                f"제목: {doc['title']}\n내용: {doc['content']}\n발행일: {doc['published_at']}"
                for doc in similar_docs
            ])
            
            # 4. 사용자 프롬프트 구성
            user_content = f"""
[분석 대상 종목]: {stock_code}

[관련 뉴스 기사들]:
{context_text if similar_docs else "관련 뉴스 없음"}
"""
            
            # 재무 데이터 자동 가져오기 및 추가
            if main_db:
                # 데이터베이스에서 재무 데이터 가져오기
                from ..models import Stock, FinancialStatement, MarketIndicator, EarningsForecast
                
                # 종목 기본 정보
                stock = main_db.query(Stock).filter(Stock.code == stock_code).first()
                if stock:
                    # 재무제표 (최신순)
                    financials = main_db.query(FinancialStatement).filter(
                        FinancialStatement.stock_code == stock_code
                    ).order_by(FinancialStatement.report_period.desc()).limit(4).all()
                    
                    # 시장지표 (최신)
                    latest_indicator = main_db.query(MarketIndicator).filter(
                        MarketIndicator.stock_code == stock_code
                    ).order_by(MarketIndicator.date.desc()).first()
                    
                    # 실적전망
                    forecasts = main_db.query(EarningsForecast).filter(
                        EarningsForecast.stock_code == stock_code
                    ).order_by(EarningsForecast.fiscal_year.desc()).limit(3).all()
                    
                    # 재무 데이터 문자열 구성
                    financial_data_parts = []
                    
                    # 기업 기본 정보 (모든 필드)
                    financial_data_parts.append(f"◆ 기업명: {stock.company_name}")
                    if stock.industry:
                        financial_data_parts.append(f"◆ 업종: {stock.industry}")
                    if stock.sector:
                        financial_data_parts.append(f"◆ 섹터: {stock.sector}")
                    if stock.business_summary:
                        financial_data_parts.append(f"◆ 사업개요: {stock.business_summary}")
                    if stock.financial_info:
                        financial_data_parts.append(f"◆ 재무정보: {stock.financial_info}")
                    
                    # 재무제표 데이터 (모든 필드)
                    if financials:
                        financial_data_parts.append("\n◆ 재무제표:")
                        for f in financials:
                            financial_data_parts.append(f"  - {f.report_period} ({f.report_type})")
                            # 손익계산서 항목
                            if f.revenue:
                                financial_data_parts.append(f"    매출액: {f.revenue:,}원")
                            if f.operating_income:
                                financial_data_parts.append(f"    영업이익: {f.operating_income:,}원")
                            if f.net_income:
                                financial_data_parts.append(f"    순이익: {f.net_income:,}원")
                            if f.gross_profits:
                                financial_data_parts.append(f"    매출총이익: {f.gross_profits:,}원")
                            if f.ebitda:
                                financial_data_parts.append(f"    EBITDA: {f.ebitda:,}원")
                            
                            # 재무상태표 항목
                            if f.assets:
                                financial_data_parts.append(f"    총자산: {f.assets:,}원")
                            if f.liabilities:
                                financial_data_parts.append(f"    총부채: {f.liabilities:,}원")
                            if f.equity:
                                financial_data_parts.append(f"    자본총계: {f.equity:,}원")
                            
                            # 현금흐름표 항목
                            if f.operating_cashflow:
                                financial_data_parts.append(f"    영업현금흐름: {f.operating_cashflow:,}원")
                            if f.free_cashflow:
                                financial_data_parts.append(f"    잉여현금흐름: {f.free_cashflow:,}원")
                            
                            # 주당 지표
                            if f.revenue_per_share:
                                financial_data_parts.append(f"    주당매출: {float(f.revenue_per_share):,.3f}원")
                            
                            # 수익성 지표
                            if f.gross_margins:
                                financial_data_parts.append(f"    매출총이익률: {float(f.gross_margins)*100:.2f}%")
                            if f.ebitda_margins:
                                financial_data_parts.append(f"    EBITDA 마진: {float(f.ebitda_margins)*100:.2f}%")
                            if f.operating_margins:
                                financial_data_parts.append(f"    영업이익률: {float(f.operating_margins)*100:.2f}%")
                            if f.return_on_assets:
                                financial_data_parts.append(f"    ROA: {float(f.return_on_assets)*100:.2f}%")
                            if f.return_on_equity:
                                financial_data_parts.append(f"    ROE: {float(f.return_on_equity)*100:.2f}%")
                            
                            # 안정성 지표
                            if f.debt_to_equity:
                                financial_data_parts.append(f"    부채비율: {float(f.debt_to_equity):.2f}")
                            if f.quick_ratio:
                                financial_data_parts.append(f"    당좌비율: {float(f.quick_ratio):.2f}")
                            if f.current_ratio:
                                financial_data_parts.append(f"    유동비율: {float(f.current_ratio):.2f}")
                            
                            # 성장성 지표
                            if f.earnings_growth:
                                financial_data_parts.append(f"    순이익 증가율: {float(f.earnings_growth)*100:.2f}%")
                            if f.revenue_growth:
                                financial_data_parts.append(f"    매출 증가율: {float(f.revenue_growth)*100:.2f}%")
                            
                            # 기업가치 지표
                            if f.enterprise_value:
                                financial_data_parts.append(f"    기업가치(EV): {f.enterprise_value:,}원")
                            if f.enterprise_to_revenue:
                                financial_data_parts.append(f"    EV/매출: {float(f.enterprise_to_revenue):.2f}")
                            if f.enterprise_to_ebitda:
                                financial_data_parts.append(f"    EV/EBITDA: {float(f.enterprise_to_ebitda):.2f}")
                            
                            financial_data_parts.append("")
                    
                    # 시장지표 데이터 (모든 필드)
                    if latest_indicator:
                        financial_data_parts.append("◆ 시장지표 (최근 데이터):")
                        financial_data_parts.append(f"  - 기준일: {latest_indicator.date}")
                        
                        # 주가 정보
                        if latest_indicator.current_price:
                            financial_data_parts.append(f"    현재가: {float(latest_indicator.current_price):,}원")
                        if latest_indicator.previous_close:
                            financial_data_parts.append(f"    전일종가: {float(latest_indicator.previous_close):,}원")
                        if latest_indicator.open:
                            financial_data_parts.append(f"    시가: {float(latest_indicator.open):,}원")
                        if latest_indicator.close_price:
                            financial_data_parts.append(f"    종가: {latest_indicator.close_price:,}원")
                        if latest_indicator.day_low:
                            financial_data_parts.append(f"    일 최저가: {float(latest_indicator.day_low):,}원")
                        if latest_indicator.day_high:
                            financial_data_parts.append(f"    일 최고가: {float(latest_indicator.day_high):,}원")
                        if latest_indicator.fifty_two_week_low:
                            financial_data_parts.append(f"    52주 최저가: {float(latest_indicator.fifty_two_week_low):,}원")
                        if latest_indicator.fifty_two_week_high:
                            financial_data_parts.append(f"    52주 최고가: {float(latest_indicator.fifty_two_week_high):,}원")
                        if latest_indicator.fifty_two_week_change_percent:
                            financial_data_parts.append(f"    52주 변동률: {float(latest_indicator.fifty_two_week_change_percent)*100:.2f}%")
                        
                        # 거래량 정보
                        if latest_indicator.volume:
                            financial_data_parts.append(f"    거래량: {latest_indicator.volume:,}주")
                        if latest_indicator.average_volume:
                            financial_data_parts.append(f"    평균거래량: {latest_indicator.average_volume:,}주")
                        
                        # 시장 정보
                        if latest_indicator.market_cap:
                            financial_data_parts.append(f"    시가총액: {latest_indicator.market_cap:,}원")
                        if latest_indicator.market:
                            financial_data_parts.append(f"    시장: {latest_indicator.market}")
                        if latest_indicator.exchange:
                            financial_data_parts.append(f"    거래소: {latest_indicator.exchange}")
                        if latest_indicator.currency:
                            financial_data_parts.append(f"    통화: {latest_indicator.currency}")
                        
                        # 밸류에이션 지표
                        if latest_indicator.per:
                            financial_data_parts.append(f"    PER: {latest_indicator.per:.2f}")
                        if latest_indicator.pbr:
                            financial_data_parts.append(f"    PBR: {latest_indicator.pbr:.2f}")
                        if latest_indicator.pe_ratio_trailing:
                            financial_data_parts.append(f"    PER(후행): {float(latest_indicator.pe_ratio_trailing):.2f}")
                        if latest_indicator.pe_ratio_forward:
                            financial_data_parts.append(f"    PER(선행): {float(latest_indicator.pe_ratio_forward):.2f}")
                        
                        # 주당 지표
                        if latest_indicator.eps:
                            financial_data_parts.append(f"    EPS: {latest_indicator.eps:,}원")
                        if latest_indicator.eps_forward:
                            financial_data_parts.append(f"    EPS(선행): {float(latest_indicator.eps_forward):,}원")
                        if latest_indicator.eps_current_year:
                            financial_data_parts.append(f"    EPS(당해년도): {float(latest_indicator.eps_current_year):,}원")
                        if latest_indicator.price_eps_current_year:
                            financial_data_parts.append(f"    주가/EPS(당해년도): {float(latest_indicator.price_eps_current_year):.2f}")
                        if latest_indicator.bps:
                            financial_data_parts.append(f"    BPS: {latest_indicator.bps:,}원")
                        if latest_indicator.book_value:
                            financial_data_parts.append(f"    장부가치: {float(latest_indicator.book_value):,}원")
                        
                        # 배당 정보
                        if latest_indicator.dividend_yield:
                            financial_data_parts.append(f"    배당수익률: {latest_indicator.dividend_yield:.2f}%")
                        if latest_indicator.dividend_rate:
                            financial_data_parts.append(f"    배당률: {float(latest_indicator.dividend_rate):.2f}%")
                        if latest_indicator.dividend_date:
                            financial_data_parts.append(f"    배당일: {latest_indicator.dividend_date}")
                        if latest_indicator.ex_dividend_date:
                            financial_data_parts.append(f"    배당락일: {latest_indicator.ex_dividend_date}")
                        if latest_indicator.payout_ratio:
                            financial_data_parts.append(f"    배당성향: {float(latest_indicator.payout_ratio)*100:.2f}%")
                        
                        # 리스크 지표
                        if latest_indicator.beta:
                            financial_data_parts.append(f"    베타: {float(latest_indicator.beta):.2f}")
                    
                    # 실적전망 데이터 (모든 필드)
                    if forecasts:
                        financial_data_parts.append("\n◆ 실적전망:")
                        for e in forecasts:
                            financial_data_parts.append(f"  - {e.fiscal_year}년 전망")
                            if e.expected_revenue:
                                financial_data_parts.append(f"    예상매출: {e.expected_revenue:,}원")
                            if e.expected_operating_income:
                                financial_data_parts.append(f"    예상영업이익: {e.expected_operating_income:,}원")
                            if e.expected_eps:
                                financial_data_parts.append(f"    예상EPS: {e.expected_eps:,}원")
                            if e.source:
                                financial_data_parts.append(f"    출처: {e.source}")
                            financial_data_parts.append("")
                    
                    financial_data = "\n".join(financial_data_parts)
                    
                    # 재무 데이터를 user_content에 바로 추가
                    user_content += f"\n[재무 정보]:\n{financial_data}\n"
            
            user_content += f"\n[분석 요청]: {stock_code} 기업에 대한 종합 분석 보고서를 작성해주세요."
            
            # 5. GPT 분석 실행
            messages = [
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": user_content}
            ]
            
            print(f"GPT 분석 시작: {stock_code}", flush=True)
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.7,
                max_tokens=10000
            )
            print(f"GPT 분석 완료: {stock_code}", flush=True)
            
            # 생성된 보고서를 DB에 저장
            report_content = response.choices[0].message.content
            if main_db:
                try:
                    from ..models import Reports
                    from datetime import datetime
                    
                    # 새로운 보고서 생성
                    new_report = Reports(
                        stock_code=stock_code,
                        report=report_content,
                        created_at=datetime.now()
                    )
                    
                    main_db.add(new_report)
                    main_db.commit()
                    main_db.refresh(new_report)
                    
                    print(f"보고서 저장 완료: {stock_code}, ID: {new_report.id}")
                    
                except Exception as e:
                    print(f"보고서 저장 실패: {e}")
                    main_db.rollback()
            
            return {
                "stock_code": stock_code,
                "query": "기업 종합 분석",
                "response": report_content,
                "sources": similar_docs,
                "success": True
            }
            
        except Exception as e:
            print(f"주식 분석 실행 실패: {e}", flush=True)
            import traceback
            print(f"상세 오류: {traceback.format_exc()}", flush=True)
            return {
                "stock_code": stock_code,
                "query": "기업 종합 분석",
                "response": "분석 중 오류가 발생했습니다.",
                "sources": [],
                "success": False
            }

    def chat_with_rag(
        self,
        user_query: str,
        user_id: str,
        stock_code: str = None,
        news_db: Session = None,
        main_db: Session = None,
        top_k: int = 25,  # 10 → 25 (청크 기반이므로 더 많이)
        similarity_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """사용자 질문에 대해 RAG를 활용한 채팅 응답 생성"""
        try:
            print(f"채팅 RAG 시작: {user_query}", flush=True)
            
            # userID로 사용자 테이블 ID 조회
            user_table_id = None
            if main_db and user_id:
                from ..models import User
                user = main_db.query(User).filter(User.userID == user_id).first()
                if user:
                    user_table_id = user.id
                    print(f"사용자 ID 조회 완료: {user_id} -> {user_table_id}", flush=True)
                else:
                    print(f"사용자를 찾을 수 없음: {user_id}", flush=True)
            
            # 1. DB에서 채팅 내역 가져오기
            chat_history = []
            if main_db and stock_code and user_table_id:
                from ..models import ChatHistory
                recent_chats = main_db.query(ChatHistory).filter(
                    ChatHistory.user_id == user_table_id,
                    ChatHistory.stock_code == stock_code
                ).order_by(ChatHistory.created_at.desc()).limit(40).all()
                
                # 시간순으로 정렬 (오래된 것부터)
                recent_chats.reverse()
                chat_history = [
                    {"role": chat.role.value, "content": chat.chat} 
                    for chat in recent_chats
                ]
                print(f"가져온 채팅 내역 수: {len(chat_history)}", flush=True)
            
            # 2. DB에서 주식 보고서 가져오기
            stock_report = None
            if main_db and stock_code:
                from ..models import Reports
                latest_report = main_db.query(Reports).filter(
                    Reports.stock_code == stock_code
                ).order_by(Reports.created_at.desc()).first()
                
                if latest_report:
                    stock_report = latest_report.report
                    print(f"주식 보고서 찾음: {stock_code}", flush=True)
                else:
                    print(f"주식 보고서 없음: {stock_code}", flush=True)
            
            # 3. 사용자 질문과 관련된 뉴스 검색
            similar_docs = []
            if news_db:
                similar_docs = self.similarity_search(
                    query=user_query,
                    db=news_db,
                    top_k=top_k,
                    similarity_threshold=similarity_threshold
                )
                print(f"검색된 뉴스 수: {len(similar_docs)}", flush=True)
            
            # 2. 채팅용 시스템 프롬프트
            chat_system_prompt = """당신은 금융 전문가입니다. 사용자의 질문에 대해 제공된 정보들을 바탕으로 정확하고 도움이 되는 답변을 제공하세요.

답변 원칙:
- 제공된 뉴스 기사, 분석 보고서, 대화 맥락을 종합적으로 활용하세요
- 구체적인 사실과 데이터를 인용하세요
- 이전 대화 내용을 참고하여 연속성 있는 답변을 하세요
- 추측이나 확실하지 않은 정보는 피하세요
- 친근하고 이해하기 쉬운 톤으로 답변하세요

💡 **답변**
- 사용자 질문에 대한 구체적인 답변

⚠️ **참고사항**
- 투자 시 고려할 점이나 주의사항"""

            # 3. 뉴스 컨텍스트 구성
            news_context = ""
            if similar_docs:
                news_summaries = []
                for i, doc in enumerate(similar_docs, 1):
                    news_summaries.append(f"{i}. 제목: {doc['title']}\n   내용: {doc['content'][:300]}...\n   발행일: {doc['published_at']}")
                news_context = "\n".join(news_summaries)
                print(f"뉴스 컨텍스트: {news_context}", flush=True)
            else:
                news_context = "관련 뉴스를 찾을 수 없습니다."
            
            # 4. 대화 내역 구성
            chat_context = ""
            if chat_history:
                chat_messages = []
                for chat in chat_history:  # 모든 채팅 내역
                    role = "user" if chat["role"] == "user" else "gpt"
                    chat_messages.append(f"{role}: {chat['content']}")
                chat_context = "\n".join(chat_messages)
                print(f"이전 대화 내역: {chat_context}", flush=True)
            else:
                chat_context = "이전 대화 없음"
            
            # 5. 보고서 컨텍스트 구성
            report_context = ""
            if stock_report and stock_code:
                report_context = f"[{stock_code} 분석 보고서]:\n{stock_report}"
                print(f"주식 보고서: {report_context}", flush=True)
            else:
                report_context = "관련 분석 보고서 없음"
            
            # 6. 사용자 프롬프트 구성
            user_content = f"""
[현재 질문]: {user_query}

[이전 대화 내역]:
{chat_context}

[관련 뉴스 기사들]:
{news_context}

{report_context}

위의 모든 정보를 종합하여 사용자의 질문에 답변해주세요.
"""
            
            # 7. GPT 채팅 응답 생성
            messages = [
                {"role": "system", "content": chat_system_prompt},
                {"role": "user", "content": user_content}
            ]
            
            print("GPT 채팅 응답 생성 시작", flush=True)
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.7,
                max_tokens=10000,
                timeout=30
            )
            print("GPT 채팅 응답 생성 완료", flush=True)
            
            chat_response = response.choices[0].message.content
            
            return {
                "user_query": user_query,
                "response": chat_response,
                "sources": similar_docs,
                "source_count": len(similar_docs),
                "success": True
            }
            
        except Exception as e:
            print(f"채팅 RAG 실행 실패: {e}", flush=True)
            import traceback
            print(f"상세 오류: {traceback.format_exc()}", flush=True)
            
            # 오류 발생 시 기본 응답
            fallback_response = f"죄송합니다. '{user_query}'에 대한 답변을 생성하는 중 오류가 발생했습니다. 다시 시도해주세요."
            
            return {
                "user_query": user_query,
                "response": fallback_response,
                "sources": [],
                "source_count": 0,
                "success": False,
                "error": str(e)
            }

# 전역 RAG 서비스 인스턴스
rag_service = RAGService() 