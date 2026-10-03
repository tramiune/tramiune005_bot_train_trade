import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

broken = """                trade = Trade(
                    symbol="DOGE/USDT",
                    strategy="DOGE_3M_DEGEN",
                    # Convert UTC to local naive (using simple timedelta or tz_convert)
                    local_dt = entry_time.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None)
                    side=side,
                    entry_time=local_dt.to_pydatetime(),
                    entry_price=entry_price,"""

fixed = """                # Convert UTC to local naive (using simple timedelta or tz_convert)
                local_dt = entry_time.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None)
                
                trade = Trade(
                    symbol="DOGE/USDT",
                    strategy="DOGE_3M_DEGEN",
                    side=side,
                    entry_time=local_dt.to_pydatetime(),
                    entry_price=entry_price,"""

content = content.replace(broken, fixed)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
