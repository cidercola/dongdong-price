from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from curl_cffi import requests as cffi_requests
from bs4 import BeautifulSoup
import requests
import urllib.parse
import time
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Referer': 'https://web.joongna.com/',
    'Origin': 'https://web.joongna.com'
}

DAANGN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7'
}

def is_exact_keyword_match(title: str, keyword: str) -> bool:
    if not title or not keyword:
        return False
    clean_title = title.lower()
    clean_keyword = keyword.lower().strip()
    nospace_title = clean_title.replace(" ", "")
    nospace_keyword = clean_keyword.replace(" ", "")
    return nospace_keyword in nospace_title

def calculate_time_ago(raw_time, now_ts):
    if not raw_time:
        return None
    try:
        ts = int(raw_time)
        if ts <= 0:
            return None
        if ts > 10000000000:
            ts = ts // 1000
            
        diff_sec = now_ts - ts
        if diff_sec < 60:
            return "방금 전"
        diff_min = diff_sec // 60
        if diff_min < 60:
            return f"{diff_min}분 전"
        diff_hour = diff_min // 60
        if diff_hour < 24:
            return f"{diff_hour}시간 전"
        diff_day = diff_hour // 24
        if diff_day < 30:
            return f"{diff_day}일 전"
        return "오래 전"
    except:
        return None

