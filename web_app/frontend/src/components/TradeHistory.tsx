import React, { useEffect, useState } from 'react';
import axios from 'axios';

const API_BASE = `http://${window.location.hostname}:8000/api`;

const TradeHistory: React.FC = () => {
    const [trades, setTrades] = useState<any[]>([]);

    useEffect(() => {
        const fetchTrades = async () => {
            try {
                const res = await axios.get(`${API_BASE}/trades`);
                setTrades(res.data);
            } catch (e) {
                console.error("Failed to fetch trades", e);
            }
        };
        fetchTrades();
        const interval = setInterval(fetchTrades, 10000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 shadow-lg mt-6">
            <h2 className="text-xl font-bold mb-4 text-white">Recent Trades</h2>
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-gray-400">
                    <thead className="text-xs text-gray-400 uppercase bg-gray-700">
                        <tr>
                            <th className="px-4 py-3">Time</th>
                            <th className="px-4 py-3">Symbol</th>
                            <th className="px-4 py-3">Side</th>
                            <th className="px-4 py-3">Entry</th>
                            <th className="px-4 py-3">SL</th>
                            <th className="px-4 py-3">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {trades.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="px-4 py-4 text-center">No trades yet</td>
                            </tr>
                        ) : (
                            trades.map((trade, idx) => (
                                <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700">
                                    <td className="px-4 py-3">{new Date(trade.entry_time).toLocaleString()}</td>
                                    <td className="px-4 py-3 text-white font-medium">{trade.symbol}</td>
                                    <td className={`px-4 py-3 font-bold ${trade.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>
                                        {trade.side}
                                    </td>
                                    <td className="px-4 py-3">${trade.entry_price.toFixed(4)}</td>
                                    <td className="px-4 py-3">${trade.stop_loss.toFixed(4)}</td>
                                    <td className="px-4 py-3">
                                        <span className={`px-2 py-1 rounded text-xs ${trade.status === 'OPEN' ? 'bg-blue-900 text-blue-300' : 'bg-gray-600 text-gray-300'}`}>
                                            {trade.status}
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
