import re
import os

for filename in ['web_app/frontend/src/components/ControlPanel.tsx', 'web_app/frontend/src/components/ChartWidget.tsx', 'web_app/frontend/src/components/TradeHistory.tsx']:
    with open(filename, 'r') as f:
        content = f.read()

    # 1. Add API_BASE logic
    if 'activeTab: string' not in content:
        if 'interface Props' in content:
            content = content.replace('interface Props {', 'interface Props {\n    activeTab: string;')
            content = content.replace('({ symbol, focusedTrade }: Props)', '({ symbol, focusedTrade, activeTab }: Props)')
            content = content.replace('({ onTradeClick, focusedTrade }: Props)', '({ onTradeClick, focusedTrade, activeTab }: Props)')
        else:
            if 'const ControlPanel' in content:
                content = content.replace('const ControlPanel = () => {', 'const ControlPanel = ({ activeTab }: { activeTab: string }) => {')
            elif 'const TradeHistory' in content:
                content = content.replace('focusedTrade?: any}> = ({onTradeClick, focusedTrade}) => {', 'focusedTrade?: any, activeTab: string}> = ({onTradeClick, focusedTrade, activeTab}) => {')
                
        api_base_line = "{\n    const API_BASE = activeTab === 'XRPUSDT' ? '/api/xrp' : '/api/sol';\n"
        if 'ControlPanel' in filename:
            content = content.replace('const ControlPanel = ({ activeTab }: { activeTab: string }) => {', f'const ControlPanel = ({{ activeTab }}: {{ activeTab: string }}) => {api_base_line}')
        elif 'ChartWidget' in filename:
            content = content.replace('({ symbol, focusedTrade, activeTab }: Props) => {', f'({{ symbol, focusedTrade, activeTab }}: Props) => {api_base_line}')
        elif 'TradeHistory' in filename:
            content = content.replace('focusedTrade, activeTab}) => {', f'focusedTrade, activeTab}}) => {api_base_line}')

    # 2. Replace API endpoints
    # e.g. axios.get('/api/status') -> axios.get(`${API_BASE}/status`)
    content = re.sub(r"'/api/([^']*)'", r"`${API_BASE}/\1`", content)
    # also handle double quotes if any
    content = re.sub(r'"/api/([^"]*)"', r"`${API_BASE}/\1`", content)
    
    with open(filename, 'w') as f:
        f.write(content)

