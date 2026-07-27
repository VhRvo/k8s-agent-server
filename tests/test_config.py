from k8s_agent.core.config import Settings


def test_settings_defaults():
    s = Settings(_env_file=None)
    assert s.server_port == 7777
    assert s.cors_origin_list == [
        "http://localhost:7778",
        "http://127.0.0.1:7778",
    ]
    assert s.upstream_api_base_url == "http://172.16.30.62:7777"
    assert s.inspection_interval_minutes == 30
    assert s.sqlite_path == "data/inspections.db"
    assert s.log_level == "INFO"


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("SERVER_PORT", "8888")
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://console.example, https://console.internal",
    )
    monkeypatch.setenv("UPSTREAM_API_BASE_URL", "http://backend.example:9000")
    monkeypatch.setenv("INSPECTION_INTERVAL_MINUTES", "10")
    s = Settings(_env_file=None)
    assert s.server_port == 8888
    assert s.cors_origin_list == [
        "https://console.example",
        "https://console.internal",
    ]
    assert s.upstream_api_base_url == "http://backend.example:9000"
    assert s.inspection_interval_minutes == 10


def test_agent_settings_defaults():
    s = Settings(_env_file=None)
    assert s.agent_db_path == "data/agent.db"
    assert s.agent_user_id == "default"
    assert s.agent_history_messages == 20


def test_agent_settings_from_env(monkeypatch):
    monkeypatch.setenv("AGENT_DB_PATH", "/tmp/agent.db")
    monkeypatch.setenv("AGENT_USER_ID", "alice")
    monkeypatch.setenv("AGENT_HISTORY_MESSAGES", "50")
    s = Settings(_env_file=None)
    assert s.agent_db_path == "/tmp/agent.db"
    assert s.agent_user_id == "alice"
    assert s.agent_history_messages == 50
