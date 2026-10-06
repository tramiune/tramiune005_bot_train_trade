import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()

from engine.exchange import BinanceFutures
from engine.telegram import send_telegram_message
from database import SessionLocal
from models import Trade, BotConfig, Settings

async def run_audit():
    print("=" * 60)
    print("🚀 AUDIT HỆ THỐNG GIAO DỊCH BOT (BINANCE FUTURES & DATABASE)")
    print("=" * 60)
    
    # 1. API Keys & Balance
    ex = BinanceFutures()
    print("\n[1] KIỂM TRA TÀI KHOẢN BINANCE:")
    print(f"  API Key: {ex.api_key[:6]}...{ex.api_key[-4:] if ex.api_key else 'NONE'}")
    bal = await ex.get_balance('USDT')
    print(f"  Số dư ký quỹ Futures khả dụng: {bal:.4f} USDT")
    
    # 2. Vị thế đang mở trên Binance
    print("\n[2] KIỂM TRA VỊ THẾ ĐANG MỞ TRÊN BINANCE:")
    try:
        positions = await ex.exchange.fapiPrivateV2GetPositionRisk()
        active_pos = [p for p in positions if float(p.get('positionAmt', 0)) != 0]
        if not active_pos:
            print("  ✅ Không có vị thế nào đang treo (Sạch 100%).")
        else:
            for p in active_pos:
                print(f"  ⚠️ Đang có vị thế: Symbol={p['symbol']}, Side={p['positionSide']}, Amount={p['positionAmt']}, Unrealized PnL={p['unRealizedProfit']}")
    except Exception as e:
        print(f"  Lỗi kiểm tra vị thế: {e}")

    # 3. Lệnh chờ (Open Orders & Algo Orders)
    print("\n[3] KIỂM TRA LỆNH CHỜ (OPEN ORDERS & ALGO ORDERS):")
    try:
        orders = await ex.exchange.fapiPrivateGetOpenOrders()
        algo_orders = await ex.exchange.fapiPrivateGetOpenAlgoOrders()
        print(f"  Lệnh thường đang chờ (Limit/Market): {len(orders)}")
        print(f"  Lệnh Algo đang chờ (Stop Loss / Take Profit): {len(algo_orders)}")
        if len(orders) == 0 and len(algo_orders) == 0:
            print("  ✅ Không có lệnh treo rác trên sàn (Sạch 100%).")
        else:
            for o in orders:
                print(f"    - Order {o.get('orderId')}: {o.get('symbol')} {o.get('side')} {o.get('origQty')} @ {o.get('price')}")
            for a in algo_orders:
                print(f"    - Algo {a.get('algoId')}: {a.get('symbol')} {a.get('orderType')} @ {a.get('triggerPrice')}")
    except Exception as e:
        print(f"  Lỗi kiểm tra lệnh: {e}")

    # 4. Kiểm tra Database SQLite
    print("\n[4] KIỂM TRA DATABASE (SQLite):")
    db = SessionLocal()
    trades = db.query(Trade).all()
    print(f"  Tổng số lệnh trong bảng trades: {len(trades)}")
    for t in trades:
        print(f"    - ID={t.id}: {t.symbol} {t.side} {t.strategy} | Status={t.status} | Entry={t.entry_price} | PnL={t.pnl}")
        
    settings = db.query(Settings).first()
    risk_pct = settings.risk_pct if settings else 10.0
    print(f"  Cài đặt Risk hiện tại: {risk_pct}%")
    db.close()

    # 5. Kiểm tra Telegram
    print("\n[5] KIỂM TRA THÔNG BÁO TELEGRAM:")
    tg_token = os.getenv("TELEGRAM_BOT_TOKEN")
    tg_chat = os.getenv("TELEGRAM_CHAT_ID")
    print(f"  Token: {tg_token[:10]}... Chat ID: {tg_chat}")
    
    # 6. Bot Mode
    bot_mode = os.getenv("BOT_MODE", "XRP")
    print(f"\n[6] CẤU HÌNH BOT MODE HIỆN TẠI: {bot_mode}")

    await ex.close()
    print("\n" + "=" * 60)
    print("✅ KẾT THÚC KIỂM TRA TOÀN DIỆN")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_audit())
