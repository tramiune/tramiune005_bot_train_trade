import re

with open('web_app/backend/server/main.py', 'r') as f:
    content = f.read()

# Replace the 1440 cap in doge_inverse
content = re.sub(
    r'for j in range\(i\+1, min\(i\+1440, len\(df\)\)\):',
    r'for j in range(i+1, len(df)):',
    content
)

# And if exit_idx is still i, it means it hit the end of the dataframe
# We should mark to market
old_logic = """                if exit_idx > i:
                    if compounding:
                        risk_amount = balance * (risk_pct / 100.0)
                        pos_size = risk_amount / (sl_pct / 100.0)
                    else:
                        pos_size = 200.0"""
new_logic = """                if exit_idx == i:
                    # Mark to market at the end of data
                    exit_idx = len(df) - 1
                    exit_price = df['close'].iloc[-1]
                    if side == 'long':
                        is_win = exit_price > entry
                    else:
                        is_win = exit_price < entry
                        
                if exit_idx > i:
                    if compounding:
                        risk_amount = balance * (risk_pct / 100.0)
                        pos_size = risk_amount / (sl_pct / 100.0)
                    else:
                        pos_size = 200.0"""

content = content.replace(old_logic, new_logic)

# Wait, we need to correctly handle the PNL if it exits by mark to market
old_pnl = """                    win_mult = (tp_pct/100) - maker_fee - maker_fee
                    loss_mult = -(sl_pct/100) - maker_fee - taker_fee
                    
                    if is_win:
                        trade_pnl = pos_size * win_mult
                    else:
                        trade_pnl = pos_size * loss_mult"""
new_pnl = """                    win_mult = (tp_pct/100) - maker_fee - maker_fee
                    loss_mult = -(sl_pct/100) - maker_fee - taker_fee
                    
                    if exit_idx == len(df) - 1 and exit_price not in [tp_price, sl_price]:
                        # Mark to market PNL
                        if side == 'long':
                            actual_pct = (exit_price - entry) / entry
                        else:
                            actual_pct = (entry - exit_price) / entry
                        trade_pnl = pos_size * (actual_pct - maker_fee - taker_fee)
                    else:
                        if is_win:
                            trade_pnl = pos_size * win_mult
                        else:
                            trade_pnl = pos_size * loss_mult"""

content = content.replace(old_pnl, new_pnl)

with open('web_app/backend/server/main.py', 'w') as f:
    f.write(content)
print("Patched doge_inverse in main.py")
