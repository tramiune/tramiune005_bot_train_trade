import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

funcs = """    const fetchSettings = async () => {
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
        fetchSettings();
    }, []);"""

content = content.replace("    const fetchBalance = async () => {", funcs + "\n\n    const fetchBalance = async () => {")

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)

