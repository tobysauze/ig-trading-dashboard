import asyncio
import json
from datetime import datetime
from pathlib import Path

from app.models.instrument_universe import INSTRUMENTS
from app.services.price_data import fetch_prices, prices_to_df, fetch_current_price
from app.services.technical_analysis import compute_indicators
from app.services.pattern_detection import detect_candlestick_patterns, detect_chart_patterns
from app.services.signal_engine import score_timeframe, score_instrument_multi_timeframe
from app.services.news_sentiment import get_news_sentiment

_scan_progress = {"status": "idle", "completed": 0, "total": 0, "current": ""}
_latest_scan = None

SCAN_CACHE_PATH = Path(__file__).parent.parent.parent / "scan_cache.json"


def get_scan_progress():
    return _scan_progress


def get_latest_scan():
    global _latest_scan
    if _latest_scan is not None:
        return _latest_scan
    if SCAN_CACHE_PATH.exists():
        try:
            with open(SCAN_CACHE_PATH, "r") as f:
                _latest_scan = json.load(f)
            return _latest_scan
        except Exception:
            pass
    return None


def _save_scan(data: dict):
    global _latest_scan
    _latest_scan = data
    try:
        with open(SCAN_CACHE_PATH, "w") as f:
            json.dump(data, f, default=str)
    except Exception as e:
        print(f"Cache save error: {e}")


