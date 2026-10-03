import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_time = "last_trade_time = pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01')"
new_time = "last_trade_time = pd.to_datetime(last_trade.exit_time) if (last_trade and last_trade.exit_time) else (pd.to_datetime(last_trade.entry_time) if last_trade else pd.Timestamp('2000-01-01'))"

content = content.replace(old_time, new_time)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
