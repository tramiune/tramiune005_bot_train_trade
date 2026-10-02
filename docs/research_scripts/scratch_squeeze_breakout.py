import asyncio
import pandas as pd
import numpy as np
import time
import ccxt.async_support as ccxt
import sys

async def fetch_data(symbol, tf='15m', years=4):
    exchange = ccxt.binanceusdm({'enableRateLimit': True})
    now = int(time.time() * 1000)
    ms = years * 365 * 24 * 60 * 60 * 1000
    since = now - ms
    all_klines = []
    
    print(f"Fetching {years} Year(s) of {symbol} {tf} Data...")
    while since < now:
        try:
            klines = await exchange.fetch_ohlcv(symbol, tf, since=since, limit=1500)
            if not klines: break
            all_klines.extend(klines)
            since = klines[-1][0] + (15 * 60 * 1000 if tf=='15m' else 300000)
        except Exception:
            await asyncio.sleep(0.5)
    await exchange.close()
    return all_klines

def calculate_kc(df, period=20, mult=1.5):
    # Keltner Channel
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        )
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (mult * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (mult * df['atr'])
    return df

def calculate_bb(df, period=20, mult=2.0):
    # Bollinger Bands
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (mult * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (mult * df['bb_std'])
    return df

async def run():
    data = await fetch_data('BTC/USDT', '15m', 4)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df = df.drop_duplicates(subset=['timestamp']).reset_index(drop=True)
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Calculate Channels
    df = calculate_kc(df, period=20, mult=1.5)
    df = calculate_bb(df, period=20, mult=2.0)
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    # Squeeze ON: BB is completely inside KC
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    
    # Track how long the squeeze was on
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    tp_pct = 3.0
    sl_pct = 1.0
    maker_fee = 0.02 / 100
    taker_fee = 0.05 / 100
    
    trades = []
    
    i = 50
    while i < len(df) - 1:
        # Firing condition: Squeeze transitions from ON (for at least 5 candles) to OFF
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        
        # Volume expansion
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            # Determine direction: simple momentum (close vs 20 SMA)
            is_bullish = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'LONG' if is_bullish else 'SHORT'
            
            entry_price = df['close'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry_price * (1 - sl_pct/100)
                tp_price = entry_price * (1 + tp_pct/100)
            else:
                sl_price = entry_price * (1 + sl_pct/100)
                tp_price = entry_price * (1 - tp_pct/100)
                
            is_win = False
            exit_idx = i
            for j in range(i+1, min(i+96, len(df))): # Look forward 24 hours max (96 candles)
                if side == 'LONG':
                    if df['low'].iloc[j] <= sl_price:
                        is_win = False; exit_idx = j; break
                    elif df['high'].iloc[j] >= tp_price:
                        is_win = True; exit_idx = j; break
                else:
                    if df['high'].iloc[j] >= sl_price:
                        is_win = False; exit_idx = j; break
                    elif df['low'].iloc[j] <= tp_price:
                        is_win = True; exit_idx = j; break
            
            if exit_idx > i:
                trades.append({
                    "timestamp": df['datetime'].iloc[i],
                    "side": side,
                    "is_win": is_win
                })
                i = exit_idx
            else:
                i += 1
            continue
        i += 1
        
    trades_df = pd.DataFrame(trades)
    
    print("\n" + "="*60)
    print("=== VOLATILITY SQUEEZE BREAKOUT (BTC 15m) ===")
    print(f"Risk/Reward: 1:{tp_pct/sl_pct} (SL: {sl_pct}%, TP: {tp_pct}%)")
    print("="*60)
    
    if len(trades_df) == 0:
        print("No trades found.")
        return
        
    w = len(trades_df[trades_df['is_win'] == True])
    l = len(trades_df) - w
    wr = w/len(trades_df)*100
    
    win_mult = tp_pct - maker_fee*100 - maker_fee*100
    loss_mult = -sl_pct - maker_fee*100 - taker_fee*100
    
    pnl = (w * win_mult) + (l * loss_mult)
    
    print(f"Total Trades: {len(trades_df)}")
    print(f"Wins: {w} | Losses: {l} | Win Rate: {wr:.2f}%")
    print(f"Net PnL (Risking $100 per trade): ${pnl:.2f}")
    
    # Breakeven WR
    be_wr = abs(loss_mult) / (win_mult + abs(loss_mult)) * 100
    print(f"\nBreak-even Win Rate required: {be_wr:.2f}%")
    if wr > be_wr:
        print("STATUS: LÃI ĐẬM KHỦNG KHIẾP 🚀")
    else:
        print("STATUS: Lỗ sml 💀")

asyncio.run(run())
