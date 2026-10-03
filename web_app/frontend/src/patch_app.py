import re

with open("App.tsx", "r") as f:
    content = f.read()

old_layout = """        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
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

            <ChartWidget symbol={activeTab} focusedTrade={focusedTrade} />
          </div>

          <div className="space-y-6">
            <ControlPanel />
          </div>
        </div>"""

new_layout = """        <div className="space-y-6">
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
        </div>"""

content = content.replace(old_layout, new_layout)

with open("App.tsx", "w") as f:
    f.write(content)
