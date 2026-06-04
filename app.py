import os
import json
import requests
from datetime import datetime, timedelta, timezone
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

# --- LINE 與 TDX 環境變數 ---
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
TDX_CLIENT_ID = os.environ.get('TDX_CLIENT_ID')
TDX_CLIENT_SECRET = os.environ.get('TDX_CLIENT_SECRET')

# --- 🗺️ 全台台鐵車站代碼字典 (完整版) ---
STATION_MAP = {
    # ── 基隆、台北、新北 ──
    "基隆": "0900", "三坑": "0910", "八堵": "0930", "七堵": "0920", "百福": "0940", 
    "五堵": "0950", "汐止": "0960", "汐科": "0970", "南港": "0980", "松山": "0990", 
    "台北": "1000", "萬華": "1010", "板橋": "1020", "浮洲": "1030", "樹林": "1040", 
    "南樹林": "1050", "山佳": "1070", "鶯歌": "1060",
    
    # ── 桃園、新竹 ──
    "桃園": "1080", "內壢": "1090", "中壢": "1100", "埔心": "1110", "楊梅": "1120", 
    "富岡": "1130", "新富": "1140", "北湖": "1150", "湖口": "1160", "新豐": "1170", 
    "竹北": "1180", "北新竹": "1190", "新竹": "1210", "三姓橋": "1220", "香山": "1230",
    
    # ── 苗栗、台中、彰化 (山線 + 海線) ──
    "竹南": "1250", "造橋": "3140", "豐富": "3150", "苗栗": "3160", "南勢": "3170", 
    "銅鑼": "3180", "三義": "3190", "泰安": "3210", "后里": "3220", "豐原": "3230", 
    "栗林": "3240", "潭子": "3250", "頭家厝": "3270", "松竹": "3280", "太原": "3310", 
    "精武": "3320", "台中": "3300", "五權": "3330", "大慶": "3340", "烏日": "3350", 
    "新烏日": "3370", "成功": "3380", "談文": "2110", "大山": "2120", "後龍": "2130", 
    "龍港": "2140", "白沙屯": "2150", "新埔": "2160", "通霄": "2170", "苑裡": "2180", 
    "日南": "2190", "大甲": "2200", "台中港": "2210", "清水": "2220", "沙鹿": "2230", 
    "龍井": "2240", "大肚": "2250", "追分": "2260", "彰化": "3360", "花壇": "3420", 
    "大村": "3430", "員林": "3390", "永靖": "3450", "社頭": "3470", "田中": "3480", 
    "二水": "3490",
    
    # ── 雲林、嘉義、台南 ──
    "林內": "3250", "斗六": "3260", "石榴": "3270", "斗南": "3290", "石龜": "3310", 
    "大林": "4030", "民雄": "4050", "嘉北": "4070", "嘉義": "4080", "水上": "4090", 
    "南靖": "4100", "後壁": "4110", "新營": "4120", "柳營": "4130", "林鳳營": "4140", 
    "隆田": "4150", "拔林": "4160", "善化": "4170", "新市": "4180", "永康": "4190", 
    "大橋": "4200", "台南": "4220", "保安": "4250", "仁德": "4260", "中洲": "4270",
    
    # ── 高雄、屏東 ──
    "大湖": "4290", "路竹": "4300", "岡山": "4310", "橋頭": "4320", "楠梓": "4330", 
    "新左營": "4340", "左營": "4350", "內惟": "4360", "美術館": "4370", "鼓山": "4380", 
    "三塊厝": "4390", "高雄": "4400", "民族": "4410", "科工館": "4420", "正義": "4430", 
    "鳳山": "4440", "後庄": "4450", "九曲堂": "4460", "六塊厝": "5010", "屏東": "5000", 
    "歸來": "5020", "麟洛": "5030", "西勢": "5040", "竹田": "5060", "潮州": "5050", 
    "崁頂": "5070", "南州": "5080", "鎮安": "5090", "林邊": "5100", "佳冬": "5110", 
    "東海": "5130", "枋寮": "5120", "加祿": "5140", "內獅": "5160", "枋山": "5170",
    
    # ── 台東、花蓮 ──
    "大武": "5240", "瀧溪": "5230", "金崙": "5220", "太麻里": "5210", "知本": "5200", 
    "康樂": "5190", "台東": "6000", "山里": "6010", "鹿野": "6020", "瑞源": "6030", 
    "瑞和": "6040", "關山": "6050", "海端": "6060", "池上": "6070", "富里": "6080", 
    "東竹": "6090", "東里": "6100", "玉里": "6110", "三民": "6130", "瑞穗": "6150", 
    "富源": "6170", "大富": "6180", "光復": "6190", "萬榮": "6200", "鳳林": "6210", 
    "南平": "6220", "林榮新光": "6230", "豐田": "6240", "壽豐": "6250", "平和": "6260", 
    "志學": "6270", "吉安": "7010", "花蓮": "7000", "新城": "7030", "崇德": "7040", 
    "和仁": "7050", "和平": "7070",
    
    # ── 宜蘭、新北北海岸 ──
    "漢本": "7080", "武塔": "7090", "南澳": "7100", "東澳": "7110", "蘇澳新": "7120", 
    "蘇澳": "7130", "新馬": "7140", "冬山": "7150", "羅東": "7160", "中里": "7170", 
    "二結": "7180", "宜蘭": "7190", "四城": "7200", "礁溪": "7210", "頂埔": "7220", 
    "頭城": "7230", "外澳": "7240", "龜山": "7250", "大溪": "7260", "大里": "7270", 
    "石城": "7280", "福隆": "7330", "貢寮": "7320", "雙溪": "7310", "牡丹": "7300", 
    "三貂嶺": "7290", "猴硐": "7350", "瑞芳": "7360", "四腳亭": "7380", "暖暖": "7390",
    
    # ── 熱門觀光支線 (平溪、深澳、內灣、集集、沙崙) ──
    "菁桐": "7440", "平溪": "7430", "嶺腳": "7420", "望古": "7410", "十分": "7400", 
    "大華": "7370", "海科館": "7450", "八斗子": "7460", "千甲": "1240", "新莊": "1260", 
    "竹中": "1270", "六家": "1280", "竹東": "1300", "內灣": "1360", "濁水": "3450", 
    "集集": "3470", "水里": "3480", "車埕": "3490", "長榮大學": "4280", "沙崙": "4290"
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

# --- 智慧語意拆解功能 ---
def parse_stations(text):
    # 移除關鍵字與所有空白
    clean_text = text.replace("查詢", "").replace(" ", "").strip()
    
    # 情境 A：使用者有輸入明顯的分隔標記
    for separator in ["到", "往", "至", "-", "➔", "->"]:
        if separator in clean_text:
            parts = clean_text.split(separator)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    
    # 情境 B：使用者只輸入「台中台北」這種連在一起的字串
    matches = []
    for station in STATION_MAP.keys():
        if station in clean_text:
            pos = clean_text.find(station)
            matches.append((pos, station))
    
    # 依照車站字元在訊息中出現的先後順序進行排序
    matches.sort(key=lambda x: x[0])
    
    # 如果抓到至少兩個已註冊的車站，第一個為起點，第二個為終點
    if len(matches) >= 2:
        return matches[0][1], matches[1][1]
        
    return None, None

# --- 查詢 TDX 台鐵時刻表 ---
def get_train_info(start_station, end_station):
    start_id = STATION_MAP.get(start_station)
    end_id = STATION_MAP.get(end_station)

    if not start_id or not end_id:
        return "找不到該車站，請確認名稱是否正確！（例：台鐵無雲林站，請輸入斗六或斗南）"

    token = get_tdx_token()
    if not token:
        return "系統發生錯誤：無法取得 TDX 授權。"

    # 設定台灣時區 (UTC+8)
    tz_taiwan = timezone(timedelta(hours=8))
    now_taiwan = datetime.now(tz_taiwan)
    today = now_taiwan.strftime("%Y-%m-%d")
    current_time = now_taiwan.strftime("%H:%M") # 24小時制格式

    # 呼叫 TDX API，篩選出發時間大於等於台灣當前時間的班次
    url = (
        f"https://tdx.transportdata.tw/api/basic/v2/Rail/TRA/DailyTimetable/OD/{start_id}/to/{end_id}/{today}?"
        f"$filter=OriginStopTime/DepartureTime ge '{current_time}'&"
        f"$top=3&$format=JSON"
    )
    
    headers = {"authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return "查詢台鐵 API 失敗，請稍後再試。"

    data = response.json()
    if not data:
        return f"今天 {current_time} 之後，從 {start_station} 到 {end_station} 已經沒有班次囉！"

    # 建立回覆內容
    result = f"⏰ 查詢時間：{current_time}\n【接下來最近 3 班車：{start_station} ➔ {end_station}】\n---\n"
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
    user_text = event.message.text
    
    # 智慧拆解出發地與目的地
    start_station, end_station = parse_stations(user_text)
    
    if start_station and end_station:
        # 執行 24 小時制即時數據查詢
        response_text = get_train_info(start_station, end_station)
        
        # 紀錄歷史紀錄至 Firebase
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
        response_text = "嗨！我是鐵路小助手 🔍\n請輸入例如：『台中到台北』或直接輸入『板橋礁溪』，我就能為您查詢最近的火車時刻表喔！"
        
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )

if __name__ == "__main__":
    app.run()