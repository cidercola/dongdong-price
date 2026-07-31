from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from curl_cffi import requests as cffi_requests
import requests
import urllib.parse
import time
import os

# 🌟 구글 클라우드 Firestore 라이브러리
from google.cloud import firestore

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 🌟 텔레그램 설정
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = "8924745828:AAEuVPMKZK1Y4s_LNfGPWZPfqQkNCNYDN34"
TELEGRAM_CHAT_ID = "8909792233"

# ----------------------------------------------------
# 📂 Firestore DB 클라이언트 초기화
# ----------------------------------------------------
db = firestore.Client()
WATCHLIST_COLLECTION = "watchlist"
BLOCKED_USERS_COLLECTION = "blocked_users"

# 중복 알림 방지 및 서버 최초 발견 시간 메모리 (아이템ID: 발견된 타임스탬프)
SEEN_ITEMS = {}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Content-Type': 'application/json',
    'Referer': 'https://web.joongna.com/',
    'Origin': 'https://web.joongna.com'
}

def load_watchlist():
    try:
        docs = db.collection(WATCHLIST_COLLECTION).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print("Firestore 읽기 오류 (watchlist):", e)
        return []

def save_watchlist_item(keyword, min_price, max_price):
    doc_ref = db.collection(WATCHLIST_COLLECTION).document(keyword.lower().strip())
    doc_ref.set({
        "keyword": keyword,
        "min_price": min_price,
        "max_price": max_price,
        "updated_at": firestore.SERVER_TIMESTAMP
    })

def delete_watchlist_item(keyword):
    doc_ref = db.collection(WATCHLIST_COLLECTION).document(keyword.lower().strip())
    doc_ref.delete()

def load_blocked_users():
    try:
        docs = db.collection(BLOCKED_USERS_COLLECTION).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print("Firestore 읽기 오류 (blocked_users):", e)
        return []

def save_blocked_user(user_id):
    clean_id = user_id.strip()
    doc_ref = db.collection(BLOCKED_USERS_COLLECTION).document(clean_id.lower())
    doc_ref.set({
        "user_id": clean_id,
        "created_at": firestore.SERVER_TIMESTAMP
    })

def delete_blocked_user(user_id):
    clean_id = user_id.strip()
    doc_ref = db.collection(BLOCKED_USERS_COLLECTION).document(clean_id.lower())
    doc_ref.delete()

def send_telegram_msg(title, price, platform, link, img_url, seller_name=""):
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return

    msg = f"🚨 <b>[{platform}] 신규 매물 포착!</b>\n\n"
    msg += f"📦 <b>상품명:</b> {title}\n"
    msg += f"💰 <b>가격:</b> {price:,}원\n"
    if seller_name:
        msg += f"👤 <b>판매자:</b> {seller_name}\n"
    msg += f"🔗 <a href='{link}'>매물 바로가기</a>"

    if img_url:
        photo_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": img_url,
            "caption": msg,
            "parse_mode": "HTML"
        }
        try:
            requests.post(photo_url, data=payload, timeout=5)
            return
        except:
            pass

    text_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }
    requests.post(text_url, data=payload, timeout=5)

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

@app.get("/")
def health_check():
    return {"status": "ok", "version": "v3.1-strict-time-filter"}

@app.get("/api/watchlist")
def get_watchlist_api():
    return load_watchlist()

@app.post("/api/watchlist")
def add_watchlist_api(item: dict):
    keyword = item.get("keyword", "").strip()
    min_price = int(item.get("min_price", 0))
    max_price = int(item.get("max_price", 100000000))
    if not keyword:
        raise HTTPException(status_code=400, detail="키워드를 입력해 주세요.")
    save_watchlist_item(keyword, min_price, max_price)
    return {"status": "success", "watchlist": load_watchlist()}

@app.put("/api/watchlist")
def update_watchlist_api(item: dict):
    old_keyword = item.get("old_keyword", "").strip()
    new_keyword = item.get("keyword", "").strip()
    min_price = int(item.get("min_price", 0))
    max_price = int(item.get("max_price", 100000000))
    if not old_keyword or not new_keyword:
        raise HTTPException(status_code=400, detail="키워드 정보가 올바르지 않습니다.")
    if old_keyword.lower() != new_keyword.lower():
        delete_watchlist_item(old_keyword)
    save_watchlist_item(new_keyword, min_price, max_price)
    return {"status": "success", "watchlist": load_watchlist()}

