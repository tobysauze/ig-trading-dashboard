import pandas as pd
from dataclasses import dataclass


@dataclass
class CandlestickPattern:
    name: str
    type: str  # bullish, bearish, neutral
    confidence: float
    description: str = ""


@dataclass
class ChartPattern:
    name: str
    type: str
    confidence: float
    description: str = ""


def detect_candlestick_patterns(df: pd.DataFrame) -> list[CandlestickPattern]:
    patterns = []
    if len(df) < 3:
        return patterns

    c = df.iloc[-1]
    p = df.iloc[-2]
    pp = df.iloc[-3]

    body = c["close"] - c["open"]
    body_abs = abs(body)
    candle_range = c["high"] - c["low"]
    if candle_range == 0:
        return patterns

    upper_wick = c["high"] - max(c["close"], c["open"])
    lower_wick = min(c["close"], c["open"]) - c["low"]
    body_ratio = body_abs / candle_range

    prev_body = p["close"] - p["open"]
    prev_body_abs = abs(prev_body)
    pp_body = pp["close"] - pp["open"]

    # Doji
    if body_ratio < 0.1:
        patterns.append(CandlestickPattern("Doji", "neutral", 0.70, "Indecision candle"))

    # Hammer
    if body_ratio < 0.35 and lower_wick >= 2 * body_abs and upper_wick < body_abs:
        patterns.append(CandlestickPattern("Hammer", "bullish", 0.75, "Bullish reversal at support"))

    # Inverted Hammer
    if body_ratio < 0.35 and upper_wick >= 2 * body_abs and lower_wick < body_abs:
        patterns.append(CandlestickPattern("Inverted Hammer", "bearish", 0.65, "Bearish reversal signal"))

    # Shooting Star
    if upper_wick >= 2 * body_abs and lower_wick < body_abs * 0.5 and c["close"] < c["open"]:
        patterns.append(CandlestickPattern("Shooting Star", "bearish", 0.70, "Bearish reversal at resistance"))

    # Bullish Engulfing
    if prev_body < 0 and body > 0 and c["close"] > p["open"] and c["open"] < p["close"]:
        patterns.append(CandlestickPattern("Bullish Engulfing", "bullish", 0.80, "Strong bullish reversal"))

    # Bearish Engulfing
    if prev_body > 0 and body < 0 and c["open"] > p["close"] and c["close"] < p["open"]:
        patterns.append(CandlestickPattern("Bearish Engulfing", "bearish", 0.80, "Strong bearish reversal"))

    # Morning Star
    if pp_body < 0 and prev_body_abs < candle_range * 0.3 and body > 0:
        if c["close"] > (pp["open"] + pp["close"]) / 2:
            patterns.append(CandlestickPattern("Morning Star", "bullish", 0.85, "Three-candle bullish reversal"))

    # Evening Star
    if pp_body > 0 and prev_body_abs < candle_range * 0.3 and body < 0:
        if c["close"] < (pp["open"] + pp["close"]) / 2:
            patterns.append(CandlestickPattern("Evening Star", "bearish", 0.85, "Three-candle bearish reversal"))

    # Bullish Pin Bar
    if lower_wick >= 2.5 * body_abs and c["close"] > c["open"]:
        quality = min(lower_wick / (candle_range * 0.6), 1.0)
        conf = 0.70 + quality * 0.20
        patterns.append(CandlestickPattern("Bullish Pin Bar", "bullish", conf, "Rejection of lower prices"))

    # Bearish Pin Bar
    if upper_wick >= 2.5 * body_abs and c["close"] < c["open"]:
        quality = min(upper_wick / (candle_range * 0.6), 1.0)
        conf = 0.70 + quality * 0.20
        patterns.append(CandlestickPattern("Bearish Pin Bar", "bearish", conf, "Rejection of higher prices"))

    # Inside Bar
    if c["high"] < p["high"] and c["low"] > p["low"]:
        lean = (c["close"] - c["low"]) / candle_range if candle_range > 0 else 0.5
        if lean > 0.6:
            patterns.append(CandlestickPattern("Inside Bar", "bullish", 0.60, "Consolidation, lean bullish"))
        elif lean < 0.4:
            patterns.append(CandlestickPattern("Inside Bar", "bearish", 0.60, "Consolidation, lean bearish"))
        else:
            patterns.append(CandlestickPattern("Inside Bar", "neutral", 0.55, "Consolidation"))

    # Three White Soldiers
    if len(df) >= 3:
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        if (c1["close"] > c1["open"] and c2["close"] > c2["open"] and c3["close"] > c3["open"] and
            c2["close"] > c1["close"] and c3["close"] > c2["close"]):
            patterns.append(CandlestickPattern("Three White Soldiers", "bullish", 0.85, "Strong bullish continuation"))

    # Three Black Crows
    if len(df) >= 3:
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        if (c1["close"] < c1["open"] and c2["close"] < c2["open"] and c3["close"] < c3["open"] and
            c2["close"] < c1["close"] and c3["close"] < c2["close"]):
            patterns.append(CandlestickPattern("Three Black Crows", "bearish", 0.85, "Strong bearish continuation"))

    return patterns


