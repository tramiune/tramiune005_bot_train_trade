import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

# In sync_missed_trades: Convert to local time (add 7 hours for Vietnam/Local or just rely on tz local)
# Actually, since the system is in VN, it's UTC+7.
# Instead of hardcoding +7, we can use datetime's local timezone.
old_sync = """                    side=side,
                    entry_time=entry_time.to_pydatetime(),
                    entry_price=entry_price,"""

new_sync = """                    import tzlocal
                    # convert UTC to local naive
                    local_tz = tzlocal.get_localzone()
                    local_dt = entry_time.tz_localize('UTC').tz_convert(local_tz).tz_localize(None)
                    side=side,
                    entry_time=local_dt.to_pydatetime(),
                    entry_price=entry_price,"""

content = content.replace(old_sync, new_sync)

# In execute_trade, pass entry_time explicitely as local time
old_exec = """        trade = Trade(
            symbol=symbol,
            strategy=strategy,
            side=side,
            entry_price=entry_price,
            stop_loss=sl_price,
            take_profit=tp_price,
            size=position_size,
            status="OPEN"
        )"""

new_exec = """        import datetime, tzlocal
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

content = content.replace(old_exec, new_exec)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
