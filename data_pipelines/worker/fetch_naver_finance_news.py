import time, requests, pandas as pd
from bs4 import BeautifulSoup, Tag
from urllib.parse import urlparse, parse_qs, unquote
import random
from urllib.parse import urljoin
import requests
import json, pathlib

date = "2025-05-16"
url = f"https://finance.naver.com/news/mainnews.naver?date={date}"
BASE = "https://n.news.naver.com"
CSV_NAME = f"naverfinance_mainnews_{date}.csv"
MAX_PAGES = 10

articles = []

headers = {
    "User-Agent": "Mozilla/5.0"
}

from urllib.parse import urlparse, parse_qs

def news_read_to_mnews(url: str) -> str:
    """
    '/news/news_read.naver?article_id=0001209610&office_id=215&…'
        → 'https://n.news.naver.com/mnews/article/215/0001209610'
    """
    if "/news/news_read" not in url:
        return url                          # 대상이 아니면 그대로

    qs  = parse_qs(urlparse(url).query)     # 쿼리 → dict
    oid = qs.get("office_id", [""])[0]
    aid = qs.get("article_id", [""])[0]
    return f"https://n.news.naver.com/mnews/article/{oid}/{aid}" if oid and aid else url

for page_no in range(1, MAX_PAGES + 1):
    time.sleep(random.uniform(1.5, 3.0))
    url = f"https://finance.naver.com/news/mainnews.naver?date={date}&page={page_no}"
    response = requests.get(url)
    html = response.text
    soup = BeautifulSoup(html, "lxml")

    print(f"\n🔄 [목록] page {page_no} 요청 → {url}")

    for li in soup.select("div.mainNewsList li.block1"):   # 카드 전부 순회
        title_a = li.select_one("dd.articleSubject > a[href]")
        press   = li.select_one("dd.articleSummary span.press")
        wdate   = li.select_one("dd.articleSummary span.wdate")

        if not title_a:
            continue

        url = news_read_to_mnews(title_a["href"])
        articles.append({
            "title": title_a.get_text(strip=True),
            "url":   url,         # 이미 https://n.news.naver.com/…
            "press": press.get_text(strip=True) if press else "",
            "time":  wdate.get_text(strip=True) if wdate else ""
        })
    
    print(f"📄 page {page_no} 수집 완료 (기사 {len(articles)}개)")

full = []

for idx, art in enumerate(articles, start=1):
    time.sleep(random.uniform(1.5, 3.0))        # 딜레이

    res = requests.get(art["url"], headers=headers, timeout=10)
    if res.status_code != 200:
        print("❌ 요청 실패", art["url"])
        continue

    page = BeautifulSoup(res.text, "html.parser")
    body = page.select_one("#dic_area, .go_trans._article_content")
    art["content"] = body.get_text(strip=True) if body else ""
    full.append(art)

    print(f"✅ page {idx} 본문 저장")

# 💾 STEP 3: 저장
df = pd.DataFrame(full or articles)
df.to_csv(CSV_NAME, index=False, encoding="utf-8-sig")
print("\n✅ CSV 저장 완료: {CSV_NAME}")

path = pathlib.Path("CSV_NAME.jsonl")
with path.open("w", encoding="utf-8") as f:
    for art in full:
        f.write(json.dumps(art, ensure_ascii=False) + "\n")
print(f"\n✅ JSONL 저장 완료: {path}")