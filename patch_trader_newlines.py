import sys

content = open("web_app/backend/engine/trader.py").read()

content = content.replace("SIGNAL*\n\"", "SIGNAL*\\n\"")
content = content.replace("{symbol}\n\"", "{symbol}\\n\"")
content = content.replace("{side}\n\"", "{side}\\n\"")
content = content.replace("{entry_price:.5f}\n\"", "{entry_price:.5f}\\n\"")
content = content.replace("{sl_price:.5f}\n\"", "{sl_price:.5f}\\n\"")
content = content.replace("{tp_price:.5f}\n\"", "{tp_price:.5f}\\n\"")
content = content.replace("{position_size:.1f}\n\"", "{position_size:.1f}\\n\"")
content = content.replace("{required_leverage}x\n\"", "{required_leverage}x\\n\"")

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)

