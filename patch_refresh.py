import re

with open("web_app/frontend/src/components/ControlPanel.tsx", "r") as f:
    content = f.read()

# Separate fetchBalance
old_fetch = """                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
                
                const balRes = await axios.get(`${API_BASE}/balance`);
                if (balRes.data.status === 'ok') {
                    setBalance(balRes.data.balance);
                } else {
                    setBalance(null); // keys missing or error
                }
            } catch (e) {
                console.error(e);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 15000);
        return () => clearInterval(interval);
    }, []);"""

new_fetch = """                const tgRes = await axios.get(`${API_BASE}/telegram/status`);
                setTgReady(tgRes.data.ready);
            } catch (e) {
                console.error(e);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000); // Poll status every 5s
        return () => clearInterval(interval);
    }, []);

    const fetchBalance = async () => {
        try {
            const balRes = await axios.get(`${API_BASE}/balance`);
            if (balRes.data.status === 'ok') {
                setBalance(balRes.data.balance);
            } else {
                setBalance(null); // keys missing or error
            }
        } catch (e) {
            console.error(e);
        }
    };

    // Initial balance fetch
    useEffect(() => {
        fetchBalance();
    }, []);"""

content = content.replace(old_fetch, new_fetch)

# Add refresh button
old_ui = """                <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-700">
                    <span className="text-gray-400 text-sm">Futures Available:</span>
                    <span className="text-yellow-400 font-bold font-mono">
                        {balance !== null ? `$${balance.toFixed(2)}` : 'N/A'}
                    </span>
                </div>"""

new_ui = """                <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-700">
                    <span className="text-gray-400 text-sm">Futures Available:</span>
                    <div className="flex items-center space-x-2">
                        <span className="text-yellow-400 font-bold font-mono">
                            {balance !== null ? `$${balance.toFixed(2)}` : 'N/A'}
                        </span>
                        <button onClick={fetchBalance} className="text-gray-500 hover:text-white transition-colors" title="Refresh Balance">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                        </button>
                    </div>
                </div>"""

content = content.replace(old_ui, new_ui)

with open("web_app/frontend/src/components/ControlPanel.tsx", "w") as f:
    f.write(content)
