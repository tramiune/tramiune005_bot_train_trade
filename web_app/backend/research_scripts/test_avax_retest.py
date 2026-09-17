from datetime import datetime, timedelta, timezone
import pandas as pd
from server.main import _fetch_ohlcv_ccxt, _sma, _ema, _atr

def run_analysis():
    print("Fetching 4 years of 1h data for AVAX...")
    since = datetime.now(timezone.utc) - timedelta(days=1460)
    sol = _fetch_ohlcv_ccxt("binance", "AVAX/USDT", "1h", since=since, limit=100000)
    btc = _fetch_ohlcv_ccxt("binance", "BTC/USDT", "1h", since=since, limit=100000)
    
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol, btc, on="timestamp", how="left")
    
    df["e200"] = _ema(df["close"], 200)
    df["e20"] = _ema(df["close"], 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"], 20)
    df["btc_e200"] = _ema(df["btc_close"], 200)
    
    for rr in [5.0, 10.0, 15.0]:
        w_cnt = 0
        l_cnt = 0
        skip_idx = 0
        
        last_bullish_cross_idx = 0
        i = 205
        while i < len(df) - 1:
            if i < skip_idx:
                i += 1
                continue
                
            c = float(df["close"].iloc[i])
            h = float(df["high"].iloc[i])
            l = float(df["low"].iloc[i])
            v = float(df["volume"].iloc[i])
            
            e200_val = float(df["e200"].iloc[i]) if pd.notna(df["e200"].iloc[i]) else 0
            e20_val = float(df["e20"].iloc[i]) if pd.notna(df["e20"].iloc[i]) else 0
            prev_e20 = float(df["e20"].iloc[i-1]) if pd.notna(df["e20"].iloc[i-1]) else 0
            prev_e200 = float(df["e200"].iloc[i-1]) if pd.notna(df["e200"].iloc[i-1]) else 0
            at = float(df["atr14"].iloc[i]) if pd.notna(df["atr14"].iloc[i]) else 0
            v_ma = float(df["v20"].iloc[i]) if pd.notna(df["v20"].iloc[i]) else 0
            
            btc_c = float(df["btc_close"].iloc[i]) if pd.notna(df["btc_close"].iloc[i]) else 0
            btc_e200_val = float(df["btc_e200"].iloc[i]) if pd.notna(df["btc_e200"].iloc[i]) else 0
            
            if prev_e20 <= prev_e200 and e20_val > e200_val:
                last_bullish_cross_idx = i
                
            candle_range = h - l
            close_pct = (c - l) / candle_range if candle_range > 0 else 0
            dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
            
            is_uptrend = e20_val > e200_val
            candles_since_cross = i - last_bullish_cross_idx
            is_proper_speed = 20 <= candles_since_cross < 150
            is_strong_rejection = close_pct > 0.6
            has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
            is_touching = l <= e200_val and c > e200_val
            btc_bullish = btc_c > btc_e200_val
            is_midweek = dt.dayofweek in [1, 2, 3] # Tue, Wed, Thu
            
            if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bullish and is_midweek:
                entry = c
                sl = entry - 1.5 * at
                
                risk = entry - sl
                if risk > 0:
                    tp = entry + rr * risk
                    j = i + 1
                    exit_idx = None
                    result = None
                    
                    while j < len(df):
                        hi = float(df["high"].iloc[j])
                        lo = float(df["low"].iloc[j])
                        if lo <= sl: exit_idx, result = j, "LOSS"; break
                        if hi >= tp: exit_idx, result = j, "WIN"; break
                        j += 1
                        
                    if exit_idx is not None:
                        if result == "WIN": w_cnt += 1
                        else: l_cnt += 1
                        skip_idx = exit_idx
            i += 1

        tot = w_cnt + l_cnt
        wr = w_cnt / tot * 100 if tot else 0
        net = (w_cnt * rr) - l_cnt
        print(f"AVAX RR {rr:>4.1f} | Trades: {tot:>2} | Wins: {w_cnt:>2} | Losses: {l_cnt:>2} | WR: {wr:05.2f}% | Net Profit: {net:>+6.1f} R")

if __name__ == "__main__":
    run_analysis()
