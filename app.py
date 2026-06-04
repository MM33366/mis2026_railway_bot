import os
import json
import re
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

# --- 🗺️ 全台台鐵車站代碼字典 ---
STATION_MAP = {
    "基隆": "0900", "三坑": "0910", "八堵": "0930", "七堵": "0920", "百福": "0940", 
    "五堵": "0950", "汐止": "0960", "汐科": "0970", "南港": "0980", "松山": "0990", 
    "台北": "1000", "萬華": "1010", "板橋": "1020", "浮洲": "1030", "樹林": "1040", 
    "南樹林": "1050", "山佳": "1070", "鶯歌": "1060", "桃園": "1080", "內壢": "1090", 
    "中壢": "1100", "埔心": "1110", "楊梅": "1120", "富岡": "1130", "新富": "1140", 
    "北湖": "1150", "湖口": "1160", "新豐": "1170", "竹北": "1180", "北新竹": "1190", 
    "新竹": "1210", "三姓橋": "1220", "香山": "1230", "竹南": "1250", "造橋": "3140", 
    "豐富": "3150", "苗栗": "3160", "南勢": "3170", "銅鑼": "3180", "三義": "3190", 
    "泰安": "3210", "后里": "3220", "豐原": "3230", "栗林": "3240", "潭子": "3250", 
    "頭家厝": "3270", "松竹": "3280", "太原": "3310", "精武": "3320", "台中": "3300", 
    "五權": "3330", "大慶": "3340", "烏日": "3350", "新烏日": "3370", "成功": "3380", 
    "談文": "2110", "大山": "2120", "後龍": "2130", "龍港": "2140", "白沙屯": "2150", 
    "新埔": "2160", "通霄": "2170", "苑裡": "2180", "日南": "2190", "大甲": "2200", 
    "台中港": "2210", "清水": "2220", "沙鹿": "2230", "龍井": "2240", "大肚": "2250", 
    "追分": "2260", "彰化": "3360", "花壇": "3420", "大村": "3430", "員林": "3390", 
    "永靖": "3450", "社頭": "3470", "田中": "3480", "二水": "3490", "林內": "3250", 
    "斗六": "3260", "石榴": "3270", "斗南": "3290", "石龜": "3310", "大林": "4030", 
    "民雄": "4050", "嘉北": "4070", "嘉義": "4080", "水上": "4090", "南靖": "4100", 
    "後壁": "4110", "新營": "4120", "柳營": "4130", "林鳳營": "4140", "隆田": "4150", 
    "拔林": "4160", "善化": "4170", "新市": "4180", "永康": "4190", "大橋": "4200", 
    "台南": "4220", "保安": "4250", "仁德": "4260", "宗洲": "4270", "大湖": "4290", 
    "路竹": "4300", "岡山": "4310", "橋頭": "4320", "楠梓": "4330", "新左營": "4340", 
    "左營": "4350", "內惟": "4360", "美術館": "4370", "鼓山": "4380", "三塊厝": "4390", 
    "高雄": "4400", "民族": "4410", "科工館": "4420", "正義": "4430", "鳳山": "4440", 
    "後庄": "4450", "九曲堂": "4460", "六塊厝": "5010", "屏東": "5000", "歸來": "5020", 
    "麟洛": "5030", "西勢": "5040", "竹田": "5060", "潮州": "5050", "崁頂": "5070", 
    "南州": "5080", "鎮安": "5090", "林邊": "5100", "佳冬": "5110", "東海": "5130", 
    "枋寮": "5120", "加祿": "5140", "內獅": "5160", "枋山": "5170", "大武": "5240", 
    "瀧溪": "5230", "金崙": "5220", "太麻里": "5210", "知本": "5200", "康樂": "5190", 
    "台東": "6000", "山里": "6010", "鹿野": "6020", "瑞源": "6030", "瑞和": "6040", 
    "關山": "6050", "海端": "6060", "池上": "6070", "富里": "6080", "東竹": "6090", 
    "東里": "6100", "玉里": "6110", "三民": "6130", "瑞穗": "6150", "富源": "6170", 
    "大富": "6180", "光復": "6190", "萬榮": "6200", "鳳林": "6210", "南平": "6220", 
    "林榮新光": "6230", "豐田": "6240", "壽豐": "6250", "平和": "6260", "志學": "6270", 
    "吉安": "7010", "花蓮": "7000", "新城": "7030", "崇德": "7040", "和仁": "7050", 
    "和平": "7070", "漢本": "7080", "武塔": "7090", "南澳": "7100", "東澳": "7110", 
    "蘇澳新": "7120", "蘇澳": "7130", "新馬": "7140", "冬山": "7150", "羅東": "7160", 
    "中里": "7170", "二結": "7180", "宜蘭": "7190", "四城": "7200", "礁溪": "7210", 
    "頂埔": "7220", "頭城": "7230", "外澳": "7240", "龜山": "7250", "大溪": "7260", 
    "大里": "7270", "石城": "7280", "福隆": "7330", "貢寮": "7320", "雙溪": "7310", 
    "牡丹": "7300", "三貂嶺": "7290", "猴硐": "7350", "瑞芳": "7360", "四腳亭": "7380", 
    "暖暖": "7390", "菁桐": "7440", "平溪": "7430", "嶺腳": "7420", "望古": "7410", 
    "十分": "7400", "大華": "7370", "海科館": "7450", "八斗子": "7460", "千甲": "1240", 
    "新莊": "1260", "竹中": "1270", "六家": "1280", "竹東": "1300", "內灣": "1360", 
    "濁水": "3450", "集集": "3470", "水里": "3480", "車埕": "3490", "長榮大學": "4280", 
    "沙崙": "4290"
}

