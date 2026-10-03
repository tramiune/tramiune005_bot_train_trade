import React, { useState } from 'react';
import ChartWidget from './components/ChartWidget';
import ControlPanel from './components/ControlPanel';
import TradeHistory from './components/TradeHistory';
import { Activity } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('DOGEUSDT');
  const [focusedTrade, setFocusedTrade] = useState<any>(null);

  return (
    <div className="min-h-screen bg-[#0B0E14] text-gray-200 font-sans p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="flex items-center justify-between border-b border-gray-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-wide">Quant Command Center</h1>
          </div>
          <div className="text-sm font-mono text-gray-500">
            v1.0.0 | DOGE Degen Mode Ready
          </div>
        </header>

        <div className="space-y-6">
          <ControlPanel />
          
          <div className="space-y-4">
            <div className="flex space-x-2">
              {['DOGEUSDT'].map((tab) => (
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

            <div className="w-full">
              <ChartWidget symbol={activeTab} focusedTrade={focusedTrade} />
            </div>
          </div>
        </div>

        <div className="mt-8">
          <TradeHistory onTradeClick={(trade: any) => setFocusedTrade(trade)} focusedTrade={focusedTrade} />
        </div>
      </div>
    </div>
  );
}

export default App;
