from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse
import time
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BUNJANG_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://m.bunjang.co.kr',
    'Referer': 'https://m.bunjang.co.kr/'
}

JOONGNA_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
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

    # 2. 중고나라 수집 (2번 방식: 우회 터널 프록시 경유 수집)
    for page in range(1, 4):
        try:
            target_url = f"https://web.joongna.com/api/product/list?searchWord={encoded_keyword}&page={page}&size=30&sort=RECENT_DATE"
            
            # 차단 회피용 프록시 파이프라인
            proxy_url = f"https://api.allorigins.win/get?url={urllib.parse.quote(target_url)}"
            res = requests.get(proxy_url, timeout=7)
            
            if res.status_code == 200:
                raw_contents = res.json().get('contents', '')
                if raw_contents:
                    data = json.loads(raw_contents)
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
            print("중고나라 우회 수집 오류:", e)
            break

    # 최신 등록순 정렬
    results.sort(key=lambda x: x['createdAt'], reverse=True)
    return results