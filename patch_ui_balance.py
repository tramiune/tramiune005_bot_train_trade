import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Add balance state
content = content.replace("const [tgReady, setTgReady] = useState<boolean>(false);", "const [tgReady, setTgReady] = useState<boolean>(false);\n    const [balance, setBalance] = useState<number | null>(null);")

# Update fetchStatus to also fetch balance
old_fetch = """                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
            } catch (e) {"""

new_fetch = """                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
                
                const balRes = await axios.get(`${API_BASE}/balance`);
                if (balRes.data.status === 'ok') {
                    setBalance(balRes.data.balance);
                } else {
                    setBalance(null); // keys missing or error
                }
            } catch (e) {"""
content = content.replace(old_fetch, new_fetch)

# Add Balance UI
old_ui = """                <div className="flex items-center justify-between mb-6">
                    <span className="text-gray-400 text-sm">Engine Status:</span>"""

new_ui = """                <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-700">
                    <span className="text-gray-400 text-sm">Futures Available:</span>
                    <span className="text-yellow-400 font-bold font-mono">
                        {balance !== null ? `$${balance.toFixed(2)}` : 'N/A'}
                    </span>
                </div>
                
                <div className="flex items-center justify-between mb-6">
                    <span className="text-gray-400 text-sm">Engine Status:</span>"""
                
content = content.replace(old_ui, new_ui)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)
