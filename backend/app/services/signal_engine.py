import math
from app.models.instrument_universe import MARKET_THRESHOLDS, TIMEFRAME_WEIGHTS
from app.services.technical_analysis import TechnicalIndicators
from app.services.pattern_detection import CandlestickPattern, ChartPattern


def score_timeframe(ti: TechnicalIndicators, market_type: str,
                    candle_patterns: list[CandlestickPattern],
                    chart_patterns: list[ChartPattern]) -> tuple[float, float, list[str]]:
    thresholds = MARKET_THRESHOLDS.get(market_type, MARKET_THRESHOLDS["share"])
    trend_score = 0.0
    reversion_score = 0.0
    reasons = []

    # Divergence (highest impact)
    if ti.bullish_divergence_rsi:
        reversion_score += 3.0
        reasons.append("RSI bullish divergence (+3.0)")
    if ti.bearish_divergence_rsi:
        reversion_score -= 3.0
        reasons.append("RSI bearish divergence (-3.0)")
    if ti.bullish_divergence_macd:
        reversion_score += 2.5
        reasons.append("MACD bullish divergence (+2.5)")
    if ti.bearish_divergence_macd:
        reversion_score -= 2.5
        reasons.append("MACD bearish divergence (-2.5)")

    # RSI
    ob = thresholds["rsi_overbought"]
    os_ = thresholds["rsi_oversold"]
    if ti.rsi < os_:
        reversion_score += 2
        reasons.append(f"RSI oversold {ti.rsi:.0f} (+2.0)")
    elif ti.rsi < os_ + 10:
        reversion_score += 1
        reasons.append(f"RSI near oversold {ti.rsi:.0f} (+1.0)")
    elif ti.rsi > ob:
        reversion_score -= 2
        reasons.append(f"RSI overbought {ti.rsi:.0f} (-2.0)")
    elif ti.rsi > ob - 10:
        reversion_score -= 1
        reasons.append(f"RSI near overbought {ti.rsi:.0f} (-1.0)")

    # Stochastic RSI
    stob = thresholds["stoch_overbought"]
    stos = thresholds["stoch_oversold"]
    if ti.stoch_rsi_k < stos / 100:
        reversion_score += 1.5
        reasons.append("Stoch RSI oversold (+1.5)")
    elif ti.stoch_rsi_k > stob / 100:
        reversion_score -= 1.5
        reasons.append("Stoch RSI overbought (-1.5)")

    # MACD Histogram
    if ti.macd_histogram > 0:
        trend_score += 1.5
        reasons.append("MACD histogram positive (+1.5)")
    elif ti.macd_histogram < 0:
        trend_score -= 1.5
        reasons.append("MACD histogram negative (-1.5)")

    # Bollinger Bands
    close = (ti.bb_upper + ti.bb_lower) / 2 if ti.bb_middle == 0 else ti.bb_middle
    if ti.bb_lower > 0 and close <= ti.bb_lower * 1.01:
        reversion_score += 1.5
        reasons.append("At lower Bollinger Band (+1.5)")
    elif ti.bb_upper > 0 and close >= ti.bb_upper * 0.99:
        reversion_score -= 1.5
        reasons.append("At upper Bollinger Band (-1.5)")

    # Moving Averages
    if ti.sma_20 > ti.sma_50 > 0:
        trend_score += 1
        reasons.append("SMA20 > SMA50 (+1.0)")
    elif ti.sma_50 > ti.sma_20 > 0:
        trend_score -= 1
        reasons.append("SMA20 < SMA50 (-1.0)")

    if ti.ema_12 > ti.ema_26 > 0:
        trend_score += 0.5
        reasons.append("EMA12 > EMA26 (+0.5)")
    elif ti.ema_26 > ti.ema_12 > 0:
        trend_score -= 0.5
        reasons.append("EMA12 < EMA26 (-0.5)")

    # EMA 20 slope with ADX confirmation
    if abs(ti.ema_20_slope) > 0.1:
        if ti.ema_20_slope > 0 and ti.adx > thresholds["adx_weak"]:
            trend_score += 2.0
            reasons.append(f"EMA20 slope up + ADX confirm (+2.0)")
        elif ti.ema_20_slope < 0 and ti.adx > thresholds["adx_weak"]:
            trend_score -= 2.0
            reasons.append(f"EMA20 slope down + ADX confirm (-2.0)")

    # Directional Indicators
    if ti.plus_di > ti.minus_di:
        trend_score += 0.5
        reasons.append("+DI > -DI (+0.5)")
    else:
        trend_score -= 0.5
        reasons.append("-DI > +DI (-0.5)")

    # Volume Profile
    if ti.accumulation == "accumulation":
        trend_score += 1.5
        reasons.append("Volume accumulation (+1.5)")
    elif ti.accumulation == "distribution":
        trend_score -= 1.5
        reasons.append("Volume distribution (-1.5)")

    if ti.volume_trend > 1.3:
        direction = "+" if trend_score + reversion_score > 0 else "-"
        trend_score += 1.0 if trend_score + reversion_score > 0 else -1.0
        reasons.append(f"Expanding volume ({direction}1.0)")

    # OBV
    if ti.obv > ti.obv_sma > 0:
        trend_score += 0.5
        reasons.append("OBV above SMA (+0.5)")
    elif ti.obv_sma > ti.obv > 0:
        trend_score -= 0.5
        reasons.append("OBV below SMA (-0.5)")

    # S/R proximity
    if ti.support > 0 and ti.resistance > 0 and ti.support != ti.resistance:
        dist_to_support = abs(close - ti.support) / (ti.resistance - ti.support) if close > ti.support else 0
        dist_to_resistance = abs(close - ti.resistance) / (ti.resistance - ti.support) if close < ti.resistance else 0
        if dist_to_support < 0.1:
            reversion_score += 1.0
            reasons.append("Near support (+1.0)")
        if dist_to_resistance < 0.1:
            reversion_score -= 1.0
            reasons.append("Near resistance (-1.0)")

    # Rate of Change
    if ti.roc_10 > 3:
        trend_score += 1.0
        reasons.append(f"Strong momentum ROC {ti.roc_10:.1f}% (+1.0)")
    elif ti.roc_10 < -3:
        trend_score -= 1.0
        reasons.append(f"Weak momentum ROC {ti.roc_10:.1f}% (-1.0)")

    # Overextension
    if abs(ti.dist_sma20) > 5:
        reversion_score += -0.5 if ti.dist_sma20 > 0 else 0.5
        reasons.append(f"Extended from SMA20 {ti.dist_sma20:.1f}%")

    # Consecutive candles
    if abs(ti.consecutive_candles) >= 5:
        sign = -0.5 if ti.consecutive_candles > 0 else 0.5
        reversion_score += sign
        reasons.append(f"Exhaustion warning ({ti.consecutive_candles} candles)")

    # Regime-aware weighting
    if ti.regime == "trending":
        combined = trend_score * 1.3 + reversion_score * 0.7
    elif ti.regime == "ranging":
        combined = trend_score * 0.6 + reversion_score * 1.4
    else:
        combined = trend_score + reversion_score

    # Candlestick pattern context
    for pat in candle_patterns:
        ctx_mult = 0.5
        if close <= ti.support * 1.02 and pat.type == "bullish":
            ctx_mult = 1.8
        elif close >= ti.resistance * 0.98 and pat.type == "bearish":
            ctx_mult = 1.8
        elif (close <= ti.bb_lower * 1.02 and pat.type == "bullish") or (close >= ti.bb_upper * 0.98 and pat.type == "bearish"):
            ctx_mult = 1.6

        pat_score = pat.confidence * ctx_mult * (1 if pat.type == "bullish" else -1 if pat.type == "bearish" else 0)
        combined += pat_score
        if abs(pat_score) > 0.3:
            reasons.append(f"{pat.name} ({pat_score:+.1f})")

    # Chart patterns
    for pat in chart_patterns:
        pat_score = pat.confidence * 1.5 * (1 if pat.type == "bullish" else -1 if pat.type == "bearish" else 0)
        combined += pat_score
        reasons.append(f"{pat.name} ({pat_score:+.1f})")

    return combined, 0, reasons


