from k8s_agent.core.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.server_port == 7777
    assert s.inspection_interval_minutes == 30
    assert s.sqlite_path == "data/inspections.db"
    assert s.log_level == "INFO"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SERVER_PORT", "8888")
    monkeypatch.setenv("INSPECTION_INTERVAL_MINUTES", "10")
    s = Settings(_env_file=None)
    assert s.server_port == 8888
    assert s.inspection_interval_minutes == 10
