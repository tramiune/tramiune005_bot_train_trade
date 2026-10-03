import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

content = content.replace("setInterval(fetchStatus, 5000)", "setInterval(fetchStatus, 15000)")

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)
