import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

content = content.replace("tp_price = 0.06000", "tp_price = 0.10000")
content = content.replace("TP (0.06)", "TP (0.10)")

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
