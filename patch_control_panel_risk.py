import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Add state
old_state = "    const [isCanceling, setIsCanceling] = useState(false);"
new_state = """    const [isCanceling, setIsCanceling] = useState(false);
    const [riskPct, setRiskPct] = useState<number>(30);
    const [leverage, setLeverage] = useState<number>(20);
    const [isSavingSettings, setIsSavingSettings] = useState(false);"""
content = content.replace(old_state, new_state)

# Fetch settings on load
old_effect = """    useEffect(() => {
        fetchStatus();
        fetchTelegramStatus();
        fetchBalance();
        const interval = setInterval(() => {
            fetchStatus();
        }, 3000);
        return () => clearInterval(interval);
    }, []);"""

new_effect = """    const fetchSettings = async () => {
        try {
            const res = await axios.get(`${API_BASE}/settings`);
            setRiskPct(res.data.risk_pct);
            setLeverage(res.data.leverage);
        } catch (e) {
            console.error("Error fetching settings", e);
        }
    };

    const saveSettings = async () => {
        setIsSavingSettings(true);
        try {
            const res = await axios.post(`${API_BASE}/settings`, {
                risk_pct: riskPct,
                leverage: leverage
            });
            if (res.data.status === 'ok') {
                alert("Đã lưu cấu hình thành công!" + (res.data.leverage_updated_on_binance ? " Đã đồng bộ đòn bẩy lên Binance." : " Lỗi đồng bộ đòn bẩy, bạn hãy tự kiểm tra trên app Binance nhé."));
            }
        } catch (e) {
            alert("Lỗi khi lưu cấu hình!");
        } finally {
            setIsSavingSettings(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        fetchTelegramStatus();
        fetchBalance();
        fetchSettings();
        const interval = setInterval(() => {
            fetchStatus();
        }, 3000);
        return () => clearInterval(interval);
    }, []);"""
content = content.replace(old_effect, new_effect)

# Add UI
old_ui = """            {/* Control Buttons */}
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 border border-gray-700">
                <h3 className="text-xl font-bold mb-4 flex items-center">
                    <Activity className="w-5 h-5 mr-2 text-blue-400" /> Control Hub
                </h3>"""

new_ui = """            {/* Settings */}
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 border border-gray-700 mb-6">
                <h3 className="text-xl font-bold mb-4 flex items-center">
                    <svg className="w-5 h-5 mr-2 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg> 
                    Cấu Hình Quản Lý Vốn
                </h3>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">Rủi Ro Mỗi Lệnh (%)</label>
                        <input 
                            type="number" 
                            value={riskPct} 
                            onChange={(e) => setRiskPct(Number(e.target.value))}
                            className="w-full bg-gray-700 text-white rounded p-2 border border-gray-600 focus:outline-none focus:border-purple-500"
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-gray-400 mb-1">Đòn Bẩy (Leverage)</label>
                        <input 
                            type="number" 
                            value={leverage} 
                            onChange={(e) => setLeverage(Number(e.target.value))}
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

            {/* Control Buttons */}
            <div className="bg-gray-800 rounded-lg shadow-xl p-6 border border-gray-700">
                <h3 className="text-xl font-bold mb-4 flex items-center">
                    <Activity className="w-5 h-5 mr-2 text-blue-400" /> Control Hub
                </h3>"""
content = content.replace(old_ui, new_ui)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)
