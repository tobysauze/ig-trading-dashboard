from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from datetime import datetime
from contextlib import asynccontextmanager

from app.services.scanner import run_scan, get_scan_progress, get_latest_scan
from app.services.trade_recommendations import generate_recommendation
from app.services.price_data import fetch_prices, prices_to_df
from app.services.technical_analysis import compute_indicators
from app.services.pattern_detection import detect_candlestick_patterns, detect_chart_patterns
from app.services.signal_engine import score_timeframe
from app.services.news_sentiment import get_news_sentiment
from app.services import trade_journal
from app.models.instrument_universe import INSTRUMENTS


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="IG Trading Dashboard", version="2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/scan")
def start_scan(scan_mode: str = Query("swing"), limit: int = Query(0)):
    try:
        from app.services.scanner import run_scan
        result = run_scan(scan_mode, limit=limit)
        return _sanitize(result)
    except Exception as e:
        import traceback
        print(f"SCAN ERROR: {traceback.format_exc()}")
        return {"error": str(e)}


@app.post("/api/scan/selected")
async def scan_selected(epics: list[str] = Query([])):
    selected = [i for i in INSTRUMENTS if i.get("ig_epic", i["yahoo"]) in epics]
    if not selected:
        return {"error": "No matching instruments"}
    scan_mode = "swing"
    tasks = []
    from app.services.scanner import _analyse_instrument
    for inst in selected:
        tasks.append(_analyse_instrument(inst, scan_mode))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in results if isinstance(r, dict)]
    return _sanitize({"signals": valid, "count": len(valid)})


@app.post("/api/scan/refresh-prices")
async def refresh_prices():
    scan = get_latest_scan()
    if not scan or not scan.get("signals"):
        return {"error": "No scan data. Run a scan first."}
    for sig in scan["signals"]:
        inst = next((i for i in INSTRUMENTS if i.get("ig_epic", sig.get("epic")) == sig.get("epic") or i["yahoo"] == sig.get("yahoo")), None)
        if inst:
            price = fetch_current_price_async(inst)
            if price:
                sig["current_price"] = round(price, 4)
    scan["timestamp"] = datetime.utcnow().isoformat()
    return _sanitize(scan)


from app.services.price_data import fetch_current_price


def fetch_current_price_async(inst):
    return fetch_current_price(inst)


@app.get("/api/scan/latest")
async def latest_scan():
    scan = get_latest_scan()
    if not scan:
        return {"error": "No scan data available"}
    try:
        return _sanitize(scan)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": f"Sanitize error: {e}", "signals_found": scan.get("signals_found", 0)}


@app.get("/api/scan/progress")
async def scan_progress():
    return get_scan_progress()


@app.get("/api/scan/signals/{signal_type}")
async def get_signals_by_type(signal_type: str):
    scan = get_latest_scan()
    if not scan:
        return []
    if signal_type.upper() == "ALL":
        return _sanitize(scan.get("signals", []))
    filtered = [s for s in scan.get("signals", []) if s.get("signal_type", "").upper() == signal_type.upper()]
    return _sanitize(filtered)


@app.get("/api/scan/signals/breakouts")
async def get_breakout_signals():
    scan = get_latest_scan()
    if not scan:
        return []
    filtered = [s for s in scan.get("signals", []) if s.get("has_breakout")]
    return _sanitize(filtered)


@app.get("/api/scan/signals/by-market/{market_type}")
async def get_signals_by_market(market_type: str):
    scan = get_latest_scan()
    if not scan:
        return []
    filtered = [s for s in scan.get("signals", []) if s.get("market_type") == market_type]
    return _sanitize(filtered)


@app.get("/api/trade-rec")
async def trade_recommendation(
    epic: str = Query(...),
    account_size: float = Query(10000),
    risk_pct: float = Query(1.0),
    mode: str = Query("spread_bet"),
):
    scan = get_latest_scan()
    if not scan:
        return {"error": "No scan data"}
    sig = next((s for s in scan.get("signals", []) if s.get("epic") == epic or s.get("yahoo") == epic), None)
    if not sig:
        return {"error": f"Instrument {epic} not found in scan"}

    inst = next((i for i in INSTRUMENTS if i.get("ig_epic", epic) == epic or i["yahoo"] == epic), None)
    if not inst:
        return {"error": "Instrument not found"}

    prices = fetch_prices(inst, "1d")
    df = prices_to_df(prices)
    ti = compute_indicators(df, inst["market_type"])

    tf_agree = sig.get("confluence", 0)

    rec = generate_recommendation(
        signal=sig["signal_type"],
        composite_score=sig["composite_score"],
        confidence=sig["confidence"],
        ti=ti,
        market_type=inst["market_type"],
        account_size=account_size,
        risk_pct=risk_pct,
        mode=mode,
        timeframe_agreement=tf_agree,
        has_volume_spike=sig.get("has_volume_spike", False),
        has_breakout=sig.get("has_breakout", False),
        has_divergence=sig.get("has_divergence", False),
    )

    rec["instrument"] = sig
    return _sanitize(rec)


@app.get("/api/instrument/{epic}")
async def instrument_detail(epic: str):
    scan = get_latest_scan()
    if not scan:
        return {"error": "No scan data"}
    sig = next((s for s in scan.get("signals", []) if s.get("epic") == epic), None)
    if not sig:
        return {"error": "Not found"}
    return _sanitize(sig)


# ── Journal endpoints ──

@app.post("/api/journal/trade")
async def journal_open_trade(data: dict):
    return trade_journal.open_trade(data)


@app.patch("/api/journal/trade/{trade_id}")
async def journal_update_trade(trade_id: int, updates: dict):
    return trade_journal.update_trade(trade_id, updates)


@app.put("/api/journal/trade/{trade_id}/close")
async def journal_close_trade(trade_id: int, data: dict = {}):
    exit_price = data.get("exit_price", 0)
    outcome = data.get("outcome", "manual")
    notes = data.get("notes", "")
    return trade_journal.close_trade(trade_id, exit_price, outcome, notes)


@app.delete("/api/journal/trade/{trade_id}")
async def journal_delete_trade(trade_id: int):
    return trade_journal.delete_trade(trade_id)


@app.get("/api/journal/open")
async def journal_open():
    return trade_journal.get_open_trades()


@app.get("/api/journal/history")
async def journal_history(limit: int = Query(50)):
    return trade_journal.get_trade_history(limit)


@app.get("/api/journal/stats")
async def journal_stats():
    return trade_journal.get_stats()


@app.get("/api/journal/alerts")
async def journal_alerts():
    return trade_journal.get_trade_alerts()


@app.get("/api/journal/equity-curve")
async def journal_equity_curve():
    return trade_journal.get_equity_curve()


@app.get("/api/journal/risk-of-ruin")
async def journal_risk_of_ruin(account_size: float = Query(1000)):
    return trade_journal.get_risk_of_ruin(account_size)


def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize(i) for i in obj]
    elif isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
    return obj


import math
