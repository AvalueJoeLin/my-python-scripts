import requests

def SendMessage(text):
    # LINE Notify 權杖
    token = 'GG2rgvCBc7QJqewK1mP3nz43xtdKLoorFpnniXPRAGC'
    
    # 要發送的訊息
    message = text

    # HTTP 標頭參數與資料
    headers = { "Authorization": "Bearer " + token }
    data = { 'message': message }

    # 以 requests 發送 POST 請求
    requests.post("https://notify-api.line.me/api/notify", headers = headers, data = data)
    
