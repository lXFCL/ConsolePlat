from consoleplat.services.monitor_service import DemoMonitorSource, MonitorSnapshot, UrgencyOrder


def test_demo_monitor_source_returns_snapshot_with_orders_and_metrics():
    source = DemoMonitorSource()

    snapshot = source.fetch()

    assert isinstance(snapshot, MonitorSnapshot)
    assert snapshot.refresh_interval_seconds == 5
    assert snapshot.metrics["待发货"] >= 1
    assert len(snapshot.orders) >= 3
    assert all(isinstance(order, UrgencyOrder) for order in snapshot.orders)


def test_snapshot_detects_new_orders_by_order_id():
    previous = MonitorSnapshot.demo(seed=1)
    current = MonitorSnapshot.demo(seed=2)

    new_orders = current.diff_new_orders(previous)

    assert new_orders
    assert all(order.order_id not in {old.order_id for old in previous.orders} for order in new_orders)


def test_monitor_snapshot_round_trips_through_dict():
    snapshot = MonitorSnapshot.demo(seed=3)

    restored = MonitorSnapshot.from_dict(snapshot.to_dict())

    assert restored == snapshot
