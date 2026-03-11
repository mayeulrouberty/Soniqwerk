def test_celery_app_has_redis_broker():
    from workers.celery_app import celery_app
    assert "redis" in celery_app.conf.broker_url


def test_ingest_document_task_is_registered():
    import workers.tasks  # noqa: F401 — triggers task registration via @celery_app.task
    from workers.celery_app import celery_app
    registered = list(celery_app.tasks.keys())
    assert any("ingest_document" in name for name in registered)
