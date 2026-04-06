import traceback
import asyncio

try:
    from app.services.scanner import _analyse_instrument
    from app.models.instrument_universe import INSTRUMENTS

    inst = [i for i in INSTRUMENTS if i["yahoo"] == "AAPL"][0]
    print(f"Testing: {inst['name']}")

    result = asyncio.run(_analyse_instrument(inst, "swing"))
    if result:
        print(f"Signal: {result['signal_type']}")
        print(f"Score: {result['composite_score']}")
        print(f"Price: {result['current_price']}")
        print(f"RSI: {result['rsi']}")
        print(f"ADX: {result['adx']}")
        print(f"Reasons: {result['reasons'][:5]}")
    else:
        print("No result returned")
except Exception as e:
    traceback.print_exc()
