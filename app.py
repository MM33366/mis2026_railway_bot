import os
import json
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# --- Firebase 初始化邏輯 (支援雲端與本地) ---
if 'FIREBASE_KEY_JSON' in os.environ:
    # 這是雲端部署時使用的：從環境變數讀取
    key_dict = json.loads(os.environ['FIREBASE_KEY_JSON'])
    cred = credentials.Certificate(key_dict)
else:
    # 這是你在電腦測試時使用的：讀取檔案
    cred = credentials.Certificate("firebase-key.json")

firebase_admin.initialize_app(cred)
db = firestore.client()
# ----------------------------------------

# 之後記得換成你在 LINE Developers 拿到的 Token 與 Secret
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

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
    # 簡單測試：回應使用者
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="已收到訊息！")
    )

if __name__ == "__main__":
    app.run()