import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_config = """            priceFormat: {
                type: 'price',
                precision: 4,
                minMove: 0.0001,
            },"""

new_config = """            priceFormat: {
                type: 'price',
                precision: 5,
                minMove: 0.00001,
            },"""

content = content.replace(old_config, new_config)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
