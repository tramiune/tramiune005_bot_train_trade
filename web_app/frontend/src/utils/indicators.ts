export function calculateEMA(data: any[], period: number, key: string = 'close') {
    if (data.length === 0) return [];
    const k = 2 / (period + 1);
    const emaData = [];
    let sum = 0;
    for (let i = 0; i < Math.min(period, data.length); i++) {
        sum += data[i][key];
    }
    if (data.length < period) return [];
    let currentEma = sum / period;
    emaData.push({ time: data[period - 1].time, value: currentEma });
    for (let i = period; i < data.length; i++) {
        currentEma = (data[i][key] - currentEma) * k + currentEma;
        emaData.push({ time: data[i].time, value: currentEma });
    }
    return emaData;
}

export function calculateSMA(data: any[], period: number, key: string = 'close') {
    if (data.length < period) return [];
    const smaData = [];
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j][key];
        }
        smaData.push({ time: data[i].time, value: sum / period });
    }
    return smaData;
}

export function calculateBB(data: any[], period: number = 20, stdDevMult: number = 2.0) {
    if (data.length < period) return { upper: [], lower: [], mid: [] };
    const upper = [];
    const lower = [];
    const mid = [];
    
    for (let i = period - 1; i < data.length; i++) {
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += data[i - j].close;
        }
        const mean = sum / period;
        
        let sumSq = 0;
        for (let j = 0; j < period; j++) {
            const diff = data[i - j].close - mean;
            sumSq += diff * diff;
        }
        const stdDev = Math.sqrt(sumSq / period);
        
        mid.push({ time: data[i].time, value: mean });
        upper.push({ time: data[i].time, value: mean + (stdDev * stdDevMult) });
        lower.push({ time: data[i].time, value: mean - (stdDev * stdDevMult) });
    }
    return { upper, lower, mid };
}

export function calculateATR(data: any[], period: number = 20) {
    if (data.length < 2) return [];
    const atrData = [];
    let trSum = 0;
    const trValues = [];
    
    // First TR requires prev close, so i=0 doesn't have TR
    for (let i = 1; i < data.length; i++) {
        const high = data[i].high;
        const low = data[i].low;
        const prevClose = data[i-1].close;
        
        const tr1 = high - low;
        const tr2 = Math.abs(high - prevClose);
        const tr3 = Math.abs(low - prevClose);
        const tr = Math.max(tr1, tr2, tr3);
        trValues.push(tr);
    }
    
    // Initial ATR is simple average of first 'period' TRs
    if (trValues.length < period) return [];
    
    for (let i = 0; i < period; i++) {
        trSum += trValues[i];
    }
    let currentAtr = trSum / period;
    // atrData matches data[period] (which is index period)
    atrData.push({ time: data[period].time, value: currentAtr });
    
    for (let i = period; i < trValues.length; i++) {
        // SMA of TR for Keltner Channel in this specific strategy
        // Wait, strategy uses rolling mean or Wilder's moving average?
        // df['atr'] = df['tr'].rolling(window=period).mean() -> It's SMA of TR!
        let sum = 0;
        for (let j = 0; j < period; j++) {
            sum += trValues[i - j];
        }
        currentAtr = sum / period;
        atrData.push({ time: data[i+1].time, value: currentAtr });
    }
    
    return atrData;
}

export function calculateKC(data: any[], period: number = 20, mult: number = 1.5) {
    const sma = calculateSMA(data, period, 'close');
    const atr = calculateATR(data, period);
    
    if (sma.length === 0 || atr.length === 0) return { upper: [], lower: [], mid: [] };
    
    const upper = [];
    const lower = [];
    
    // Find intersection of times
    const smaMap = new Map(sma.map(item => [item.time, item.value]));
    
    for (const atrItem of atr) {
        if (smaMap.has(atrItem.time)) {
            const mean = smaMap.get(atrItem.time)!;
            upper.push({ time: atrItem.time, value: mean + (mult * atrItem.value) });
            lower.push({ time: atrItem.time, value: mean - (mult * atrItem.value) });
        }
    }
    
    return { upper, lower, mid: sma };
}
