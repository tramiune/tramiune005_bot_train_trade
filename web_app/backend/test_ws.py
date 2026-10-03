import asyncio
import websockets
import json

async def test():
    uri = "wss://fstream.binance.com/ws/dogeusdt@kline_3m"
    print(f"Connecting to {uri}")
    async with websockets.connect(uri) as ws:
        print("Connected! Waiting for message...")
        msg = await ws.recv()
        print(f"Received: {msg[:100]}")

asyncio.run(test())
