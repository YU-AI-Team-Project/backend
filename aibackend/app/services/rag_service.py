import openai
import os
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from dotenv import load_dotenv
from aibackend.app.news_vector import NewsVector
from aibackend.app.news_vector_db import get_news_db

load_dotenv()

class RAGService:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.embedding_model = "text-embedding-ada-002"
        self.chat_model = "gpt-4o"
    
    def get_embedding(self, text: str) -> List[float]:
        """텍스트를 임베딩 벡터로 변환"""
        try:
            response = self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"임베딩 생성 실패: {e}")
            return []
    
    def similarity_search(
        self, 
        query: str, 
        db: Session, 
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """쿼리와 유사한 뉴스 기사들을 벡터 검색으로 찾기"""
        try:
            # 쿼리 임베딩
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # pgvector의 코사인 유사도 검색
            # 1 - (embedding <=> query_embedding)으로 유사도 계산
            query_text = text("""
                SELECT id, title, content, published_at,
                       1 - (embedding <=> :query_embedding) as similarity
                FROM news_vectors
                WHERE 1 - (embedding <=> :query_embedding) > :threshold
                ORDER BY embedding <=> :query_embedding
                LIMIT :limit
            """)
            
            result = db.execute(
                query_text,
                {
                    "query_embedding": query_embedding,
                    "threshold": similarity_threshold,
                    "limit": top_k
                }
            )
            
            similar_docs = []
            for row in result:
                similar_docs.append({
                    "id": str(row.id),
                    "title": row.title,
                    "content": row.content,
                    "published_at": row.published_at.isoformat() if row.published_at else None,
                    "similarity": float(row.similarity)
                })
            
            return similar_docs
            
        except Exception as e:
            print(f"유사도 검색 실패: {e}")
            return []
    
    def generate_response(
        self, 
        query: str, 
        context_docs: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        """검색된 문서들을 컨텍스트로 사용하여 응답 생성"""
        try:
            # 컨텍스트 문서들을 문자열로 변환
            context_text = "\n\n".join([
                f"제목: {doc['title']}\n내용: {doc['content']}\n발행일: {doc['published_at']}"
                for doc in context_docs
            ])
            
            # 시스템 프롬프트 설정
            if not system_prompt:
                system_prompt = """당신은 월스트리트 출신의 전문 주식 분석가입니다.

제공된 뉴스 기사들을 바탕으로 해당 기업의 투자 적합성 여부를 전문가 관점에서 분석하세요.

🎯 당신의 분석 작업:
1. 뉴스 기사 분석 및 긍/부정 판단
2. 투자 관점에서의 의미 해석
3. 투자 의사결정을 위한 정보 제공

🧾 출력 형식:

[뉴스 분석]:
- 핵심 내용 정리:
- 투자 관점 판단: ✅ 긍정적 / ⚠️ 주의 / ❌ 부정적
- 판단 근거:

[투자 관점]:
- 단기 영향:
- 중장기 전망:
- 주요 리스크:

[종합 의견]:
- 투자 방향성:
- 주의사항:

⚠️ 작성 조건:
- 분석은 전문가 시점에서 정확하고 간결하게 작성
- 뉴스 내용을 인용해 구체적으로 설명
- 투자 위험성을 반드시 언급
- 객관적이고 균형잡힌 시각 유지
- 구체적인 매수/매도 조언보다는 정보 제공에 중점"""
            
            # GPT에게 질문과 컨텍스트 전달
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"""
다음은 관련 뉴스 기사들입니다:

{context_text}

사용자 질문: {query}

위 뉴스 기사들을 참고하여 질문에 답변해주세요.
"""}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"응답 생성 실패: {e}")
            return "죄송합니다. 응답을 생성하는 중에 오류가 발생했습니다."
    
    def generate_stock_analysis(
        self,
        stock_code: str,
        news_query: str,
        financial_data: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """주식 분석용 특화 RAG (뉴스 + 재무 데이터)"""
        try:
            # 1. 해당 주식 관련 뉴스 검색
            search_query = f"{stock_code} {news_query}"
            similar_docs = self.similarity_search(
                query=search_query,
                db=db,
                top_k=5,
                similarity_threshold=0.6
            )
            
            if not similar_docs:
                return {
                    "stock_code": stock_code,
                    "query": news_query,
                    "response": f"{stock_code} 관련 뉴스를 찾을 수 없습니다.",
                    "sources": [],
                    "success": False
                }
            
            # 2. 주식 분석용 시스템 프롬프트
            analysis_prompt = """당신은 월스트리트 출신의 전문 주식 분석가입니다.

주어진 뉴스 기사와 재무 데이터를 바탕으로, 해당 기업의 투자 적합성 여부를 전문가 관점에서 분석하세요.

📌 주어지는 데이터:
- 뉴스 기사 (제목 + 본문)
- 재무 정보 (제공된 경우)

🎯 당신의 분석 작업:
1. 뉴스 기사 분석 및 긍/부정 판단
2. 재무 지표 분석 (제공된 경우)
3. 최종 투자 의견 제시

🧾 출력 형식:

[뉴스 분석]:
- 핵심 내용 정리:
- 투자 관점 판단: ✅ 긍정적 / ⚠️ 주의 / ❌ 부정적
- 판단 근거:

[재무 분석] (재무 데이터가 제공된 경우):
- 수익성 분석:
- 재무건전성:
- 시장지표 해석:

[종합 판단]:
- 투자 방향성: 관심 / 관망 / 주의
- 주요 근거:
- 리스크 요인:

⚠️ 작성 조건:
- 분석은 전문가 시점에서 정확하고 간결하게 작성
- 수치를 인용해 구체적으로 설명 (재무 데이터 있는 경우)
- 투자 위험성을 반드시 언급
- 구체적인 매수/매도 조언보다는 정보 제공에 중점"""
            
            # 3. 컨텍스트 구성
            context_text = "\n\n".join([
                f"제목: {doc['title']}\n내용: {doc['content']}\n발행일: {doc['published_at']}"
                for doc in similar_docs
            ])
            
            # 4. 사용자 프롬프트 구성
            user_content = f"""
[분석 대상 종목]: {stock_code}

[관련 뉴스 기사들]:
{context_text}
"""
            
            # 재무 데이터가 있으면 추가
            if financial_data:
                user_content += f"\n[재무 정보]:\n{financial_data}\n"
            
            user_content += f"\n[분석 요청]: {news_query}"
            
            # 5. GPT 분석 실행
            messages = [
                {"role": "system", "content": analysis_prompt},
                {"role": "user", "content": user_content}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            return {
                "stock_code": stock_code,
                "query": news_query,
                "response": response.choices[0].message.content,
                "sources": similar_docs,
                "has_financial_data": bool(financial_data),
                "success": True
            }
            
        except Exception as e:
            print(f"주식 분석 실행 실패: {e}")
            return {
                "stock_code": stock_code,
                "query": news_query,
                "response": "분석 중 오류가 발생했습니다.",
                "sources": [],
                "success": False
            }

    def rag_query(
        self, 
        query: str, 
        db: Session,
        top_k: int = 5,
        similarity_threshold: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """RAG 파이프라인 전체 실행"""
        try:
            # 1. 유사한 문서 검색
            similar_docs = self.similarity_search(
                query=query,
                db=db,
                top_k=top_k,
                similarity_threshold=similarity_threshold
            )
            
            if not similar_docs:
                return {
                    "query": query,
                    "response": "관련된 뉴스 기사를 찾을 수 없습니다. 다른 키워드로 검색해보세요.",
                    "sources": [],
                    "success": False
                }
            
            # 2. 컨텍스트를 바탕으로 응답 생성
            response = self.generate_response(
                query=query,
                context_docs=similar_docs,
                system_prompt=system_prompt
            )
            
            return {
                "query": query,
                "response": response,
                "sources": similar_docs,
                "success": True
            }
            
        except Exception as e:
            print(f"RAG 쿼리 실행 실패: {e}")
            return {
                "query": query,
                "response": "처리 중 오류가 발생했습니다.",
                "sources": [],
                "success": False
            }

# 전역 RAG 서비스 인스턴스
rag_service = RAGService() 