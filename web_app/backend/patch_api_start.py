import re

with open("web_app/backend/main.py", "r") as f:
    content = f.read()

old_start = """@app.post("/api/start")
async def start_bot():
    if not trader_instance.is_running:
        import asyncio
        trader_instance.is_running = True
        asyncio.create_task(trader_instance.run_loop())
    return {"status": "RUNNING"}"""

new_start = """@app.post("/api/start")
async def start_bot():
    if not trader_instance.is_running:
        trader_instance.is_running = True
        trader_instance.log("Trading Engine set to ACTIVE (Will execute new trades).")
    return {"status": "RUNNING"}"""

content = content.replace(old_start, new_start)

with open("web_app/backend/main.py", "w") as f:
    f.write(content)
print("Start API fixed")
