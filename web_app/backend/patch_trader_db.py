import re

with open("web_app/backend/engine/trader.py", "r") as f:
    content = f.read()

old_db = """        try:
            db = SessionLocal()"""
new_db = """        db = None
        try:
            db = SessionLocal()"""
content = content.replace(old_db, new_db)

old_finally = """        finally:
            db.close()"""
new_finally = """        finally:
            if db:
                db.close()"""
content = content.replace(old_finally, new_finally)

with open("web_app/backend/engine/trader.py", "w") as f:
    f.write(content)
print("trader db patched!")
