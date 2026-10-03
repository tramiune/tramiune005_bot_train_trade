import requests

token = "8934179085:AAG0RzgYmfIq4G-Sl2ejv1mKE-ytdGOZaVA"
url = f"https://api.telegram.org/bot{token}/getUpdates"

res = requests.get(url).json()
if res.get("ok") and len(res.get("result", [])) > 0:
    chat_id = res["result"][-1]["message"]["chat"]["id"]
    with open(".env", "w") as f:
        f.write(f'TELEGRAM_BOT_TOKEN="{token}"\n')
        f.write(f'TELEGRAM_CHAT_ID="{chat_id}"\n')
    print(f"SUCCESS: Configured Telegram with Chat ID {chat_id}")
else:
    print("NO_MESSAGES")
