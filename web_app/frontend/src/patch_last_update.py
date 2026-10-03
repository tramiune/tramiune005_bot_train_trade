import re

with open("components/ChartWidget.tsx", "r") as f:
    content = f.read()

# 1. Add lastUpdate state
old_state = "    const [activeTradeId, setActiveTradeId] = useState<number | null>(null);"
new_state = "    const [activeTradeId, setActiveTradeId] = useState<number | null>(null);\n    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);"
content = content.replace(old_state, new_state)

# 2. Update state in fetchKlines
old_fetch = """                if (seriesRef.current) {
                    seriesRef.current.setData(uniqueData);"""
                    
new_fetch = """                if (seriesRef.current) {
                    seriesRef.current.setData(uniqueData);
                    setLastUpdate(new Date());"""

content = content.replace(old_fetch, new_fetch)

# 3. Update UI to show last update
old_ui = """                    <span className="flex items-center text-xs text-green-400">
                        <span className="w-2 h-2 rounded-full bg-green-400 mr-2 animate-pulse"></span>
                        Live + Backtest Active
                    </span>"""

new_ui = """                    <span className={`flex items-center text-xs ${lastUpdate && (new Date().getTime() - lastUpdate.getTime() < 10000) ? 'text-green-400' : 'text-orange-400'}`}>
                        <span className={`w-2 h-2 rounded-full mr-2 ${lastUpdate && (new Date().getTime() - lastUpdate.getTime() < 10000) ? 'bg-green-400 animate-pulse' : 'bg-orange-400'}`}></span>
                        {lastUpdate ? `Last tick: ${lastUpdate.toLocaleTimeString()}` : 'Connecting...'}
                    </span>"""
content = content.replace(old_ui, new_ui)

with open("components/ChartWidget.tsx", "w") as f:
    f.write(content)
print("Chart UI patched!")
