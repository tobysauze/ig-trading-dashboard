import asyncio
import traceback

async def main():
    from app.services.scanner import _analyse_instrument
    from app.models.instrument_universe import INSTRUMENTS

    for i in range(22, 28):
        inst = INSTRUMENTS[i]
        try:
            result = await _analyse_instrument(inst, "swing")
            sig = result.get("signal_type", "?") if result else "NO DATA"
            print(f"{i+1}: {inst['name']:20s} -> {sig}")
        except Exception as e:
            print(f"{i+1}: {inst['name']:20s} -> ERROR: {str(e)[:80]}")
            traceback.print_exc()

asyncio.run(main())
