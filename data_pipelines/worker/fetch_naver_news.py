import time, requests, pandas as pd
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, parse_qs, unquote
import random

response = requests.get("https://search.naver.com/search.naver?ssc=tab.news.all&where=news&sm=tab_jum&query=%EC%82%BC%EC%84%B1%EC%A0%84%EC%9E%90")

html = response.text
soup = BeautifulSoup(html, "lxml")

articles = []

headers = {
    "User-Agent": "Mozilla/5.0"
}

def real_url(a: Tag) -> str:
    # 1) cru가 있으면 그대로
    if a.has_attr("cru"):
        return a["cru"]

    # 2) href 안의 u= 파라미터 디코드
    qs = parse_qs(urlparse(a["href"]).query)
    if "u" in qs:
        return unquote(qs["u"][0])

    # 3) fallback – 마지막 보호막
    return a["href"]

for wrapper in soup.select('span.sds-comps-profile-info-subtext'):   # list<Tag>
    a_tag = wrapper.select_one('a[href]')        # Tag | None
    if not a_tag:                    # ‘10시간 전’ 같이 링크 없는 경우
        continue
    articles.append(
        {
            "press": a_tag.get_text(strip=True),  # 네이버뉴스
            "url": real_url(a_tag)
        }
    )

full_articles = []

for index, article in enumerate(articles):
    url = article["url"]

    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"⚠️ {index+1}번 기사 요청 실패: {e}")
        continue

    html = res.text
    soup = BeautifulSoup(html, "html.parser")

    try:
        title = soup.select_one("#title_area").get_text(strip=True)
        content = soup.select_one("#dic_area").get_text(strip=True)
    except AttributeError:
        print(f"❌ 본문/제목 선택 실패: {url}")
        continue

    print(f"\n================ {index+1} 번째 기사 ================\n")
    print("제목:", title)
    print("기사 내용:\n", content[:200] + "..." if len(content) > 200 else content)

    full_articles.append({
        "title": title,
        "content": content,
        "press": article["press"],
        "url": url
    })

    time.sleep(random.uniform(1.5, 3.5))  # 서버에 부담 주지 않도록

# 💾 STEP 3: 저장
df = pd.DataFrame(full_articles)
df.to_csv("naver_news.csv", index=False, encoding="utf-8-sig")
print("\n✅ CSV 저장 완료: naver_news.csv")