@app.route("/", methods=['GET'])
def home():
    return "🚂 鐵路小助手 LINE Bot 正常運行中！"

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

# --- 🧠 新增：核心口語時間解析器 ---
def extract_time_advanced(text):
    # 1. 優先處理標準的 24 小時制 (例如 15:30)
    time_match = re.search(r'(\d{1,2}):(\d{2})', text)
    if time_match:
        return f"{int(time_match.group(1)):02d}:{int(time_match.group(2)):02d}"

    # 2. 定義中文數字對應表與時間區段
    cn_hours = {"十二": 12, "十一": 11, "十": 10, "九": 9, "八": 8, "七": 7, "六": 6, "五": 5, "四": 4, "三": 3, "二": 2, "兩": 2, "一": 1}
    is_pm = any(p in text for p in ["下午", "晚上", "傍晚", "夜間", "下半天"])
    is_am = any(p in text for p in ["早上", "上午", "凌晨", "清晨", "上半天"])

    # 3. 尋找「點」或「点」字作拆分
    if "點" in text or "点" in text:
        keyword = "點" if "點" in text else "点"
        parts = text.split(keyword)
        hour_part = parts[0]
        minute_part = parts[1] if len(parts) > 1 else ""

        # A. 解析小時 (先找中文再找阿拉伯數字)
        hour = None
        for cn, val in cn_hours.items():
            if cn in hour_part:
                hour = val
                break
        if hour is None:
            digit_match = re.search(r'(\d{1,2})$', hour_part)
            if digit_match:
                hour = int(digit_match.group(1))

        # B. 如果成功抓到小時，接著解析分鐘
        if hour is not None:
            minute = 0
            if "半" in minute_part:
                minute = 30
            elif "分" in minute_part:
                min_digit_match = re.search(r'(\d{1,2})', minute_part)
                if min_digit_match:
                    minute = int(min_digit_match.group(1))
            else:
                # 處理像「3點30」這種後面直接連著數字的情況
                min_digit_match = re.search(r'^(\d{1,2})', minute_part)
                if min_digit_match:
                    minute = int(min_digit_match.group(1))

            # 4. 根據上下午制調整成 24 小時制
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0

            return f"{hour:02d}:{minute:02d}"
            
    return None

