import os

with open('backend/server/main.py', 'r') as f:
    content = f.read()

sol_endpoint = """
@app.get("/api/backtest/sol_inverse")
async def backtest_sol_inverse(
    timeframe: str = Query("5m"),
    days: int = Query(30)
):
    try:
        from core.exchange import fetch_ohlcv
        import numpy as np
        
        limit = int(days * 24 * 60 / int(timeframe.replace('m', '')))
        df = await fetch_ohlcv("SOL/USDT", timeframe, limit=limit + 200)
        
        # Calculate KC and BB
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
        sl_pct = 12.0
        maker_fee = 0.02 / 100
        taker_fee = 0.05 / 100
        
        i = 200
        while i < len(df) - 1:
            was_squeezed = df['squeeze_duration'].iloc[i-1] >= 5
            fires_now = df['squeeze_off'].iloc[i] and df['squeeze_on'].iloc[i-1]
            high_vol = df['volume'].iloc[i] > (1.5 * df['vol_ma'].iloc[i])
            
            if was_squeezed and fires_now and high_vol:
                is_bullish_breakout = df['close'].iloc[i] > df['bb_mid'].iloc[i]
                side = 'short' if is_bullish_breakout else 'long'
                entry = df['close'].iloc[i]
                
                if side == 'long':
                    sl_price = entry * (1 - sl_pct/100)
                    tp_price = entry * (1 + tp_pct/100)
                else:
                    sl_price = entry * (1 + sl_pct/100)
                    tp_price = entry * (1 - tp_pct/100)
                    
                exit_idx = i
                exit_price = 0
                is_win = False
                for j in range(i+1, len(df)):
                    if side == 'long':
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
                    pnl_pct = (tp_pct - 0.04) if is_win else (-sl_pct - 0.07)
                    trades.append({
                        "id": str(df.index[i]),
                        "symbol": "SOLUSDT",
                        "side": side.upper(),
                        "entry_price": float(entry),
                        "exit_price": float(exit_price),
                        "entry_time": int(df['timestamp'].iloc[i]),
                        "exit_time": int(df['timestamp'].iloc[exit_idx]),
                        "pnl": float(pnl_pct * 200 / 100), # Assume $200 position size
                        "pnl_pct": float(pnl_pct)
                    })
                    i = exit_idx
                    continue
            i += 1
            
        win_trades = [t for t in trades if t['pnl'] > 0]
        loss_trades = [t for t in trades if t['pnl'] <= 0]
        total_pnl = sum(t['pnl'] for t in trades)
        
        return {
            "status": "success",
            "data": {
                "total_trades": len(trades),
                "win_trades": len(win_trades),
                "loss_trades": len(loss_trades),
                "win_rate": (len(win_trades) / len(trades) * 100) if trades else 0,
                "total_pnl": total_pnl,
                "trades": trades,
                "market_data": df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_dict(orient="records")
            }
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/backtest/eth_vwap")
"""

content = content.replace('@app.get("/api/backtest/eth_vwap")', sol_endpoint)
with open('backend/server/main.py', 'w') as f:
    f.write(content)

