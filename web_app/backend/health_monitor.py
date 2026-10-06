import asyncio
import os
import sys
import time
import shutil
import json
import subprocess
from datetime import datetime, timezone, timedelta
import httpx
from dotenv import load_dotenv

# Set timezone to Vietnam GMT+7
VN_TZ = timezone(timedelta(hours=7))

# Load root .env
load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8934179085:AAG0RzgYmfIq4G-Sl2ejv1mKE-ytdGOZaVA")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "6067707939")

async def send_tg(msg: str):
    if not TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(url, json=payload)
    except Exception as e:
        print(f"Error sending TG: {e}")

def get_system_stats():
    # CPU Load
    try:
        load1, load5, _ = os.getloadavg()
    except Exception:
        load1, load5 = 0.0, 0.0

    # Memory
    try:
        import psutil
        mem = psutil.virtual_memory()
        mem_str = f"{mem.used / (1024**3):.1f}GB / {mem.total / (1024**3):.1f}GB ({mem.percent}%)"
    except Exception:
        # Fallback to free -m
        try:
            out = subprocess.check_output("free -m", shell=True).decode()
            lines = out.strip().split("\n")
            parts = lines[1].split()
            mem_str = f"{int(parts[2])}MB / {int(parts[1])}MB"
        except Exception:
            mem_str = "N/A"

    # Disk
    try:
        total, used, free = shutil.disk_usage("/")
        disk_str = f"{used // (2**30)}GB / {total // (2**30)}GB ({used*100//total}%)"
    except Exception:
        disk_str = "N/A"

    # Uptime
    try:
        uptime_out = subprocess.check_output("uptime -p", shell=True).decode().strip()
    except Exception:
        uptime_out = "N/A"

    return {
        "load": f"{load1:.2f}, {load5:.2f}",
        "mem": mem_str,
        "disk": disk_str,
        "uptime": uptime_out
    }

def get_pm2_stats():
    try:
        cmd = "/usr/bin/pm2 jlist" if os.path.exists("/usr/bin/pm2") else "pm2 jlist"
        out = subprocess.check_output(cmd, shell=True).decode()
        data = json.loads(out)
        res = {}
        for p in data:
            name = p.get("name")
            if name in ["bot-xrp", "bot-sol"]:
                status = p.get("pm2_env", {}).get("status", "unknown")
                restarts = p.get("pm2_env", {}).get("restart_time", 0)
                mem = p.get("monit", {}).get("memory", 0) / (1024 * 1024)
                res[name] = {
                    "status": status,
                    "restarts": restarts,
                    "mem": f"{mem:.1f} MB"
                }
        return res
    except Exception as e:
        return {"error": str(e)}

