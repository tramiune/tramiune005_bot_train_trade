import pandas as pd
import numpy as np

class ETHVWAPRobust:
    def __init__(self):
        self.name = "ETH_VWAP_Robust"
        self.tp_pct = 2.5
        self.sl_pct = 3.0

    def calculate_vwap_bands(self, df):
        # Requires 1m or 5m data
        df['date'] = df['datetime'].dt.date
        df['tp'] = (df['high'] + df['low'] + df['close']) / 3
        df['vol_tp'] = df['volume'] * df['tp']
        
        # Calculate daily cumulative values
        df['cum_vol'] = df.groupby('date')['volume'].cumsum()
        df['cum_vol_tp'] = df.groupby('date')['vol_tp'].cumsum()
        
        # VWAP
        df['vwap'] = df['cum_vol_tp'] / df['cum_vol']
        
        # Variance and Standard Deviation
        df['dev_sq'] = df['volume'] * ((df['tp'] - df['vwap']) ** 2)
        df['cum_dev_sq'] = df.groupby('date')['dev_sq'].cumsum()
        df['variance'] = df['cum_dev_sq'] / df['cum_vol']
        df['sd'] = np.sqrt(df['variance'])
        
        # 2.5 SD Bands
        df['upper_band'] = df['vwap'] + (2.5 * df['sd'])
        df['lower_band'] = df['vwap'] - (2.5 * df['sd'])
        
        # Bandwidth
        df['bandwidth'] = (df['upper_band'] - df['lower_band']) / df['vwap'] * 100
        
        return df

    def analyze(self, df: pd.DataFrame) -> dict:
        if len(df) < 288: # Need at least a day of 5m data
            return {'signal': 'NEUTRAL', 'reason': 'Not enough data'}
            
        df = self.calculate_vwap_bands(df.copy())
        
        current_candle = df.iloc[-1]
        
        # Filter: Bandwidth must be < 5.0% (Prevents trading during apocalyptic crashes/pumps)
        if current_candle['bandwidth'] >= 5.0:
            return {'signal': 'NEUTRAL', 'reason': f'Bandwidth {current_candle["bandwidth"]:.2f}% >= 5.0% (High Volatility)'}
            
        # Avoid the very first hour of the UTC day as VWAP is resetting and unstable
        if current_candle['datetime'].hour == 0:
             return {'signal': 'NEUTRAL', 'reason': 'VWAP resetting (Hour 0)'}
             
        # Mean Reversion Logic
        # LONG if price touched lower band and closed back inside
        if (current_candle['low'] <= current_candle['lower_band']) and \
           (current_candle['close'] > current_candle['lower_band']) and \
           (current_candle['close'] > current_candle['open']):
            return {
                'signal': 'BUY',
                'entry_price': current_candle['close'],
                'tp_price': current_candle['close'] * (1 + self.tp_pct/100),
                'sl_price': current_candle['close'] * (1 - self.sl_pct/100),
                'reason': f'VWAP Lower Band Reversion. BW: {current_candle["bandwidth"]:.2f}%'
            }
            
        # SHORT if price touched upper band and closed back inside
        if (current_candle['high'] >= current_candle['upper_band']) and \
           (current_candle['close'] < current_candle['upper_band']) and \
           (current_candle['close'] < current_candle['open']):
            return {
                'signal': 'SELL',
                'entry_price': current_candle['close'],
                'tp_price': current_candle['close'] * (1 - self.tp_pct/100),
                'sl_price': current_candle['close'] * (1 + self.sl_pct/100),
                'reason': f'VWAP Upper Band Reversion. BW: {current_candle["bandwidth"]:.2f}%'
            }
            
        return {'signal': 'NEUTRAL', 'reason': 'No setup'}
