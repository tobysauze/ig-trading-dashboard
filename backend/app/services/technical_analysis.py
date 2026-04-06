import pandas as pd
import numpy as np
import ta
from dataclasses import dataclass, field
from app.models.instrument_universe import MARKET_THRESHOLDS


@dataclass
class TechnicalIndicators:
    rsi: float = 0
    macd: float = 0
    macd_signal: float = 0
    macd_histogram: float = 0
    bb_upper: float = 0
    bb_middle: float = 0
    bb_lower: float = 0
    bb_width: float = 0
    sma_20: float = 0
    sma_50: float = 0
    ema_12: float = 0
    ema_26: float = 0
    ema_20: float = 0
    ema_20_slope: float = 0
    atr: float = 0
    stoch_rsi_k: float = 0
    stoch_rsi_d: float = 0
    adx: float = 0
    plus_di: float = 0
    minus_di: float = 0
    obv: float = 0
    obv_sma: float = 0
    roc_10: float = 0
    dist_sma20: float = 0
    dist_sma50: float = 0
    consecutive_candles: int = 0
    atr_move_ratio: float = 0
    regime: str = "unknown"
    regime_confidence: float = 0
    hurst: float = 0.5
    support: float = 0
    resistance: float = 0
    fib_levels: dict = field(default_factory=dict)
    pivot: float = 0
    r1: float = 0
    r2: float = 0
    s1: float = 0
    s2: float = 0
    bullish_divergence_rsi: bool = False
    bearish_divergence_rsi: bool = False
    bullish_divergence_macd: bool = False
    bearish_divergence_macd: bool = False
    accumulation: str = "neutral"
    volume_trend: float = 1.0
    volume_up_ratio: float = 0.5


def _safe_last(series, default=0):
    if series is None or len(series) == 0:
        return default
    val = series.iloc[-1]
    return float(val) if not pd.isna(val) else default