def score_instrument_multi_timeframe(
    timeframe_scores: dict[str, tuple[float, list[str]]],
    market_type: str,
    breakout_signal: str | None = None,
    breakout_volume: bool = False,
    news_score: float = 0,
    session_status: str = "good",
    has_volume_support: bool = True,
) -> tuple[float, str, float, list[str]]:
    thresholds = MARKET_THRESHOLDS.get(market_type, MARKET_THRESHOLDS["share"])
    weights = {"1d": 0.40, "4h": 0.35, "1h": 0.25, "15m": 0.15}

    composite = 0.0
    total_weight = 0.0
    all_reasons = []
    directions = []

    daily_score = timeframe_scores.get("1d", (0, []))[0]

    for tf, (score, reasons) in timeframe_scores.items():
        w = weights.get(tf, 0.1)
        if tf != "1d" and abs(daily_score) > 2:
            if (score > 0 and daily_score > 0) or (score < 0 and daily_score < 0):
                w *= 1.15
            elif (score > 0 and daily_score < 0) or (score < 0 and daily_score > 0):
                w *= 0.85
        composite += score * w
        total_weight += w
        if score > 0.5:
            directions.append(1)
        elif score < -0.5:
            directions.append(-1)
        else:
            directions.append(0)
        all_reasons.extend(reasons)

    if total_weight > 0:
        composite /= total_weight

    agree = sum(1 for d in directions if d == directions[0] and d != 0)
    neutral = sum(1 for d in directions if d == 0)
    disagree = len(directions) - agree - neutral

    if agree >= len(directions) - 1 and disagree == 0:
        composite *= 1.4
        composite += 1.5
        all_reasons.append(f"Full confluence ({agree}/{len(directions)}) (x1.4 + 1.5)")
    elif agree > disagree:
        composite *= 1.25
        all_reasons.append(f"Strong confluence ({agree}/{len(directions)}) (x1.25)")
    elif agree > 0:
        composite *= 1.15
        all_reasons.append(f"Partial confluence ({agree}/{len(directions)}) (x1.15)")
    elif disagree > agree:
        composite *= 0.9
        all_reasons.append(f"TF disagreement (x0.9)")

    if breakout_signal == "bullish":
        bonus = 1.5 if breakout_volume else 0.75
        composite += bonus
        all_reasons.append(f"Bullish breakout ({'volume-confirmed' if breakout_volume else 'unconfirmed'}) (+{bonus})")
    elif breakout_signal == "bearish":
        bonus = -1.5 if breakout_volume else -0.75
        composite += bonus
        all_reasons.append(f"Bearish breakout ({'volume-confirmed' if breakout_volume else 'unconfirmed'}) ({bonus})")

    composite += news_score
    if abs(news_score) > 0.5:
        all_reasons.append(f"News impact ({news_score:+.1f})")

    if session_status == "avoid":
        composite *= 0.7
        all_reasons.append("Session avoid (x0.7)")
    elif session_status == "closed":
        composite *= 0.5
        all_reasons.append("Market closed (x0.5)")
    elif session_status == "best":
        composite *= 1.1
        all_reasons.append("Best session (x1.1)")

    if not has_volume_support and market_type != "forex":
        composite *= 0.75
        all_reasons.append("Lacks volume support (x0.75)")

    if composite >= thresholds["strong_buy"]:
        signal = "STRONG_BUY"
    elif composite >= thresholds["buy"]:
        signal = "BUY"
    elif composite <= thresholds["strong_sell"]:
        signal = "STRONG_SELL"
    elif composite <= thresholds["sell"]:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    confidence = min(abs(composite) / 15.0, 1.0)

    return composite, signal, confidence, all_reasons
