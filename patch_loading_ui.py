import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Add loading states
old_state = """    const [status, setStatus] = useState<string>("STOPPED");
    const [tgReady, setTgReady] = useState<boolean>(false);
    const [balance, setBalance] = useState<number | null>(null);"""

new_state = """    const [status, setStatus] = useState<string>("STOPPED");
    const [tgReady, setTgReady] = useState<boolean>(false);
    const [balance, setBalance] = useState<number | null>(null);
    const [isTesting, setIsTesting] = useState(false);
    const [isCanceling, setIsCanceling] = useState(false);"""
content = content.replace(old_state, new_state)

# Update functions to use loading states
old_funcs = """    const cancelOrders = async () => {
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

    const testOrder = async () => {
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
    };"""

new_funcs = """    const cancelOrders = async () => {
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
                alert(res.data.message + "\\n\\nBạn có thể mở app Binance lên để xem lệnh đang treo nhé!");
            } else {
                alert("Lỗi khi đặt lệnh: " + res.data.message);
            }
        } catch (e) {
            console.error(e);
            alert("Lỗi kết nối máy chủ");
        } finally {
            setIsTesting(false);
        }
    };"""
content = content.replace(old_funcs, new_funcs)

# Update UI to disable buttons
old_buttons = """                <div className="flex space-x-4">
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

new_buttons = """                <div className="flex space-x-4">
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
                </div>"""
content = content.replace(old_buttons, new_buttons)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)

