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
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Referer': 'https://web.joongna.com/',
    'Origin': 'https://web.joongna.com'
}

@app.get("/api/search")
def search_products(keyword: str):
    results = []
    encoded_keyword = urllib.parse.quote(keyword)
    now_ts = int(time.time())

    # 1. 번개장터 수집
    for page in range(0, 4):
        try:
            bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&order=date&page={page}&n=30&stat_device=android"
            res = requests.get(bunjang_url, headers=HEADERS, timeout=5)
            
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

    # 2. 중고나라 수집 (최신 POST API 및 파라미터 적용)
    joonggo_api_url = "https://web.joongna.com/api/v2/product/search"
    
    for page in range(1, 4):
        try:
            payload = {
                "searchWord": keyword,
                "page": page,
                "size": 30,
                "sort": "RECENT_DATE"
            }
            
            # POST 요청으로 변경
            res = requests.post(joonggo_api_url, headers=HEADERS, json=payload, timeout=5)
            
            # 만약 v2 POST 방식 실패 시 GET fallback 처리
            if res.status_code != 200:
                fallback_url = f"https://web.joongna.com/api/product/search?searchWord={encoded_keyword}&page={page}&size=30&sort=RECENT_DATE"
                res = requests.get(fallback_url, headers=HEADERS, timeout=5)

            if res.status_code == 200:
                data = res.json()
                # 중고나라 응답 객체 데이터 트레이싱
                items = data.get('data', {}).get('items', []) or data.get('data', []) or data.get('items', [])
                
                if not items and isinstance(data, list):
                    items = data

                if not items:
                    break
                
                for item in items:
                    reg_date = item.get('sortDate') or item.get('regDate') or item.get('articleRegDate') or 0
                    update_time = int(reg_date / 1000) if reg_date > 10000000000 else int(reg_date)
                    img_url = item.get('detailImgUrl') or item.get('productImg') or item.get('imgUrl') or item.get('mediaUrl') or ''
                    product_id = item.get('seq') or item.get('productSeq') or item.get('articleSeq') or item.get('id')
                    
                    if product_id:
                        results.append({
                            "id": f"joong-{product_id}",
                            "platform": "중고나라",
                            "platformColor": "bg-blue-600",
                            "title": item.get('title') or item.get('productTitle') or item.get('articleTitle'),
                            "price": int(item.get('price', 0)),
                            "location": item.get('locationName') or item.get('location') or '전국',
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
