import re

for filename in ['web_app/frontend/src/components/ControlPanel.tsx', 'web_app/frontend/src/components/ChartWidget.tsx', 'web_app/frontend/src/components/TradeHistory.tsx']:
    with open(filename, 'r') as f:
        content = f.read()
        
    if 'activeTab: string' not in content:
        # 1. Add activeTab to props
        if 'interface Props' in content:
            content = content.replace('interface Props {', 'interface Props {\n    activeTab: string;')
            content = content.replace('({ symbol, focusedTrade }: Props)', '({ symbol, focusedTrade, activeTab }: Props)')
            content = content.replace('({ onTradeClick, focusedTrade }: Props)', '({ onTradeClick, focusedTrade, activeTab }: Props)')
        else:
            if 'const ControlPanel' in content:
                content = content.replace('const ControlPanel = () => {', 'const ControlPanel = ({ activeTab }: { activeTab: string }) => {')
            
        # 2. Add API_BASE inside the component
        api_base_line = "{\n    const API_BASE = activeTab === 'XRPUSDT' ? '/api/xrp' : '/api/sol';\n"
        
        # We need to replace the first `=> {` after the component name declaration
        if 'ControlPanel' in filename:
            content = content.replace('const ControlPanel = ({ activeTab }: { activeTab: string }) => {', f'const ControlPanel = ({{ activeTab }}: {{ activeTab: string }}) => {api_base_line}')
        elif 'ChartWidget' in filename:
            content = content.replace('({ symbol, focusedTrade, activeTab }: Props) => {', f'({{ symbol, focusedTrade, activeTab }}: Props) => {api_base_line}')
        elif 'TradeHistory' in filename:
            # wait, tradehistory might not use Props interface if it was inline
            pass
            
    with open(filename, 'w') as f:
        f.write(content)

print("Props patched!")
