import traceback
import asyncio

try:
    from app.services.price_data import fetch_prices, prices_to_df
    from app.services.technical_analysis import compute_indicators
    from app.services.pattern_detection import detect_candlestick_patterns, detect_chart_patterns
    from app.services.signal_engine import score_timeframe, score_instrument_multi_timeframe
    from app.models.instrument_universe import INSTRUMENTS

    inst = [i for i in INSTRUMENTS if i["yahoo"] == "AAPL"][0]
    print(f"Testing: {inst['name']} ({inst['market_type']})")

    timeframes = [("1d", "6mo"), ("4h", "60d"), ("1h", "60d")]
    tf_scores = {}

    for tf, _ in timeframes:
        prices = fetch_prices(inst, tf)
        print(f"\n--- {tf}: {len(prices)} candles ---")
        if len(prices) < 26:
            print(f"  Skipping: not enough data")
            continue

        df = prices_to_df(prices)
        ti = compute_indicators(df, inst["market_type"])
        candle_pats = detect_candlestick_patterns(df)
        chart_pats = detect_chart_patterns(df) if tf in ("1d", "4h") else []

        print(f"  RSI: {ti.rsi:.1f}, ADX: {ti.adx:.1f}, MACD_hist: {ti.macd_histogram:.4f}")
        print(f"  SMA20: {ti.sma_20:.2f}, SMA50: {ti.sma_50:.2f}")
        print(f"  Regime: {ti.regime} ({ti.regime_confidence:.2f})")
        print(f"  Support: {ti.support:.2f}, Resistance: {ti.resistance:.2f}")
        print(f"  Patterns: {len(candle_pats)} candle, {len(chart_pats)} chart")

        score, _, reasons = score_timeframe(ti, inst["market_type"], candle_pats, chart_pats)
        tf_scores[tf] = (score, reasons)
        print(f"  Timeframe score: {score:.2f}")
        for r in reasons[:5]:
            print(f"    - {r}")

    if tf_scores:
        print(f"\n--- Multi-timeframe scoring ---")
        composite, signal, confidence, reasons = score_instrument_multi_timeframe(
            tf_scores, inst["market_type"]
        )
        print(f"Composite: {composite:.2f}")
        print(f"Signal: {signal}")
        print(f"Confidence: {confidence:.2f}")
        for r in reasons[:10]:
            print(f"  - {r}")
    else:
        print("No timeframe scores computed")

except Exception as e:
    traceback.print_exc()
