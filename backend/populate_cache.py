import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.scanner import run_scan

print("Running full scan...")
result = run_scan("swing")
print(f"Done: {result['signals_found']} signals from {result['total_instruments']} instruments")
print(f"Buy: {result['buy_signals']}, Sell: {result['sell_signals']}")
print()
for s in result["signals"][:15]:
    print(f"  {s['signal_type']:12s} | {s['name']:22s} | {s['composite_score']:.1f} | {s['market_type']}")
