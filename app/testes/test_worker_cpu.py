from unittest.mock import patch, MagicMock
from pathlib import Path
import pytest
from app.worker.main import SubmissionWorker


def test_submission_worker_cpu_metrics():
    with patch("app.worker.main.SQSQueueManager"), patch("app.worker.main.SandboxExecutor"):
        worker = SubmissionWorker()
        metrics = worker.get_cpu_metrics()
        assert "cpu_percent" in metrics
        assert isinstance(metrics["cpu_percent"], (int, float))
        assert metrics["cpu_percent"] >= 0.0
        assert "load_1m" in metrics


def test_submission_worker_procfs_fallback(tmp_path, monkeypatch):
    """Testa o cálculo nativo de CPU via /proc/stat do Linux."""
    with patch("app.worker.main.SQSQueueManager"), patch("app.worker.main.SandboxExecutor"):
        worker = SubmissionWorker()

        # Força desativação do psutil para testar o fallback de Linux puro
        monkeypatch.setattr("app.worker.main.psutil", None)

        fake_stat_1 = "cpu  1000 0 200 8800 0 0 0 0 0 0\n"
        fake_stat_2 = "cpu  1200 0 300 8900 0 0 0 0 0 0\n"

        # Simula primeira leitura
        stat_file = tmp_path / "proc_stat"
        stat_file.write_text(fake_stat_1)
        monkeypatch.setattr("app.worker.main.Path", lambda p: stat_file if p == "/proc/stat" else Path(p))

        worker._init_cpu_metrics()
        assert worker.last_proc_stat is not None

        # Simula segunda leitura (mais carga de CPU)
        stat_file.write_text(fake_stat_2)
        metrics = worker.get_cpu_metrics()
        assert metrics["cpu_percent"] > 0.0
