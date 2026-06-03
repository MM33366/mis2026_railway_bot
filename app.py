import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 這些金鑰未來會放在環境變數中，現在可以先用變數測試
line_bot_api = LineBotApi('你的LINE_CHANNEL_ACCESS_TOKEN')
handler = WebhookHandler('你的LINE_CHANNEL_SECRET')

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
    # 這裡未來會接 TDX 的查詢功能
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="你說了: " + event.message.text)
    )

if __name__ == "__main__":
    app.run()