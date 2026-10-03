import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

content = content.replace("tp_price = 0.10000", "tp_price = 0.50000")
content = content.replace("TP (0.10)", "TP (0.50)")

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