# --- 🚀 智慧拆解車站與日期時間 ---
def parse_user_input(text):
    clean_text = text.replace("查詢", "").replace(" ", "").strip()
    
    # 1. 拆解車站
    start_station, end_station = None, None
    for separator in ["到", "往", "至", "-", "➔", "->"]:
        if separator in clean_text:
            parts = clean_text.split(separator)
            if len(parts) >= 2:
                start_station, end_station = parts[0].strip()[:4], parts[1].strip()[:4]
    
    if not start_station or not end_station:
        matches = []
        for station in STATION_MAP.keys():
            if station in clean_text:
                pos = clean_text.find(station)
                matches.append((pos, station))
        matches.sort(key=lambda x: x[0])
        if len(matches) >= 2:
            start_station, end_station = matches[0][1], matches[1][1]
            
    if not start_station or not end_station:
        return None, None, None, None

    # 2. 計算目標日期 (台北時區)
    tz_taiwan = timezone(timedelta(hours=8))
    now_taiwan = datetime.now(tz_taiwan)
    
    target_date = now_taiwan.strftime("%Y-%m-%d")
    has_custom_date = False
    
    if "明天" in text:
        target_date = (now_taiwan + timedelta(days=1)).strftime("%Y-%m-%d")
        has_custom_date = True
    elif "後天" in text:
        target_date = (now_taiwan + timedelta(days=2)).strftime("%Y-%m-%d")
        has_custom_date = True
        
    # 3. 呼叫智慧時間萃取器
    extracted_time = extract_time_advanced(text)
    if extracted_time:
        target_time = extracted_time
    else:
        # 如果指明了特定日期但沒講時間，從凌晨 00:00 開始查
        if has_custom_date:
            target_time = "00:00"
        else:
            target_time = now_taiwan.strftime("%H:%M") # 完全沒提時間就用當下時間

    return start_station, end_station, target_date, target_time

# --- 查詢 TDX 台鐵時刻表 ---
def get_train_info(start_station, end_station, target_date, target_time):
    start_id = STATION_MAP.get(start_station)
    end_id = STATION_MAP.get(end_station)

    if not start_id or not end_id:
        return "找不到該車站，請確認名稱是否正確喔！"

    token = get_tdx_token()
    if not token:
        return "系統錯誤：無法取得 TDX 授權。"

    url = (
        f"https://tdx.transportdata.tw/api/basic/v2/Rail/TRA/DailyTimetable/OD/{start_id}/to/{end_id}/{target_date}?"
        f"$filter=OriginStopTime/DepartureTime ge '{target_time}'&"
        f"$top=3&$format=JSON"
    )
    
    headers = {"authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        return "查詢台鐵 API 失敗，請稍後再試。"

    data = response.json()
    if not data:
        return f"📅 {target_date} {target_time} 之後，從 {start_station} 到 {end_station} 已經沒有班次囉！"

    result = f"📅 查詢日期：{target_date}\n⏰ 查詢時間點：{target_time} 之後\n【🚂 台鐵最近 3 班車：{start_station} ➔ {end_station}】\n---\n"
    for item in data:
        train_no = item['DailyTrainInfo']['TrainNo']
        train_type = item['DailyTrainInfo']['TrainTypeName']['Zh_tw']
        dep_time = item['OriginStopTime']['DepartureTime']
        arr_time = item['DestinationStopTime']['ArrivalTime']
        
        result += f"🚄 {train_type} ({train_no}車次)\n"
        result += f"出發: {dep_time} | 抵達: {arr_time}\n---\n"
        
    return result.strip()

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    start_station, end_station, target_date, target_time = parse_user_input(user_text)
    
    if start_station and end_station:
        response_text = get_train_info(start_station, end_station, target_date, target_time)
        try:
            db.collection("user_queries").add({
                "user_id": event.source.user_id,
                "start_station": start_station,
                "end_station": end_station,
                "target_date": target_date,
                "target_time": target_time,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print("Firebase 寫入失敗:", e)
    else:
        response_text = "嗨！我是鐵路小助手 🚂\n您可以輸入：\n🔹『台北台中』(查現在最近3班)\n🔹『台北到台南 明天下午三點』\n🔹『板橋礁溪 後天 14:30』"
        
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )

if __name__ == "__main__":
    app.run()