async def _analyse_instrument(instrument: dict, scan_mode: str = "swing") -> dict | None:
    market_type = instrument["market_type"]
    name = instrument["name"]
    yahoo = instrument["yahoo"]
    binance = instrument.get("binance", "")

    timeframes = {
        "swing": [("1d", "6mo"), ("4h", "60d"), ("1h", "60d")],
        "short": [("4h", "60d"), ("1h", "60d"), ("15m", "60d")],
    }
    tfs = timeframes.get(scan_mode, timeframes["swing"])

    tf_scores = {}
    all_ti = {}
    all_patterns = {}

    for tf, _ in tfs:
        prices = fetch_prices(instrument, tf)
        if len(prices) < 26:
            continue
        df = prices_to_df(prices)
        ti = compute_indicators(df, market_type)
        candle_pats = detect_candlestick_patterns(df)
        chart_pats = detect_chart_patterns(df) if tf in ("1d", "4h") else []
        score, _, reasons = score_timeframe(ti, market_type, candle_pats, chart_pats)
        tf_scores[tf] = (score, reasons)
        all_ti[tf] = ti
        all_patterns[tf] = {"candle": candle_pats, "chart": chart_pats}

    if not tf_scores:
        return None

    daily_prices = fetch_prices(instrument, "1d")
    daily_df = prices_to_df(daily_prices) if daily_prices else None
    sparkline = []
    if daily_df is not None and len(daily_df) > 0:
        sparkline = daily_df["close"].tail(30).tolist()

    current_price = sparkline[-1] if sparkline else 0
    daily_ti = all_ti.get("1d", all_ti.get("4h", None))

    # Volume check
    has_volume = True
    if daily_ti:
        has_volume = daily_ti.volume_trend > 0.8

    # Breakout
    breakout_signal = None
    breakout_vol = False
    if daily_ti and daily_ti.support > 0 and daily_ti.resistance > 0:
        if current_price > daily_ti.resistance:
            breakout_signal = "bullish"
            breakout_vol = daily_ti.volume_trend > 1.3
        elif current_price < daily_ti.support:
            breakout_signal = "bearish"
            breakout_vol = daily_ti.volume_trend > 1.3

    # News
    news = get_news_sentiment(name, market_type)

    # Session
    session = _get_session_status(market_type)

    # Composite score
    composite, signal, confidence, reasons = score_instrument_multi_timeframe(
        tf_scores, market_type,
        breakout_signal=breakout_signal,
        breakout_volume=breakout_vol,
        news_score=news["score"],
        session_status=session["status"],
        has_volume_support=has_volume,
    )

    # Confluence
    agreeing = sum(1 for _, (s, _) in tf_scores.items() if (s > 0 and composite > 0) or (s < 0 and composite < 0))
    confluence = agreeing / len(tf_scores) if tf_scores else 0

    rsi = daily_ti.rsi if daily_ti else 0
    adx = daily_ti.adx if daily_ti else 0

    # Candlestick patterns for flags
    daily_patterns = all_patterns.get("1d", {}).get("candle", [])
    chart_patterns = all_patterns.get("1d", {}).get("chart", [])

    has_divergence = False
    if daily_ti:
        has_divergence = any([
            daily_ti.bullish_divergence_rsi, daily_ti.bearish_divergence_rsi,
            daily_ti.bullish_divergence_macd, daily_ti.bearish_divergence_macd,
        ])

    return {
        "name": name,
        "epic": instrument.get("ig_epic", yahoo),
        "yahoo": yahoo,
        "market_type": market_type,
        "current_price": round(current_price, 4),
        "signal_type": signal,
        "composite_score": round(composite, 2),
        "confidence": round(confidence, 2),
        "confluence": round(confluence, 2),
        "rsi": round(rsi, 1),
        "adx": round(adx, 1),
        "regime": daily_ti.regime if daily_ti else "unknown",
        "timeframe_scores": {tf: round(s, 1) for tf, (s, _) in tf_scores.items()},
        "reasons": reasons,
        "has_breakout": breakout_signal is not None,
        "has_volume_spike": daily_ti and daily_ti.volume_trend > 2.0 if daily_ti else False,
        "has_patterns": len(daily_patterns) > 0,
        "candlestick_patterns": [{"name": p.name, "type": p.type, "confidence": p.confidence} for p in daily_patterns],
        "chart_patterns": [{"name": p.name, "type": p.type, "confidence": p.confidence} for p in chart_patterns],
        "has_divergence": has_divergence,
        "news_score": news["score"],
        "news_sentiment": news["sentiment"],
        "news_headlines": news.get("top_headlines", []),
        "session_status": session["status"],
        "sparkline": [round(x, 4) for x in sparkline],
        "support": round(daily_ti.support, 4) if daily_ti else 0,
        "resistance": round(daily_ti.resistance, 4) if daily_ti else 0,
        "atr": round(daily_ti.atr, 4) if daily_ti else 0,
        "indicators": {
            "macd": round(daily_ti.macd, 4) if daily_ti else 0,
            "macd_signal": round(daily_ti.macd_signal, 4) if daily_ti else 0,
            "macd_histogram": round(daily_ti.macd_histogram, 4) if daily_ti else 0,
            "bb_upper": round(daily_ti.bb_upper, 4) if daily_ti else 0,
            "bb_lower": round(daily_ti.bb_lower, 4) if daily_ti else 0,
            "bb_width": round(daily_ti.bb_width, 4) if daily_ti else 0,
            "sma_20": round(daily_ti.sma_20, 4) if daily_ti else 0,
            "sma_50": round(daily_ti.sma_50, 4) if daily_ti else 0,
            "ema_20": round(daily_ti.ema_20, 4) if daily_ti else 0,
            "plus_di": round(daily_ti.plus_di, 1) if daily_ti else 0,
            "minus_di": round(daily_ti.minus_di, 1) if daily_ti else 0,
            "stoch_rsi_k": round(daily_ti.stoch_rsi_k, 2) if daily_ti else 0,
            "obv_trend": daily_ti.accumulation if daily_ti else "neutral",
            "volume_trend": round(daily_ti.volume_trend, 2) if daily_ti else 1,
            "roc_10": round(daily_ti.roc_10, 2) if daily_ti else 0,
            "hurst": round(daily_ti.hurst, 2) if daily_ti else 0.5,
            "pivot": round(daily_ti.pivot, 4) if daily_ti else 0,
            "r1": round(daily_ti.r1, 4) if daily_ti else 0,
            "r2": round(daily_ti.r2, 4) if daily_ti else 0,
            "s1": round(daily_ti.s1, 4) if daily_ti else 0,
            "s2": round(daily_ti.s2, 4) if daily_ti else 0,
        },
    }


