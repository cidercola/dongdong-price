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
    twelve_hours_ago = now_ts - (12 * 3600) # 현재 시간 기준 12시간 전 타임스탬프

    # 번개장터 여러 페이지 요청 (12시간 이내 데이터 확보)
    for page in range(0, 5): # 최대 5페이지 탐색
        try:
            bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&page={page}&request_id=2024&stat_device=android&sort=time"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            res = requests.get(bunjang_url, headers=headers, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                items = data.get('list', [])
                if not items:
                    break
                
                stop_fetching = False
                for item in items:
                    update_time = int(item.get('update_time', 0))
                    
                    # 12시간 이전 데이터가 나오면 수집 중단
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
            print("수집 오류:", e)
            break

    return results