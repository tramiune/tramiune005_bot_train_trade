import asyncio
import ccxt.async_support as ccxt
import sys

key1 = "PgYgCctSlrjcjeW8wgttUoXZF9hRkSLWiaIy1xmY5ghX6i1hDRO8oHcAVNEpJPux"
key2 = "OcMoYAhV8jRTjk7zOdI4jmsopWUam5X3nPzjinkyqFVgqtjdO1GPMu09uXeUMiiq"

async def test_keys(api_key, secret):
    exchange = ccxt.binance({
        'apiKey': api_key,
        'secret': secret,
        'enableRateLimit': True,
        'options': {'defaultType': 'future'}
    })
    try:
        bal = await exchange.fetch_balance()
        print(f"SUCCESS! Balance: {bal.get('USDT', {}).get('free')}")
        return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False
    finally:
        await exchange.close()

async def main():
    print("Testing Key1 as API_KEY, Key2 as SECRET...")
    if await test_keys(key1, key2):
        print("MATCH_1")
        return
        
    print("\nTesting Key2 as API_KEY, Key1 as SECRET...")
    if await test_keys(key2, key1):
        print("MATCH_2")
        return

asyncio.run(main())
