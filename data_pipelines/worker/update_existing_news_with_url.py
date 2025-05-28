import os
import sys
import time
import random
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from sqlalchemy import text
from dotenv import load_dotenv

# 경로 설정을 통해 aibackend 패키지를 import 할 수 있도록 함
backend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
sys.path.append(backend_path)

# 환경 변수 로드 (루트 디렉토리의 .env 파일)
dotenv_path = os.path.join(backend_path, '.env')
load_dotenv(dotenv_path)

# aibackend에서 필요한 모듈 가져오기
from aibackend.app.news_vector_db import NewsSessionLocal

# ──────────────── 파라미터 ──────────────────────
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def search_naver_news_url(title: str, content: str = "") -> str:
    """네이버 뉴스에서 제목으로 기사 URL 검색"""
    try:
        # 검색어 준비 (제목의 처음 50자만 사용)
        search_query = title[:50].strip()
        if not search_query:
            return None
        
        # 네이버 뉴스 검색 URL
        search_url = f"https://search.naver.com/search.naver?where=news&query={search_query}"
        
        time.sleep(random.uniform(1.0, 2.0))  # 요청 간격
        response = requests.get(search_url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # 검색 결과에서 뉴스 링크 찾기
        news_items = soup.select(".news_area")
        
        for item in news_items[:3]:  # 상위 3개 결과만 확인
            # 제목 요소 찾기
            title_elem = item.select_one(".news_tit")
            if not title_elem:
                continue
                
            # 제목 텍스트 비교
            found_title = title_elem.get_text(strip=True)
            
            # 제목 유사도 체크 (간단한 포함 관계)
            title_words = set(title.replace(" ", "").lower())
            found_words = set(found_title.replace(" ", "").lower())
            
            # 70% 이상 겹치면 같은 기사로 판단
            if len(title_words & found_words) / len(title_words) > 0.7:
                url = title_elem.get("href")
                if url:
                    print(f"✅ URL 찾음: {title[:30]}... -> {url}")
                    return url
        
        print(f"⚠️ URL 못찾음: {title[:30]}...")
        return None
        
    except Exception as e:
        print(f"❌ URL 검색 실패 ({title[:30]}...): {e}")
        return None

def update_news_with_urls():
    """기존 뉴스 데이터에 URL 추가"""
    session = NewsSessionLocal()
    
    try:
        # URL이 없는 뉴스 데이터 조회
        print("🔍 URL이 없는 뉴스 데이터 조회 중...")
        
        query = text("""
            SELECT id, title, content 
            FROM news_vectors 
            WHERE url IS NULL OR url = ''
            ORDER BY published_at DESC
            LIMIT 100
        """)
        
        result = session.execute(query)
        news_list = result.fetchall()
        
        print(f"📊 처리할 뉴스 수: {len(news_list)}개")
        
        if not news_list:
            print("✅ 모든 뉴스에 URL이 이미 있습니다!")
            return
        
        updated_count = 0
        failed_count = 0
        
        for i, news in enumerate(news_list, 1):
            print(f"\n🔄 [{i}/{len(news_list)}] 처리 중: {news.title[:50]}...")
            
            # URL 검색
            found_url = search_naver_news_url(news.title, news.content)
            
            if found_url:
                # URL 업데이트
                try:
                    update_query = text("""
                        UPDATE news_vectors 
                        SET url = :url 
                        WHERE id = :id
                    """)
                    
                    session.execute(update_query, {
                        "url": found_url,
                        "id": news.id
                    })
                    session.commit()
                    
                    updated_count += 1
                    print(f"✅ URL 업데이트 완료!")
                    
                except Exception as e:
                    print(f"❌ DB 업데이트 실패: {e}")
                    session.rollback()
                    failed_count += 1
            else:
                failed_count += 1
            
            # 진행률 표시
            if i % 10 == 0:
                print(f"📈 진행률: {i}/{len(news_list)} ({i/len(news_list)*100:.1f}%)")
                print(f"   업데이트: {updated_count}개, 실패: {failed_count}개")
        
        print(f"\n🎉 URL 업데이트 완료!")
        print(f"✅ 성공: {updated_count}개")
        print(f"❌ 실패: {failed_count}개")
        print(f"📊 성공률: {updated_count/(updated_count+failed_count)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ 전체 프로세스 중 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

def update_news_with_manual_search():
    """수동으로 URL 패턴을 만들어 업데이트 (더 정확한 방법)"""
    session = NewsSessionLocal()
    
    try:
        print("🔍 제목에서 언론사 정보 추출하여 URL 생성 시도...")
        
        # 제목에서 언론사 정보가 있는 뉴스 조회
        query = text("""
            SELECT id, title, content, published_at
            FROM news_vectors 
            WHERE url IS NULL OR url = ''
            ORDER BY published_at DESC
            LIMIT 50
        """)
        
        result = session.execute(query)
        news_list = result.fetchall()
        
        print(f"📊 처리할 뉴스 수: {len(news_list)}개")
        
        updated_count = 0
        
        for i, news in enumerate(news_list, 1):
            print(f"\n🔄 [{i}/{len(news_list)}] {news.title[:50]}...")
            
            # 간단한 URL 생성 시도 (실제로는 더 복잡한 로직 필요)
            # 여기서는 뉴스 제목과 내용으로 검색하는 방식 사용
            found_url = search_naver_news_url(news.title)
            
            if found_url:
                try:
                    update_query = text("""
                        UPDATE news_vectors 
                        SET url = :url 
                        WHERE id = :id
                    """)
                    
                    session.execute(update_query, {
                        "url": found_url,
                        "id": news.id
                    })
                    session.commit()
                    
                    updated_count += 1
                    print(f"✅ URL 업데이트 완료: {found_url}")
                    
                except Exception as e:
                    print(f"❌ DB 업데이트 실패: {e}")
                    session.rollback()
        
        print(f"\n🎉 URL 업데이트 완료! (업데이트: {updated_count}개)")
        
    except Exception as e:
        print(f"❌ 프로세스 중 오류 발생: {e}")
        session.rollback()
    finally:
        session.close()

def check_current_status():
    """현재 DB 상태 확인"""
    session = NewsSessionLocal()
    
    try:
        # 전체 뉴스 수
        total_query = text("SELECT COUNT(*) FROM news_vectors")
        total_count = session.execute(total_query).scalar()
        
        # URL이 있는 뉴스 수
        with_url_query = text("SELECT COUNT(*) FROM news_vectors WHERE url IS NOT NULL AND url != ''")
        with_url_count = session.execute(with_url_query).scalar()
        
        # URL이 없는 뉴스 수
        without_url_count = total_count - with_url_count
        
        print(f"📊 현재 DB 상태:")
        print(f"   전체 뉴스: {total_count}개")
        print(f"   URL 있음: {with_url_count}개 ({with_url_count/total_count*100:.1f}%)")
        print(f"   URL 없음: {without_url_count}개 ({without_url_count/total_count*100:.1f}%)")
        
        return without_url_count > 0
        
    except Exception as e:
        print(f"❌ 상태 확인 중 오류: {e}")
        return False
    finally:
        session.close()

def main():
    """메인 실행 함수"""
    print("🚀 기존 뉴스 데이터에 URL 추가 프로세스 시작")
    
    # 현재 상태 확인
    needs_update = check_current_status()
    
    if not needs_update:
        print("✅ 모든 뉴스에 URL이 이미 있습니다!")
        return
    
    print("\n" + "="*50)
    print("URL 업데이트 방법을 선택하세요:")
    print("1. 자동 검색 (네이버 뉴스 검색 사용)")
    print("2. 상태 확인만")
    print("="*50)
    
    try:
        choice = input("선택 (1 또는 2): ").strip()
        
        if choice == "1":
            print("\n🔍 자동 URL 검색 시작...")
            update_news_with_urls()
        elif choice == "2":
            print("\n📊 상태 확인 완료")
        else:
            print("❌ 잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 실행 중 오류: {e}")

if __name__ == "__main__":
    main() 