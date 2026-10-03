import re

with open("components/ControlPanel.tsx", "r") as f:
    content = f.read()

old_fetch = """        const fetchStatus = async () => {
            try {
                const res = await axios.get(`${API_BASE}/status`);
                setStatus(res.data.status);
                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
            } catch (e) {
                console.error(e);
            }
        };"""

new_fetch = """        const fetchStatus = async () => {
            try {
                const res = await axios.get(`${API_BASE}/status`);
                setStatus(res.data.status);
                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
            } catch (e) {
                console.error(e);
                setStatus("OFFLINE");
            }
        };"""

content = content.replace(old_fetch, new_fetch)

old_ui = """                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        status === 'RUNNING' ? 'bg-green-900 text-green-400 border border-green-500' : 'bg-red-900 text-red-400 border border-red-500'
                    }`}>"""

new_ui = """                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        status === 'RUNNING' ? 'bg-green-900 text-green-400 border border-green-500' : status === 'OFFLINE' ? 'bg-gray-800 text-gray-500 border border-gray-600' : 'bg-red-900 text-red-400 border border-red-500'
                    }`}>"""

content = content.replace(old_ui, new_ui)

with open("components/ControlPanel.tsx", "w") as f:
    f.write(content)
print("ControlPanel patched!")