def _analyse_instrument_sync(instrument: dict, scan_mode: str = "swing") -> dict | None:
    market_type = instrument["market_type"]
    name = instrument["name"]
    yahoo = instrument["yahoo"]
    binance = instrument.get("binance", "")

    timeframes = {
        "swing": [("1d", "6mo"), ("4h", "60d"), ("1h", "60d")],
        "short": [("4h", "60d"), ("1h", "60d"), ("15m", "60d")],
    }
    tfs = timeframes.get(scan_mode, timeframes["swing"])

    tf_scores = {}
    all_ti = {}
    all_patterns = {}

    for tf, _ in tfs:
        prices = fetch_prices(instrument, tf)
        if len(prices) < 26:
            continue
        df = prices_to_df(prices)
        ti = compute_indicators(df, market_type)
        candle_pats = detect_candlestick_patterns(df)
        chart_pats = detect_chart_patterns(df) if tf in ("1d", "4h") else []
        score, _, reasons = score_timeframe(ti, market_type, candle_pats, chart_pats)
        tf_scores[tf] = (score, reasons)
        all_ti[tf] = ti
        all_patterns[tf] = {"candle": candle_pats, "chart": chart_pats}

    if not tf_scores:
        return None

    daily_prices = fetch_prices(instrument, "1d")
    daily_df = prices_to_df(daily_prices) if daily_prices else None
    sparkline = []
    if daily_df is not None and len(daily_df) > 0:
        sparkline = daily_df["close"].tail(30).tolist()

    current_price = sparkline[-1] if sparkline else 0
    daily_ti = all_ti.get("1d", all_ti.get("4h", None))

    has_volume = True
    if daily_ti:
        has_volume = daily_ti.volume_trend > 0.8

    breakout_signal = None
    breakout_vol = False
    if daily_ti and daily_ti.support > 0 and daily_ti.resistance > 0:
        if current_price > daily_ti.resistance:
            breakout_signal = "bullish"
            breakout_vol = daily_ti.volume_trend > 1.3
        elif current_price < daily_ti.support:
            breakout_signal = "bearish"
            breakout_vol = daily_ti.volume_trend > 1.3

    news = get_news_sentiment(name, market_type)
    session = _get_session_status(market_type)

    composite, signal, confidence, reasons = score_instrument_multi_timeframe(
        tf_scores, market_type,
        breakout_signal=breakout_signal,
        breakout_volume=breakout_vol,
        news_score=news["score"],
        session_status=session["status"],
        has_volume_support=has_volume,
    )

    agreeing = sum(1 for _, (s, _) in tf_scores.items() if (s > 0 and composite > 0) or (s < 0 and composite < 0))
    confluence = agreeing / len(tf_scores) if tf_scores else 0

    rsi = daily_ti.rsi if daily_ti else 0
    adx = daily_ti.adx if daily_ti else 0

    daily_patterns = all_patterns.get("1d", {}).get("candle", [])
    chart_patterns = all_patterns.get("1d", {}).get("chart", [])

    has_divergence = False
    if daily_ti:
        has_divergence = any([
            daily_ti.bullish_divergence_rsi, daily_ti.bearish_divergence_rsi,
            daily_ti.bullish_divergence_macd, daily_ti.bearish_divergence_macd,
        ])

    return {
        "name": name,
        "epic": instrument.get("ig_epic", yahoo),
        "yahoo": yahoo,
        "market_type": market_type,
        "current_price": round(current_price, 4),
        "signal_type": signal,
        "composite_score": round(composite, 2),
        "confidence": round(confidence, 2),
        "confluence": round(confluence, 2),
        "rsi": round(rsi, 1),
        "adx": round(adx, 1),
        "regime": daily_ti.regime if daily_ti else "unknown",
        "timeframe_scores": {tf: round(s, 1) for tf, (s, _) in tf_scores.items()},
        "reasons": reasons,
        "has_breakout": breakout_signal is not None,
        "has_volume_spike": daily_ti and daily_ti.volume_trend > 2.0 if daily_ti else False,
        "has_patterns": len(daily_patterns) > 0,
        "candlestick_patterns": [{"name": p.name, "type": p.type, "confidence": p.confidence} for p in daily_patterns],
        "chart_patterns": [{"name": p.name, "type": p.type, "confidence": p.confidence} for p in chart_patterns],
        "has_divergence": has_divergence,
        "news_score": news["score"],
        "news_sentiment": news["sentiment"],
        "news_headlines": news.get("top_headlines", []),
        "session_status": session["status"],
        "sparkline": [round(x, 4) for x in sparkline],
        "support": round(daily_ti.support, 4) if daily_ti else 0,
        "resistance": round(daily_ti.resistance, 4) if daily_ti else 0,
        "atr": round(daily_ti.atr, 4) if daily_ti else 0,
        "indicators": {
            "macd": round(daily_ti.macd, 4) if daily_ti else 0,
            "macd_signal": round(daily_ti.macd_signal, 4) if daily_ti else 0,
            "macd_histogram": round(daily_ti.macd_histogram, 4) if daily_ti else 0,
            "bb_upper": round(daily_ti.bb_upper, 4) if daily_ti else 0,
            "bb_lower": round(daily_ti.bb_lower, 4) if daily_ti else 0,
            "bb_width": round(daily_ti.bb_width, 4) if daily_ti else 0,
            "sma_20": round(daily_ti.sma_20, 4) if daily_ti else 0,
            "sma_50": round(daily_ti.sma_50, 4) if daily_ti else 0,
            "ema_20": round(daily_ti.ema_20, 4) if daily_ti else 0,
            "plus_di": round(daily_ti.plus_di, 1) if daily_ti else 0,
            "minus_di": round(daily_ti.minus_di, 1) if daily_ti else 0,
            "stoch_rsi_k": round(daily_ti.stoch_rsi_k, 2) if daily_ti else 0,
            "obv_trend": daily_ti.accumulation if daily_ti else "neutral",
            "volume_trend": round(daily_ti.volume_trend, 2) if daily_ti else 1,
            "roc_10": round(daily_ti.roc_10, 2) if daily_ti else 0,
            "hurst": round(daily_ti.hurst, 2) if daily_ti else 0.5,
            "pivot": round(daily_ti.pivot, 4) if daily_ti else 0,
            "r1": round(daily_ti.r1, 4) if daily_ti else 0,
            "r2": round(daily_ti.r2, 4) if daily_ti else 0,
            "s1": round(daily_ti.s1, 4) if daily_ti else 0,
            "s2": round(daily_ti.s2, 4) if daily_ti else 0,
        },
    }


