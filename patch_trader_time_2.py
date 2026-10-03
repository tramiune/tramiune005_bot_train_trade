import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# Fix sync_missed_trades
old_sync = """                    import tzlocal
                    # convert UTC to local naive
                    local_tz = tzlocal.get_localzone()
                    local_dt = entry_time.tz_localize('UTC').tz_convert(local_tz).tz_localize(None)
                    side=side,
                    entry_time=local_dt.to_pydatetime(),
                    entry_price=entry_price,"""

new_sync = """                    # Convert UTC to local naive (using simple timedelta or tz_convert)
                    local_dt = entry_time.tz_localize('UTC').tz_convert('Asia/Ho_Chi_Minh').tz_localize(None)
                    side=side,
                    entry_time=local_dt.to_pydatetime(),
                    entry_price=entry_price,"""

content = content.replace(old_sync, new_sync)

# Fix execute_trade
old_exec = """        import datetime, tzlocal
        local_tz = tzlocal.get_localzone()
        now_local = datetime.datetime.now(local_tz).replace(tzinfo=None)
        trade = Trade(
            symbol=symbol,
            strategy=strategy,
            side=side,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            size=position_size,
            status="OPEN",
            entry_time=now_local
        )"""

new_exec = """        from datetime import datetime
        now_local = datetime.now() # naive local time
        trade = Trade(
            symbol=symbol,
            strategy=strategy,
            side=side,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            size=position_size,
            status="OPEN",
            entry_time=now_local
        )"""

content = content.replace(old_exec, new_exec)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