def compute_indicators(df: pd.DataFrame, market_type: str = "share") -> TechnicalIndicators:
    ti = TechnicalIndicators()
    thresholds = MARKET_THRESHOLDS.get(market_type, MARKET_THRESHOLDS["share"])

    if df.empty or len(df) < 50:
        return ti

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    ti.rsi = _safe_last(ta.momentum.RSIIndicator(close, window=14).rsi())

    macd_ind = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    ti.macd = _safe_last(macd_ind.macd())
    ti.macd_signal = _safe_last(macd_ind.macd_signal())
    ti.macd_histogram = _safe_last(macd_ind.macd_diff())

    bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
    ti.bb_upper = _safe_last(bb.bollinger_hband())
    ti.bb_middle = _safe_last(bb.bollinger_mavg())
    ti.bb_lower = _safe_last(bb.bollinger_lband())
    if ti.bb_middle > 0:
        ti.bb_width = (ti.bb_upper - ti.bb_lower) / ti.bb_middle

    ti.sma_20 = _safe_last(ta.trend.SMAIndicator(close, window=20).sma_indicator())
    ti.sma_50 = _safe_last(ta.trend.SMAIndicator(close, window=50).sma_indicator())
    ti.ema_12 = _safe_last(ta.trend.EMAIndicator(close, window=12).ema_indicator())
    ti.ema_26 = _safe_last(ta.trend.EMAIndicator(close, window=26).ema_indicator())
    ema20_series = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    ti.ema_20 = _safe_last(ema20_series)

    if len(ema20_series) >= 6 and ema20_series.iloc[-6] != 0:
        ti.ema_20_slope = (ema20_series.iloc[-1] - ema20_series.iloc[-6]) / ema20_series.iloc[-6] * 100
    else:
        ti.ema_20_slope = 0

    ti.atr = _safe_last(ta.volatility.AverageTrueRange(high, low, close, window=14).average_true_range())

    stoch_rsi = ta.momentum.StochRSIIndicator(close, window=14, smooth1=3, smooth2=3)
    ti.stoch_rsi_k = _safe_last(stoch_rsi.stochrsi_k())
    ti.stoch_rsi_d = _safe_last(stoch_rsi.stochrsi_d())

    adx_ind = ta.trend.ADXIndicator(high, low, close, window=14)
    ti.adx = _safe_last(adx_ind.adx())
    ti.plus_di = _safe_last(adx_ind.adx_pos())
    ti.minus_di = _safe_last(adx_ind.adx_neg())

    obv_series = ta.volume.OnBalanceVolumeIndicator(close, volume).on_balance_volume()
    ti.obv = _safe_last(obv_series)
    ti.obv_sma = _safe_last(obv_series.rolling(20).mean())

    ti.roc_10 = _safe_last(ta.momentum.ROCIndicator(close, window=10).roc())

    if ti.sma_20 > 0:
        ti.dist_sma20 = (close.iloc[-1] - ti.sma_20) / ti.sma_20 * 100
    if ti.sma_50 > 0:
        ti.dist_sma50 = (close.iloc[-1] - ti.sma_50) / ti.sma_50 * 100

    # Consecutive candles
    consec = 0
    for i in range(len(df) - 1, max(len(df) - 20, 0), -1):
        if i == 0:
            break
        if close.iloc[i] > close.iloc[i - 1]:
            consec = consec + 1 if consec > 0 else 1
        elif close.iloc[i] < close.iloc[i - 1]:
            consec = consec - 1 if consec < 0 else -1
        else:
            break
    ti.consecutive_candles = consec

    # ATR move ratio
    if ti.atr > 0 and len(df) >= 2:
        move = abs(close.iloc[-1] - close.iloc[-2])
        ti.atr_move_ratio = move / ti.atr

    # Support / Resistance
    ti.support, ti.resistance = _find_support_resistance(df, ti.atr)

    # Fibonacci
    ti.fib_levels = _fibonacci_retracement(df)

    # Pivot points
    if len(df) >= 2:
        prev_h = high.iloc[-2]
        prev_l = low.iloc[-2]
        prev_c = close.iloc[-2]
        ti.pivot = (prev_h + prev_l + prev_c) / 3
        ti.r1 = 2 * ti.pivot - prev_l
        ti.r2 = ti.pivot + (prev_h - prev_l)
        ti.s1 = 2 * ti.pivot - prev_h
        ti.s2 = ti.pivot - (prev_h - prev_l)

    # Divergence
    ti.bullish_divergence_rsi, ti.bearish_divergence_rsi = _detect_divergence(close, pd.Series(ti.rsi if isinstance(ti.rsi, list) else [ti.rsi] * len(close)), 30)
    ti.bullish_divergence_macd, ti.bearish_divergence_macd = _detect_divergence(close, pd.Series([ti.macd_histogram] * len(close)), 30)

    # Volume profile
    if len(df) >= 20 and volume.iloc[-20:].sum() > 0:
        up_vol = sum(volume.iloc[i] for i in range(-20, 0) if close.iloc[i] > close.iloc[max(i - 1, -len(df))])
        ratio = up_vol / volume.iloc[-20:].sum()
        ti.volume_up_ratio = ratio
        if ratio > 0.6:
            ti.accumulation = "accumulation"
        elif ratio < 0.4:
            ti.accumulation = "distribution"
        else:
            ti.accumulation = "neutral"

    if len(df) >= 20:
        recent_vol = volume.iloc[-3:].mean()
        hist_vol = volume.iloc[-20:].mean()
        ti.volume_trend = recent_vol / hist_vol if hist_vol > 0 else 1.0

    # Market regime
    ti.regime, ti.regime_confidence, ti.hurst = _detect_regime(df, thresholds, ti)

    return ti


def _find_support_resistance(df: pd.DataFrame, atr: float) -> tuple[float, float]:
    close = df["close"].iloc[-1]
    highs = df["high"].values
    lows = df["low"].values

    if atr <= 0:
        atr = close * 0.01

    bin_size = atr * 0.3
    support_bins = {}
    resistance_bins = {}

    window = min(60, len(df))
    for i in range(len(df) - window, len(df)):
        low_bin = round(lows[i] / bin_size) * bin_size
        high_bin = round(highs[i] / bin_size) * bin_size
        weight = 2 if i >= len(df) - 20 else 1
        if low_bin < close:
            support_bins[low_bin] = support_bins.get(low_bin, 0) + weight
        if high_bin > close:
            resistance_bins[high_bin] = resistance_bins.get(high_bin, 0) + weight

    support_levels = [(level, count) for level, count in support_bins.items() if count >= 2]
    resistance_levels = [(level, count) for level, count in resistance_bins.items() if count >= 2]

    support = max(support_levels, key=lambda x: x[1])[0] if support_levels else df["low"].iloc[-window:].min()
    resistance = min(resistance_levels, key=lambda x: x[1])[0] if resistance_levels else df["high"].iloc[-window:].max()

    return float(support), float(resistance)


def _fibonacci_retracement(df: pd.DataFrame) -> dict:
    window = min(50, len(df))
    recent = df.iloc[-window:]
    high = recent["high"].max()
    low = recent["low"].min()
    high_idx = recent["high"].idxmax()
    low_idx = recent["low"].idxmin()

    diff = high - low
    if high_idx > low_idx:
        return {
            "0%": high, "23.6%": high - 0.236 * diff, "38.2%": high - 0.382 * diff,
            "50%": high - 0.5 * diff, "61.8%": high - 0.618 * diff,
            "78.6%": high - 0.786 * diff, "100%": low,
        }
    else:
        return {
            "0%": low, "23.6%": low + 0.236 * diff, "38.2%": low + 0.382 * diff,
            "50%": low + 0.5 * diff, "61.8%": low + 0.618 * diff,
            "78.6%": low + 0.786 * diff, "100%": high,
        }


