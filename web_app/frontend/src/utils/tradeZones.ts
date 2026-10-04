// Series primitive that paints the entry / TP / SL zone of EVERY trade on the chart.
// Only trades inside the visible horizontal range are painted, so panning back through
// hundreds of trades stays cheap. Coordinates are derived from the loaded candle array
// (nearest candle), so trades whose candles are not loaded yet are simply clipped.

export interface ZoneTrade {
    time: number;          // entry time (unix seconds)
    exit_time?: number;    // exit time (unix seconds); undefined while the trade is open
    side: string;
    entry: number;
    sl: number;
    tp: number;
}

type CandleLike = { time: number };

const GREEN = '38, 166, 154';
const RED = '239, 83, 80';

export class TradeZonesPrimitive {
    private _trades: ZoneTrade[] = [];
    private _activeTime: number | null = null;
    private _chart: any = null;
    private _series: any = null;
    private _requestUpdate: (() => void) | null = null;
    private _getCandles: () => CandleLike[];

    constructor(getCandles: () => CandleLike[]) {
        this._getCandles = getCandles;
    }

    attached(param: any) {
        this._chart = param.chart;
        this._series = param.series;
        this._requestUpdate = param.requestUpdate;
    }

    detached() {
        this._chart = null;
        this._series = null;
        this._requestUpdate = null;
    }

    setTrades(trades: ZoneTrade[]) {
        this._trades = trades;
        this._requestUpdate?.();
    }

    setActive(time: number | null) {
        this._activeTime = time;
        this._requestUpdate?.();
    }

    updateAllViews() {}

    paneViews() {
        return [new TradeZonesPaneView(this)];
    }

    // x coordinate (media pixels) for a unix time, or null if it cannot be resolved.
    // Times before the first loaded candle -> -Infinity, after the last -> +Infinity.
    _xOf(time: number, candles: CandleLike[]): number | null {
        if (!this._chart || candles.length === 0) return null;
        if (time < candles[0].time) return -Infinity;
        if (time > candles[candles.length - 1].time) return Infinity;
        let lo = 0, hi = candles.length - 1;
        while (lo < hi) {
            const mid = (lo + hi) >> 1;
            if (candles[mid].time < time) lo = mid + 1; else hi = mid;
        }
        const x = this._chart.timeScale().logicalToCoordinate(lo);
        return x === null || x === undefined ? null : (x as number);
    }

    _draw(scope: any) {
        if (!this._series || !this._chart) return;
        const candles = this._getCandles();
        if (candles.length === 0 || this._trades.length === 0) return;

        const ctx: CanvasRenderingContext2D = scope.context;
        const hr: number = scope.horizontalPixelRatio;
        const vr: number = scope.verticalPixelRatio;
        const width: number = scope.bitmapSize.width;
        const lastTime = candles[candles.length - 1].time;

        for (const t of this._trades) {
            const endTime = t.exit_time ?? lastTime;
            const rawX1 = this._xOf(t.time, candles);
            const rawX2 = this._xOf(endTime, candles);
            if (rawX1 === null || rawX2 === null) continue;
            // Entirely left of the loaded data or right of the last candle -> nothing to draw
            if (rawX1 === Infinity || rawX2 === -Infinity) continue;

            const x1 = (rawX1 === -Infinity ? -10 : rawX1) * hr;
            const x2 = (rawX2 === Infinity ? width / hr + 10 : rawX2) * hr;
            if (x2 < 0 || x1 > width) continue; // not in the visible range

            const yEntry = this._series.priceToCoordinate(t.entry);
            const yTp = this._series.priceToCoordinate(t.tp);
            const ySl = this._series.priceToCoordinate(t.sl);
            if (yEntry === null || yTp === null || ySl === null) continue;

            const active = this._activeTime !== null && this._activeTime === t.time;
            const alpha = active ? 0.28 : 0.14;
            const w = Math.max(x2 - x1, 2 * hr);

            ctx.fillStyle = `rgba(${GREEN}, ${alpha})`;
            ctx.fillRect(x1, Math.min(yEntry, yTp) * vr, w, Math.abs(yTp - yEntry) * vr);
            ctx.fillStyle = `rgba(${RED}, ${alpha})`;
            ctx.fillRect(x1, Math.min(yEntry, ySl) * vr, w, Math.abs(ySl - yEntry) * vr);

            // TP / SL edges and entry line
            ctx.lineWidth = Math.max(1, Math.round(hr));
            ctx.setLineDash([]);
            ctx.strokeStyle = `rgba(${GREEN}, 0.9)`;
            ctx.beginPath(); ctx.moveTo(x1, yTp * vr); ctx.lineTo(x1 + w, yTp * vr); ctx.stroke();
            ctx.strokeStyle = `rgba(${RED}, 0.9)`;
            ctx.beginPath(); ctx.moveTo(x1, ySl * vr); ctx.lineTo(x1 + w, ySl * vr); ctx.stroke();
            ctx.strokeStyle = 'rgba(217, 217, 217, 0.8)';
            ctx.setLineDash([4 * hr, 3 * hr]);
            ctx.beginPath(); ctx.moveTo(x1, yEntry * vr); ctx.lineTo(x1 + w, yEntry * vr); ctx.stroke();
            ctx.setLineDash([]);
        }
    }
}

class TradeZonesPaneView {
    private _source: TradeZonesPrimitive;

    constructor(source: TradeZonesPrimitive) {
        this._source = source;
    }

    zOrder() {
        return 'bottom' as const;
    }

    renderer() {
        const source = this._source;
        return {
            draw(target: any) {
                target.useBitmapCoordinateSpace((scope: any) => source._draw(scope));
            },
        };
    }
}
