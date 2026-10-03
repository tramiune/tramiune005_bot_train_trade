import React, { useEffect, useState } from 'react';
import { Play, Square, Activity } from 'lucide-react';
import axios from 'axios';

const API_BASE = `http://${window.location.hostname}:8000/api`;

const ControlPanel: React.FC = () => {
    const [status, setStatus] = useState<string>("STOPPED");
    const [tgReady, setTgReady] = useState<boolean>(false);
    const [balance, setBalance] = useState<number | null>(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await axios.get(`${API_BASE}/status`);
                setStatus(res.data.status);
                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
            } catch (e) {
                console.error(e);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000); // Poll status every 5s
        return () => clearInterval(interval);
    }, []);

    const fetchBalance = async () => {
        try {
            const balRes = await axios.get(`${API_BASE}/balance`);
            if (balRes.data.status === 'ok') {
                setBalance(balRes.data.balance);
            } else {
                setBalance(null); // keys missing or error
            }
        } catch (e) {
            console.error(e);
        }
    };

    // Initial balance fetch
    useEffect(() => {
        fetchBalance();
    }, []);

    const testOrder = async () => {
        try {
            const res = await axios.post(`${API_BASE}/test_order`);
            if (res.data.status === 'ok') {
                alert(res.data.message + "\n\nBạn có thể mở app Binance lên để xem lệnh đang treo nhé!");
            } else {
                alert("Lỗi khi đặt lệnh: " + res.data.message);
            }
        } catch (e) {
            console.error(e);
            alert("Lỗi kết nối máy chủ");
        }
    };

    const startBot = async () => {
        try {
            await axios.post(`${API_BASE}/start`);
            setStatus("RUNNING");
        } catch (e) {
            console.error(e);
        }
    };

    const stopBot = async () => {
        try {
            await axios.post(`${API_BASE}/stop`);
            setStatus("STOPPED");
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="flex flex-col space-y-6">
            
            {/* Engine Control */}
            <div className="bg-[#1E222D] rounded-lg p-6 border border-gray-700 shadow-lg">
                <h3 className="text-white font-bold mb-4 flex items-center justify-between">
                    <div className="flex items-center">
                        <Activity className="w-5 h-5 mr-2 text-blue-500" />
                        System Control
                    </div>
                    <div className={`flex items-center text-xs px-2 py-1 rounded-full border ${tgReady ? 'bg-blue-900/50 text-blue-400 border-blue-500/50' : 'bg-gray-800 text-gray-400 border-gray-600'}`}>
                        <svg className="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.892-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                        {tgReady ? 'TG Ready' : 'TG Disconnected'}
                    </div>
                </h3>
                
                <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-700">
                    <span className="text-gray-400 text-sm">Futures Available:</span>
                    <div className="flex items-center space-x-2">
                        <span className="text-yellow-400 font-bold font-mono">
                            {balance !== null ? `$${balance.toFixed(2)}` : 'N/A'}
                        </span>
                        <button onClick={fetchBalance} className="text-gray-500 hover:text-white transition-colors" title="Refresh Balance">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        </button>
                    </div>
                </div>
                
                <div className="flex items-center justify-between mb-6">
                    <span className="text-gray-400 text-sm">Engine Status:</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        status === 'RUNNING' ? 'bg-green-900 text-green-400 border border-green-500' : 'bg-red-900 text-red-400 border border-red-500'
                    }`}>
                        {status}
                    </span>
                </div>

                <div className="flex space-x-4 mb-4">
                    <button 
                        onClick={startBot}
                        disabled={status === 'RUNNING'}
                        className={`flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all ${
                            status === 'RUNNING' 
                                ? 'bg-gray-700 text-gray-500 cursor-not-allowed' 
                                : 'bg-green-600 hover:bg-green-500 text-white shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                        }`}
                    >
                        <Play className="w-4 h-4 mr-2" /> Start Bot
                    </button>
                    <button 
                        onClick={stopBot}
                        disabled={status === 'STOPPED'}
                        className={`flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all ${
                            status === 'STOPPED' 
                                ? 'bg-gray-700 text-gray-500 cursor-not-allowed' 
                                : 'bg-red-600 hover:bg-red-500 text-white shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                        }`}
                    >
                        <Square className="w-4 h-4 mr-2" /> Stop Bot
                    </button>
                </div>
                
                <button 
                    onClick={testOrder}
                    className="w-full flex items-center justify-center py-2 rounded-md font-semibold transition-all bg-yellow-600 hover:bg-yellow-500 text-white shadow-[0_0_15px_rgba(202,138,4,0.3)]"
                >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    Bắn Thử 1 Lệnh LIMIT
                </button>
            </div>

            {/* Strategy List */}
            <div className="bg-[#1E222D] rounded-lg p-6 border border-gray-700 shadow-lg">
                <h3 className="text-white font-bold mb-4">Active Strategies</h3>
                <div className="space-y-3">
                    
                    <div className="flex justify-between items-center p-3 bg-gray-800 rounded border border-gray-700">
                        <div>
                            <div className="text-gray-300 font-semibold text-sm">SOL God Mode</div>
                            <div className="text-gray-500 text-xs">1H • EMA20/200 • Tue-Thu</div>
                        </div>
                        <div className="text-green-400 font-mono text-sm">+15.0 RR</div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
                        <div>
                            <div className="text-gray-300 font-semibold text-sm">BTC Trend Pullback</div>
                            <div className="text-gray-500 text-xs">1H • EMA200 • NY Session</div>
                        </div>
                        <div className="text-green-400 font-mono text-sm">+2.0 RR</div>
                    </div>
                </div>
            </div>

        </div>
    );
};

export default ControlPanel;
