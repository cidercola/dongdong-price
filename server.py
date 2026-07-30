from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse

app = FastAPI()

# 브라우저 CORS 차단 해제 설정
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
    
    # 1. 번개장터 실시간 검색 API (내부 호출)
    try:
        bunjang_url = f"https://api.bunjang.co.kr/api/1/find_v2.json?q={encoded_keyword}&page=0&request_id=2024&stat_device=android&sort=time"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(bunjang_url, headers=headers, timeout=5)
        
        if res.status_code == 200:
            data = res.json()
            items = data.get('list', [])[:5] # 상위 5개 추출
            for item in items:
                results.append({
                    "id": f"bunk-{item.get('pid')}",
                    "platform": "번개장터",
                    "platformColor": "bg-red-500",
                    "title": item.get('name'),
                    "price": int(item.get('price', 0)),
                    "location": item.get('location', '지역 정보 없음'),
                    "imageUrl": item.get('product_image'), # 실제 상품 이미지
                    "createdAt": item.get('update_time'),   # 실제 등록 타임스탬프
                    "link": f"https://m.bunjang.co.kr/products/{item.get('pid')}" # 실제 게시글 링크
                })
    except Exception as e:
        print("번개장터 수집 에러:", e)

    return results

# 서버 실행 방법 (터미널): uvicorn server:app --reload