"""SQLite persistence layer for benchmark results.

Uses WAL journal mode for concurrent-read safety.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from types import TracebackType
from typing import Self

from llm_bench.models import (
    BenchmarkResult,
    BenchmarkSettings,
    QualityMetrics,
    TimingMetrics,
)

_CREATE_TABLE = """\
CREATE TABLE IF NOT EXISTS results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          INTEGER NOT NULL,
    backend_name    TEXT    NOT NULL,
    model_id        TEXT    NOT NULL,
    prompt_name     TEXT    NOT NULL,
    prompt_text     TEXT    NOT NULL,
    output_text     TEXT    NOT NULL,
    ttft_ms         REAL    NOT NULL,
    tps             REAL    NOT NULL,
    prompt_eval_tps REAL    NOT NULL,
    model_load_time_s REAL  NOT NULL,
    peak_memory_mb  REAL    NOT NULL,
    total_duration_s REAL   NOT NULL,
    perplexity      REAL,
    task_accuracy   REAL,
    run_index       INTEGER NOT NULL,
    timestamp       TEXT    NOT NULL,
    max_tokens      INTEGER NOT NULL,
    runs_per_config INTEGER NOT NULL
);
"""


class ResultsDB:
    """SQLite store for benchmark results with context-manager support."""

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute(_CREATE_TABLE)
        self._conn.commit()

    # -- context manager -----------------------------------------------------

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # -- writes --------------------------------------------------------------

    def save_result(self, result: BenchmarkResult) -> int:
        """Insert a single result row and return its row id."""
        run_id = (self.get_latest_run_id() or 0) + 1
        return self._insert_row(result, run_id)

    def save_results(self, results: list[BenchmarkResult]) -> list[int]:
        """Insert a batch of results under the same run_id and return their row ids."""
        run_id = (self.get_latest_run_id() or 0) + 1
        ids: list[int] = []
        for r in results:
            ids.append(self._insert_row(r, run_id))
        self._conn.commit()
        return ids

    # -- reads ---------------------------------------------------------------

    def get_results(
        self,
        backend: str | None = None,
        model: str | None = None,
    ) -> list[BenchmarkResult]:
        """Query results with optional backend/model filters."""
        clauses: list[str] = []
        params: list[str] = []
        if backend is not None:
            clauses.append("backend_name = ?")
            params.append(backend)
        if model is not None:
            clauses.append("model_id = ?")
            params.append(model)

        sql = "SELECT * FROM results"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY id"

        rows = self._conn.execute(sql, params).fetchall()
        return [self._row_to_result(row) for row in rows]

    def get_latest_run_id(self) -> int | None:
        """Return the highest run_id, or None if the table is empty."""
        row = self._conn.execute("SELECT MAX(run_id) FROM results").fetchone()
        return row[0] if row and row[0] is not None else None

    # -- lifecycle -----------------------------------------------------------

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    # -- internals -----------------------------------------------------------

    def _insert_row(self, result: BenchmarkResult, run_id: int) -> int:
        """Insert one result row; caller is responsible for committing."""
        q = result.quality
        cursor = self._conn.execute(
            """\
            INSERT INTO results (
                run_id, backend_name, model_id, prompt_name, prompt_text,
                output_text, ttft_ms, tps, prompt_eval_tps, model_load_time_s,
                peak_memory_mb, total_duration_s, perplexity, task_accuracy,
                run_index, timestamp, max_tokens, runs_per_config
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                result.backend_name,
                result.model_id,
                result.prompt_name,
                result.prompt_text,
                result.output_text,
                result.timing.ttft_ms,
                result.timing.tps,
                result.timing.prompt_eval_tps,
                result.timing.model_load_time_s,
                result.timing.peak_memory_mb,
                result.timing.total_duration_s,
                q.perplexity if q else None,
                q.task_accuracy if q else None,
                result.run_index,
                result.timestamp.isoformat(),
                result.settings.max_tokens,
                result.settings.runs_per_config,
            ),
        )
        self._conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    @staticmethod
    def _row_to_result(row: tuple[object, ...]) -> BenchmarkResult:
        """Deserialize a raw SQLite row into a BenchmarkResult."""
        # Column order mirrors _CREATE_TABLE:
        #  0  id
        #  1  run_id
        #  2  backend_name
        #  3  model_id
        #  4  prompt_name
        #  5  prompt_text
        #  6  output_text
        #  7  ttft_ms
        #  8  tps
        #  9  prompt_eval_tps
        # 10  model_load_time_s
        # 11  peak_memory_mb
        # 12  total_duration_s
        # 13  perplexity
        # 14  task_accuracy
        # 15  run_index
        # 16  timestamp
        # 17  max_tokens
        # 18  runs_per_config
        timing = TimingMetrics(
            ttft_ms=row[7],  # type: ignore[arg-type]
            tps=row[8],  # type: ignore[arg-type]
            prompt_eval_tps=row[9],  # type: ignore[arg-type]
            model_load_time_s=row[10],  # type: ignore[arg-type]
            peak_memory_mb=row[11],  # type: ignore[arg-type]
            total_duration_s=row[12],  # type: ignore[arg-type]
        )
        perplexity = row[13]
        task_accuracy = row[14]
        quality = (
            QualityMetrics(perplexity=perplexity, task_accuracy=task_accuracy)  # type: ignore[arg-type]
            if perplexity is not None or task_accuracy is not None
            else None
        )
        return BenchmarkResult(
            backend_name=row[2],  # type: ignore[arg-type]
            model_id=row[3],  # type: ignore[arg-type]
            prompt_name=row[4],  # type: ignore[arg-type]
            prompt_text=row[5],  # type: ignore[arg-type]
            output_text=row[6],  # type: ignore[arg-type]
            timing=timing,
            quality=quality,
            run_index=row[15],  # type: ignore[arg-type]
            timestamp=datetime.fromisoformat(row[16]),  # type: ignore[arg-type]
            settings=BenchmarkSettings(
                max_tokens=row[17],  # type: ignore[arg-type]
                runs_per_config=row[18],  # type: ignore[arg-type]
            ),
        )
