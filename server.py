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

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://m.bunjang.co.kr',
    'Referer': 'https://m.bunjang.co.kr/'
}

@app.get("/api/search")
def search_products(keyword: str):
    results = []
    encoded_keyword = urllib.parse.quote(keyword)
    now_ts = int(time.time())

    # 1. 번개장터 수집 (모바일 앱 실시간 검색 API 사용)
    for page in range(0, 4): # 최근 등록순 100개 수집
        try:
            # order=date (최신순 정렬) 적용
            bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&order=date&page={page}&n=30&stat_device=android"
            res = requests.get(bunjang_url, headers=HEADERS, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('list', [])
                if not items:
                    break
                
                for item in items:
                    update_time = int(item.get('update_time', 0))
                    
                    # 이미지 URL 보정
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

    # 2. 중고나라 수집 (모바일/웹 공용 API)
    for page in range(1, 4):
        try:
            joonggo_url = f"https://web.joongna.com/api/product/list?searchWord={encoded_keyword}&page={page}&size=30&sort=RECENT_DATE"
            res = requests.get(joonggo_url, headers=HEADERS, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('data', {}).get('items', [])
                if not items:
                    break
                
                for item in items:
                    reg_date = item.get('sortDate') or item.get('regDate') or 0
                    update_time = int(reg_date / 1000) if reg_date > 10000000000 else int(reg_date)
                    img_url = item.get('detailImgUrl') or item.get('productImg') or ''
                    
                    results.append({
                        "id": f"joong-{item.get('seq')}",
                        "platform": "중고나라",
                        "platformColor": "bg-blue-600",
                        "title": item.get('title') or item.get('productTitle'),
                        "price": int(item.get('price', 0)),
                        "location": item.get('locationName') or '전국',
                        "imageUrl": img_url,
                        "createdAt": update_time if update_time > 0 else now_ts,
                        "link": f"https://web.joongna.com/product/{item.get('seq')}"
                    })
        except Exception as e:
            print("중고나라 수집 오류:", e)
            break

    # 최신 등록순 정렬
    results.sort(key=lambda x: x['createdAt'], reverse=True)
    return results