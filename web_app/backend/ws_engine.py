import asyncio
import pandas as pd
from database import engine
from kline_cache import KLINES_CACHE
from engine.trader import TradingEngine
import time

trader_instance = TradingEngine()

async def binance_ws_loop():
    symbol = "DOGE/USDT"
    interval = "3m"
    cache_key = "DOGEUSDT_3m"
    table_name = "klines_dogeusdt_3m"
    
    print("Starting Binance REST Polling (Fallback for WS)...")
    
    while True:
        try:
            ohlcv = await trader_instance.exchange.fetch_ohlcv(symbol, interval, limit=2)
            if not ohlcv or len(ohlcv) < 2:
                await asyncio.sleep(2)
                continue
                
            current_candle_data = ohlcv[-1]
            candle = {
                "time": int(current_candle_data[0] / 1000),
                "open": float(current_candle_data[1]),
                "high": float(current_candle_data[2]),
                "low": float(current_candle_data[3]),
                "close": float(current_candle_data[4]),
                "volume": float(current_candle_data[5])
            }
            
            # Debug alive
            if int(time.time()) % 10 == 0:
                import sys
                print(f"REST Polling alive, latest close: {candle['close']}")
                sys.stdout.flush()
            
            if cache_key in KLINES_CACHE and len(KLINES_CACHE[cache_key]) > 0:
                last_idx = len(KLINES_CACHE[cache_key]) - 1
                
                if KLINES_CACHE[cache_key][last_idx]['time'] == candle['time']:
                    KLINES_CACHE[cache_key][last_idx] = candle
                elif candle['time'] > KLINES_CACHE[cache_key][last_idx]['time']:
                    # A new candle just started! This means the PREVIOUS candle just closed!
                    closed_candle_data = ohlcv[-2]
                    closed_candle = {
                        "time": int(closed_candle_data[0] / 1000),
                        "open": float(closed_candle_data[1]),
                        "high": float(closed_candle_data[2]),
                        "low": float(closed_candle_data[3]),
                        "close": float(closed_candle_data[4]),
                        "volume": float(closed_candle_data[5])
                    }
                    
                    if KLINES_CACHE[cache_key][last_idx]['time'] == closed_candle['time']:
                        KLINES_CACHE[cache_key][last_idx] = closed_candle
                        
                    KLINES_CACHE[cache_key].append(candle)
                    
                    import sys
                    print(f"Candle Closed at {closed_candle['time']}! Saving to DB and triggering Engine...")
                    sys.stdout.flush()
                    
                    df = pd.DataFrame([closed_candle])
                    df.to_sql(table_name, con=engine, if_exists='append', index=False)
                    
                    await trader_instance.on_candle_closed()
            
            # SMART POLLING: Calculate seconds until next 3m candle close
            now_ts = int(time.time())
            seconds_to_next_candle = 180 - (now_ts % 180)
            
            if seconds_to_next_candle > 10:
                await asyncio.sleep(10) # Far from close, poll every 10s to keep UI updated
            elif seconds_to_next_candle > 3:
                await asyncio.sleep(2)  # Getting closer, poll every 2s
            else:
                await asyncio.sleep(0.5) # Right at the boundary, poll 2 times per second to catch it instantly!
                
        except Exception as e:
            print(f"REST Polling error: {e}. Retrying in 5s...")
            await asyncio.sleep(5)
