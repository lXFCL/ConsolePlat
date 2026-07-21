from workers import BatchPublishWorker, CdpActionWorker


def test_single_action_forwards_declare_price(monkeypatch):
    captured = {}

    def fake_flow(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("workers.select_shop_category_flow", fake_flow)

    worker = CdpActionWorker(
        "select_shop_category",
        "http://127.0.0.1:9222",
        "https://example.test/create",
        shop_name="店铺A",
        category="T恤",
        declare_price="14.50",
    )
    worker.run()

    assert captured["declare_price"] == "14.5"


def test_batch_worker_snapshots_and_forwards_declare_price(monkeypatch):
    captured = {}

    def fake_flow(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("workers.select_shop_category_flow", fake_flow)

    worker = BatchPublishWorker(
        "http://127.0.0.1:9222",
        "https://example.test/create",
        "",
        [],
        1,
        declare_price="14.50",
    )
    row = {
        "shop_name": "店铺A",
        "category": "T恤",
        "title": "标题",
        "sku": "SKU-1",
        "color": "白",
    }

    assert worker.declare_price == "14.5"
    assert worker._run_one({"url": "https://example.test/create"}, row, 1, 1, 0) is True
    assert captured["declare_price"] == "14.5"


def test_single_action_forwards_custom_weights(monkeypatch):
    captured = {}

    def fake_flow(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("workers.select_shop_category_flow", fake_flow)
    weights = (140, 145, 150, 155, 160)

    worker = CdpActionWorker(
        "select_shop_category",
        "http://127.0.0.1:9222",
        "https://example.test/create",
        shop_name="店铺A",
        category="T恤",
        weights=weights,
    )
    worker.run()

    assert captured["weights"] == weights


def test_batch_worker_snapshots_and_forwards_custom_weights(monkeypatch):
    captured = {}

    def fake_flow(*args, **kwargs):
        captured.update(kwargs)

    monkeypatch.setattr("workers.select_shop_category_flow", fake_flow)
    weights = (140, 145, 150, 155, 160)

    worker = BatchPublishWorker(
        "http://127.0.0.1:9222",
        "https://example.test/create",
        "",
        [],
        1,
        weights=weights,
    )
    row = {
        "shop_name": "店铺A",
        "category": "T恤",
        "title": "标题",
        "sku": "SKU-1",
        "color": "白",
    }

    assert worker.weights == weights
    assert worker._run_one({"url": "https://example.test/create"}, row, 1, 1, 0) is True
    assert captured["weights"] == weights
