import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Remove state
content = content.replace("    const [leverage, setLeverage] = useState<number>(20);\n", "")

# Update fetch
old_fetch = """            setRiskPct(res.data.risk_pct);
            setLeverage(res.data.leverage);"""
new_fetch = """            setRiskPct(res.data.risk_pct);"""
content = content.replace(old_fetch, new_fetch)

# Update post
old_post = """            const res = await axios.post(`${API_BASE}/settings`, {
                risk_pct: riskPct,
                leverage: leverage
            });
            if (res.data.status === 'ok') {
                alert("Đã lưu cấu hình thành công!" + (res.data.leverage_updated_on_binance ? " Đã đồng bộ đòn bẩy lên Binance." : " Lỗi đồng bộ đòn bẩy, bạn hãy tự kiểm tra trên app Binance nhé."));
            }"""
new_post = """            const res = await axios.post(`${API_BASE}/settings`, {
                risk_pct: riskPct
            });
            if (res.data.status === 'ok') {
                alert("Đã lưu tỷ lệ rủi ro thành công! Đòn bẩy sẽ được Bot tự động tính toán lúc vào lệnh.");
            }"""
content = content.replace(old_post, new_post)

# Remove input box
old_input = """                    <div>
                        <label className="block text-sm text-gray-400 mb-1">Đòn Bẩy (Leverage)</label>
                        <input 
                            type="number" 
                            value={leverage} 
                            onChange={(e) => setLeverage(Number(e.target.value))}
                            className="w-full bg-gray-700 text-white rounded p-2 border border-gray-600 focus:outline-none focus:border-purple-500"
                        />
                    </div>"""
content = content.replace(old_input, "")

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)

