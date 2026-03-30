from __future__ import annotations

from pathlib import Path

from llm_bench.models import BenchmarkResult
from llm_bench.storage import ResultsDB


class TestResultsDB:
    """SQLite storage for benchmark results."""

    def test_save_and_retrieve(
        self, tmp_db: ResultsDB, sample_result: BenchmarkResult
    ) -> None:
        tmp_db.save_result(sample_result)
        results = tmp_db.get_results()
        assert len(results) == 1
        assert results[0].backend == sample_result.backend
        assert results[0].model == sample_result.model

    def test_save_results_batch(
        self, tmp_db: ResultsDB, sample_result: BenchmarkResult
    ) -> None:
        batch = [sample_result, sample_result]
        tmp_db.save_results(batch)
        results = tmp_db.get_results()
        assert len(results) == 2

    def test_get_results_filter_backend(
        self, tmp_db: ResultsDB, sample_result: BenchmarkResult
    ) -> None:
        tmp_db.save_result(sample_result)
        # Filter by matching backend
        results = tmp_db.get_results(backend="ollama")
        assert len(results) == 1
        # Filter by non-matching backend
        results = tmp_db.get_results(backend="mlx-lm")
        assert len(results) == 0

    def test_get_results_filter_model(
        self, tmp_db: ResultsDB, sample_result: BenchmarkResult
    ) -> None:
        tmp_db.save_result(sample_result)
        results = tmp_db.get_results(model="llama3.2:3b")
        assert len(results) == 1
        results = tmp_db.get_results(model="nonexistent")
        assert len(results) == 0

    def test_context_manager(self, tmp_path: Path) -> None:
        db_path = tmp_path / "ctx_results.db"
        with ResultsDB(db_path) as db:
            assert db is not None
        # After exiting, the connection should be closed.
        # Reopening should work without error (file still exists).
        assert db_path.exists()

    def test_table_creation_idempotent(self, tmp_path: Path) -> None:
        db_path = tmp_path / "idem_results.db"
        db1 = ResultsDB(db_path)
        db1.close()
        # Creating a second instance on the same file should not raise.
        db2 = ResultsDB(db_path)
        db2.close()

    def test_wal_mode(self, tmp_db: ResultsDB) -> None:
        """Verify WAL journal mode is enabled."""
        import sqlite3

        # Access the underlying connection to check pragma.
        # ResultsDB should expose its connection or we query directly.
        conn = tmp_db._conn
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode == "wal"
