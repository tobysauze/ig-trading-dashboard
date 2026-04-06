import asyncio
import traceback

async def test():
    from app.services.scanner import _analyse_instrument
    from app.models.instrument_universe import INSTRUMENTS

    errors = []
    successes = []
    for i, inst in enumerate(INSTRUMENTS[:20]):
        try:
            result = await _analyse_instrument(inst, "swing")
            if result:
                successes.append(f"{result['signal_type']:12s} | {inst['name']}")
            else:
                errors.append(f"NO DATA: {inst['name']}")
        except Exception as e:
            errors.append(f"ERROR: {inst['name']}: {str(e)[:100]}")

    print(f"Tested 20 instruments: {len(successes)} OK, {len(errors)} issues")
    for s in successes:
        print(s)
    if errors:
        print("--- Issues ---")
        for e in errors[:10]:
            print(e)

asyncio.run(test())
