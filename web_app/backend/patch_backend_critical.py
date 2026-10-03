import re

# 1. Fix ws_engine.py
with open("web_app/backend/ws_engine.py", "r") as f:
    ws_content = f.read()
ws_content = ws_content.replace("from engine.trader import Trader", "from engine.trader import TradingEngine")
ws_content = ws_content.replace("trader_instance = Trader()", "trader_instance = TradingEngine()")
with open("web_app/backend/ws_engine.py", "w") as f:
    f.write(ws_content)

# 2. Fix main.py
with open("web_app/backend/main.py", "r") as f:
    main_content = f.read()

# Replace engine_instance = TradingEngine()
main_content = main_content.replace("engine_instance = TradingEngine()", "from ws_engine import trader_instance, binance_ws_loop")

# Replace lifespan logic
old_lifespan = """@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    import asyncio
    engine_instance.is_running = True
    asyncio.create_task(engine_instance.run_loop())
    # Start prefetching in background
    asyncio.create_task(prefetch_klines())
    
    yield
    engine_instance.stop()
    await engine_instance.exchange.close()"""

new_lifespan = """@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    import asyncio
    # Start prefetching in background
    await prefetch_klines() # block until cache is loaded
    
    asyncio.create_task(trader_instance.start())
    asyncio.create_task(binance_ws_loop())
    
    yield
    trader_instance.stop()
    await trader_instance.exchange.close()"""

main_content = main_content.replace(old_lifespan, new_lifespan)

# Replace all engine_instance with trader_instance in main.py
main_content = main_content.replace("engine_instance.", "trader_instance.")

with open("web_app/backend/main.py", "w") as f:
    f.write(main_content)

print("Patched completely!")
