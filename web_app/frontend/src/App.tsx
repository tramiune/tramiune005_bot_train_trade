import React, { useState } from 'react';
import ChartWidget from './components/ChartWidget';
import ControlPanel from './components/ControlPanel';
import TradeHistory from './components/TradeHistory';
import { Activity } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('SOLUSDT');

  return (
    <div className="min-h-screen bg-[#0B0E14] text-gray-200 font-sans p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* Header */}
        <header className="flex items-center justify-between border-b border-gray-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-wide">Quant Command Center</h1>
          </div>
          <div className="text-sm font-mono text-gray-500">
            v1.0.0 | SOL God Mode Active
          </div>
        </header>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Left Column: Chart */}
          <div className="lg:col-span-2 space-y-4">
            
            {/* Tabs */}
            <div className="flex space-x-2">
              {['SOLUSDT', 'BTCUSDT'].map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`px-4 py-2 rounded-md font-semibold text-sm transition-colors ${
                    activeTab === tab 
                      ? 'bg-blue-600 text-white' 
                      : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                  }`}
                >
                  {tab.replace('USDT', '')}
                </button>
              ))}
            </div>

            <ChartWidget symbol={activeTab} />
          </div>

          {/* Right Column: Controls */}
          <div className="space-y-6">
            <ControlPanel />
          </div>
          
        </div>

        {/* Bottom Row: Trades */}
        <div className="mt-8">
          <TradeHistory />
        </div>

      </div>
    </div>
  );
}

export default App;
