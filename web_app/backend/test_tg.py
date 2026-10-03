import asyncio
from dotenv import load_dotenv
load_dotenv()

# Import AFTER load_dotenv
from engine.telegram import send_telegram_message

async def main():
    await send_telegram_message("✅ <b>Quant Command Center</b>\nTelegram integration successfully connected! Bot is ready to send trade signals.")

asyncio.run(main())
