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

export function calculateNadarayaWatson(data: any[], h: number = 8.0, mult: number = 3.0) {
    if (data.length < 500) return { upper: [], lower: [], baseline: [] };
    
    const n = data.length;
    const windowSize = 500;
    const weights = new Float64Array(windowSize);
    let weightSum = 0;
    const twoH2 = 2 * h * h;
    for (let k = 0; k < windowSize; k++) {
        weights[k] = Math.exp(-(k * k) / twoH2);
        weightSum += weights[k];
    }
    
    const out = new Float64Array(n);
    const absDiff = new Float64Array(n);
    
    for (let i = 0; i < n; i++) {
        let sum = 0;
        let wSum = 0;
        const maxK = Math.min(i, windowSize - 1);
        for (let k = 0; k <= maxK; k++) {
            sum += data[i - k].close * weights[k];
            wSum += weights[k];
        }
        out[i] = sum / wSum;
        absDiff[i] = Math.abs(data[i].close - out[i]);
    }
    
    const upper: any[] = [];
    const lower: any[] = [];
    const baseline: any[] = [];
    
    let rollingDiffSum = 0;
    for (let i = 0; i < 499 && i < n; i++) {
        rollingDiffSum += absDiff[i];
    }
    
    for (let i = 499; i < n; i++) {
        rollingDiffSum += absDiff[i] - absDiff[i - 499];
        const mae = (rollingDiffSum / 499) * mult;
        const time = data[i].time;
        baseline.push({ time, value: out[i] });
        upper.push({ time, value: out[i] + mae });
        lower.push({ time, value: out[i] - mae });
    }
    
    return { upper, lower, baseline };
}

export function calculateSupertrend(data: any[], period: number = 17, mult: number = 4.4) {
    if (data.length < period + 2) return { supertrend: [] };
    
    const n = data.length;
    const tr = new Float64Array(n);
    tr[0] = data[0].high - data[0].low;
    for (let i = 1; i < n; i++) {
        const hl = data[i].high - data[i].low;
        const hc = Math.abs(data[i].high - data[i - 1].close);
        const lc = Math.abs(data[i].low - data[i - 1].close);
        tr[i] = Math.max(hl, hc, lc);
    }
    
    const atr = new Float64Array(n);
    atr[0] = tr[0];
    for (let i = 1; i < n; i++) {
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period;
    }
    
    const finalUb = new Float64Array(n);
    const finalLb = new Float64Array(n);
    const trend = new Int8Array(n);
    trend.fill(1);
    
    for (let i = 1; i < n; i++) {
        const hl2 = (data[i].high + data[i].low) / 2;
        const basicUb = hl2 + mult * atr[i];
        const basicLb = hl2 - mult * atr[i];
        
        if (basicUb < finalUb[i - 1] || data[i - 1].close > finalUb[i - 1]) {
            finalUb[i] = basicUb;
        } else {
            finalUb[i] = finalUb[i - 1];
        }
        
        if (basicLb > finalLb[i - 1] || data[i - 1].close < finalLb[i - 1]) {
            finalLb[i] = basicLb;
        } else {
            finalLb[i] = finalLb[i - 1];
        }
        
        if (trend[i - 1] === 1 && data[i].close < finalLb[i]) {
            trend[i] = -1;
        } else if (trend[i - 1] === -1 && data[i].close > finalUb[i]) {
            trend[i] = 1;
        } else {
            trend[i] = trend[i - 1];
        }
    }
    
    const supertrend: any[] = [];
    for (let i = period; i < n; i++) {
        supertrend.push({
            time: data[i].time,
            value: trend[i] === 1 ? finalLb[i] : finalUb[i],
            color: trend[i] === 1 ? '#22c55e' : '#ef4444'
        });
    }
    
    return { supertrend };
}
