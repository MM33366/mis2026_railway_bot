from dotenv import load_dotenv
load_dotenv() # 這行會自動把 .env 裡的鑰匙餵給程式
import os
import requests

# 從系統環境變數讀取 (Vercel 後端設定)
CLIENT_ID = os.environ.get('TDX_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TDX_CLIENT_SECRET')

# 測試用：在本地端執行時，如果 Vercel 還沒設定，可以先暫時用這行測試
# CLIENT_ID = '你自己的ID' 
# CLIENT_SECRET = '你自己的SECRET'

auth_url = 'https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token'

payload = {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET
}

response = requests.post(auth_url, data=payload)

if response.status_code == 200:
    print("成功取得 Token！")
else:
    print("失敗，請檢查環境變數是否正確設定：", response.text)