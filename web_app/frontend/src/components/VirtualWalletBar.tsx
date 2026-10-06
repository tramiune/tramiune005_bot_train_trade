import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Wallet, PieChart, ShieldCheck } from 'lucide-react';

interface WalletInfo {
    strategy: string;
    allocation_pct: number;
    balance: number;
    realized_pnl: number;
}

interface WalletsData {
    status: string;
    total_balance: number;
    total_free: number;
    wallets: {
        XRP?: WalletInfo;
        SOL?: WalletInfo;
    };
}

interface Props {
    activeSymbol: string;
    onSelectSymbol: (symbol: string) => void;
}

const VirtualWalletBar: React.FC<Props> = ({ activeSymbol, onSelectSymbol }) => {
    const [data, setData] = useState<WalletsData | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [xrpPct, setXrpPct] = useState(50);
    const [isSaving, setIsSaving] = useState(false);

    const fetchWallets = async () => {
        try {
            // XRP backend is on port 8000 (/api/xrp)
            const res = await axios.get('/api/xrp/wallets');
            if (res.data.status === 'ok') {
                setData(res.data);
                if (res.data.wallets?.XRP?.allocation_pct !== undefined) {
                    setXrpPct(res.data.wallets.XRP.allocation_pct);
                }
            }
        } catch (e) {
            console.error('Failed to fetch virtual wallets', e);
        }
    };

    useEffect(() => {
        fetchWallets();
        const timer = setInterval(fetchWallets, 5000);
        return () => clearInterval(timer);
    }, []);

    const handleSaveAllocation = async () => {
        setIsSaving(true);
        try {
            const solPct = 100 - xrpPct;
            await Promise.all([
                axios.post('/api/xrp/wallets/allocation', { xrp_pct: xrpPct, sol_pct: solPct }),
                axios.post('/api/sol/wallets/allocation', { xrp_pct: xrpPct, sol_pct: solPct })
            ]);
            await fetchWallets();
            setIsEditing(false);
        } catch (e) {
            alert('Lỗi lưu phân bổ ví ảo');
        } finally {
            setIsSaving(false);
        }
    };

    const totalBal = data?.total_balance ?? 0;
    const xrpWallet = data?.wallets?.XRP;
    const solWallet = data?.wallets?.SOL;

    const xrpBal = xrpWallet?.balance ?? 0;
    const solBal = solWallet?.balance ?? 0;
    const xrpPnl = xrpWallet?.realized_pnl ?? 0;
    const solPnl = solWallet?.realized_pnl ?? 0;

    return (
        <div className="bg-gradient-to-r from-slate-900/90 via-[#0e1424]/95 to-slate-900/90 border border-indigo-500/20 shadow-xl rounded-2xl p-4 backdrop-blur-xl">
            <div className="flex flex-col lg:flex-row items-center justify-between gap-4">
                
                {/* 1. Tổng ví Binance Futures */}
                <div className="flex items-center space-x-3.5 w-full lg:w-auto">
                    <div className="p-2.5 bg-amber-500/10 border border-amber-500/30 rounded-xl text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.15)]">
                        <Wallet className="w-5 h-5" />
                    </div>
                    <div>
                        <div className="flex items-center space-x-2">
                            <span className="text-[10px] uppercase tracking-widest text-gray-400 font-bold">Tổng Ví Binance Futures (1 Nick)</span>
                            <span className="inline-flex items-center px-1.5 py-0.2 text-[9px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded">
                                <ShieldCheck className="w-2.5 h-2.5 mr-1" /> Isolated
                            </span>
                        </div>
                        <div className="flex items-baseline space-x-2">
                            <span className="text-xl font-black font-mono text-white tracking-tight">
                                ${totalBal.toFixed(2)} <span className="text-xs font-normal text-gray-400">USDT</span>
                            </span>
                        </div>
                    </div>
                </div>

                <div className="h-10 w-px bg-white/10 hidden lg:block"></div>

                {/* 2. Hai ngăn ví ảo: XRP vs SOL */}
                <div className="grid grid-cols-2 gap-3 w-full lg:w-auto flex-1 max-w-2xl">
                    
                    {/* Ngăn Ví XRP */}
                    <div 
                        onClick={() => onSelectSymbol('XRPUSDT')}
                        className={`cursor-pointer p-3 rounded-xl border transition-all duration-200 relative overflow-hidden ${
                            activeSymbol === 'XRPUSDT' 
                                ? 'bg-blue-600/15 border-blue-500/50 shadow-[0_0_20px_rgba(59,130,246,0.15)] ring-1 ring-blue-500/40' 
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                        }`}
                    >
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-[11px] font-bold text-blue-400 flex items-center">
                                <span className="w-2 h-2 rounded-full bg-blue-500 mr-1.5 animate-pulse"></span>
                                Ví Ảo XRP ({xrpWallet?.allocation_pct ?? 50}%)
                            </span>
                            <span className="text-[10px] text-gray-400 font-mono">Sniper 5m</span>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <span className="text-base font-black font-mono text-white">
                                ${xrpBal.toFixed(2)}
                            </span>
                            <span className={`text-[10px] font-mono font-semibold ${xrpPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                PnL: {xrpPnl >= 0 ? `+${xrpPnl.toFixed(2)}` : xrpPnl.toFixed(2)}$
                            </span>
                        </div>
                    </div>

                    {/* Ngăn Ví SOL */}
                    <div 
                        onClick={() => onSelectSymbol('SOLUSDT')}
                        className={`cursor-pointer p-3 rounded-xl border transition-all duration-200 relative overflow-hidden ${
                            activeSymbol === 'SOLUSDT' 
                                ? 'bg-purple-600/15 border-purple-500/50 shadow-[0_0_20px_rgba(168,85,247,0.15)] ring-1 ring-purple-500/40' 
                                : 'bg-white/[0.02] border-white/10 hover:border-white/20'
                        }`}
                    >
                        <div className="flex items-center justify-between mb-1">
                            <span className="text-[11px] font-bold text-purple-400 flex items-center">
                                <span className="w-2 h-2 rounded-full bg-purple-500 mr-1.5 animate-pulse"></span>
                                Ví Ảo SOL ({solWallet?.allocation_pct ?? 50}%)
                            </span>
                            <span className="text-[10px] text-gray-400 font-mono">Trend 4h</span>
                        </div>
                        <div className="flex items-baseline justify-between">
                            <span className="text-base font-black font-mono text-white">
                                ${solBal.toFixed(2)}
                            </span>
                            <span className={`text-[10px] font-mono font-semibold ${solPnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                PnL: {solPnl >= 0 ? `+${solPnl.toFixed(2)}` : solPnl.toFixed(2)}$
                            </span>
                        </div>
                    </div>

                </div>

                <div className="h-10 w-px bg-white/10 hidden lg:block"></div>

                {/* 3. Nút chỉnh phân bổ % */}
                <div className="w-full lg:w-auto flex justify-end">
                    {isEditing ? (
                        <div className="flex items-center space-x-2 bg-black/40 p-2 rounded-xl border border-indigo-500/30">
                            <div className="text-[10px] font-mono text-gray-300">
                                XRP: <span className="font-bold text-blue-400">{xrpPct}%</span> | SOL: <span className="font-bold text-purple-400">{100 - xrpPct}%</span>
                            </div>
                            <input 
                                type="range" 
                                min="10" 
                                max="90" 
                                step="5" 
                                value={xrpPct} 
                                onChange={(e) => setXrpPct(Number(e.target.value))}
                                className="w-24 accent-indigo-500 cursor-pointer"
                            />
                            <button 
                                onClick={handleSaveAllocation}
                                disabled={isSaving}
                                className="px-2.5 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-[10px] font-bold transition-all"
                            >
                                {isSaving ? '...' : 'Lưu'}
                            </button>
                            <button 
                                onClick={() => setIsEditing(false)}
                                className="px-2 py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[10px] transition-all"
                            >
                                Hủy
                            </button>
                        </div>
                    ) : (
                        <button 
                            onClick={() => setIsEditing(true)}
                            className="flex items-center space-x-1.5 px-3 py-2 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 hover:border-indigo-400/50 rounded-xl text-indigo-300 hover:text-white text-xs font-bold transition-all shadow-sm"
                            title="Điều chỉnh tỷ lệ phân bổ vốn giữa XRP và SOL"
                        >
                            <PieChart className="w-3.5 h-3.5" />
                            <span>Chỉnh Tỷ Lệ Ví</span>
                        </button>
                    )}
                </div>

            </div>
        </div>
    );
};

export default VirtualWalletBar;
