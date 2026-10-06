import React, { useEffect, useState } from 'react';
import axios from 'axios';

interface ControlPanelProps {
    symbol: string;
}

const ControlPanel: React.FC<ControlPanelProps> = ({ symbol }) => {
    const isSol = symbol === 'SOLUSDT';
    const apiBase = isSol ? '/api/sol' : '/api/xrp';
    const coinLabel = isSol ? 'SOL' : 'XRP';

    const [status, setStatus] = useState<string>('UNKNOWN');
    const [balance, setBalance] = useState<number | null>(null);
    const [balanceStatus, setBalanceStatus] = useState<string>('ok');
    const [allocPct, setAllocPct] = useState<number | null>(null);
    const [totalWallet, setTotalWallet] = useState<number | null>(null);
    const [riskPct, setRiskPct] = useState<number>(10);
    const [tgReady, setTgReady] = useState<boolean>(false);
    
    // UI states
    const [isTesting, setIsTesting] = useState(false);
    const [isCanceling, setIsCanceling] = useState(false);
    const [isSavingSettings, setIsSavingSettings] = useState(false);

    useEffect(() => {
        setBalance(null);
        setBalanceStatus('loading');
        fetchStatus();
        fetchBalance();
        fetchSettings();
        
        const interval = setInterval(() => {
            fetchStatus();
            fetchBalance();
        }, 5000);
        return () => clearInterval(interval);
    }, [symbol]);

    const fetchStatus = async () => {
        try {
            const [statusRes, tgRes] = await Promise.all([
                axios.get(`${apiBase}/status`),
                axios.get(`${apiBase}/telegram/status`)
            ]);
            setStatus(statusRes.data.status);
            setTgReady(tgRes.data.ready);
        } catch (error) {
            setStatus('OFFLINE');
            setTgReady(false);
        }
    };

    const fetchBalance = async () => {
        try {
            const res = await axios.get(`${apiBase}/balance`);
            setBalance(res.data.balance);
            setBalanceStatus(res.data.status || 'ok');
            if (res.data.allocation_pct !== undefined) setAllocPct(res.data.allocation_pct);
            if (res.data.total_balance !== undefined) setTotalWallet(res.data.total_balance);
        } catch (error) {
            console.error('Failed to fetch balance', error);
            setBalance(null);
            setBalanceStatus('error');
        }
    };

    const fetchSettings = async () => {
        try {
            const res = await axios.get(`${apiBase}/settings`);
            setRiskPct(res.data.risk_pct);
        } catch (error) {
            console.error('Failed to fetch settings', error);
        }
    };

    const saveSettings = async () => {
        setIsSavingSettings(true);
        try {
            await axios.post(`${apiBase}/settings`, { risk_pct: riskPct });
            alert(`Đã lưu cấu hình rủi ro ${coinLabel}: ${riskPct}%!`);
        } catch (error) {
            console.error('Failed to save settings', error);
            alert('Lưu thất bại!');
        } finally {
            setIsSavingSettings(false);
        }
    };

    const startBot = async () => {
        await axios.post(`${apiBase}/start`);
        fetchStatus();
    };

    const stopBot = async () => {
        await axios.post(`${apiBase}/stop`);
        fetchStatus();
    };

    const testOrder = async (side: 'LONG' | 'SHORT' = 'LONG') => {
        if (!confirm(`Kích hoạt bắn 1 tín hiệu ${side} ${coinLabel} thử nghiệm tại giá thị trường hiện tại (vận hành đầy đủ y hệt tín hiệu thật)?`)) return;
        
        setIsTesting(true);
        try {
            const res = await axios.post(`${apiBase}/test_order`, { side });
            alert(res.data.message || `Lệnh Test ${side} ${coinLabel} đã được bắn lên Binance & Telegram thành công!`);
        } catch (error: any) {
            alert('Lỗi Test Order: ' + (error.response?.data?.detail || error.message));
        } finally {
            setIsTesting(false);
        }
    };

    const cancelOrders = async () => {
        if (!confirm(`Huỷ TOÀN BỘ vị thế & lệnh ${coinLabel} đang mở trên Binance?`)) return;
        setIsCanceling(true);
        try {
            const res = await axios.post(`${apiBase}/cancel_orders`);
            alert(res.data.message || `Đã huỷ mọi lệnh ${coinLabel}!`);
        } catch (error: any) {
            alert('Lỗi Huỷ lệnh: ' + (error.response?.data?.detail || error.message));
        } finally {
            setIsCanceling(false);
        }
    };

    return (
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 shadow-2xl rounded-2xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
            {/* Left side: Status indicators */}
            <div className="flex items-center space-x-6 w-full md:w-auto justify-between md:justify-start">
                <div className="flex items-center space-x-3">
                    <button 
                        onClick={status === 'RUNNING' ? stopBot : startBot}
                        disabled={status === 'OFFLINE' || status === 'UNKNOWN'}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-all duration-300 focus:outline-none ${status === 'RUNNING' ? 'bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.5)]' : 'bg-gray-700'} ${(status === 'OFFLINE' || status === 'UNKNOWN') ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-300 ${status === 'RUNNING' ? 'translate-x-6' : 'translate-x-1'}`} />
                    </button>
                    <span className={`text-xs font-extrabold tracking-wider ${status === 'RUNNING' ? 'text-green-400 drop-shadow-[0_0_8px_rgba(74,222,128,0.5)]' : 'text-gray-500'}`}>
                        {status === 'RUNNING' ? `${coinLabel} ON` : `${coinLabel} OFF`}
                    </span>
                </div>
                
                <div className="h-8 w-px bg-white/10 hidden md:block"></div>
                
                <div className="flex flex-col items-center md:items-start">
                    <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold mb-0.5">
                        Ví Ảo {coinLabel} {allocPct !== null ? `(${allocPct}%)` : ''}
                    </span>
                    <div className="flex items-center text-sm">
                        {balanceStatus === 'loading' ? (
                            <span className="text-gray-400 font-mono text-xs animate-pulse">Loading...</span>
                        ) : balanceStatus === 'keys_missing' ? (
                            <span className="text-amber-400/90 font-mono text-xs bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/30" title="Chưa nhập API Key cho bot này">Chưa có API Key</span>
                        ) : balance !== null ? (
                            <span className="text-yellow-400 font-mono font-bold drop-shadow-md" title={`Tổng ví Binance: $${totalWallet?.toFixed(2) ?? '---'}`}>
                                ${balance.toFixed(2)}
                            </span>
                        ) : (
                            <span className="text-gray-500 font-mono text-xs">---</span>
                        )}
                        <button onClick={fetchBalance} className="ml-1.5 text-gray-500 hover:text-white transition-colors" title="Làm mới số dư">↻</button>
                    </div>
                </div>
                
                <div className="h-8 w-px bg-white/10 hidden md:block"></div>

                <div className="flex flex-col items-center">
                    <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold mb-1">Telegram</span>
                    <div className="flex items-center space-x-1.5">
                        <span className={`w-2.5 h-2.5 rounded-full ${tgReady ? 'bg-blue-400 shadow-[0_0_8px_rgba(96,165,250,0.8)]' : 'bg-gray-600'}`}></span>
                        <span className={`text-[10px] font-bold ${tgReady ? 'text-blue-400' : 'text-gray-500'}`}>{tgReady ? 'READY' : 'N/A'}</span>
                    </div>
                </div>
            </div>

            {/* Right side: Controls & Settings */}
            <div className="flex flex-col md:flex-row items-center space-y-3 md:space-y-0 md:space-x-4 w-full md:w-auto">
                {/* Risk Setting */}
                <div className="flex items-center bg-black/30 rounded-xl p-1.5 border border-white/5 shadow-inner w-full md:w-auto justify-between">
                    <span className="text-[10px] text-gray-400 uppercase tracking-widest font-semibold px-2">{coinLabel} Risk %</span>
                    <input 
                        type="number"
                        value={riskPct}
                        onChange={(e) => setRiskPct(Number(e.target.value))}
                        className="w-14 bg-transparent text-white font-mono font-bold text-sm text-center outline-none border-b border-transparent focus:border-purple-500 transition-colors mx-1"
                    />
                    <button 
                        onClick={saveSettings}
                        disabled={isSavingSettings}
                        className="bg-purple-600/80 hover:bg-purple-500 text-white text-[10px] uppercase font-bold py-1.5 px-3 rounded-lg transition-colors shadow-lg shadow-purple-900/20"
                    >
                        {isSavingSettings ? '...' : 'Lưu'}
                    </button>
                </div>
                
                <div className="flex space-x-2 w-full md:w-auto">
                    {isSol ? (
                        <>
                            <button 
                                onClick={() => testOrder('LONG')}
                                disabled={isTesting}
                                className={`px-3 py-2 text-xs rounded-xl font-bold tracking-wide transition-all border ${isTesting ? 'opacity-50 cursor-not-allowed' : 'bg-green-500/10 hover:bg-green-500/20 text-green-400 border-green-500/30 hover:border-green-400/50'}`}
                            >
                                {isTesting ? '...' : 'Test BUY'}
                            </button>
                            <button 
                                onClick={() => testOrder('SHORT')}
                                disabled={isTesting}
                                className={`px-3 py-2 text-xs rounded-xl font-bold tracking-wide transition-all border ${isTesting ? 'opacity-50 cursor-not-allowed' : 'bg-orange-500/10 hover:bg-orange-500/20 text-orange-400 border-orange-500/30 hover:border-orange-400/50'}`}
                            >
                                {isTesting ? '...' : 'Test SELL'}
                            </button>
                        </>
                    ) : (
                        <button 
                            onClick={() => testOrder('LONG')}
                            disabled={isTesting}
                            className={`flex-1 md:flex-none px-4 py-2 text-xs rounded-xl font-bold tracking-wide transition-all duration-300 border ${isTesting ? 'bg-yellow-900/30 text-yellow-700/50 border-yellow-900/50 cursor-not-allowed' : 'bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-400 border-yellow-500/30 hover:border-yellow-400/50 hover:shadow-[0_0_15px_rgba(234,179,8,0.2)]'}`}
                        >
                            {isTesting ? 'Testing...' : 'Test Lệnh BUY'}
                        </button>
                    )}
                    <button 
                        onClick={cancelOrders}
                        disabled={isCanceling}
                        className={`flex-1 md:flex-none px-4 py-2 text-xs rounded-xl font-bold tracking-wide transition-all duration-300 border ${isCanceling ? 'bg-red-900/30 text-red-700/50 border-red-900/50 cursor-not-allowed' : 'bg-red-500/10 hover:bg-red-500/20 text-red-400 border-red-500/30 hover:border-red-400/50 hover:shadow-[0_0_15px_rgba(239,68,68,0.2)]'}`}
                    >
                        {isCanceling ? 'Canceling...' : 'Hủy Hết Lệnh'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default ControlPanel;
