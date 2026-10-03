import React, { useEffect, useState } from 'react';
import { Play, Square, Activity, Settings } from 'lucide-react';
import axios from 'axios';

const ControlPanel: React.FC = () => {
    const [status, setStatus] = useState<string>('UNKNOWN');
    const [balance, setBalance] = useState<number | null>(null);
    const [riskPct, setRiskPct] = useState<number>(30);
    const [tgReady, setTgReady] = useState<boolean>(false);
    
    // UI states
    const [isTesting, setIsTesting] = useState(false);
    const [isCanceling, setIsCanceling] = useState(false);
    const [isSavingSettings, setIsSavingSettings] = useState(false);

    useEffect(() => {
        fetchStatus();
        fetchBalance();
        fetchSettings();
        
        const interval = setInterval(() => {
            fetchStatus();
        }, 5000);
        return () => clearInterval(interval);
    }, []);

    const fetchStatus = async () => {
        try {
            const res = await axios.get(`/api/status`);
            setStatus(res.data.status);
            setTgReady(res.data.telegram_configured);
        } catch (error) {
            setStatus('OFFLINE');
            setTgReady(false);
        }
    };

    const fetchBalance = async () => {
        try {
            const res = await axios.get(`/api/balance`);
            setBalance(res.data.balance);
        } catch (error) {
            console.error('Failed to fetch balance', error);
        }
    };

    const fetchSettings = async () => {
        try {
            const res = await axios.get(`/api/settings`);
            setRiskPct(res.data.risk_pct);
        } catch (error) {
            console.error('Failed to fetch settings', error);
        }
    };

    const saveSettings = async () => {
        setIsSavingSettings(true);
        try {
            await axios.post(`/api/settings`, { risk_pct: riskPct });
            alert('Đã lưu cấu hình!');
        } catch (error) {
            console.error('Failed to save settings', error);
            alert('Lưu thất bại!');
        } finally {
            setIsSavingSettings(false);
        }
    };

    const startBot = async () => {
        await axios.post(`/api/start`);
        fetchStatus();
    };

    const stopBot = async () => {
        await axios.post(`/api/stop`);
        fetchStatus();
    };

    const testOrder = async () => {
        if (!confirm('Bạn có chắc muốn Test bắn lệnh lên sàn và Telegram không? Lệnh sẽ huỷ sau 10 giây.')) return;
        setIsTesting(true);
        try {
            const res = await axios.post(`/api/test_order`);
            alert(res.data.message || 'Lệnh Test đã được gửi!');
        } catch (error: any) {
            alert('Lỗi Test Order: ' + (error.response?.data?.detail || error.message));
        } finally {
            setIsTesting(false);
        }
    };

    const cancelOrders = async () => {
        if (!confirm('Huỷ TOÀN BỘ lệnh đang mở trên Binance?')) return;
        setIsCanceling(true);
        try {
            const res = await axios.post(`/api/cancel_all`);
            alert(res.data.message || 'Đã huỷ mọi lệnh!');
        } catch (error: any) {
            alert('Lỗi Huỷ lệnh: ' + (error.response?.data?.detail || error.message));
        } finally {
            setIsCanceling(false);
        }
    };

    return (
        <div className="flex flex-col md:flex-row gap-4">
            {/* Cấu Hình Quản Lý Vốn */}
            <div className="bg-[#1E222D] rounded border border-gray-700 p-3 w-full md:w-1/3 flex flex-col justify-between">
                <div className="flex items-center text-sm font-semibold text-gray-300 mb-3">
                    <Settings className="w-4 h-4 mr-1 text-purple-400" />
                    Cấu Hình Vốn
                </div>
                <div className="flex items-center space-x-2">
                    <div className="flex-1">
                        <label className="text-xs text-gray-400 block mb-1">Rủi Ro Lệnh (%)</label>
                        <input 
                            type="number"
                            value={riskPct}
                            onChange={(e) => setRiskPct(Number(e.target.value))}
                            className="w-full bg-gray-800 text-white rounded px-2 py-1 text-sm border border-gray-600 focus:border-purple-500 outline-none"
                        />
                    </div>
                    <div className="pt-5">
                        <button 
                            onClick={saveSettings}
                            disabled={isSavingSettings}
                            className="bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold py-1.5 px-3 rounded"
                        >
                            {isSavingSettings ? 'Đang Lưu...' : 'Lưu'}
                        </button>
                    </div>
                </div>
            </div>

            {/* System Control */}
            <div className="bg-[#1E222D] rounded border border-gray-700 p-3 w-full md:w-2/3 flex flex-col justify-between">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center text-sm font-semibold text-gray-300">
                        <Activity className="w-4 h-4 mr-1 text-blue-500" />
                        System Status
                    </div>
                    <div className="flex space-x-3 text-xs">
                        <div className="flex items-center text-gray-400">
                            <span className="mr-1">Balance:</span>
                            <span className="text-yellow-400 font-mono font-bold">${balance !== null ? balance.toFixed(2) : '---'}</span>
                            <button onClick={fetchBalance} className="ml-1 text-gray-500 hover:text-white">↻</button>
                        </div>
                        <div className="flex items-center">
                            <span className={`w-2 h-2 rounded-full mr-1 ${tgReady ? 'bg-blue-500' : 'bg-gray-500'}`}></span>
                            <span className={tgReady ? 'text-blue-400' : 'text-gray-500'}>TG</span>
                        </div>
                        <div className="flex items-center">
                            <span className={`px-2 rounded-sm font-bold ${status === 'RUNNING' ? 'bg-green-900 text-green-400' : status === 'OFFLINE' ? 'bg-gray-800 text-gray-500' : 'bg-red-900 text-red-400'}`}>
                                {status}
                            </span>
                        </div>
                    </div>
                </div>
                
                <div className="flex space-x-2 mt-2">
                    <div className="flex items-center bg-gray-800 rounded px-3 space-x-2">
                        <span className={`text-xs font-bold ${status === 'RUNNING' ? 'text-green-500' : 'text-gray-500'}`}>
                            {status === 'RUNNING' ? 'BOT ON' : 'BOT OFF'}
                        </span>
                        <button 
                            onClick={status === 'RUNNING' ? stopBot : startBot}
                            disabled={status === 'OFFLINE' || status === 'UNKNOWN'}
                            className={`relative inline-flex h-4 w-8 items-center rounded-full transition-colors focus:outline-none ${status === 'RUNNING' ? 'bg-green-600' : 'bg-gray-600'} ${(status === 'OFFLINE' || status === 'UNKNOWN') ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            <span className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white transition-transform ${status === 'RUNNING' ? 'translate-x-4.5' : 'translate-x-0.5'}`} style={{ transform: status === 'RUNNING' ? 'translateX(1.125rem)' : 'translateX(0.125rem)' }} />
                        </button>
                    </div>

                    <button 
                        onClick={testOrder}
                        disabled={isTesting}
                        className={`flex-1 flex items-center justify-center py-1.5 text-xs rounded font-semibold transition-colors ${isTesting ? 'bg-yellow-900 text-yellow-700 cursor-not-allowed' : 'bg-yellow-600 hover:bg-yellow-500 text-white'}`}
                    >
                        {isTesting ? 'Đang Test...' : 'Test Lệnh'}
                    </button>
                    <button 
                        onClick={cancelOrders}
                        disabled={isCanceling}
                        className={`flex-1 flex items-center justify-center py-1.5 text-xs rounded font-semibold transition-colors border ${isCanceling ? 'bg-gray-800 text-gray-600 border-gray-700 cursor-not-allowed' : 'bg-gray-700 hover:bg-gray-600 text-white border-gray-600'}`}
                    >
                        {isCanceling ? 'Đang Hủy...' : 'Hủy Hết Lệnh'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ControlPanel;
