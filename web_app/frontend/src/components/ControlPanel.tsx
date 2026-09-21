import React, { useEffect, useState } from 'react';
import { Play, Square, Activity } from 'lucide-react';
import axios from 'axios';

const API_BASE = `http://${window.location.hostname}:8000/api`;

const ControlPanel: React.FC = () => {
    const [status, setStatus] = useState<string>("STOPPED");

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                const res = await axios.get(`${API_BASE}/status`);
                setStatus(res.data.status);
            } catch (e) {
                console.error(e);
            }
        };
        fetchStatus();
        const interval = setInterval(fetchStatus, 5000);
        return () => clearInterval(interval);
    }, []);

    const startBot = async () => {
        try {
            await axios.post(`${API_BASE}/start`);
            setStatus("RUNNING");
        } catch (e) {
            console.error(e);
        }
    };

    const stopBot = async () => {
        try {
            await axios.post(`${API_BASE}/stop`);
            setStatus("STOPPED");
        } catch (e) {
            console.error(e);
        }
    };

    return (
        <div className="flex flex-col space-y-6">
            
            {/* Engine Control */}
            <div className="bg-[#1E222D] rounded-lg p-6 border border-gray-700 shadow-lg">
                <h3 className="text-white font-bold mb-4 flex items-center">
                    <Activity className="w-5 h-5 mr-2 text-blue-500" />
                    System Control
                </h3>
                
                <div className="flex items-center justify-between mb-6">
                    <span className="text-gray-400 text-sm">Engine Status:</span>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                        status === 'RUNNING' ? 'bg-green-900 text-green-400 border border-green-500' : 'bg-red-900 text-red-400 border border-red-500'
                    }`}>
                        {status}
                    </span>
                </div>

                <div className="flex space-x-4">
                    <button 
                        onClick={startBot}
                        disabled={status === 'RUNNING'}
                        className={`flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all ${
                            status === 'RUNNING' 
                                ? 'bg-gray-700 text-gray-500 cursor-not-allowed' 
                                : 'bg-green-600 hover:bg-green-500 text-white shadow-[0_0_15px_rgba(34,197,94,0.3)]'
                        }`}
                    >
                        <Play className="w-4 h-4 mr-2" /> Start Bot
                    </button>
                    <button 
                        onClick={stopBot}
                        disabled={status === 'STOPPED'}
                        className={`flex-1 flex items-center justify-center py-2 rounded-md font-semibold transition-all ${
                            status === 'STOPPED' 
                                ? 'bg-gray-700 text-gray-500 cursor-not-allowed' 
                                : 'bg-red-600 hover:bg-red-500 text-white shadow-[0_0_15px_rgba(239,68,68,0.3)]'
                        }`}
                    >
                        <Square className="w-4 h-4 mr-2" /> Stop Bot
                    </button>
                </div>
            </div>

            {/* Strategy List */}
            <div className="bg-[#1E222D] rounded-lg p-6 border border-gray-700 shadow-lg">
                <h3 className="text-white font-bold mb-4">Active Strategies</h3>
                <div className="space-y-3">
                    
                    <div className="flex justify-between items-center p-3 bg-gray-800 rounded border border-gray-700">
                        <div>
                            <div className="text-gray-300 font-semibold text-sm">SOL God Mode</div>
                            <div className="text-gray-500 text-xs">1H • EMA20/200 • Tue-Thu</div>
                        </div>
                        <div className="text-green-400 font-mono text-sm">+15.0 RR</div>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg border border-gray-700">
                        <div>
                            <div className="text-gray-300 font-semibold text-sm">BTC Trend Pullback</div>
                            <div className="text-gray-500 text-xs">1H • EMA200 • NY Session</div>
                        </div>
                        <div className="text-green-400 font-mono text-sm">+2.0 RR</div>
                    </div>
                </div>
            </div>

        </div>
    );
};

export default ControlPanel;
