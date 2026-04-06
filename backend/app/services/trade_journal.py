import sqlite3
import json
import math
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent.parent / "trade_journal.db"


def _get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epic TEXT NOT NULL,
            name TEXT NOT NULL,
            market_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            trade_rating TEXT,
            confidence REAL DEFAULT 0,
            entry_price REAL NOT NULL,
            stop_loss REAL,
            take_profit REAL,
            position_size REAL DEFAULT 0,
            risk_amount REAL DEFAULT 0,
            status TEXT DEFAULT 'open',
            outcome TEXT,
            exit_price REAL,
            profit_loss REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            opened_at TEXT NOT NULL,
            closed_at TEXT,
            expected_hold_time TEXT,
            scan_mode TEXT DEFAULT 'swing'
        );
        CREATE TABLE IF NOT EXISTS signal_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            epic TEXT NOT NULL,
            name TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            confidence REAL DEFAULT 0,
            score REAL DEFAULT 0,
            trade_rating TEXT,
            scanned_at TEXT NOT NULL
        );
    """)
    conn.commit()


def open_trade(data: dict) -> dict:
    conn = _get_conn()
    now = datetime.utcnow().isoformat()
    cur = conn.execute("""
        INSERT INTO trades (epic, name, market_type, direction, signal_type, trade_rating, confidence,
            entry_price, stop_loss, take_profit, position_size, risk_amount, status,
            notes, opened_at, expected_hold_time, scan_mode)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
    """, (
        data["epic"], data["name"], data["market_type"], data["direction"],
        data["signal_type"], data.get("trade_rating"), data.get("confidence", 0),
        data["entry_price"], data.get("stop_loss"), data.get("take_profit"),
        data.get("position_size", 0), data.get("risk_amount", 0),
        data.get("notes", ""), now, data.get("expected_hold_time"), data.get("scan_mode", "swing"),
    ))
    conn.commit()
    trade_id = cur.lastrowid
    conn.close()
    return {"id": trade_id, "opened_at": now}


def close_trade(trade_id: int, exit_price: float, outcome: str = "manual", notes: str = "") -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": "Trade not found"}
    entry = row["entry_price"]
    direction = row["direction"]
    size = row["position_size"]
    if direction == "BUY":
        pl = (exit_price - entry) * size
    else:
        pl = (entry - exit_price) * size
    now = datetime.utcnow().isoformat()
    conn.execute("""
        UPDATE trades SET status='closed', exit_price=?, profit_loss=?, outcome=?,
            closed_at=?, notes=notes || ? WHERE id=?
    """, (exit_price, round(pl, 2), outcome, now, f"\n{notes}" if notes else "", trade_id))
    conn.commit()
    conn.close()
    return {"id": trade_id, "profit_loss": round(pl, 2), "closed_at": now}


def update_trade(trade_id: int, updates: dict) -> dict:
    conn = _get_conn()
    allowed = {"entry_price", "stop_loss", "take_profit", "position_size", "risk_amount", "notes", "exit_price", "profit_loss", "status"}
    sets = []
    vals = []
    for k, v in updates.items():
        if k in allowed:
            sets.append(f"{k}=?")
            vals.append(v)
    if not sets:
        conn.close()
        return {"error": "No valid fields"}
    vals.append(trade_id)
    conn.execute(f"UPDATE trades SET {', '.join(sets)} WHERE id=?", vals)
    conn.commit()
    conn.close()
    return {"id": trade_id, "updated": True}


def delete_trade(trade_id: int) -> dict:
    conn = _get_conn()
    conn.execute("DELETE FROM trades WHERE id=?", (trade_id,))
    conn.commit()
    conn.close()
    return {"deleted": trade_id}


def get_open_trades() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM trades WHERE status='open' ORDER BY opened_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_trade_history(limit: int = 50) -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM trades WHERE status='closed' ORDER BY closed_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM trades WHERE status='closed'").fetchall()
    conn.close()
    if not rows:
        return {"total_trades": 0, "win_rate": 0, "total_pl": 0, "avg_win": 0, "avg_loss": 0, "profit_factor": 0}

    wins = [r for r in rows if r["profit_loss"] > 0]
    losses = [r for r in rows if r["profit_loss"] <= 0]
    total_pl = sum(r["profit_loss"] for r in rows)
    avg_win = sum(r["profit_loss"] for r in wins) / len(wins) if wins else 0
    avg_loss = sum(r["profit_loss"] for r in losses) / len(losses) if losses else 0
    gross_profit = sum(r["profit_loss"] for r in wins) if wins else 0
    gross_loss = abs(sum(r["profit_loss"] for r in losses)) if losses else 1

    return {
        "total_trades": len(rows),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(rows) * 100, 1),
        "total_pl": round(total_pl, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(gross_profit / max(gross_loss, 0.01), 2),
        "best_trade": max((r["profit_loss"] for r in rows), default=0),
        "worst_trade": min((r["profit_loss"] for r in rows), default=0),
    }


def get_equity_curve() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT closed_at, profit_loss FROM trades WHERE status='closed' ORDER BY closed_at").fetchall()
    conn.close()
    curve = []
    cum = 0
    peak = 0
    for r in rows:
        cum += r["profit_loss"]
        peak = max(peak, cum)
        curve.append({
            "date": r["closed_at"],
            "cumulative_pl": round(cum, 2),
            "drawdown": round(cum - peak, 2),
        })
    return curve


def get_risk_of_ruin(account_size: float = 1000) -> dict:
    conn = _get_conn()
    rows = conn.execute("SELECT profit_loss FROM trades WHERE status='closed'").fetchall()
    conn.close()
    if len(rows) < 5:
        return {"edge": 0, "payoff_ratio": 0, "risk_of_ruin": 1.0, "verdict": "Insufficient data"}

    wins = [r["profit_loss"] for r in rows if r["profit_loss"] > 0]
    losses = [abs(r["profit_loss"]) for r in rows if r["profit_loss"] <= 0]

    win_rate = len(wins) / len(rows)
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 1
    payoff = avg_win / avg_loss if avg_loss > 0 else 1
    edge = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    ror_results = {}
    for pct in [0.10, 0.20, 0.30, 0.50]:
        units = (account_size * pct) / abs(edge) if edge != 0 else float("inf")
        if units < 1:
            ror = 1.0
        else:
            ror = ((1 - edge / avg_loss) / (1 + edge / avg_loss)) ** units if avg_loss > 0 and edge > 0 else 1.0
        ror_results[f"{int(pct*100)}%"] = round(min(ror, 1.0), 4)

    if edge > 0:
        verdict = "Positive edge detected"
    else:
        verdict = "Negative edge - review strategy"

    return {
        "win_rate": round(win_rate, 3),
        "payoff_ratio": round(payoff, 2),
        "edge_per_trade": round(edge, 2),
        "risk_of_ruin": ror_results,
        "verdict": verdict,
    }


def log_signal(data: dict):
    conn = _get_conn()
    conn.execute("""
        INSERT INTO signal_log (epic, name, signal_type, confidence, score, trade_rating, scanned_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("epic", ""), data.get("name", ""), data.get("signal_type", ""),
        data.get("confidence", 0), data.get("composite_score", 0),
        data.get("trade_rating"), datetime.utcnow().isoformat(),
    ))
    conn.commit()
    conn.close()


def get_trade_alerts() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM trades WHERE status='open'").fetchall()
    conn.close()
    alerts = []
    now = datetime.utcnow()
    for r in rows:
        if r["expected_hold_time"] and r["opened_at"]:
            try:
                opened = datetime.fromisoformat(r["opened_at"])
                hours_open = (now - opened).total_seconds() / 3600
                if "day" in r["expected_hold_time"].lower():
                    max_hours = 20 * 24
                elif "hour" in r["expected_hold_time"].lower():
                    max_hours = 24
                else:
                    max_hours = 7 * 24
                pct = hours_open / max_hours
                if pct >= 1.0:
                    alerts.append({"trade_id": r["id"], "name": r["name"], "status": "OVERDUE", "pct_elapsed": round(pct, 2)})
                elif pct >= 0.75:
                    alerts.append({"trade_id": r["id"], "name": r["name"], "status": "APPROACHING", "pct_elapsed": round(pct, 2)})
            except Exception:
                pass
    return alerts
