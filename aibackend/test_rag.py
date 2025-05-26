#!/usr/bin/env python3
"""
RAG 시스템 테스트 스크립트
"""

import requests
import json
import sys
import os

# 백엔드 서버 URL
BASE_URL = "http://localhost:8000"

def test_rag_health():
    """RAG 시스템 상태 확인"""
    print("🔍 RAG 시스템 상태 확인 중...")
    try:
        response = requests.get(f"{BASE_URL}/rag/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ RAG 시스템 상태: {data['status']}")
            print(f"   OpenAI 설정: {data['openai_configured']}")
            print(f"   임베딩 모델: {data['models']['embedding']}")
            print(f"   채팅 모델: {data['models']['chat']}")
            return True
        else:
            print(f"❌ 상태 확인 실패: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 연결 실패: {e}")
        return False

def test_similarity_search(query="엔비디아 실적"):
    """유사도 검색 테스트"""
    print(f"\n🔍 유사도 검색 테스트: '{query}'")
    try:
        params = {
            "query": query,
            "top_k": 3,
            "similarity_threshold": 0.5
        }
        response = requests.get(f"{BASE_URL}/rag/search", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 검색 결과: {data['count']}개 문서 발견")
            for i, doc in enumerate(data['results'][:2]):  # 상위 2개만 출력
                print(f"   📄 문서 {i+1}: {doc['title'][:50]}...")
                print(f"      유사도: {doc['similarity']:.3f}")
            return True
        else:
            print(f"❌ 검색 실패: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 검색 오류: {e}")
        return False

def test_rag_query(query="엔비디아 최근 실적은 어떤가요?"):
    """전체 RAG 파이프라인 테스트"""
    print(f"\n🤖 RAG 질문 답변 테스트: '{query}'")
    try:
        payload = {
            "query": query,
            "top_k": 3,
            "similarity_threshold": 0.5
        }
        response = requests.post(f"{BASE_URL}/rag/query", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ RAG 응답 성공!")
                print(f"📝 응답: {data['response'][:200]}...")
                print(f"📚 참조 문서 수: {len(data['sources'])}")
                return True
            else:
                print("❌ RAG 응답 실패")
                print(f"응답: {data['response']}")
                return False
        else:
            print(f"❌ 요청 실패: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ RAG 오류: {e}")
        return False

def test_stock_analysis(stock_code="NVDA", query="최근 실적 분석"):
    """주식 분석 테스트"""
    print(f"\n📊 주식 분석 테스트: '{stock_code} - {query}'")
    try:
        payload = {
            "stock_code": stock_code,
            "news_query": query,
            "financial_data": "매출액: 350억달러, 영업이익: 200억달러, 순이익: 180억달러, ROE: 25%, PER: 35"
        }
        response = requests.post(f"{BASE_URL}/rag/analyze-stock", json=payload)
        
        if response.status_code == 200:
            data = response.json()
            if data['success']:
                print("✅ 주식 분석 성공!")
                print(f"🏢 종목: {data['stock_code']}")
                print(f"📝 분석 결과: {data['response'][:300]}...")
                print(f"📚 참조 뉴스 수: {len(data['sources'])}")
                print(f"💰 재무 데이터 포함: {data['has_financial_data']}")
                return True
            else:
                print("❌ 주식 분석 실패")
                print(f"응답: {data['response']}")
                return False
        else:
            print(f"❌ 요청 실패: {response.status_code}")
            print(response.text)
            return False
    except Exception as e:
        print(f"❌ 주식 분석 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("🚀 RAG 시스템 종합 테스트 시작\n")
    
    # 1. 건강 상태 확인
    if not test_rag_health():
        print("❌ RAG 시스템이 준비되지 않았습니다.")
        sys.exit(1)
    
    # 2. 유사도 검색 테스트
    if not test_similarity_search():
        print("⚠️ 유사도 검색 테스트 실패 (뉴스 데이터가 없을 수 있습니다)")
    
    # 3. 전체 RAG 파이프라인 테스트
    if not test_rag_query():
        print("⚠️ RAG 질문 답변 테스트 실패")
    
    # 4. 주식 분석 테스트
    if not test_stock_analysis():
        print("⚠️ 주식 분석 테스트 실패")
    
    print("\n🎉 RAG 시스템 테스트 완료!")
    
    # 4. 대화형 모드
    print("\n💬 대화형 모드 (종료하려면 'quit' 입력)")
    while True:
        try:
            user_query = input("\n질문: ").strip()
            if user_query.lower() in ['quit', 'exit', 'q']:
                break
            if user_query:
                test_rag_query(user_query)
        except KeyboardInterrupt:
            break
    
    print("\n👋 테스트 종료")

if __name__ == "__main__":
    main() 