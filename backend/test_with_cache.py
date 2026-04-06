import asyncio
import json

async def main():
    from app.services.scanner import run_scan, get_latest_scan
    result = await run_scan("swing", limit=30)
    print(f"Signals: {result['signals_found']}")
    for s in result["signals"][:10]:
        print(f"  {s['signal_type']:12s} | {s['name']:22s} | {s['composite_score']:.1f}")

    # Verify cache works
    cached = get_latest_scan()
    print(f"\nCache: {cached['signals_found'] if cached else 'None'} signals")

asyncio.run(main())
