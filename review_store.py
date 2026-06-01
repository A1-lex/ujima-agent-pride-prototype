from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "review_history.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS review_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                member_name TEXT,
                county TEXT,
                livelihood TEXT,
                amount_kes INTEGER,
                route TEXT,
                risk_flags_json TEXT,
                reviewer_decision TEXT,
                reviewer_note TEXT,
                post_review_status TEXT,
                flow_state_json TEXT,
                result_json TEXT
            )
            """
        )
        conn.commit()


def save_review_record(
    *,
    member_name: str,
    county: str,
    livelihood: str,
    amount_kes: int,
    route: str,
    risk_flags: List[str],
    reviewer_decision: str,
    reviewer_note: str,
    post_review_status: str,
    flow_state: Dict[str, Any],
    result: Dict[str, Any],
) -> int:
    init_db()
    created_at = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO review_history (
                created_at,
                member_name,
                county,
                livelihood,
                amount_kes,
                route,
                risk_flags_json,
                reviewer_decision,
                reviewer_note,
                post_review_status,
                flow_state_json,
                result_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                member_name,
                county,
                livelihood,
                amount_kes,
                route,
                json.dumps(risk_flags, ensure_ascii=False),
                reviewer_decision,
                reviewer_note,
                post_review_status,
                json.dumps(flow_state, ensure_ascii=False, default=str),
                json.dumps(result, ensure_ascii=False, default=str),
            ),
        )
        conn.commit()
        return int(cur.lastrowid)


def fetch_review_history(limit: int = 100) -> List[Dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM review_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    records: List[Dict[str, Any]] = []
    for row in rows:
        records.append(
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "member_name": row["member_name"],
                "county": row["county"],
                "livelihood": row["livelihood"],
                "amount_kes": row["amount_kes"],
                "route": row["route"],
                "risk_flags": json.loads(row["risk_flags_json"] or "[]"),
                "reviewer_decision": row["reviewer_decision"],
                "reviewer_note": row["reviewer_note"],
                "post_review_status": row["post_review_status"],
                "flow_state": json.loads(row["flow_state_json"] or "{}"),
                "result": json.loads(row["result_json"] or "{}"),
            }
        )
    return records


def export_review_history_json(limit: int = 100) -> str:
    records = fetch_review_history(limit=limit)
    return json.dumps(records, indent=2, ensure_ascii=False, default=str)
