import asyncio
import json
import websockets
import pandas as pd
from database import engine
from kline_cache import KLINES_CACHE
from engine.trader import Trader
import time

trader_instance = Trader()

async def binance_ws_loop():
    symbol = "dogeusdt"
    interval = "3m"
    uri = f"wss://fstream.binance.com/ws/{symbol}@kline_{interval}"
    
    cache_key = "DOGEUSDT_3m"
    table_name = "klines_dogeusdt_3m"
    
    print("Starting Binance WebSocket connection...")
    
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("WebSocket Connected!")
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    k = data['k']
                    
                    is_closed = k['x']
                    
                    candle = {
                        "time": int(k['t'] / 1000),
                        "open": float(k['o']),
                        "high": float(k['h']),
                        "low": float(k['l']),
                        "close": float(k['c']),
                        "volume": float(k['v'])
                    }
                    
                    # 1. Update Memory Cache (replace last candle if time matches, else append)
                    if cache_key in KLINES_CACHE and len(KLINES_CACHE[cache_key]) > 0:
                        last_idx = len(KLINES_CACHE[cache_key]) - 1
                        if KLINES_CACHE[cache_key][last_idx]['time'] == candle['time']:
                            KLINES_CACHE[cache_key][last_idx] = candle
                        elif candle['time'] > KLINES_CACHE[cache_key][last_idx]['time']:
                            KLINES_CACHE[cache_key].append(candle)
                            
                    # 2. If Candle Closed: Save to DB & Trigger Strategy
                    if is_closed:
                        print(f"Candle Closed at {candle['time']}! Saving to DB and triggering Engine...")
                        
                        # Save to DB
                        df = pd.DataFrame([candle])
                        df.to_sql(table_name, con=engine, if_exists='append', index=False)
                        
                        # Trigger Strategy
                        await trader_instance.on_candle_closed()
                        
        except Exception as e:
            print(f"WebSocket disconnected: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)
