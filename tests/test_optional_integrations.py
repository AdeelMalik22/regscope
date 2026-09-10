import pytest
from concurrent.futures import ThreadPoolExecutor

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


def test_requests_collector_restores_existing_hook(monkeypatch) -> None:
    requests = pytest.importorskip("requests")
    original = requests.sessions.Session.request

    def existing_hook(self, method, url, *args, **kwargs):
        return requests.Response()

    monkeypatch.setattr(requests.sessions.Session, "request", existing_hook)
    collector = HTTPCollector()
    collector.attach()
    collector.detach()

    assert requests.sessions.Session.request is existing_hook
    monkeypatch.setattr(requests.sessions.Session, "request", original)


def test_requests_collector_does_not_clobber_later_hook(monkeypatch) -> None:
    requests = pytest.importorskip("requests")
    original = requests.sessions.Session.request
    collector = HTTPCollector()
    collector.attach()

    def later_hook(self, method, url, *args, **kwargs):
        return requests.Response()

    monkeypatch.setattr(requests.sessions.Session, "request", later_hook)
    collector.detach()

    assert requests.sessions.Session.request is later_hook
    monkeypatch.setattr(requests.sessions.Session, "request", original)


def test_requests_collector_counts_concurrent_calls(monkeypatch) -> None:
    requests = pytest.importorskip("requests")
    response = requests.Response()

    def fake_send(self, request, **kwargs):
        return response

    monkeypatch.setattr(requests.sessions.Session, "send", fake_send)
    collector = HTTPCollector()
    collector.attach()
    try:
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: requests.get("https://example.invalid"), range(8)))
        assert collector.request_count == 8
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


def test_redis_collector_restores_existing_hook(monkeypatch) -> None:
    redis = pytest.importorskip("redis")
    original = redis.Redis.execute_command

    def existing_hook(self, *args, **kwargs):
        return "PONG"

    monkeypatch.setattr(redis.Redis, "execute_command", existing_hook)
    collector = RedisCollector()
    collector.attach()
    collector.detach()

    assert redis.Redis.execute_command is existing_hook
    monkeypatch.setattr(redis.Redis, "execute_command", original)


def test_redis_collector_does_not_clobber_later_hook(monkeypatch) -> None:
    redis = pytest.importorskip("redis")
    original = redis.Redis.execute_command
    collector = RedisCollector()
    collector.attach()

    def later_hook(self, *args, **kwargs):
        return "PONG"

    monkeypatch.setattr(redis.Redis, "execute_command", later_hook)
    collector.detach()

    assert redis.Redis.execute_command is later_hook
    monkeypatch.setattr(redis.Redis, "execute_command", original)


def test_redis_collector_counts_concurrent_calls(monkeypatch) -> None:
    redis = pytest.importorskip("redis")

    def fake_execute(self, *args, **kwargs):
        return "PONG"

    monkeypatch.setattr(redis.Redis, "execute_command", fake_execute)
    collector = RedisCollector()
    collector.attach()
    try:
        client = redis.Redis()
        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(lambda _: client.execute_command("PING"), range(8)))
        assert collector.command_count == 8
    finally:
        collector.detach()
