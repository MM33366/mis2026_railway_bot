import os
import json
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- Firebase 初始化 ---
if 'FIREBASE_KEY_JSON' in os.environ:
    key_dict = json.loads(os.environ['FIREBASE_KEY_JSON'])
    cred = credentials.Certificate(key_dict)
else:
    cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# --- 環境變數設定 ---
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
TDX_CLIENT_ID = os.environ.get('TDX_CLIENT_ID')
TDX_CLIENT_SECRET = os.environ.get('TDX_CLIENT_SECRET')

# --- 建立車站對應字典 (可以自行擴充) ---
STATION_MAP = {
    "台北": "1000", "板橋": "1020", "桃園": "1080", "新竹": "1210",
    "苗栗": "3160", "台中": "3300", "彰化": "3360", "嘉義": "4080",
    "台南": "4220", "左營": "4340", "高雄": "4400", "花蓮": "7000"
}

# --- 取得 TDX Token ---
def get_tdx_token():
    auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'
    payload = {
        'grant_type': 'client_credentials',
        'client_id': TDX_CLIENT_ID,
        'client_secret': TDX_CLIENT_SECRET
    }
    response = requests.post(auth_url, data=payload)
    if response.status_code == 200:
        return response.json().get('access_token')
    return None

# --- 查詢 TDX 台鐵時刻表 ---
def get_train_info(start_station, end_station):
    start_id = STATION_MAP.get(start_station)
    end_id = STATION_MAP.get(end_station)

    if not start_id or not end_id:
        return f"找不到車站！請確認是否有錯字，目前支援：{', '.join(STATION_MAP.keys())}"

    token = get_tdx_token()
    if not token:
        return "系統發生錯誤：無法取得 TDX 授權。"

    # 取得當天日期，呼叫 TDX OD (Origin-Destination) 班表 API (抓前三筆)
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://tdx.transportdata.tw/api/basic/v2/Rail/TRA/DailyTimetable/OD/{start_id}/to/{end_id}/{today}?$top=3&$format=JSON"
    
    headers = {"authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return "查詢台鐵 API 失敗，請稍後再試。"

    data = response.json()
    if not data:
        return f"今天從 {start_station} 到 {end_station} 已經沒有班次囉！"

    # 整理文字回覆
    result = f"【時刻表：{start_station} ➔ {end_station}】\n"
    for item in data:
        train_no = item['DailyTrainInfo']['TrainNo']
        train_type = item['DailyTrainInfo']['TrainTypeName']['Zh_tw']
        dep_time = item['OriginStopTime']['DepartureTime']
        arr_time = item['DestinationStopTime']['ArrivalTime']
        
        result += f"🚄 {train_type} ({train_no}車次)\n"
        result += f"出發: {dep_time} | 抵達: {arr_time}\n---\n"
        
    return result.strip()

# --- Webhook 路由 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# --- 處理文字訊息 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    # 1. 自動拆解字串 (去掉"查詢"並去頭尾空白)
    user_text = event.message.text.replace("查詢", "").strip()
    
    if "到" in user_text:
        parts = user_text.split("到")
        if len(parts) == 2:
            start_station = parts[0].strip()
            end_station = parts[1].strip()
            
            # 2. 呼叫我們寫好的 TDX 查詢函式
            response_text = get_train_info(start_station, end_station)
            
            # 3. 順便寫入 Firebase 紀錄使用者的查詢行為！
            try:
                db.collection("user_queries").add({
                    "user_id": event.source.user_id,
                    "start_station": start_station,
                    "end_station": end_station,
                    "timestamp": firestore.SERVER_TIMESTAMP
                })
            except Exception as e:
                print("Firebase 寫入失敗:", e)
        else:
            response_text = "格式好像不太對？請輸入像是「台中到台北」。"
    else:
        response_text = "嗨！我是鐵路小助手，請輸入例如：『台中到台北』來查詢真實的火車時刻表喔！"
        
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )

if __name__ == "__main__":
    app.run()