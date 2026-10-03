import re

with open("web_app/backend/ws_engine.py", "r") as f:
    content = f.read()

old_loop = """                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)"""
                    
new_loop = """                while True:
                    msg = await ws.recv()
                    import sys
                    print(f"RAW MSG: {msg[:100]}")
                    sys.stdout.flush()
                    data = json.loads(msg)"""

content = content.replace(old_loop, new_loop)

with open("web_app/backend/ws_engine.py", "w") as f:
    f.write(content)
print("WS debug patched!")
