import os

with open('frontend/src/App.tsx', 'r') as f:
    content = f.read()

content = content.replace("['BTCUSDT', 'ETHUSDT']", "['BTCUSDT', 'ETHUSDT', 'SOLUSDT']")
content = content.replace("symbol === 'ETHUSDT' ? 'ETH VWAP Mean Reversion'", "symbol === 'ETHUSDT' ? 'ETH VWAP Mean Reversion' : symbol === 'SOLUSDT' ? 'SOL Inverse Breakout (5m, Degen)'")

with open('frontend/src/App.tsx', 'w') as f:
    f.write(content)

with open('frontend/src/components/ChartWidget.tsx', 'r') as f:
    content = f.read()

endpoint_logic = """
      let endpoint = '/api/backtest';
      if (symbol === 'ETHUSDT') {
        endpoint = '/api/backtest/eth_vwap';
      } else if (symbol === 'SOLUSDT') {
        endpoint = '/api/backtest/sol_inverse?timeframe=5m';
      }
      
      const response = await fetch(`http://localhost:8000${endpoint}`);
"""

content = content.replace("""
      const endpoint = symbol === 'ETHUSDT' ? '/api/backtest/eth_vwap' : '/api/backtest';
      const response = await fetch(`http://localhost:8000${endpoint}`);
""", endpoint_logic)

with open('frontend/src/components/ChartWidget.tsx', 'w') as f:
    f.write(content)

