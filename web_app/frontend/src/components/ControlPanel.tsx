import React, { useEffect, useState } from 'react';
import { Play, Square, Activity } from 'lucide-react';
import axios from 'axios';

const API_BASE = `http://${window.location.hostname}:8000/api`;

const ControlPanel: React.FC = () => {
    const [status, setStatus] = useState<string>("STOPPED");
    const [tgReady, setTgReady] = useState<boolean>(false);
    const [balance, setBalance] = useState<number | null>(null);
    const [isTesting, setIsTesting] = useState(false);
    const [isCanceling, setIsCanceling] = useState(false);
    const [riskPct, setRiskPct] = useState<number>(30);
    const [isSavingSettings, setIsSavingSettings] = useState(false);

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

    const fetchSettings = async () => {
        try {
            const res = await axios.get(`${API_BASE}/settings`);
            setRiskPct(res.data.risk_pct);
        } catch (e) {
            console.error("Error fetching settings", e);
        }
    };

    const saveSettings = async () => {
        setIsSavingSettings(true);
        try {
            const res = await axios.post(`${API_BASE}/settings`, {
                risk_pct: riskPct
            });
            if (res.data.status === 'ok') {
                alert("Đã lưu tỷ lệ rủi ro thành công! Đòn bẩy sẽ được Bot tự động tính toán lúc vào lệnh.");
            }
        } catch (e) {
            alert("Lỗi khi lưu cấu hình!");
        } finally {
            setIsSavingSettings(false);
        }
    };

    useEffect(() => {
        fetchSettings();
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

    const cancelOrders = async () => {
        if (isCanceling) return;
        setIsCanceling(true);
        try {
            const res = await axios.post(`${API_BASE}/cancel_orders`);
            if (res.data.status === 'ok') {
                alert(res.data.message);
            } else {
                alert("Lỗi khi hủy lệnh: " + res.data.message);
            }
        } catch (e) {
            console.error(e);
            alert("Lỗi kết nối máy chủ");
        } finally {
            setIsCanceling(false);
        }
    };

    const testOrder = async () => {
        if (isTesting) return;
        setIsTesting(true);
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
        } finally {
            setIsTesting(false);
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
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Settings */}
            <div className="bg-[#1E222D] rounded-lg shadow-xl p-6 border border-gray-700">
                <h3 className="text-white font-bold mb-4 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg> 
                    Cấu Hình Quản Lý Vốn
                </h3>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">Rủi Ro Mỗi Lệnh (% tài khoản)</label>
                        <input 
                            type="number" 
                            value={riskPct} 
                            onChange={(e) => setRiskPct(Number(e.target.value))}
                            className="w-full bg-gray-700 text-white rounded p-2 border border-gray-600 focus:outline-none focus:border-purple-500"
                        />
                    </div>

                    <button 
                        onClick={saveSettings}
                        disabled={isSavingSettings}
                        className="w-full bg-purple-600 hover:bg-purple-500 text-white font-bold py-2 px-4 rounded transition-colors"
                    >
                        {isSavingSettings ? 'Đang Lưu...' : 'Lưu Cấu Hình'}
                    </button>
                </div>
            </div>

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
                
                <div className="flex space-x-4">
                    <button 
                        onClick={testOrder}
                        disabled={isTesting}
                        className={`flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all shadow-[0_0_15px_rgba(202,138,4,0.3)] ${
                            isTesting ? 'bg-yellow-800 text-yellow-500 cursor-not-allowed' : 'bg-yellow-600 hover:bg-yellow-500 text-white'
                        }`}
                    >
                        {isTesting ? (
                            <svg className="animate-spin w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                        ) : (
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                        )}
                        {isTesting ? 'Đang Bắn...' : 'Test Lệnh Full'}
                    </button>
                    <button 
                        onClick={cancelOrders}
                        disabled={isCanceling}
                        className={`flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all border ${
                            isCanceling ? 'bg-gray-800 text-gray-500 border-gray-700 cursor-not-allowed' : 'bg-gray-600 hover:bg-gray-500 text-white border-gray-500'
                        }`}
                    >
                        {isCanceling ? (
                            <svg className="animate-spin w-4 h-4 mr-2" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                        ) : (
                            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                        )}
                        {isCanceling ? 'Đang Hủy...' : 'Hủy Mọi Lệnh'}
                    </button>
                </div>
            </div>

        </div>
    );
};

export default ControlPanel;
