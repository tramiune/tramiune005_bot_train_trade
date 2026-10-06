import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface TradeHistoryProps {
    onTradeClick?: (trade: any) => void;
    focusedTrade?: any;
    symbol?: string;
}

const TradeHistory: React.FC<TradeHistoryProps> = ({ onTradeClick, focusedTrade, symbol = 'XRPUSDT' }) => {
    const [trades, setTrades] = useState<any[]>([]);
    const isSol = symbol === 'SOLUSDT';
    const apiBase = isSol ? '/api/sol' : '/api/xrp';

    useEffect(() => {
        const fetchTrades = async () => {
            try {
                const res = await axios.get(`${apiBase}/trades`);
                const targetSymbol = symbol.replace('USDT', '/USDT');
                const filtered = (res.data || []).filter((t: any) => 
                    t.symbol && !t.symbol.includes('DOGE') && t.symbol === targetSymbol
                );
                setTrades(filtered);
            } catch (e) {
                console.error("Failed to fetch trades", e);
            }
        };
        fetchTrades();
        const interval = setInterval(fetchTrades, 5000);
        return () => clearInterval(interval);
    }, [symbol]);

    const wins = trades.filter(t => t.pnl && t.pnl > 0).length;
    const losses = trades.filter(t => t.pnl && t.pnl <= 0).length;
    const winrate = trades.length > 0 ? ((wins / trades.length) * 100).toFixed(1) : '0.0';

    return (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 shadow-lg mt-6">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-white">Recent Trades</h2>
                <div className="flex gap-4 text-sm font-medium">
                    <span className="text-gray-400">Total: <span className="text-white">{trades.length}</span></span>
                    <span className="text-green-400">Wins: {wins}</span>
                    <span className="text-red-400">Losses: {losses}</span>
                    <span className="text-blue-400">Win Rate: {winrate}%</span>
                </div>
            </div>
            
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                <table className="w-full text-left text-sm text-gray-400 relative">
                    <thead className="text-xs text-gray-400 uppercase bg-gray-700 sticky top-0">
                        <tr>
                            <th className="px-4 py-3">STT</th>
                            <th className="px-4 py-3">Time</th>
                            <th className="px-4 py-3">Symbol</th>
                            <th className="px-4 py-3">Side</th>
                            <th className="px-4 py-3">Entry</th>
                            <th className="px-4 py-3">Exit</th>
                            <th className="px-4 py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-4 py-4 text-center">No trades yet</td>
                            </tr>
                        ) : (
                            trades.map((trade, idx) => (
                                <tr key={idx} onClick={() => onTradeClick && onTradeClick(trade)} className={`border-b border-gray-700 cursor-pointer ${focusedTrade?.id === trade.id ? "bg-yellow-900/50 outline outline-1 outline-yellow-500" : "hover:bg-gray-700"}`}>
                                    <td className="px-4 py-3 text-gray-500">{trades.length - idx}</td>
                                    <td className="px-4 py-3">{new Date(trade.entry_time).toLocaleString()}</td>
                                    <td className="px-4 py-3 text-white font-medium">{trade.symbol}</td>
                                    <td className={`px-4 py-3 font-bold ${trade.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                                        {trade.side}
                                    </td>
                                    <td className="px-4 py-3">${trade.entry_price?.toFixed(5) || '0.00000'}</td>
                                    <td className={`px-4 py-3 font-medium ${trade.pnl > 0 ? 'text-green-400' : trade.pnl < 0 ? 'text-red-400' : ''}`}>
                                        {trade.exit_price ? `$${trade.exit_price.toFixed(5)}` : '-'}
                                    </td>
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 rounded text-xs ${trade.status === 'OPEN' ? 'bg-blue-900 text-blue-300' : trade.pnl > 0 ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'}`}>
                                            {trade.status === 'OPEN' ? 'OPEN' : trade.pnl > 0 ? 'WIN' : 'LOSS'}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default TradeHistory;