def detect_chart_patterns(df: pd.DataFrame) -> list[ChartPattern]:
    patterns = []
    if len(df) < 30:
        return patterns

    swing_window = 3
    highs = df["high"].values
    lows = df["low"].values

    swing_highs = []
    swing_lows = []

    for i in range(swing_window, len(df) - swing_window):
        if highs[i] == max(highs[i - swing_window:i + swing_window + 1]):
            swing_highs.append((i, highs[i]))
        if lows[i] == min(lows[i - swing_window:i + swing_window + 1]):
            swing_lows.append((i, lows[i]))

    # Higher Highs
    if len(swing_highs) >= 3 and swing_highs[-1][1] > swing_highs[-2][1] > swing_highs[-3][1]:
        patterns.append(ChartPattern("Higher Highs", "bullish", 0.75, "Uptrend structure"))

    # Higher Lows
    if len(swing_lows) >= 3 and swing_lows[-1][1] > swing_lows[-2][1] > swing_lows[-3][1]:
        patterns.append(ChartPattern("Higher Lows", "bullish", 0.75, "Uptrend structure"))

    # Lower Highs
    if len(swing_highs) >= 3 and swing_highs[-1][1] < swing_highs[-2][1] < swing_highs[-3][1]:
        patterns.append(ChartPattern("Lower Highs", "bearish", 0.75, "Downtrend structure"))

    # Lower Lows
    if len(swing_lows) >= 3 and swing_lows[-1][1] < swing_lows[-2][1] < swing_lows[-3][1]:
        patterns.append(ChartPattern("Lower Lows", "bearish", 0.75, "Downtrend structure"))

    # Double Top
    if len(swing_highs) >= 2:
        h1, h2 = swing_highs[-2][1], swing_highs[-1][1]
        if abs(h1 - h2) / max(h1, h2) < 0.005 and swing_highs[-1][0] - swing_highs[-2][0] >= 5:
            neckline = min(lows[swing_highs[-2][0]:swing_highs[-1][0]])
            if df["close"].iloc[-1] <= neckline * 1.01:
                patterns.append(ChartPattern("Double Top", "bearish", 0.80, "Bearish reversal pattern"))

    # Double Bottom
    if len(swing_lows) >= 2:
        l1, l2 = swing_lows[-2][1], swing_lows[-1][1]
        if abs(l1 - l2) / max(l1, l2) < 0.005 and swing_lows[-1][0] - swing_lows[-2][0] >= 5:
            neckline = max(highs[swing_lows[-2][0]:swing_lows[-1][0]])
            if df["close"].iloc[-1] >= neckline * 0.99:
                patterns.append(ChartPattern("Double Bottom", "bullish", 0.80, "Bullish reversal pattern"))

    # Fair Value Gap
    if len(df) >= 3:
        c1, c2, c3 = df.iloc[-3], df.iloc[-2], df.iloc[-1]
        price = df["close"].iloc[-1]
        # Bullish FVG: gap between c1 high and c3 low
        if c3["low"] > c1["high"] and (c3["low"] - c1["high"]) / price > 0.003:
            patterns.append(ChartPattern("Fair Value Gap (Bullish)", "bullish", 0.70, "Gap to fill above"))
        # Bearish FVG: gap between c1 low and c3 high
        if c3["high"] < c1["low"] and (c1["low"] - c3["high"]) / price > 0.003:
            patterns.append(ChartPattern("Fair Value Gap (Bearish)", "bearish", 0.70, "Gap to fill below"))

    return patterns
