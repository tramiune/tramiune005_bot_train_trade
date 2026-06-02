# Web TradingView-like Chart + Backtest (Prototype)

This is a prototype web UI with:
- TradingView-style interactive candlestick chart (zoom/pan, crosshair)
- Timeframe selector
- Backtest button (runs Python backtester and overlays trades)

## Run

### Backend (FastAPI)
```bash
cd web_app/backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn server.main:app --reload --port 8000
```

### Frontend (Vite + React)
```bash
cd web_app/frontend
npm install
npm run dev
```

Open the UI from the Vite output (typically `http://localhost:5173`).

