import re

with open("web_app/frontend/src/components/ChartWidget.tsx", "r") as f:
    content = f.read()

old_td = """                                    <td className={"px-4 py-2 font-mono " + (symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "text-green-400" : "text-red-400") : "text-blue-300")}>
                                        {symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "+" : "") + trade.pnl.toFixed(2) + "$" : ((trade.tp - trade.entry) / (trade.entry - trade.sl)).toFixed(1)}
                                    </td>"""

new_td = """                                    <td className={"px-4 py-2 font-mono " + (symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "text-green-400" : (trade.pnl < 0 ? "text-red-400" : "text-gray-400")) : "text-blue-300")}>
                                        {symbol === 'DOGEUSDT' ? (trade.pnl != null ? ((trade.pnl > 0 ? "+" : "") + trade.pnl.toFixed(2) + "$") : "OPEN") : ((trade.tp - trade.entry) / (trade.entry - trade.sl)).toFixed(1)}
                                    </td>"""

content = content.replace(old_td, new_td)

with open("web_app/frontend/src/components/ChartWidget.tsx", "w") as f:
    f.write(content)
