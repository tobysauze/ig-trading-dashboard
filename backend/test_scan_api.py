import traceback
import asyncio

from app.services.scanner import run_scan

try:
    result = asyncio.run(run_scan("swing", limit=5))
    print(f"Signals: {result['signals_found']}")
    for s in result["signals"][:10]:
        print(f"  {s['signal_type']:12s} | {s['name']:20s} | Score: {s['composite_score']}")
except Exception as e:
    traceback.print_exc()