def _detect_divergence(price: pd.Series, indicator: pd.Series, lookback: int = 30) -> tuple[bool, bool]:
    if len(price) < lookback + 5 or len(indicator) < lookback + 5:
        return False, False

    p = price.iloc[-lookback:]
    ind = indicator.iloc[-lookback:]

    swing_window = 3
    price_lows = []
    price_highs = []
    ind_lows = []
    ind_highs = []

    for i in range(swing_window, len(p) - swing_window):
        if p.iloc[i] == p.iloc[i - swing_window:i + swing_window + 1].min():
            price_lows.append((i, p.iloc[i]))
        if p.iloc[i] == p.iloc[i - swing_window:i + swing_window + 1].max():
            price_highs.append((i, p.iloc[i]))
        if not pd.isna(ind.iloc[i]):
            if ind.iloc[i] == ind.iloc[i - swing_window:i + swing_window + 1].min():
                ind_lows.append((i, ind.iloc[i]))
            if ind.iloc[i] == ind.iloc[i - swing_window:i + swing_window + 1].max():
                ind_highs.append((i, ind.iloc[i]))

    bullish = False
    bearish = False

    if len(price_lows) >= 2 and len(ind_lows) >= 2:
        if price_lows[-1][1] < price_lows[-2][1] and ind_lows[-1][1] > ind_lows[-2][1]:
            bullish = True

    if len(price_highs) >= 2 and len(ind_highs) >= 2:
        if price_highs[-1][1] > price_highs[-2][1] and ind_highs[-1][1] < ind_highs[-2][1]:
            bearish = True

    return bullish, bearish


def _detect_regime(df: pd.DataFrame, thresholds: dict, ti: TechnicalIndicators) -> tuple[str, float, float]:
    votes = {"trending": 0, "ranging": 0, "volatile": 0}

    adx_str = thresholds.get("adx_strong", 25)
    adx_weak = thresholds.get("adx_weak", 18)

    if ti.adx > adx_str:
        votes["trending"] += 2
    elif ti.adx < adx_weak:
        votes["ranging"] += 2

    bb_vol = thresholds.get("bb_volatile", 0.05)
    bb_trend = thresholds.get("bb_trending", 0.03)
    bb_range = thresholds.get("bb_ranging", 0.02)

    if ti.bb_width > bb_vol:
        votes["volatile"] += 2
    elif ti.bb_width > bb_trend:
        votes["trending"] += 1
    elif ti.bb_width < bb_range:
        votes["ranging"] += 1

    # Volatility expansion/contraction
    if len(df) >= 30:
        recent_range = (df["high"].iloc[-5:] - df["low"].iloc[-5:]).mean()
        hist_range = (df["high"].iloc[-30:-5] - df["low"].iloc[-30:-5]).mean()
        if hist_range > 0:
            vol_ratio = recent_range / hist_range
            if vol_ratio > 1.3:
                votes["volatile"] += 1
                votes["trending"] += 1
            elif vol_ratio < 0.7:
                votes["ranging"] += 1

    # Hurst exponent (simplified variance ratio)
    hurst = _calc_hurst(df["close"])
    if hurst > 0.6:
        votes["trending"] += 2
    elif hurst < 0.4:
        votes["ranging"] += 2

    total = sum(votes.values())
    if total == 0:
        return "unknown", 0, hurst

    winner = max(votes, key=votes.get)
    confidence = votes[winner] / total
    return winner, confidence, hurst


def _calc_hurst(series: pd.Series) -> float:
    try:
        n = min(len(series), 200)
        s = series.iloc[-n:].values
        if len(s) < 20:
            return 0.5
        lags = [2, 4, 8, 16]
        variances = []
        for lag in lags:
            if lag >= len(s):
                continue
            returns = np.diff(np.log(s[:len(s) // lag * lag].reshape(-1, lag)[:, -1]))
            if len(returns) > 1:
                variances.append((lag, np.var(returns)))
        if len(variances) < 2:
            return 0.5
        log_lags = np.log([v[0] for v in variances])
        log_vars = np.log([v[1] for v in variances if v[1] > 0])
        if len(log_vars) < 2:
            return 0.5
        log_lags = log_lags[:len(log_vars)]
        slope = np.polyfit(log_lags, log_vars, 1)[0]
        hurst = 0.5 + slope / 2
        return float(np.clip(hurst, 0, 1))
    except Exception:
        return 0.5
