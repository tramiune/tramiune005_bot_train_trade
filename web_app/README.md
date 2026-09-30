# Tramiune Bot Train Trade

Đây là dự án Bot Giao Dịch Thuật Toán (Algorithmic Trading Bot) kết hợp UI quản lý và backtest chuyên sâu.

## 🌿 Cấu trúc các nhánh (Branches)

Dự án hiện tại được chia làm các nhánh (branch) chính với chức năng khác biệt:

### 1. Nhánh `web-tv-chart-clean` (Main/Trunk)
- Đây là nhánh chứa **Giao diện Web (UI/UX)** nền tảng, bao gồm hệ thống Charting kiểu TradingView (vẽ nến, zoom/pan, crosshair).
- Có API kết nối cơ bản giữa Frontend (React/Vite) và Backend (FastAPI).
- Chứa logic cho nút "Backtest" để chạy mô phỏng và vẽ các lệnh Buy/Sell trực tiếp lên biểu đồ.
- Là nơi để khởi chạy Web Dashboard giám sát hệ thống.

### 2. Nhánh `implement` (Lõi Quant Trading & Thuật toán)
- Nhánh này chứa toàn bộ **Lõi Giao Dịch (Trading Engine)** và các chiến lược đã qua Backtest khắt khe trong 4 năm.
- **Chiến lược Nổi bật:**
  - `xrp_pure_robust.py`: Chiến lược đánh chặn NADA 1.5 + RSI < 40 cho XRP (Win rate 64%, Fixed SL/TP).
  - `eth_vwap_robust.py`: Chiến lược Reversion tại dải băng VWAP (2.5 SD) cho ETH với bộ lọc Băng thông (Bandwidth < 5.0%) để né các cú sập hầm (Win rate 60%).
- Chứa hàng chục file `scratch_*.py` lưu trữ lịch sử nghiên cứu Quant, tối ưu tham số (Grid Search), kiểm tra MDD (Max Drawdown), và kiểm tra mô phỏng lãi kép (Compounding Simulation).
- Có các bản vá kết nối trực tiếp với Sàn (CCXT) và logic đặt lệnh Limit/Market (`patch_trader_execute.py`, `patch_exchange.py`).
- **Nên dùng nhánh này** khi muốn chạy Bot thực chiến hoặc tiếp tục R&D các chiến lược mới.

---

## 🚀 Hướng dẫn khởi chạy UI (Nhánh `web-tv-chart-clean`)

### Backend (FastAPI)
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

### Frontend (Vite + React)
```bash
cd frontend
npm install
npm run dev
```
Mở trình duyệt tại `http://localhost:5173`.

---

## 📊 Kế hoạch tiếp theo
- Hợp nhất (Merge) nhánh `implement` vào nhánh chính.
- Triển khai (Deploy) Bot lên VPS Linux để chạy thực chiến 24/7.
