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

@app.get("/api/search")
def search_products(keyword: str):
    results = []
    encoded_keyword = urllib.parse.quote(keyword)
    now_ts = int(time.time())
    twelve_hours_ago = now_ts - (12 * 3600)

    # 1. 번개장터 수집 (최대 15페이지 탐색)
    for page in range(0, 15):
        try:
            bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&page={page}&request_id=2024&stat_device=android&sort=time"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = requests.get(bunjang_url, headers=headers, timeout=4)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('list', [])
                if not items:
                    break
                
                stop_fetching = False
                for item in items:
                    update_time = int(item.get('update_time', 0))
                    if update_time < twelve_hours_ago:
                        stop_fetching = True
                        break
                        
                    results.append({
                        "id": f"bunk-{item.get('pid')}",
                        "platform": "번개장터",
                        "platformColor": "bg-red-500",
                        "title": item.get('name'),
                        "price": int(item.get('price', 0)),
                        "location": item.get('location', '지역 미지정'),
                        "imageUrl": item.get('product_image'),
                        "createdAt": update_time,
                        "link": f"https://m.bunjang.co.kr/products/{item.get('pid')}"
                    })
                if stop_fetching:
                    break
        except Exception as e:
            print("번개장터 수집 오류:", e)
            break

    # 2. 중고나라 수집 (웹 API)
    for page in range(1, 6):
        try:
            joonggo_url = f"https://web.joongna.com/api/product/list?searchWord={encoded_keyword}&page={page}&size=30&sort=RECENT_DATE"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = requests.get(joonggo_url, headers=headers, timeout=4)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('data', {}).get('items', [])
                if not items:
                    break
                
                stop_fetching = False
                for item in items:
                    # 중고나라 날짜 타임스탬프 변환 (밀리초 단위 분기)
                    reg_date = item.get('sortDate') or item.get('regDate') or 0
                    update_time = int(reg_date / 1000) if reg_date > 10000000000 else int(reg_date)
                    
                    if update_time > 0 and update_time < twelve_hours_ago:
                        stop_fetching = True
                        break

                    img_url = item.get('detailImgUrl') or item.get('productImg') or ''
                    
                    results.append({
                        "id": f"joong-{item.get('seq')}",
                        "platform": "중고나라",
                        "platformColor": "bg-blue-600",
                        "title": item.get('title') or item.get('productTitle'),
                        "price": int(item.get('price', 0)),
                        "location": item.get('locationName', '지역 미지정'),
                        "imageUrl": img_url,
                        "createdAt": update_time if update_time > 0 else now_ts,
                        "link": f"https://web.joongna.com/product/{item.get('seq')}"
                    })
                if stop_fetching:
                    break
        except Exception as e:
            print("중고나라 수집 오류:", e)
            break

    # 등록시간 기준 최신순 정렬
    results.sort(key=lambda x: x['createdAt'], reverse=True)
    return results