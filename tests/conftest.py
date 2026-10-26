"""Keep test runs from writing evidence logs into the repository's logs/ directory."""
import pytest


@pytest.fixture(autouse=True)
def _logs_in_tmp(monkeypatch, tmp_path_factory):
    monkeypatch.setenv("AGENT_LOG_DIR", str(tmp_path_factory.mktemp("logs")))
