from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 모바일 앱 전용 헤더 (중고나라 차단 우회 핵심)
BUNJANG_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://m.bunjang.co.kr',
    'Referer': 'https://m.bunjang.co.kr/'
}

JOONGNA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Referer': 'https://m.joongna.com/',
    'Origin': 'https://m.joongna.com'
}

@app.get("/api/search")
def search_products(keyword: str):
    results = []
    encoded_keyword = urllib.parse.quote(keyword)
    now_ts = int(time.time())

    # 1. 번개장터 수집 (모바일 앱 API)
    for page in range(0, 4):
        try:
            bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&order=date&page={page}&n=30&stat_device=android"
            res = requests.get(bunjang_url, headers=BUNJANG_HEADERS, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('list', [])
                if not items:
                    break
                
                for item in items:
                    update_time = int(item.get('update_time', 0))
                    img_url = item.get('product_image') or ''
                    if img_url and not img_url.startswith('http'):
                        img_url = f"https://media.bunjang.co.kr/product/{item.get('pid')}_1.jpg"

                    results.append({
                        "id": f"bunk-{item.get('pid')}",
                        "platform": "번개장터",
                        "platformColor": "bg-red-500",
                        "title": item.get('name'),
                        "price": int(item.get('price', 0)),
                        "location": item.get('location') or '전국',
                        "imageUrl": img_url,
                        "createdAt": update_time if update_time > 0 else now_ts,
                        "link": f"https://m.bunjang.co.kr/products/{item.get('pid')}"
                    })
        except Exception as e:
            print("번개장터 수집 오류:", e)
            break

    # 2. 중고나라 수집 (모바일 우회 API)
    for page in range(1, 4):
        try:
            joonggo_url = f"https://api.joongna.com/api/product/list?searchWord={encoded_keyword}&page={page}&size=30&sort=RECENT_DATE&osType=ANDROID"
            res = requests.get(joonggo_url, headers=JOONGNA_HEADERS, timeout=5)
            
            # 메인 모바일 API 응답이 없을 경우 모바일 웹 API로 백업 시도
            if res.status_code != 200 or not res.json().get('data', {}).get('items'):
                joonggo_url = f"https://web.joongna.com/api/product/list?searchWord={encoded_keyword}&page={page}&size=30&sort=RECENT_DATE"
                res = requests.get(joonggo_url, headers=JOONGNA_HEADERS, timeout=5)

            if res.status_code == 200:
                data = res.json()
                items = data.get('data', {}).get('items', [])
                if not items:
                    break
                
                for item in items:
                    reg_date = item.get('sortDate') or item.get('regDate') or 0
                    update_time = int(reg_date / 1000) if reg_date > 10000000000 else int(reg_date)
                    img_url = item.get('detailImgUrl') or item.get('productImg') or item.get('imgUrl') or ''
                    
                    product_id = item.get('seq') or item.get('productSeq') or item.get('articleSeq')
                    
                    if product_id:
                        results.append({
                            "id": f"joong-{product_id}",
                            "platform": "중고나라",
                            "platformColor": "bg-blue-600",
                            "title": item.get('title') or item.get('productTitle'),
                            "price": int(item.get('price', 0)),
                            "location": item.get('locationName') or '전국',
                            "imageUrl": img_url,
                            "createdAt": update_time if update_time > 0 else now_ts,
                            "link": f"https://web.joongna.com/product/{product_id}"
                        })
        except Exception as e:
            print("중고나라 수집 오류:", e)
            break

    # 최신 등록순 정렬
    results.sort(key=lambda x: x['createdAt'], reverse=True)
    return results