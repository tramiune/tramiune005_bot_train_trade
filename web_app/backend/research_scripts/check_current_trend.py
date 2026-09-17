from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _ema

def run_analysis():
    print("Checking current market trend (Sept 2026)...")
    since = datetime.now(timezone.utc) - timedelta(days=200)
    
    # Check Daily for Macro trend
    btc_1d = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1d", since=since, limit=300)
    btc_1d["e200"] = _ema(btc_1d["close"].astype(float), 200)
    
    sol_1d = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1d", since=since, limit=300)
    sol_1d["e200"] = _ema(sol_1d["close"].astype(float), 200)
    
    curr_btc_c = btc_1d["close"].iloc[-1]
    curr_btc_e200 = btc_1d["e200"].iloc[-1]
    
    curr_sol_c = sol_1d["close"].iloc[-1]
    curr_sol_e200 = sol_1d["e200"].iloc[-1]
    
    print(f"--- DAILY (MACRO) TREND ---")
    print(f"BTC Close: {curr_btc_c} | EMA 200: {curr_btc_e200:.2f} -> {'UPTREND' if curr_btc_c > curr_btc_e200 else 'DOWNTREND'}")
    print(f"SOL Close: {curr_sol_c} | EMA 200: {curr_sol_e200:.2f} -> {'UPTREND' if curr_sol_c > curr_sol_e200 else 'DOWNTREND'}")
    
    # Check 1H for Micro trend (Our Bot's TF)
    since_1h = datetime.now(timezone.utc) - timedelta(days=20)
    sol_1h = _fetch_ohlcv_ccxt("binance", "SOL/USDT", "1h", since=since_1h, limit=500)
    sol_1h["e200"] = _ema(sol_1h["close"].astype(float), 200)
    
    btc_1h = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since_1h, limit=500)
    btc_1h["e200"] = _ema(btc_1h["close"].astype(float), 200)
    
    curr_sol_1h_c = sol_1h["close"].iloc[-1]
    curr_sol_1h_e200 = sol_1h["e200"].iloc[-1]
    
    curr_btc_1h_c = btc_1h["close"].iloc[-1]
    curr_btc_1h_e200 = btc_1h["e200"].iloc[-1]
    
    print(f"\n--- 1H (MICRO) TREND ---")
    print(f"BTC 1H Close: {curr_btc_1h_c} | EMA 200: {curr_btc_1h_e200:.2f} -> {'UPTREND' if curr_btc_1h_c > curr_btc_1h_e200 else 'DOWNTREND'}")
    print(f"SOL 1H Close: {curr_sol_1h_c} | EMA 200: {curr_sol_1h_e200:.2f} -> {'UPTREND' if curr_sol_1h_c > curr_sol_1h_e200 else 'DOWNTREND'}")

if __name__ == "__main__":
    run_analysis()
