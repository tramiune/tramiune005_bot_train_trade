export function calculateEMA(data: any[], period: number, key: string = 'close') {
    if (data.length === 0) return [];
    
    const k = 2 / (period + 1);
    const emaData = [];
    
    // Calculate first SMA
    let sum = 0;
    for (let i = 0; i < Math.min(period, data.length); i++) {
        sum += data[i][key];
    }
    
    if (data.length < period) return [];
    
    let currentEma = sum / period;
    emaData.push({ time: data[period - 1].time, value: currentEma });
    
    // Subsequent EMAs
    for (let i = period; i < data.length; i++) {
        currentEma = (data[i][key] - currentEma) * k + currentEma;
        emaData.push({ time: data[i].time, value: currentEma });
    }
    
    return emaData;
}
