import asyncio
import pandas as pd
import time
import os
import sys
from dotenv import load_dotenv

load_dotenv()

BOT_MODE = os.getenv("BOT_MODE", "XRP") # "XRP" or "SOL"

# Load corresponding trading engine
from engine.trader import TradingEngine

trader_instance = TradingEngine()

async def verify_futures_source(symbol, interval):
    import httpx
    from engine.telegram import send_telegram_message
    try:
        mine = await trader_instance.exchange.fetch_ohlcv(symbol, interval, limit=4)
        async with httpx.AsyncClient(timeout=10) as client:
            fut = (await client.get("https://fapi.binance.com/fapi/v1/klines",
                                    params={"symbol": symbol.replace('/', ''), "interval": interval, "limit": 4})).json()
        truth = {k[0]: [float(x) for x in k[1:5]] for k in fut}
        closed = [(k[0], [float(x) for x in k[1:5]]) for k in mine[:-1]]
        if closed and all(truth.get(t) == v for t, v in closed):
            print(f"DATA SOURCE VERIFIED: {symbol} matches Binance Futures.")
        else:
            print("DATA SOURCE MISMATCH: candle feed does NOT match Binance Futures!")
            await send_telegram_message(f"⚠️ Dữ liệu nến {symbol} KHÔNG khớp Binance Futures!")
    except Exception as e:
        print(f"Futures source self-check could not run: {e}")

async def binance_ws_loop():
    if BOT_MODE == "XRP":
        symbol = "XRP/USDT"
        interval = "5m"
        loop_interval = 300
    else:
        symbol = "SOL/USDT"
        interval = "4h"
        loop_interval = 14400
        
    print(f"Starting {BOT_MODE} Bot Engine on {symbol} {interval}...")
    await verify_futures_source(symbol, interval)
    
    last_candle_time = 0
    last_manage_time = 0
    
    while True:
        try:
            now_ts = int(time.time())
            if now_ts - last_manage_time >= 30:
                last_manage_time = now_ts
                await trader_instance.manage_open_trades()

            ohlcv = await trader_instance.exchange.fetch_ohlcv(symbol, interval, limit=2)
            if not ohlcv or len(ohlcv) < 2:
                await asyncio.sleep(2)
                continue
                
            current_candle_data = ohlcv[-1]
            closed_candle_data = ohlcv[-2]
            
            candle_time = int(closed_candle_data[0] / 1000)
            
            if int(time.time()) % 10 == 0:
                print(f"REST Polling {symbol} {interval} alive, latest close: {current_candle_data[4]}")
                sys.stdout.flush()
                
            if last_candle_time != 0 and candle_time > last_candle_time:
                print(f"Candle Closed at {candle_time}! Triggering Engine...")
                sys.stdout.flush()
                await trader_instance.on_candle_closed(BOT_MODE)
                
            last_candle_time = candle_time
            
            now_ts = int(time.time())
            seconds_into_candle = now_ts % loop_interval
            seconds_to_next_candle = loop_interval - seconds_into_candle
            
            # Đón nến đóng siêu tốc: Trong 3s trước khi đóng nến và 6s đầu nến mới,
            # bot thăm dò dồn dập mỗi 0.5s (500ms). Sàn vừa chốt lúc :01 là bot bắt ngay lập tức!
            if seconds_into_candle <= 6 or seconds_to_next_candle <= 3:
                await asyncio.sleep(0.5)
            elif seconds_to_next_candle > 10:
                await asyncio.sleep(8)
            else:
                await asyncio.sleep(1.5)
                
        except Exception as e:
            print(f"REST Polling error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
