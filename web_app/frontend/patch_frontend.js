const fs = require('fs');

// Patch App.tsx
let appContent = fs.readFileSync('src/App.tsx', 'utf-8');
appContent = appContent.replace("['SOLUSDT', 'BTCUSDT', 'ETHUSDT']", "['SOLUSDT', 'BTCUSDT', 'ETHUSDT', 'DOGEUSDT']");
appContent = appContent.replace("v1.0.0 | SOL God Mode Active", "v1.0.0 | DOGE Degen Mode Ready");
fs.writeFileSync('src/App.tsx', appContent);

// Patch ChartWidget.tsx
let chartContent = fs.readFileSync('src/components/ChartWidget.tsx', 'utf-8');
chartContent = chartContent.replace(
    "let url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=1h&limit=1000`;",
    "let url = `https://fapi.binance.com/fapi/v1/klines?symbol=${symbol}&interval=${symbol === 'DOGEUSDT' ? '3m' : '1h'}&limit=1000`;"
);
chartContent = chartContent.replace(
    "const url = `https://api.binance.com/api/v3/klines?symbol=${symbol.replace('/', '')}&interval=1h&limit=1000&endTime=${endTimestamp * 1000}`;",
    "const url = `https://api.binance.com/api/v3/klines?symbol=${symbol.replace('/', '')}&interval=${symbol === 'DOGEUSDT' ? '3m' : '1h'}&limit=1000&endTime=${endTimestamp * 1000}`;"
);
chartContent = chartContent.replace(
    "const wsUrl = `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_1h`;",
    "const wsUrl = `wss://stream.binance.com:9443/ws/${symbol.toLowerCase()}@kline_${symbol === 'DOGEUSDT' ? '3m' : '1h'}`;"
);
chartContent = chartContent.replace(
    "<h3 className=\"text-white font-semibold text-lg\">{symbol.toUpperCase()} - 1H</h3>",
    "<h3 className=\"text-white font-semibold text-lg\">{symbol.toUpperCase()} - {symbol === 'DOGEUSDT' ? '3m (DEGEN MODE)' : '1H'}</h3>"
);
chartContent = chartContent.replace(
    "const res = await axios.get(`http://${window.location.hostname}:8000/api/backtest?symbol=${symbol.replace('USDT', '/USDT')}`);\n            const trades = res.data;",
    `let url = \`http://\${window.location.hostname}:8000/api/backtest?symbol=\${symbol.replace('USDT', '/USDT')}\`;
            if (symbol === 'DOGEUSDT') {
                url = \`http://\${window.location.hostname}:8000/api/backtest/doge_inverse?compounding=true&risk_pct=30.0\`;
            }
            const res = await axios.get(url);
            const trades = symbol === 'DOGEUSDT' ? res.data.data.trades.map(t => ({
                time: t.entry_time / 1000,
                side: t.side,
                entry: t.entry_price,
                sl: t.side === 'LONG' ? t.entry_price * 0.85 : t.entry_price * 1.15,
                tp: t.side === 'LONG' ? t.entry_price * 1.05 : t.entry_price * 0.95,
                exit_time: t.exit_time / 1000,
                pnl: t.pnl,
                balance_after: t.balance_after
            })) : res.data;`
);

// Add custom render for DOGE table
chartContent = chartContent.replace(
    `                                <th className="px-4 py-2">RR</th>
                            </tr>
                        </thead>`,
    `                                <th className="px-4 py-2">{symbol === 'DOGEUSDT' ? 'PnL' : 'RR'}</th>
                                {symbol === 'DOGEUSDT' && <th className="px-4 py-2">Balance</th>}
                            </tr>
                        </thead>`
);
chartContent = chartContent.replace(
    `                                    <td className="px-4 py-2 font-mono text-blue-300">
                                        {((trade.tp - trade.entry) / (trade.entry - trade.sl)).toFixed(1)}
                                    </td>
                                </tr>`,
    `                                    <td className={"px-4 py-2 font-mono " + (symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "text-green-400" : "text-red-400") : "text-blue-300")}>
                                        {symbol === 'DOGEUSDT' ? (trade.pnl > 0 ? "+" : "") + trade.pnl.toFixed(2) + "$" : ((trade.tp - trade.entry) / (trade.entry - trade.sl)).toFixed(1)}
                                    </td>
                                    {symbol === 'DOGEUSDT' && <td className="px-4 py-2 font-mono text-yellow-400 font-bold">\${trade.balance_after?.toFixed(2)}</td>}
                                </tr>`
);

fs.writeFileSync('src/components/ChartWidget.tsx', chartContent);
console.log("Patched React UI for DOGE Compounding");
