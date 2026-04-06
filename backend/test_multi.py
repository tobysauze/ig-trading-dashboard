import asyncio
import json

async def test():
    from app.services.scanner import _analyse_instrument
    from app.models.instrument_universe import INSTRUMENTS

    test_instruments = [
        ("AAPL", "share"),
        ("EUR/USD", "forex"),
        ("BTC/USD", "crypto"),
        ("Gold", "commodity"),
        ("US 500", "index"),
    ]

    for name, mtype in test_instruments:
        inst = next((i for i in INSTRUMENTS if i["name"] == name), None)
        if not inst:
            print(f"SKIP {name}: not found")
            continue
        try:
            result = await _analyse_instrument(inst, "swing")
            if result:
                print(f"{result['signal_type']:12s} | Score: {result['composite_score']:6.2f} | Conf: {result['confidence']:.2f} | {name} ({result['current_price']})")
            else:
                print(f"{'NO DATA':12s} | {name}")
        except Exception as e:
            print(f"{'ERROR':12s} | {name}: {e}")

asyncio.run(test())
