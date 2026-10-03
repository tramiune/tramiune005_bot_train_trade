import asyncio
import websockets

async def test():
    uri = "wss://fstream.binance.com/ws/btcusdt@kline_1m"
    print(f"Connecting to {uri}")
    try:
        async with websockets.connect(uri) as ws:
            print("Connected! Waiting for message...")
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            print(f"Received: {msg[:100]}")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test())
