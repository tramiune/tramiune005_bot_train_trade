import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

broken = "trade.exit_time = pd.to_datetime(c_time, unit='ms').to_pydatetime()"
fixed = "trade.exit_time = pd.to_datetime(c_time, unit='ms').tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None).to_pydatetime()"

content = content.replace(broken, fixed)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
