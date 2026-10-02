const fs = require('fs');
const file = 'frontend/src/components/ChartWidget.tsx';
let content = fs.readFileSync(file, 'utf8');

// Change fetchBacktest API endpoint
content = content.replace(
    'const res = await axios.get(`http://${window.location.hostname}:8000/api/backtest?symbol=${symbol.replace(\'USDT\', \'/USDT\')}`);',
    'const endpoint = symbol === "ETHUSDT" ? "/api/backtest/eth_vwap?symbol=ETH/USDT" : `/api/backtest?symbol=${symbol.replace("USDT", "/USDT")}`;\n            const res = await axios.get(`http://${window.location.hostname}:8000${endpoint}`);'
);

// We also need to map the returned data for ETH which returns {data, markers, metrics} 
// but the current chart expects backtest trades to be an array or something.
// Let's check how trades are handled in ChartWidget.
// The current `fetchBacktest` expects an array of trades.
