from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional, Dict, Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_db_path(user_id: str) -> str:
    return os.path.join("data", "user_state", user_id, "attempts.db")


def init_db(user_id: str) -> None:
    db_path = get_db_path(user_id)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                exam TEXT NOT NULL,
                section TEXT NOT NULL,
                question_folder TEXT NOT NULL,
                question_id TEXT NOT NULL,
                chosen_option TEXT,
                correct_option TEXT,
                is_correct INTEGER,
                seconds_spent INTEGER,
                extra_json TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def log_attempt(
    user_id: str,
    exam: str,
    section: str,
    question_folder: str,
    question_id: str,
    chosen_option: Optional[str],
    correct_option: Optional[str],
    seconds_spent: Optional[int],
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    init_db(user_id)
    db_path = get_db_path(user_id)

    is_correct = None
    if chosen_option is not None and correct_option is not None:
        is_correct = 1 if chosen_option == correct_option else 0

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO attempts (
              created_at, exam, section, question_folder, question_id,
              chosen_option, correct_option, is_correct, seconds_spent, extra_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                _utc_now(),
                exam,
                section,
                question_folder,
                question_id,
                chosen_option,
                correct_option,
                is_correct,
                seconds_spent,
                None if extra is None else __import__("json").dumps(extra),
            ),
        )
        conn.commit()
    finally:
        conn.close()
