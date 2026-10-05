import asyncio
from server.main import backtest_doge_inverse

async def run():
    res = await backtest_doge_inverse(timeframe="3m", days=1460, compounding=False, risk_pct=30.0, initial_balance=800.0)
    print(res)

asyncio.run(run())
