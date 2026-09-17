import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone

def _atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df['high']
    low = df['low']
    close = df['close'].shift(1)
    tr1 = high - low
    tr2 = (high - close).abs()
    tr3 = (low - close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period).mean()

def fetch_futures_data(symbol, days=1460):
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    since = exchange.parse8601((datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
    all_ohlcv = []
    while True:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '1h', since, 1000)
            if not len(ohlcv): break
            all_ohlcv += ohlcv
            since = ohlcv[-1][0] + 3600000 
            if len(ohlcv) < 1000: break
        except Exception as e:
            break
    df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
    df.drop_duplicates(subset='timestamp', inplace=True)
    df.sort_values('timestamp', inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def run_analysis():
    print("Fetching SOL and BTC Futures data...")
    sol = fetch_futures_data("SOL/USDT")
    btc = fetch_futures_data("BTC/USDT")
    btc = btc[["timestamp", "close"]].rename(columns={"close": "btc_close"})
    df = pd.merge(sol, btc, on="timestamp", how="left")
    
    df["e200"] = _ema(df["close"].astype(float), 200)
    df["e20"] = _ema(df["close"].astype(float), 20)
    df["atr14"] = _atr(df, 14)
    df["v20"] = _sma(df["volume"].astype(float), 20)
    df["btc_e200"] = _ema(df["btc_close"].astype(float), 200)
    
    print("\n--- OPTIMIZING SOL ON BINANCE FUTURES ---")
    
    for atr_mult in [1.5, 1.8, 2.0]:
        for rr_target in [10.0, 12.0, 15.0]:
            trades = []
            r_sequence = []
            i = 205
            last_bullish_cross_idx = 0
            
            while i < len(df) - 1:
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
                    
                close_pct = (c - l) / (h - l) if (h - l) > 0 else 0
                dt = pd.to_datetime(df["timestamp"].iloc[i], utc=True)
                
                # Base Filters
                is_uptrend = e20_val > e200_val
                candles_since_cross = i - last_bullish_cross_idx
                is_proper_speed = 20 <= candles_since_cross < 150
                is_touching = l <= e200_val and c > e200_val
                is_strong_rejection = close_pct > 0.6
                has_volume = (v / v_ma) > 1.2 if v_ma > 0 else False
                btc_bullish = btc_c > btc_e200_val
                is_midweek = dt.dayofweek in [1, 2, 3] 
                
                if is_uptrend and is_proper_speed and is_touching and is_strong_rejection and has_volume and btc_bullish and is_midweek:
                    entry = c
                    sl = entry - atr_mult * at
                    
                    risk = entry - sl
                    if risk > 0:
                        tp = entry + rr_target * risk
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
                            trades.append(result)
                            r_sequence.append(rr_target if result == "WIN" else -1.0)
                            i = exit_idx
                            continue
                i += 1
                
            wins = trades.count("WIN")
            losses = trades.count("LOSS")
            total = len(trades)
            wr = wins / total * 100 if total else 0
            net_r = sum(r_sequence)
            
            # Simulated 10% risk compounding on 10M VND
            cap = 10_000_000
            for r in r_sequence:
                cap += cap * 0.10 * r
                
            print(f"SL: {atr_mult} ATR | RR: {rr_target:>4.1f} | Trades: {total:>2} | Wins: {wins:>2} | Losses: {losses:>2} | WR: {wr:>5.1f}% | Net: {net_r:>+5.1f} R | Final Cap: {cap:,.0f} VND")

if __name__ == "__main__":
    run_analysis()
