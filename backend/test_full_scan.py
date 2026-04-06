import asyncio
import traceback

async def main():
    from app.services.scanner import run_scan
    try:
        result = await run_scan("swing")
        print(f"Done: {result['signals_found']} signals from {result['total_instruments']}")
        for s in result["signals"][:10]:
            print(f"  {s['signal_type']:12s} | {s['name']:22s} | {s['composite_score']:.1f}")
    except Exception as e:
        traceback.print_exc()

asyncio.run(main())
