import importlib.util

import pytest

from regscope.collectors import SQLAlchemyCollector


def test_sqlalchemy_collector_import_does_not_require_dependency() -> None:
    assert SQLAlchemyCollector is not None


def test_sqlalchemy_collector_explains_missing_extra() -> None:
    if importlib.util.find_spec("sqlalchemy") is not None:
        pytest.skip("SQLAlchemy is installed in this environment")

    with pytest.raises(RuntimeError, match=r"regscope\[db\]"):
        SQLAlchemyCollector().attach(object())


def test_sqlalchemy_collector_counts_real_table_operations() -> None:
    sqlalchemy = pytest.importorskip("sqlalchemy")
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    metadata = sqlalchemy.MetaData()
    records = sqlalchemy.Table(
        "records",
        metadata,
        sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
        sqlalchemy.Column("value", sqlalchemy.String),
    )
    collector = SQLAlchemyCollector()
    collector.attach(engine)
    try:
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(records.insert().values(value="observed"))
            result = connection.execute(sqlalchemy.select(records.c.value))
            assert result.scalar_one() == "observed"
        assert collector.query_count >= 3
    finally:
        collector.detach()


def test_track_publishes_sqlalchemy_query_metric(tmp_path) -> None:
    sqlalchemy = pytest.importorskip("sqlalchemy")
    from regscope import track

    engine = sqlalchemy.create_engine("sqlite:///:memory:")

    @track(baseline_dir=tmp_path, sqlalchemy_engine=engine)
    def query_value() -> int:
        with engine.connect() as connection:
            return int(connection.exec_driver_sql("select 1").scalar_one())

    assert query_value() == 1
    assert query_value.last_profile.metrics["db_queries"] == 1