@app.get("/api/search")
def search_products(keyword: str):
    results = []
    encoded_keyword = urllib.parse.quote(keyword)
    now_ts = int(time.time())

    bunjang_count = 0
    joongna_count = 0
    daangn_count = 0

    # 1. 번개장터 수집
    for page in range(0, 4):
        try:
            bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&order=date&page={page}&n=30&stat_device=android"
            res = requests.get(bunjang_url, headers=HEADERS, timeout=4)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('list', [])
                if not items:
                    break
                
                for item in items:
                    title = item.get('name') or ''
                    if not is_exact_keyword_match(title, keyword):
                        continue

                    img_url = item.get('product_image') or ''
                    if img_url and not img_url.startswith('http'):
                        img_url = f"https://media.bunjang.co.kr/product/{item.get('pid')}_1.jpg"

                    raw_time = item.get('update_time') or item.get('start_date')
                    time_ago_str = calculate_time_ago(raw_time, now_ts) or "최신"

                    try:
                        created_at = int(raw_time)
                        if created_at > 10000000000:
                            created_at = created_at // 1000
                    except:
                        created_at = now_ts

                    results.append({
                        "id": f"bunk-{item.get('pid')}",
                        "platform": "번개장터",
                        "platformColor": "bg-red-500",
                        "title": title,
                        "price": int(item.get('price', 0)),
                        "location": item.get('location') or '전국',
                        "imageUrl": img_url,
                        "createdAt": created_at,
                        "timeAgo": time_ago_str,
                        "link": f"https://m.bunjang.co.kr/products/{item.get('pid')}"
                    })
                    bunjang_count += 1
        except Exception as e:
            print("번개장터 수집 오류:", e)
            break

    # 2. 중고나라 수집
    joonggo_url = "https://search-api.joongna.com/v3/search/all"
    for page in range(0, 3):
        try:
            payload = {
                "osType": 2,
                "searchWord": keyword,
                "sort": "RECOMMEND_SORT",
                "page": page,
                "quantity": 50,
                "firstQuantity": 50,
                "saleYn": "SALE_N",
                "jnPayYn": "ALL",
                "parcelFeeYn": "ALL",
                "registPeriod": "ALL",
                "adjustSearchKeyword": True,
                "keywordSource": "INPUT_KEYWORD",
                "categoryFilter": [{"categoryDepth": 0, "categorySeq": 0}],
                "priceFilter": {"minPrice": 0, "maxPrice": 100000000}
            }
            
            res = cffi_requests.post(
                joonggo_url, 
                headers=HEADERS, 
                json=payload, 
                impersonate="chrome120", 
                timeout=5
            )

            if res.status_code == 200:
                data = res.json()
                inner_data = data.get('data', data)
                items = []
                if isinstance(inner_data, dict):
                    items = (
                        inner_data.get('items') or 
                        inner_data.get('list') or 
                        inner_data.get('goodsList') or 
                        []
                    )
                elif isinstance(inner_data, list):
                    items = inner_data

                if not items:
                    break
                
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    
                    product_id = item.get('seq') or item.get('productSeq') or item.get('articleSeq') or item.get('id') or item.get('productId')
                    title = item.get('title') or item.get('productTitle') or item.get('articleTitle') or item.get('name') or item.get('productName') or ''
                    
                    if not is_exact_keyword_match(title, keyword):
                        continue

                    raw_img = (
                        item.get('detailImgUrl') or 
                        item.get('url') or 
                        item.get('imageUrl') or 
                        item.get('productImg') or 
                        item.get('imgUrl') or 
                        item.get('mediaUrl') or 
                        ''
                    )
                    
                    if not raw_img and isinstance(item.get('media'), list) and len(item['media']) > 0:
                        raw_img = item['media'][0].get('url') or item['media'][0].get('path') or ''
                    elif not raw_img and isinstance(item.get('images'), list) and len(item['images']) > 0:
                        raw_img = item['images'][0].get('url') or item['images'][0].get('path') or ''

                    img_url = str(raw_img) if raw_img else ''
                    if img_url and not img_url.startswith('http'):
                        img_url = f"https://img2.joongna.com{img_url}" if img_url.startswith('/') else f"https://img2.joongna.com/{img_url}"

                    if product_id and title:
                        results.append({
                            "id": f"joong-{product_id}",
                            "platform": "중고나라",
                            "platformColor": "bg-blue-600",
                            "title": title,
                            "price": int(item.get('price', 0)),
                            "location": item.get('locationName') or item.get('location') or '전국',
                            "imageUrl": img_url,
                            "createdAt": now_ts,
                            "timeAgo": "최신",
                            "link": f"https://web.joongna.com/product/{product_id}"
                        })
                        joongna_count += 1
        except Exception as e:
            print("중고나라 수집 오류:", e)
            break

    # 3. 당근 수집 (의정부시 호원동 지역 한정 파싱)
    try:
        daangn_url = f"https://www.daangn.com/search/{encoded_keyword}/"
        res_dg = cffi_requests.get(
            daangn_url, 
            headers=DAANGN_HEADERS, 
            impersonate="chrome120", 
            timeout=5
        )
        
        if res_dg.status_code == 200:
            soup = BeautifulSoup(res_dg.text, 'html.parser')
            articles = soup.select('article.flea-market-article, a.flea-market-article-link')
            
            for idx, article in enumerate(articles[:30]):
                try:
                    title_elem = article.select_one('.article-title, .title')
                    price_elem = article.select_one('.article-price, .price')
                    region_elem = article.select_one('.article-region-name, .region-name')
                    img_elem = article.select_one('img')
                    link_elem = article if article.name == 'a' else article.select_one('a')
                    
                    title = title_elem.text.strip() if title_elem else ''
                    if not title or not is_exact_keyword_match(title, keyword):
                        continue
                    
                    price_str = price_elem.text.strip() if price_elem else '0'
                    price_num = int(re.sub(r'[^0-9]', '', price_str) or 0)
                    
                    region_str = region_elem.text.strip() if region_elem else '의정부시 호원동'
                    
                    img_url = ''
                    if img_elem:
                        img_url = img_elem.get('src') or img_elem.get('data-src') or ''
                        
                    article_link = 'https://www.daangn.com' + link_elem.get('href') if link_elem and link_elem.get('href') else 'https://www.daangn.com'

                    results.append({
                        "id": f"daangn-{idx}-{now_ts}",
                        "platform": "당근",
                        "platformColor": "bg-amber-600",
                        "title": title,
                        "price": price_num,
                        "location": region_str,
                        "imageUrl": img_url,
                        "createdAt": now_ts - (idx * 60),
                        "timeAgo": "호원동 매물",
                        "link": article_link
                    })
                    daangn_count += 1
                except Exception as ex:
                    continue
    except Exception as e:
        print("당근 수집 오류:", e)

    results.sort(key=lambda x: x['createdAt'], reverse=True)
    
    return {
        "totalCount": len(results),
        "bunjangCount": bunjang_count,
        "joongnaCount": joongna_count,
        "daangnCount": daangn_count,
        "items": results
    }
