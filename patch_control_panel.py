import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Add telegram status state
content = content.replace("const [status, setStatus] = useState<string>(\"STOPPED\");", "const [status, setStatus] = useState<string>(\"STOPPED\");\n    const [tgReady, setTgReady] = useState<boolean>(false);")

# Update fetchStatus to also fetch telegram status
old_fetch = """        const fetchStatus = async () => {
            try {
                const res = await axios.get(`${API_BASE}/status`);
                setStatus(res.data.status);
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
            }
        };"""
content = content.replace(old_fetch, new_fetch)

# Add Telegram icon UI next to System Control
old_ui = """                <h3 className="text-white font-bold mb-4 flex items-center">
                    <Activity className="w-5 h-5 mr-2 text-blue-500" />
                    System Control
                </h3>"""

new_ui = """                <h3 className="text-white font-bold mb-4 flex items-center justify-between">
                    <div className="flex items-center">
                        <Activity className="w-5 h-5 mr-2 text-blue-500" />
                        System Control
                    </div>
                    <div className={`flex items-center text-xs px-2 py-1 rounded-full border ${tgReady ? 'bg-blue-900/50 text-blue-400 border-blue-500/50' : 'bg-gray-800 text-gray-400 border-gray-600'}`}>
                        <svg className="w-3 h-3 mr-1" viewBox="0 0 24 24" fill="currentColor"><path d="M11.944 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.056 0zm4.962 7.224c.1-.002.321.023.465.14a.506.506 0 0 1 .171.325c.016.093.036.306.02.472-.18 1.898-.962 6.502-1.36 8.627-.168.9-.499 1.201-.82 1.23-.696.065-1.225-.46-1.9-.902-1.056-.693-1.653-1.124-2.678-1.8-1.185-.78-.417-1.21.258-1.91.177-.184 3.247-2.977 3.307-3.23.007-.032.014-.15-.056-.212s-.174-.041-.249-.024c-.106.024-1.793 1.14-5.061 3.345-.48.33-.913.49-1.302.48-.428-.008-1.252-.241-1.865-.44-.752-.245-1.349-.374-1.297-.789.027-.216.325-.437.892-.663 3.498-1.524 5.83-2.529 6.998-3.014 3.332-1.386 4.025-1.627 4.476-1.635z"/></svg>
                        {tgReady ? 'TG Ready' : 'TG Disconnected'}
                    </div>
                </h3>"""
                
content = content.replace(old_ui, new_ui)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)
