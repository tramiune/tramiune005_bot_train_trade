import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from engine.exchange import BinanceFutures
from engine.telegram import send_telegram_message

async def main():
    print("=== STARTING XRP REAL PIPELINE TEST ===")
    ex = BinanceFutures()
    symbol = "XRP/USDT"
    
    try:
        # 1. Fetch Price & Balance
        ticker = await ex.exchange.fetch_ticker(symbol)
        curr_price = float(ticker['last'])
        bal = await ex.get_balance('USDT')
        print(f"Current {symbol} Price: {curr_price} USDT")
        print(f"Current Futures Balance: {bal:.2f} USDT")
        
        # 2. Risk Calculation (Exact formula from trader.py)
        # Entry price: current price
        # SL: -0.55%
        # TP: +17.9%
        entry_price = curr_price
        sl_price = entry_price * (1 - 0.0055)
        tp_price = entry_price * (1 + 0.179)
        risk_per_coin = abs(entry_price - sl_price)
        
        # We use a safe size: 10 XRP (~15 USDT notional, requiring ~1.5 USDT margin at 10x)
        # To ensure notional > 5 USDT min notional limit
        position_size = 10.0
        notional_value = position_size * entry_price
        required_leverage = 10
        risk_amount = position_size * risk_per_coin
        
        print(f"Test Trade Specs:")
        print(f"  Side: LONG")
        print(f"  Entry (LIMIT): {entry_price:.4f}")
        print(f"  Stop Loss: {sl_price:.4f} (-0.55%, risk: ${risk_amount:.3f})")
        print(f"  Take Profit: {tp_price:.4f} (+17.9%, profit: ${position_size * (tp_price - entry_price):.3f})")
        print(f"  Size: {position_size} XRP (${notional_value:.2f} notional)")
        print(f"  Leverage: {required_leverage}x")
        
        # 3. Clean up existing open orders first
        symbol_raw = symbol.replace('/', '')
        try:
            await ex.exchange.fapiPrivateDeleteAllOpenOrders({'symbol': symbol_raw})
            await ex.exchange.fapiPrivateDeleteAlgoOpenOrders({'symbol': symbol_raw})
            print("Existing orders cleaned.")
        except Exception as e:
            print("Order clean notice:", e)
            
        # 4. Set Margin and Leverage
        try:
            await ex.exchange.set_margin_mode('CROSSED', symbol_raw)
        except Exception:
            pass
        try:
            await ex.exchange.set_leverage(required_leverage, symbol_raw)
            print(f"Leverage set to {required_leverage}x CROSSED.")
        except Exception as e:
            print("Leverage notice:", e)
            
        # 5. Place real trade via execute_full_trade
        print("\nExecuting full trade (LIMIT Entry + STOP_MARKET SL + TAKE_PROFIT_MARKET TP)...")
        order = await ex.execute_full_trade(symbol, 'buy', position_size, entry_price, sl_price, tp_price)
        print("Entry Order placed successfully! ID:", order.get('id') if order else 'None')
        
        # 6. Check open orders on Binance to verify
        await asyncio.sleep(1)
        open_orders = await ex.exchange.fapiPrivateGetOpenOrders({'symbol': symbol_raw})
        print(f"\nVerifying on Binance: Total Open Orders for {symbol_raw} = {len(open_orders)}")
        for o in open_orders:
            print(f"  -> Type: {o.get('type')}, Side: {o.get('side')}, Price: {o.get('price')}, StopPrice: {o.get('stopPrice')}, Status: {o.get('status')}")
            
        # 7. Send Telegram Notification
        msg = (
            f"🧪 <b>[TEST THỰC TẾ TRÊN SÀN BINANCE]</b>\n\n"
            f"<b>Cặp:</b> {symbol}\n"
            f"<b>Loại lệnh:</b> <code>LIMIT ENTRY</code>\n"
            f"<b>Chiều:</b> LONG (Mua)\n"
            f"<b>Giá vào (Entry):</b> <code>{entry_price:.4f}</code>\n"
            f"<b>Cắt lỗ (SL):</b> <code>{sl_price:.4f}</code> (-0.55% | Rủi ro: ${risk_amount:.2f})\n"
            f"<b>Chốt lời (TP):</b> <code>{tp_price:.4f}</code> (+17.9% | Mục tiêu: +${position_size * (tp_price - entry_price):.2f})\n"
            f"<b>Khối lượng:</b> {position_size} XRP (~${notional_value:.2f})\n"
            f"<b>Đòn bẩy:</b> {required_leverage}x CROSSED\n"
            f"<b>Số dư ví:</b> ${bal:.2f} USDT\n\n"
            f"<i>Lệnh đã được bắn trực tiếp lên sàn Binance Futures của bạn!</i>"
        )
        await send_telegram_message(msg)
        print("\nTelegram message sent!")
        print("=== TEST COMPLETED SUCCESSFULLY ===")
        
    except Exception as e:
        print(f"\nERROR DURING TEST: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await ex.close()

if __name__ == "__main__":
    asyncio.run(main())
