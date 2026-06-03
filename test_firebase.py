import firebase_admin
from firebase_admin import credentials, firestore

# 初始化 Firebase (請確保你的 json 檔名正確)
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# 測試寫入一筆資料
db.collection("test_collection").document("test_doc").set({"name": "Emma", "status": "Connected!"})

print("資料已成功寫入 Firebase！請去網頁後台查看。")