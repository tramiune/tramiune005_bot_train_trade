import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

# Replace run_loop with start and binance_ws_loop
old_run = """async def run_trader():
    from engine.trader import Trader
    trader = Trader()
    await trader.run_loop()"""

new_run = """async def run_trader():
    from ws_engine import trader_instance, binance_ws_loop
    await trader_instance.start()
    await binance_ws_loop()"""

content = content.replace(old_run, new_run)

# Also fix the stop API to use trader_instance
old_stop = """    # This is a bit hacky, but works for the MVP
    # Ideally, we should have a global trader instance
    return {"status": "ok", "message": "Bot stopped"}"""

new_stop = """    from ws_engine import trader_instance
    trader_instance.stop()
    return {"status": "ok", "message": "Bot stopped"}"""

content = content.replace(old_stop, new_stop)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