def _get_session_status(market_type: str) -> dict:
    from datetime import timezone
    now = datetime.now(timezone.utc)
    hour = now.hour

    if market_type in ("forex", "index"):
        if 13 <= hour <= 16:
            return {"status": "best", "sessions": ["London", "New York"]}
        elif 8 <= hour <= 22:
            return {"status": "good", "sessions": ["London" if hour < 16 else "New York"]}
        else:
            return {"status": "avoid", "sessions": ["Sydney/Tokyo"]}
    elif market_type == "crypto":
        return {"status": "good", "sessions": ["24/7"]}
    else:
        if 14 <= hour <= 21:
            return {"status": "best", "sessions": ["New York"]}
        else:
            return {"status": "closed", "sessions": []}


def run_scan(scan_mode: str = "swing", limit: int = 0) -> dict:
    global _scan_progress, _latest_scan

    instruments = INSTRUMENTS[:limit] if limit > 0 else INSTRUMENTS
    _scan_progress = {"status": "running", "completed": 0, "total": len(instruments), "current": ""}

    valid = []
    for inst in instruments:
        try:
            _scan_progress["current"] = inst["name"]
            result = _analyse_instrument_sync(inst, scan_mode)
            if result:
                valid.append(result)
            _scan_progress["completed"] += 1
        except Exception as e:
            _scan_progress["completed"] += 1
            print(f"Scan error for {inst.get('name', '?')}: {e}")

    valid.sort(key=lambda x: abs(x.get("composite_score", 0)), reverse=True)

    _scan_progress["status"] = "completed"

    buy_signals = [r for r in valid if "BUY" in r.get("signal_type", "")]
    sell_signals = [r for r in valid if "SELL" in r.get("signal_type", "")]

    scan_result = {
        "timestamp": datetime.utcnow().isoformat(),
        "scan_mode": scan_mode,
        "total_instruments": len(instruments),
        "signals_found": len(valid),
        "buy_signals": len(buy_signals),
        "sell_signals": len(sell_signals),
        "signals": valid,
    }

    _save_scan(scan_result)
    return scan_result
