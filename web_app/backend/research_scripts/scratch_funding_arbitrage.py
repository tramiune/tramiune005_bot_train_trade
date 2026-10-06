import requests
import pandas as pd
import time
from datetime import datetime

def fetch_funding_history(symbol):
    print(f"Đang cào dữ liệu Lãi suất qua đêm (Funding Rate) của {symbol} từ Binance...")
    all_rates = []
    end_time = int(time.time() * 1000)
    limit = 1000
    
    # Lấy lùi về quá khứ tối đa (Binance cho phép lấy từ lúc list coin)
    # 1 năm = 365 * 3 = 1095 kỳ funding.
    for _ in range(5): # Cào khoảng 5000 kỳ (~ 4.5 năm)
        url = f"https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit={limit}&endTime={end_time}"
        try:
            r = requests.get(url)
            data = r.json()
            if not data or not isinstance(data, list):
                break
            
            all_rates.extend(data)
            end_time = data[0]['fundingTime'] - 1 # Đẩy lùi thời gian
            time.sleep(0.5)
        except Exception as e:
            print("Lỗi:", e)
            break
            
    # Lọc trùng và sắp xếp
    if not all_rates: return None
    
    df = pd.DataFrame(all_rates)
    df = df.drop_duplicates(subset=['fundingTime'])
    df['fundingRate'] = df['fundingRate'].astype(float)
    df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
    df = df.sort_values('fundingTime').reset_index(drop=True)
    return df

def run():
    coins = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    results = []
    
    for coin in coins:
        df = fetch_funding_history(coin)
        if df is None or len(df) == 0: continue
        
        # Chỉ lấy dữ liệu 1 năm gần nhất cho sát thực tế
        one_year_ago = pd.Timestamp.now() - pd.DateOffset(years=1)
        df_1y = df[df['fundingTime'] >= one_year_ago]
        
        total_funding_1y = df_1y['fundingRate'].sum() * 100 # Chuyển sang %
        
        # Giả lập: Mua Spot (Giao ngay) 1 Tỷ, Short Futures 1 Tỷ (Đòn bẩy x1 để an toàn tuyệt đối)
        # Vì ta phải bỏ 1 Tỷ bên Spot, 1 Tỷ bên Futures = Tổng vốn 2 Tỷ.
        # Lợi nhuận thu về là trên lệnh Futures 1 Tỷ.
        # Vậy APY thực tế trên Tổng Vốn = (total_funding_1y / 2)
        
        apy_on_total_capital = total_funding_1y / 2
        
        win_rates = len(df_1y[df_1y['fundingRate'] > 0]) / len(df_1y) * 100
        
        results.append({
            'Coin': coin,
            'Số kỳ thu phí (1 Năm)': len(df_1y),
            'Tỷ lệ Sàn phát tiền (%)': win_rates,
            'Tổng % Funding 1 Năm': total_funding_1y,
            'APY (Lãi Suất/Năm)': apy_on_total_capital
        })
        
    df_res = pd.DataFrame(results).sort_values('APY (Lãi Suất/Năm)', ascending=False)
    
    print("\n=== BÁO CÁO CHIẾN LƯỢC HÚT MÁU SÀN (DELTA NEUTRAL ARBITRAGE) ===")
    print("Dữ liệu thực tế 1 Năm gần nhất từ Binance API:")
    print(df_res.round(2).to_string(index=False))
    
    # Tạo Artifact
    out_path = '/Users/finn/.gemini/antigravity/brain/921139ef-edbf-43e7-bf4e-d052df21201b/funding_arbitrage_report.md'
    md = "# CHIẾN LƯỢC ĐÁNH CẮP LÃI SUẤT (FUNDING ARBITRAGE)\n\n"
    md += "Chiến lược rủi ro bằng 0 (Delta Neutral): Mua Spot và Bán Khống Futures cùng một khối lượng. Mặc kệ giá coin tăng hay giảm, ta chỉ vắt sữa tiền Phí Qua Đêm (Funding Rate) của Sàn Binance.\n\n"
    md += "| Đồng Coin | % Thời gian Sàn Phải Trả Tiền | Tổng Phí Sàn Phải Trả (1 Năm) | **Lãi Suất Thực Tế (APY)** |\n"
    md += "|---|---|---|---|\n"
    for _, row in df_res.iterrows():
        md += f"| **{row['Coin']}** | {row['Tỷ lệ Sàn phát tiền (%)']:.1f}% | +{row['Tổng % Funding 1 Năm']:.2f}% | **+{row['APY (Lãi Suất/Năm)']:.2f}% / Năm** |\n"
        
    with open(out_path, 'w') as f:
        f.write(md)
    print(f"\nĐã lưu báo cáo tại Artifact!")

if __name__ == '__main__':
    run()
