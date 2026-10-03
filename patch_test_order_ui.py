import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Add testOrder function
old_start = """    const startBot = async () => {"""

new_start = """    const testOrder = async () => {
        try {
            const res = await axios.post(`${API_BASE}/test_order`);
            if (res.data.status === 'ok') {
                alert(res.data.message + "\\n\\nBạn có thể mở app Binance lên để xem lệnh đang treo nhé!");
            } else {
                alert("Lỗi khi đặt lệnh: " + res.data.message);
            }
        } catch (e) {
            console.error(e);
            alert("Lỗi kết nối máy chủ");
        }
    };

    const startBot = async () => {"""

content = content.replace(old_start, new_start)

# Add button UI
old_ui = """                <div className="flex space-x-4">
                    <button 
                        onClick={startBot}"""

new_ui = """                <div className="flex space-x-4 mb-4">
                    <button 
                        onClick={startBot}"""
content = content.replace(old_ui, new_ui)

old_ui2 = """                        <Square className="w-4 h-4 mr-2" /> Stop Bot
                    </button>
                </div>
            </div>"""

new_ui2 = """                        <Square className="w-4 h-4 mr-2" /> Stop Bot
                    </button>
                </div>
                
                <button 
                    onClick={testOrder}
                    className="w-full flex items-center justify-center py-2 rounded-md font-semibold transition-all bg-yellow-600 hover:bg-yellow-500 text-white shadow-[0_0_15px_rgba(202,138,4,0.3)]"
                >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    Bắn Thử 1 Lệnh LIMIT
                </button>
            </div>"""
            
content = content.replace(old_ui2, new_ui2)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)
