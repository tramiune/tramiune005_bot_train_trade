import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Add cancelOrder function
old_func = """    const testOrder = async () => {"""
new_func = """    const cancelOrders = async () => {
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
        }
    };

    const testOrder = async () => {"""
content = content.replace(old_func, new_func)

# Add the Cancel button
old_ui = """                <button 
                    onClick={testOrder}
                    className="w-full flex items-center justify-center py-2 rounded-md font-semibold transition-all bg-yellow-600 hover:bg-yellow-500 text-white shadow-[0_0_15px_rgba(202,138,4,0.3)]"
                >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                    Bắn Thử 1 Lệnh LIMIT
                </button>"""

new_ui = """                <div className="flex space-x-4">
                    <button 
                        onClick={testOrder}
                        className="flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all bg-yellow-600 hover:bg-yellow-500 text-white shadow-[0_0_15px_rgba(202,138,4,0.3)]"
                    >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" /></svg>
                        Test Lệnh Full
                    </button>
                    <button 
                        onClick={cancelOrders}
                        className="flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all bg-gray-600 hover:bg-gray-500 text-white border border-gray-500"
                    >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                        Hủy Mọi Lệnh
                    </button>
                </div>"""
content = content.replace(old_ui, new_ui)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)

