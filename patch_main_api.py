import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

new_api = """@app.get("/api/telegram/status")
def get_telegram_status():
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    ready = bool(token and chat_id and chat_id != "<WILL_BE_UPDATED>")
    return {"ready": ready}

@app.get("/api/trades")"""

content = content.replace("@app.get(\"/api/trades\")", new_api)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
