import os
import re

if os.path.exists('web_app/backend/engine/backtester.py'):
    with open('web_app/backend/engine/backtester.py', 'r') as f:
        content = f.read()

    content = re.sub(
        r'for j in range\(i\+1, min\(i\+1440, len\(df\)\)\):',
        r'for j in range(i+1, len(df)):',
        content
    )
    
    # In backtester.py, trades are dicts
    old_logic = """            if exit_idx > i:
                trades.append({
                    "side": side,"""
    new_logic = """            if exit_idx == i:
                exit_idx = len(df) - 1
                exit_price = df['close'].iloc[-1]
                is_win = (exit_price > entry) if side == 'LONG' else (exit_price < entry)
                
            if exit_idx > i:
                trades.append({
                    "side": side,"""
    
    content = content.replace(old_logic, new_logic)

    with open('web_app/backend/engine/backtester.py', 'w') as f:
        f.write(content)
    print("Patched backtester.py")
