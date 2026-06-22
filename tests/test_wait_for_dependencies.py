"""Tests for wait_for_dependencies startup helper."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

ROOT = Path(__file__).resolve().parent.parent


def _load_wait_module():
    path = ROOT / "scripts" / "wait_for_dependencies.py"
    spec = importlib.util.spec_from_file_location("wait_for_dependencies", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_wait_for_postgres_succeeds_immediately() -> None:
    mod = _load_wait_module()
    mock_engine = MagicMock()
    mock_conn = MagicMock()
    mock_engine.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
    mock_engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    with patch.object(mod, "create_engine", return_value=mock_engine):
        mod.wait_for_postgres("postgresql://x", timeout_seconds=5, interval=0.01)


def test_wait_for_postgres_times_out() -> None:
    mod = _load_wait_module()
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = OperationalError("stmt", {}, Exception("down"))
    with patch.object(mod, "create_engine", return_value=mock_engine):
        with pytest.raises(SystemExit) as exc:
            mod.wait_for_postgres("postgresql://x", timeout_seconds=0.1, interval=0.01)
        assert exc.value.code == 1


def test_wait_for_redis_succeeds() -> None:
    mod = _load_wait_module()
    mock_client = MagicMock()
    mock_client.ping.return_value = True
    with patch.object(mod, "redis") as mock_redis_mod:
        mock_redis_mod.from_url.return_value = mock_client
        mod.wait_for_redis("redis://localhost:6379/0", timeout_seconds=5, interval=0.01)
