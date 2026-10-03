import re

with open("web_app/backend/.env", "r") as f:
    content = f.read()

content = content.replace("BINANCE_SECRET=", "BINANCE_SECRET_KEY=")

with open("web_app/backend/.env", "w") as f:
    f.write(content)

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

content = content.replace('secret = os.getenv("BINANCE_SECRET", "")', 'secret = os.getenv("BINANCE_SECRET_KEY", "")')

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
