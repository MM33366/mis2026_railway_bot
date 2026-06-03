import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- Firebase 初始化邏輯 ---
if 'FIREBASE_KEY_JSON' in os.environ:
    key_dict = json.loads(os.environ['FIREBASE_KEY_JSON'])
    cred = credentials.Certificate(key_dict)
else:
    cred = credentials.Certificate("firebase-key.json")

firebase_admin.initialize_app(cred)
db = firestore.client()

# --- LINE 設定 ---
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# --- 核心功能：查詢鐵路資訊的函式 ---
def get_train_info(text):
    # 這裡未來可以擴充串接 TDX API 的邏輯
    if "台中到台北" in text:
        return "10:30 自強號 - 台中開出\n12:15 抵達台北"
    elif "台北到台中" in text:
        return "09:00 自強號 - 台北開出\n10:45 抵達台中"
    return "暫時無法查詢，請嘗試輸入『查詢 台中到台北』"

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

# --- 處理訊息事件 ---
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # 邏輯判斷：包含「查詢」關鍵字則執行查詢
    if "查詢" in user_text:
        response_text = get_train_info(user_text)
    else:
        response_text = "我只是一個鐵路小助手，試著輸入『查詢 台中到台北』看看！"
        
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response_text)
    )

if __name__ == "__main__":
    app.run()