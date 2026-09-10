import pytest

from regscope.collectors import HTTPCollector, RedisCollector, SQLAlchemyCollector


def test_sqlalchemy_collector_counts_real_engine_queries() -> None:
    sqlalchemy = pytest.importorskip("sqlalchemy")
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    collector = SQLAlchemyCollector()
    collector.attach(engine)
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("select 1")
            connection.exec_driver_sql("select 2")
        assert collector.query_count == 2
    finally:
        collector.detach()


def test_requests_collector_counts_real_session_request(monkeypatch) -> None:
    requests = pytest.importorskip("requests")
    response = requests.Response()
    response.status_code = 200

    def fake_send(self, request, **kwargs):
        return response

    monkeypatch.setattr(requests.sessions.Session, "send", fake_send)
    collector = HTTPCollector()
    collector.attach()
    try:
        result = requests.get("https://example.invalid")
        assert result.status_code == 200
        assert collector.request_count == 1
    finally:
        collector.detach()


def test_redis_collector_counts_real_client_command(monkeypatch) -> None:
    redis = pytest.importorskip("redis")

    def fake_execute(self, *args, **kwargs):
        return "PONG"

    monkeypatch.setattr(redis.Redis, "execute_command", fake_execute)
    collector = RedisCollector()
    collector.attach()
    try:
        client = redis.Redis()
        assert client.execute_command("PING") == "PONG"
        assert collector.command_count == 1
    finally:
        collector.detach()
