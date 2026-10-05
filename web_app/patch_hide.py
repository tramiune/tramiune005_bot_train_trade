import re

with open('frontend/src/App.tsx', 'r') as f:
    appContent = f.read()

appContent = appContent.replace("useState('SOLUSDT')", "useState('DOGEUSDT')")
appContent = appContent.replace("['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'DOGEUSDT']", "['DOGEUSDT']")

with open('frontend/src/App.tsx', 'w') as f:
    f.write(appContent)
print("Hide other strategies success")