async def check_bot_futures(symbol: str, bot_dir: str):
    env_file = os.path.join(bot_dir, "web_app/backend/.env")
    api_key = ""
    secret_key = ""
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                if line.startswith("BINANCE_API_KEY="):
                    api_key = line.strip().split("=", 1)[1].replace('"', '').replace("'", "")
                elif line.startswith("BINANCE_SECRET_KEY="):
                    secret_key = line.strip().split("=", 1)[1].replace('"', '').replace("'", "")

    if not api_key:
        return {"status": "NO_API_KEY", "balance": 0.0, "position": None, "orders": []}

    try:
        import ccxt.async_support as ccxt_async
        exchange = ccxt_async.binance({
            'apiKey': api_key,
            'secret': secret_key,
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        
        # Ping / Latency
        t0 = time.time()
        await exchange.fetch_time()
        latency = int((time.time() - t0) * 1000)

        # Balance
        bal = await exchange.fetch_balance()
        usdt_bal = bal.get('total', {}).get('USDT', 0.0)

        # Position
        symbol_raw = symbol.replace('/', '')
        positions = await exchange.fapiPrivateV2GetPositionRisk()
        pos_data = None
        for p in positions:
            if p['symbol'] == symbol_raw:
                amt = float(p['positionAmt'])
                if abs(amt) > 0:
                    pos_data = {
                        "side": "LONG" if amt > 0 else "SHORT",
                        "size": abs(amt),
                        "entry_price": float(p['entryPrice']),
                        "mark_price": float(p['markPrice']),
                        "unrealized_pnl": float(p['unRealizedProfit']),
                        "liquidation_price": float(p['liquidationPrice']),
                        "leverage": int(p['leverage'])
                    }
                    break

        # Open Orders
        open_orders = await exchange.fapiPrivateGetOpenOrders({'symbol': symbol_raw})
        sl_order = None
        tp_order = None
        for o in open_orders:
            ot = o.get('type')
            if ot in ['STOP_MARKET', 'STOP']:
                sl_order = float(o.get('stopPrice', 0.0))
            elif ot in ['TAKE_PROFIT_MARKET', 'TAKE_PROFIT']:
                tp_order = float(o.get('stopPrice', 0.0))

        await exchange.close()
        return {
            "status": "OK",
            "latency": f"{latency}ms",
            "balance": usdt_bal,
            "position": pos_data,
            "sl_order": sl_order,
            "tp_order": tp_order
        }
    except Exception as e:
        return {"status": f"ERROR: {str(e)[:50]}", "balance": 0.0, "position": None}

async def generate_health_report():
    now_vn = datetime.now(VN_TZ).strftime("%H:%M - %d/%m/%Y")
    sys_stats = get_system_stats()
    pm2_stats = get_pm2_stats()
    
    # Check XRP bot
    xrp_bot = await check_bot_futures("XRP/USDT", "/root/bot_xrp")
    # Check SOL bot
    sol_bot = await check_bot_futures("SOL/USDT", "/root/bot_sol")

    msg = f"🛡️ <b>[BÁO CÁO SỨC KHỎE HỆ THỐNG QUANT]</b>\n"
    msg += f"⏰ <i>Thời gian: {now_vn} (GMT+7)</i>\n"
    msg += "━━━━━━━━━━━━━━━━━━━\n\n"

    # 1. SERVER HEALTH
    msg += f"🖥️ <b>1. HẠ TẦNG VPS (165.101.47.50):</b>\n"
    msg += f"• CPU Load: <code>{sys_stats['load']}</code>\n"
    msg += f"• Bộ nhớ RAM: <code>{sys_stats['mem']}</code>\n"
    msg += f"• Ổ cứng SSD: <code>{sys_stats['disk']}</code>\n"
    msg += f"• Uptime: <code>{sys_stats['uptime']}</code>\n\n"

    # 2. PM2 ENGINES
    msg += f"⚙️ <b>2. TIẾN TRÌNH TRADING BOT (PM2):</b>\n"
    if "bot-xrp" in pm2_stats:
        p = pm2_stats["bot-xrp"]
        icon = "🟢" if p["status"] == "online" else "🔴"
        msg += f"• <b>bot-xrp (5m):</b> {icon} <code>{p['status'].upper()}</code> | RAM: {p['mem']} | Restarts: {p['restarts']}\n"
    if "bot-sol" in pm2_stats:
        p = pm2_stats["bot-sol"]
        icon = "🟢" if p["status"] == "online" else "🔴"
        msg += f"• <b>bot-sol (4H):</b> {icon} <code>{p['status'].upper()}</code> | RAM: {p['mem']} | Restarts: {p['restarts']}\n"
    msg += "\n"

    # 3. XRP STATUS
    msg += f"🪙 <b>3. VÍ & VỊ THẾ XRP (Bắt Đáy/Đỉnh):</b>\n"
    msg += f"• Kết nối sàn: <code>{xrp_bot.get('status')} ({xrp_bot.get('latency', 'N/A')})</code>\n"
    msg += f"• Số dư ví Futures: <b>${xrp_bot.get('balance', 0.0):,.2f} USDT</b>\n"
    
    pos_xrp = xrp_bot.get("position")
    if not pos_xrp:
        msg += "• Trạng thái lệnh: 🟢 <b>Đang Rình Mồi (Flat)</b>\n"
    else:
        pnl = pos_xrp["unrealized_pnl"]
        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        msg += f"• Trạng thái lệnh: 🎯 <b>ĐANG GIỮ VỊ THẾ {pos_xrp['side']}</b>\n"
        msg += f"  - Khối lượng: <code>{pos_xrp['size']:,.0f} XRP</code> ({pos_xrp['leverage']}x)\n"
        msg += f"  - Giá vào: <code>${pos_xrp['entry_price']:.4f}</code> | Giá sàn: <code>${pos_xrp['mark_price']:.4f}</code>\n"
        msg += f"  - PnL tạm tính: {pnl_icon} <b>{pnl:+,.2f} USDT</b>\n"
        
        # Check SL
        sl = xrp_bot.get("sl_order")
        if sl:
            msg += f"  - 🛡️ Cắt lỗ (SL sàn): ✅ <b>ĐÃ CÀI Ở ${sl:.4f}</b>\n"
        else:
            msg += f"  - 🛡️ Cắt lỗ (SL sàn): 🚨 <b>CHƯA CÓ LỆNH SL!</b>\n"
            
        tp = xrp_bot.get("tp_order")
        if tp:
            msg += f"  - 🏆 Chốt lời (TP sàn): ✅ <b>ĐÃ CÀI Ở ${tp:.4f}</b>\n"

    msg += "\n"

    # 4. SOL STATUS
    msg += f"🌊 <b>4. VÍ & VỊ THẾ SOL (Cưỡi Sóng):</b>\n"
    msg += f"• Kết nối sàn: <code>{sol_bot.get('status')} ({sol_bot.get('latency', 'N/A')})</code>\n"
    msg += f"• Số dư ví Futures: <b>${sol_bot.get('balance', 0.0):,.2f} USDT</b>\n"
    
    pos_sol = sol_bot.get("position")
    if not pos_sol:
        msg += "• Trạng thái lệnh: 🟢 <b>Đang Rình Mồi (Chờ nến 4H)</b>\n"
    else:
        pnl = pos_sol["unrealized_pnl"]
        pnl_icon = "🟢" if pnl >= 0 else "🔴"
        msg += f"• Trạng thái lệnh: 🎯 <b>ĐANG CƯỠI SÓNG {pos_sol['side']}</b>\n"
        msg += f"  - Khối lượng: <code>{pos_sol['size']:.2f} SOL</code> ({pos_sol['leverage']}x)\n"
        msg += f"  - Giá vào: <code>${pos_sol['entry_price']:.2f}</code> | Giá sàn: <code>${pos_sol['mark_price']:.2f}</code>\n"
        msg += f"  - PnL tạm tính: {pnl_icon} <b>{pnl:+,.2f} USDT</b>\n"
        sl = sol_bot.get("sl_order")
        if sl:
            msg += f"  - 🛡️ Cắt lỗ (SL sàn): ✅ <b>ĐÃ CÀI Ở ${sl:.2f}</b>\n"
        else:
            msg += f"  - 🛡️ Cắt lỗ (SL sàn): ℹ️ <i>Theo dõi đảo Supertrend 4H</i>\n"

    msg += "\n━━━━━━━━━━━━━━━━━━━\n"
    msg += "✨ <i>Hệ thống tự động vận hành 24/7 bảo vệ vốn của Sếp!</i>"
    
    print(msg)
    await send_tg(msg)

if __name__ == "__main__":
    asyncio.run(generate_health_report())
