import re
with open("web_app/backend/ws_engine.py", "r") as f:
    content = f.read()

content = content.replace("is_closed = k['x']\n                    if int(time.time()) % 10 == 0:\n                        print(f'Received tick... {candle}')", "is_closed = k['x']")

# add flush=True to prints
content = content.replace("print(", "print(") # no, let's just use sys.stdout.flush()

old_loop = """                    if is_closed:
                        print(f"Candle Closed at {candle['time']}! Saving to DB and triggering Engine...")"""
                        
new_loop = """                    # debug
                    if int(time.time()) % 10 == 0:
                        import sys
                        print(f"WS alive, latest close: {candle['close']}")
                        sys.stdout.flush()

                    if is_closed:
                        import sys
                        print(f"Candle Closed at {candle['time']}! Saving to DB and triggering Engine...")
                        sys.stdout.flush()"""

content = content.replace(old_loop, new_loop)

with open("web_app/backend/ws_engine.py", "w") as f:
    f.write(content)
