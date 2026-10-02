import re

# 1. Update backtester.py
with open("web_app/backend/engine/backtester.py", "a") as f:
    f.write("""
import numpy as np

def backtest_doge_3m_degen(df):
    period = 20
    df['tr'] = np.maximum(
        df['high'] - df['low'],
        np.maximum(abs(df['high'] - df['close'].shift()), abs(df['low'] - df['close'].shift()))
    )
    df['atr'] = df['tr'].rolling(window=period).mean()
    df['kc_mid'] = df['close'].rolling(window=period).mean()
    df['kc_upper'] = df['kc_mid'] + (1.5 * df['atr'])
    df['kc_lower'] = df['kc_mid'] - (1.5 * df['atr'])
    
    df['bb_mid'] = df['close'].rolling(window=period).mean()
    df['bb_std'] = df['close'].rolling(window=period).std()
    df['bb_upper'] = df['bb_mid'] + (2.0 * df['bb_std'])
    df['bb_lower'] = df['bb_mid'] - (2.0 * df['bb_std'])
    
    df['vol_ma'] = df['volume'].rolling(window=20).mean()
    
    df['squeeze_on'] = (df['bb_upper'] < df['kc_upper']) & (df['bb_lower'] > df['kc_lower'])
    df['squeeze_off'] = ~df['squeeze_on']
    df['squeeze_duration'] = df['squeeze_on'].groupby((~df['squeeze_on']).cumsum()).cumsum()
    
    trades = []
    tp_pct = 5.0
    sl_pct = 15.0
    
    i = 200
    while i < len(df) - 1:
        was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
        fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
        high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
        
        if was_squeezed and fires_now and high_vol:
            is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
            side = 'SHORT' if is_bullish_breakout else 'LONG'
            entry = df['close'].iloc[i]
            
            if side == 'LONG':
                sl_price = entry * (1 - sl_pct/100)
                tp_price = entry * (1 + tp_pct/100)
            else:
                sl_price = entry * (1 + sl_pct/100)
                tp_price = entry * (1 - tp_pct/100)
                
            exit_idx = i
            exit_price = 0
            is_win = False
            for j in range(i+1, min(i+1440, len(df))):
                if side == 'LONG':
                    if df['low'].iloc[j] <= sl_price:
                        is_win = False; exit_idx = j; exit_price = sl_price; break
                    elif df['high'].iloc[j] >= tp_price:
                        is_win = True; exit_idx = j; exit_price = tp_price; break
                else:
                    if df['high'].iloc[j] >= sl_price:
                        is_win = False; exit_idx = j; exit_price = sl_price; break
                    elif df['low'].iloc[j] <= tp_price:
                        is_win = True; exit_idx = j; exit_price = tp_price; break
            
            if exit_idx > i:
                trades.append({
                    "side": side,
                    "entry": float(entry),
                    "exit_price": float(exit_price),
                    "time": df['timestamp'].iloc[i] / 1000 if df['timestamp'].iloc[i] > 2000000000 else df['timestamp'].iloc[i],
                    "exit_time": df['timestamp'].iloc[exit_idx] / 1000 if df['timestamp'].iloc[exit_idx] > 2000000000 else df['timestamp'].iloc[exit_idx],
                    "tp": tp_price,
                    "sl": sl_price,
                    "pnl": 1 if is_win else -1
                })
                i = exit_idx
                continue
        i += 1
    return trades
""")

# 2. Update populate_db.py
with open("web_app/backend/populate_db.py", "w") as f:
    f.write("""import asyncio
import pandas as pd
from database import engine, SessionLocal
from models import Trade, BotConfig
from fetch_more import fetch_lots_of_klines
from engine.backtester import backtest_doge_3m_degen
import ccxt.async_support as ccxt
from datetime import datetime

async def main():
    exchange = ccxt.binance({'enableRateLimit': True})
    db = SessionLocal()
    
    print("Fetching DOGE 3m data (approx 210,000 candles)...")
    doge_data = await fetch_lots_of_klines(exchange, "DOGE/USDT", '3m', 210000)
    df_doge = pd.DataFrame(doge_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    doge_trades = backtest_doge_3m_degen(df_doge)
    
    await exchange.close()
    
    print(f"Found {len(doge_trades)} DOGE 3m trades.")
    
    print("Clearing old trades and configs...")
    db.query(Trade).delete()
    db.query(BotConfig).delete()
    
    # Insert only DOGE 3m config
    db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
    db.commit()

    print("Inserting to DB...")
    for t in doge_trades:
        trade = Trade(
            symbol="DOGE/USDT",
            strategy="DOGE_3M_DEGEN",
            side=t["side"],
            entry_price=t["entry"],
            stop_loss=t["sl"],
            take_profit=t["tp"],
            status="CLOSED",
            entry_time=datetime.fromtimestamp(t["time"])
        )
        db.add(trade)
        
    db.commit()
    db.close()
    print("Database populated successfully!")

if __name__ == "__main__":
    asyncio.run(main())
""")

# 3. Update engine/trader.py
with open("web_app/backend/engine/trader.py", "r") as f:
    trader_content = f.read()

# Replace config loading
trader_content = re.sub(
    r'if not db\.query\(BotConfig\)\.filter_by\(strategy="SOL_GOD_MODE"\)\.first\(\):.*?db\.commit\(\)',
    r'''if not db.query(BotConfig).filter_by(strategy="DOGE_3M_DEGEN").first():
            db.add(BotConfig(strategy="DOGE_3M_DEGEN", is_active=True, risk_per_trade_pct=30.0))
        db.commit()''',
    trader_content,
    flags=re.DOTALL
)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(trader_content)