@app.delete("/api/watchlist/{keyword}")
def delete_watchlist_api(keyword: str):
    delete_watchlist_item(keyword)
    return {"status": "success", "watchlist": load_watchlist()}

@app.get("/api/blocked-users")
def get_blocked_users_api():
    return load_blocked_users()

@app.post("/api/blocked-users")
def add_blocked_user_api(item: dict):
    user_id = item.get("user_id", "").strip()
    if not user_id:
        raise HTTPException(status_code=400, detail="판매자 아이디/닉네임을 입력해 주세요.")
    save_blocked_user(user_id)
    return {"status": "success", "blocked_users": load_blocked_users()}

@app.delete("/api/blocked-users/{user_id}")
def delete_blocked_user_api(user_id: str):
    delete_blocked_user(user_id)
    return {"status": "success", "blocked_users": load_blocked_users()}

@app.get("/api/search")
def search_products(keyword: str):
    results = []
    encoded_keyword = urllib.parse.quote(keyword)
    now_ts = int(time.time())
    blocked_list = [u.get("user_id", "").lower() for u in load_blocked_users()]

    bunjang_count = 0
    joongna_count = 0

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
                    title = item.get('name') or ''
                    if not is_exact_keyword_match(title, keyword):
                        continue

                    seller_id = str(item.get('uid') or '')
                    seller_name = str(item.get('user_name') or item.get('nick') or '')
                    if seller_id.lower() in blocked_list or seller_name.lower() in blocked_list:
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
                        "sellerId": seller_id,
                        "sellerName": seller_name,
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
            res = cffi_requests.post(joonggo_url, headers=HEADERS, json=payload, impersonate="chrome120", timeout=10)
            if res.status_code == 200:
                data = res.json()
                inner_data = data.get('data', data)
                items = []
                if isinstance(inner_data, dict):
                    items = inner_data.get('items') or inner_data.get('list') or inner_data.get('goodsList') or []
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

                    seller_id = str(item.get('storeSeq') or item.get('userSeq') or item.get('id') or '')
                    seller_name = str(item.get('nickName') or item.get('storeName') or item.get('userName') or '')
                    if seller_id.lower() in blocked_list or seller_name.lower() in blocked_list:
                        continue

                    raw_img = item.get('detailImgUrl') or item.get('url') or item.get('imageUrl') or item.get('productImg') or item.get('imgUrl') or item.get('mediaUrl') or ''
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
                            "sellerId": seller_id,
                            "sellerName": seller_name,
                            "link": f"https://web.joongna.com/product/{product_id}"
                        })
                        joongna_count += 1
        except Exception as e:
            print("중고나라 수집 오류:", e)
            break

    results.sort(key=lambda x: x['createdAt'], reverse=True)
    return {
        "totalCount": len(results),
        "bunjangCount": bunjang_count,
        "joongnaCount": joongna_count,
        "items": results
    }

@app.get("/api/cron-check")
def cron_check_and_notify():
    """스케줄러 3분 주기 감시 함수 (서버가 처음 발견한 시점 기준 필터링)"""
    watchlist = load_watchlist()
    blocked_list = [u.get("user_id", "").lower() for u in load_blocked_users()]
    new_alerts_count = 0
    
    now_ts = int(time.time())

    for target in watchlist:
        keyword = target.get("keyword")
        min_p = target.get("min_price", 0)
        max_p = target.get("max_price", 100000000)

        if not keyword:
            continue

        search_res = search_products(keyword)
        items = search_res.get("items", [])

        for item in items:
            item_id = item["id"]
            price = item["price"]
            seller_id = item.get("sellerId", "").lower()
            seller_name = item.get("sellerName", "").lower()

            # 1. 차단 판매자 필터링
            if seller_id in blocked_list or seller_name in blocked_list:
                continue

            # 2. 가격 조건 체크
            if not (min_p <= price <= max_p):
                continue

            # 3. 최초 발견 시간 기록 및 신규 매물 판별
            if item_id not in SEEN_ITEMS:
                # 서버가 이 글을 처음 본 시점을 기록
                SEEN_ITEMS[item_id] = now_ts
                
                # 방금 막 수집된 따끈따끈한 글이므로 알림 발송
                send_telegram_msg(
                    title=item["title"],
                    price=price,
                    platform=item["platform"],
                    link=item["link"],
                    img_url=item["imageUrl"],
                    seller_name=item.get("sellerName", "")
                )
                new_alerts_count += 1

    return {"status": "ok", "newAlertsSent": new_alerts_count}
