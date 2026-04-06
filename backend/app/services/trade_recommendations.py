from app.services.technical_analysis import TechnicalIndicators

SPREAD_ESTIMATES = {
    "forex": {"default": 1.0, "jpy": 1.5},
    "index": {"default": 1.0},
    "commodity": {"gold": 0.3, "oil": 2.8, "default": 1.0},
    "crypto": {"btc": 40, "eth": 3, "default": 0.5},
    "share": {"default_pct": 0.001},
    "bond": {"default": 0.02},
}


def estimate_spread(market_type: str, price: float = 0, symbol: str = "") -> float:
    if market_type == "forex":
        if "JPY" in symbol:
            return SPREAD_ESTIMATES["forex"]["jpy"]
        return SPREAD_ESTIMATES["forex"]["default"]
    elif market_type == "crypto":
        if "BTC" in symbol.upper():
            return SPREAD_ESTIMATES["crypto"]["btc"]
        elif "ETH" in symbol.upper():
            return SPREAD_ESTIMATES["crypto"]["eth"]
        return price * 0.001
    elif market_type == "commodity":
        if "gold" in symbol.lower() or "GOLD" in symbol:
            return 0.3
        if "oil" in symbol.lower() or "CRUDE" in symbol.upper() or "CL" in symbol:
            return 2.8
        return 1.0
    elif market_type == "share":
        return price * 0.001
    return 1.0


def generate_recommendation(
    signal: str, composite_score: float, confidence: float,
    ti: TechnicalIndicators, market_type: str,
    account_size: float = 10000, risk_pct: float = 1.0,
    mode: str = "spread_bet", timeframe_agreement: float = 0,
    has_volume_spike: bool = False, has_breakout: bool = False,
    has_divergence: bool = False,
) -> dict:
    price = (ti.support + ti.resistance) / 2 if ti.support > 0 and ti.resistance > 0 else 0

    rating_score = 0
    if confidence >= 0.5: rating_score += 3
    elif confidence >= 0.3: rating_score += 2
    if timeframe_agreement >= 1.0: rating_score += 3
    elif timeframe_agreement >= 0.5: rating_score += 2
    elif timeframe_agreement < 0: rating_score -= 1
    if ti.adx > 30: rating_score += 2
    elif ti.adx > 25: rating_score += 1
    elif ti.adx < 20: rating_score -= 1
    if has_volume_spike: rating_score += 1
    if has_breakout: rating_score += 2
    if "STRONG" in signal: rating_score += 2
    if has_divergence: rating_score += 2

    if rating_score >= 8: trade_rating = "STRONG"
    elif rating_score >= 5: trade_rating = "GOOD"
    elif rating_score >= 3: trade_rating = "MARGINAL"
    else: trade_rating = "AVOID"

    direction = "BUY" if "BUY" in signal else "SELL" if "SELL" in signal else "NEUTRAL"

    entry_type = "MARKET"
    if has_breakout or ("STRONG" in signal and confidence > 0.6):
        entry_type = "MARKET"
    elif ti.support > 0 and ti.resistance > 0:
        if direction == "BUY" and price > ti.support * 1.02:
            entry_type = "LIMIT"
        elif direction == "SELL" and price < ti.resistance * 0.98:
            entry_type = "LIMIT"

    atr = ti.atr if ti.atr > 0 else price * 0.01
    atr_stop = 1.5 * atr

    if direction == "BUY":
        struct_stop = ti.support - 0.2 * atr if ti.support > 0 else price - atr_stop
        stop = max(min(price - atr_stop, struct_stop), price - 0.5 * atr)
        stop_dist = price - stop
        tp1 = price + stop_dist * 1.5
        tp2 = price + stop_dist * 2.0
        tp3 = price + stop_dist * 3.0
        if ti.resistance > 0 and ti.resistance > tp1:
            tp1 = min(tp1, ti.resistance)
        if ti.resistance > 0 and ti.resistance > tp2:
            tp2 = min(tp2, ti.resistance * 1.01)
    elif direction == "SELL":
        struct_stop = ti.resistance + 0.2 * atr if ti.resistance > 0 else price + atr_stop
        stop = max(min(price + atr_stop, struct_stop), price + 0.5 * atr)
        stop_dist = stop - price
        tp1 = price - stop_dist * 1.5
        tp2 = price - stop_dist * 2.0
        tp3 = price - stop_dist * 3.0
        if ti.support > 0 and ti.support < tp1:
            tp1 = max(tp1, ti.support)
    else:
        stop_dist = atr_stop
        stop = price - stop_dist
        tp1 = price + stop_dist * 1.5
        tp2 = price + stop_dist * 2.0
        tp3 = price + stop_dist * 3.0

    risk_amount = account_size * (risk_pct / 100)
    spread = estimate_spread(market_type, price, "")

    if mode == "spread_bet":
        if stop_dist > 0:
            position_size = risk_amount / (stop_dist + spread)
        else:
            position_size = 0
        position_value = position_size * price
        rr_ratio = (tp2 - price) / stop_dist if stop_dist > 0 and direction == "BUY" else (price - tp2) / stop_dist if stop_dist > 0 else 0
    else:
        if stop_dist > 0:
            units = risk_amount / stop_dist
        else:
            units = 0
        position_size = units
        position_value = units * price
        rr_ratio = stop_dist * 2 / stop_dist if stop_dist > 0 else 0

    rr_ratio = round(max(rr_ratio, 0), 1)

    return {
        "direction": direction,
        "signal": signal,
        "trade_rating": trade_rating,
        "rating_score": rating_score,
        "confidence": round(confidence, 2),
        "entry_type": entry_type,
        "entry_price": round(price, 4),
        "stop_loss": round(stop, 4),
        "take_profit_1": round(tp1, 4),
        "take_profit_2": round(tp2, 4),
        "take_profit_3": round(tp3, 4),
        "stop_distance": round(stop_dist, 4),
        "position_size": round(position_size, 4),
        "position_value": round(position_value, 2),
        "risk_amount": round(risk_amount, 2),
        "rr_ratio": rr_ratio,
        "spread_estimate": round(spread, 4),
        "mode": mode,
        "account_size": account_size,
        "risk_pct": risk_pct,
    }
