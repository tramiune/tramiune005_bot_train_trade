import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_config = """        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            autoscaleInfoProvider"""

new_config = """        const candlestickSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#26a69a',
            downColor: '#ef5350',
            borderVisible: false,
            wickUpColor: '#26a69a',
            wickDownColor: '#ef5350',
            priceFormat: {
                type: 'price',
                precision: 4,
                minMove: 0.0001,
            },
            autoscaleInfoProvider"""

content = content.replace(old_config, new_config)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
