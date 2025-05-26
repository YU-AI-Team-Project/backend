# RAG (Retrieval-Augmented Generation) 시스템 가이드

## 📖 개요

이 RAG 시스템은 뉴스 데이터베이스를 활용하여 사용자의 질문에 대해 관련 뉴스 기사를 검색하고, 이를 바탕으로 정확하고 유용한 답변을 생성하는 AI 시스템입니다.

## 🏗️ 아키텍처

```
사용자 질문 → 임베딩 변환 → 벡터 검색 → 관련 뉴스 수집 → GPT 응답 생성
```

### 주요 구성요소

1. **벡터 임베딩**: OpenAI의 `text-embedding-ada-002` 모델 사용
2. **벡터 데이터베이스**: PostgreSQL + pgvector 확장
3. **응답 생성**: OpenAI의 `gpt-4o` 모델 사용
4. **유사도 검색**: 코사인 유사도 기반 검색

## 📁 파일 구조

```
backend/aibackend/
├── app/
│   ├── services/
│   │   └── rag_service.py          # RAG 핵심 로직
│   ├── routers/
│   │   └── rag.py                  # RAG API 엔드포인트
│   ├── models.py                   # NewsVector 모델 정의
│   └── main.py                     # RAG 라우터 등록
├── test_rag.py                     # RAG 테스트 스크립트
└── RAG_README.md                   # 이 문서
```

## 🚀 설정 및 실행

### 1. 환경 변수 설정

`.env` 파일에 OpenAI API 키를 추가하세요:

```bash
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 데이터베이스 설정

PostgreSQL에 pgvector 확장을 설치하세요:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 4. 뉴스 데이터 임베딩

뉴스 데이터를 벡터 데이터베이스에 저장하려면:

```python
from aibackend.app.ai_components.news_api_embedding import embed_and_store_news

# 뉴스 JSONL 파일 경로 지정
embed_and_store_news("path/to/news_data.jsonl")
```

### 5. 서버 실행

```bash
uvicorn aibackend.app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 API 사용법

### 1. 상태 확인

```bash
GET /rag/health
```

**응답 예시:**
```json
{
  "status": "healthy",
  "openai_configured": true,
  "models": {
    "embedding": "text-embedding-ada-002",
    "chat": "gpt-4o"
  }
}
```

### 2. 유사도 검색

```bash
GET /rag/search?query=엔비디아 실적&top_k=5&similarity_threshold=0.7
```

**응답 예시:**
```json
{
  "query": "엔비디아 실적",
  "results": [
    {
      "id": "uuid-string",
      "title": "엔비디아 3분기 실적 발표",
      "content": "엔비디아가 발표한 3분기 실적...",
      "published_at": "2024-01-15T10:00:00",
      "similarity": 0.85
    }
  ],
  "count": 5
}
```

### 3. RAG 질문 답변

```bash
POST /rag/query
```

**요청 본문:**
```json
{
  "query": "엔비디아 최근 실적은 어떤가요?",
  "top_k": 5,
  "similarity_threshold": 0.7,
  "system_prompt": "당신은 투자 전문가입니다."
}
```

**응답 예시:**
```json
{
  "query": "엔비디아 최근 실적은 어떤가요?",
  "response": "엔비디아의 최근 실적을 살펴보면...",
  "sources": [
    {
      "id": "uuid-string",
      "title": "뉴스 제목",
      "content": "뉴스 내용",
      "published_at": "2024-01-15T10:00:00",
      "similarity": 0.85
    }
  ],
  "success": true
}
```

### 4. 컨텍스트 기반 생성

```bash
POST /rag/generate
```

**요청 본문:**
```json
{
  "query": "이 정보를 바탕으로 투자 조언을 해주세요",
  "context_docs": [
    {
      "title": "뉴스 제목",
      "content": "뉴스 내용",
      "published_at": "2024-01-15T10:00:00"
    }
  ],
  "system_prompt": "투자 전문가로서 조언해주세요"
}
```

## 🧪 테스트

RAG 시스템을 테스트하려면:

```bash
cd backend/aibackend
python test_rag.py
```

테스트 스크립트는 다음을 수행합니다:
1. RAG 시스템 상태 확인
2. 유사도 검색 테스트
3. 전체 RAG 파이프라인 테스트
4. 대화형 모드 제공

## ⚙️ 설정 옵션

### RAGService 파라미터

- `embedding_model`: 임베딩 모델 (기본값: "text-embedding-ada-002")
- `chat_model`: 채팅 모델 (기본값: "gpt-4o")

### 검색 파라미터

- `top_k`: 반환할 최대 문서 수 (기본값: 5)
- `similarity_threshold`: 유사도 임계값 (기본값: 0.7)
- `system_prompt`: 사용자 정의 시스템 프롬프트

## 🔍 프론트엔드 연동 예시

### JavaScript/React 예시

```javascript
// RAG 질문 요청
const askQuestion = async (question) => {
  try {
    const response = await fetch('/rag/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: question,
        top_k: 5,
        similarity_threshold: 0.7
      })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('답변:', data.response);
      console.log('참조 문서:', data.sources);
    } else {
      console.log('오류:', data.response);
    }
  } catch (error) {
    console.error('요청 실패:', error);
  }
};

// 사용 예시
askQuestion("엔비디아 주가 전망은 어떤가요?");
```

### Python 클라이언트 예시

```python
import requests

def ask_rag_question(question, base_url="http://localhost:8000"):
    response = requests.post(
        f"{base_url}/rag/query",
        json={
            "query": question,
            "top_k": 5,
            "similarity_threshold": 0.7
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        if data['success']:
            print(f"답변: {data['response']}")
            print(f"참조 문서 수: {len(data['sources'])}")
        else:
            print(f"오류: {data['response']}")
    else:
        print(f"요청 실패: {response.status_code}")

# 사용 예시
ask_rag_question("테슬라 최근 뉴스는?")
```

## 🚨 주의사항

1. **OpenAI API 비용**: RAG 시스템은 임베딩과 채팅 API를 사용하므로 비용이 발생합니다.
2. **데이터베이스 크기**: 뉴스 데이터가 많을수록 더 나은 검색 결과를 얻을 수 있습니다.
3. **임베딩 품질**: 검색 품질은 뉴스 데이터의 임베딩 품질에 크게 의존합니다.
4. **응답 시간**: 벡터 검색과 GPT 응답 생성으로 인해 약간의 지연이 있을 수 있습니다.

## 📈 성능 최적화

1. **인덱스 최적화**: pgvector 인덱스 설정
2. **캐싱**: 자주 사용되는 질문의 결과 캐싱
3. **배치 처리**: 여러 질문을 배치로 처리
4. **컨텍스트 길이 제한**: GPT 토큰 제한 고려

## 🛠️ 트러블슈팅

### 일반적인 문제들

1. **OpenAI API 키 오류**
   - `.env` 파일에 올바른 API 키가 설정되어 있는지 확인

2. **pgvector 확장 오류**
   - PostgreSQL에 pgvector 확장이 설치되어 있는지 확인

3. **검색 결과 없음**
   - 뉴스 데이터가 데이터베이스에 저장되어 있는지 확인
   - 유사도 임계값을 낮춰보세요

4. **응답 생성 실패**
   - OpenAI API 할당량 확인
   - 네트워크 연결 상태 확인

## 📞 지원

문제가 발생하면 다음을 확인해보세요:

1. 로그 파일 확인
2. `/rag/health` 엔드포인트로 시스템 상태 확인
3. `test_rag.py` 스크립트로 종합 테스트 실행 