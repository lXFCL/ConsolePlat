from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class UrgencyOrder:
    order_id: str
    product_sku: str
    sku_code: str
    color: str
    size: str
    quantity: int
    age_minutes: int
    status: str


@dataclass(frozen=True)
class MonitorEvent:
    time_text: str
    level: str
    message: str


@dataclass(frozen=True)
class MonitorSnapshot:
    shop_name: str
    region: str
    fetched_at: datetime
    refresh_interval_seconds: int
    metrics: dict[str, int]
    orders: tuple[UrgencyOrder, ...]
    events: tuple[MonitorEvent, ...]
    source_status: str = "演示数据源"

    @classmethod
    def empty(
        cls,
        shop_name: str = "YUHOOBO",
        region: str = "全球",
        refresh_interval_seconds: int = 5,
        source_status: str = "等待刷新",
        message: str = "尚未读取真实页面数据",
    ) -> "MonitorSnapshot":
        now = datetime.now()
        return cls(
            shop_name=shop_name,
            region=region,
            fetched_at=now,
            refresh_interval_seconds=refresh_interval_seconds,
            metrics={
                "待发货": 0,
                "备货件数": 0,
                "高优先级": 0,
                "异常提醒": 0,
            },
            orders=(),
            events=(MonitorEvent(now.strftime("%H:%M:%S"), "notice", message),),
            source_status=source_status,
        )

    @classmethod
    def demo(cls, seed: int = 0, refresh_interval_seconds: int = 5) -> "MonitorSnapshot":
        now = datetime.now()
        offset = max(0, int(seed))
        orders = (
            UrgencyOrder(f"WB260619{4882401 + offset}", f"SZW-{3113 + offset}", f"SZW-{3113 + offset}-M", "黑色", "M", 12 + offset, 4, "新增待发货"),
            UrgencyOrder(f"WB260619{4882412 + offset}", f"BO-{1616 + offset}", f"BO-{1616 + offset}-XL", "白色", "XL", 7, 11, "待生成拿货表"),
            UrgencyOrder(f"WB260619{4882428 + offset}", f"SZW-{3114 + offset}", f"SZW-{3114 + offset}-L", "黑色", "L", 18, 19, "待确认库存"),
            UrgencyOrder(f"WB260619{4882455 + offset}", f"BO-{1617 + offset}", f"BO-{1617 + offset}-S", "白色", "S", 5, 28, "普通备货"),
        )
        total_quantity = sum(order.quantity for order in orders)
        metrics = {
            "待发货": len(orders),
            "备货件数": total_quantity,
            "高优先级": sum(1 for order in orders if order.age_minutes <= 12),
            "异常提醒": 1 if offset % 2 else 0,
        }
        events = (
            MonitorEvent(now.strftime("%H:%M:%S"), "notice", f"发现 {metrics['待发货']} 条待处理备货记录"),
            MonitorEvent((now - timedelta(seconds=18)).strftime("%H:%M:%S"), "ok", "页面监控刷新完成"),
            MonitorEvent((now - timedelta(minutes=1)).strftime("%H:%M:%S"), "warn", "BO 店铺存在一条库存待确认记录"),
        )
        return cls(
            shop_name="YUHAOBO / YUHOOBO",
            region="全球",
            fetched_at=now,
            refresh_interval_seconds=refresh_interval_seconds,
            metrics=metrics,
            orders=orders,
            events=events,
        )

    def diff_new_orders(self, previous: "MonitorSnapshot | None") -> tuple[UrgencyOrder, ...]:
        if previous is None:
            return self.orders
        previous_ids = {order.order_id for order in previous.orders}
        return tuple(order for order in self.orders if order.order_id not in previous_ids)

    def to_dict(self) -> dict[str, Any]:
        return {
            "shop_name": self.shop_name,
            "region": self.region,
            "fetched_at": self.fetched_at.isoformat(),
            "refresh_interval_seconds": self.refresh_interval_seconds,
            "metrics": dict(self.metrics),
            "orders": [order.__dict__ for order in self.orders],
            "events": [event.__dict__ for event in self.events],
            "source_status": self.source_status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MonitorSnapshot":
        return cls(
            shop_name=str(data.get("shop_name") or "YUHOOBO"),
            region=str(data.get("region") or "全球"),
            fetched_at=datetime.fromisoformat(str(data.get("fetched_at"))),
            refresh_interval_seconds=int(data.get("refresh_interval_seconds") or 5),
            metrics={str(key): int(value or 0) for key, value in (data.get("metrics") or {}).items()},
            orders=tuple(UrgencyOrder(**item) for item in (data.get("orders") or [])),
            events=tuple(MonitorEvent(**item) for item in (data.get("events") or [])),
            source_status=str(data.get("source_status") or "未知数据源"),
        )


class DemoMonitorSource:
    def __init__(self, refresh_interval_seconds: int = 5) -> None:
        self.refresh_interval_seconds = refresh_interval_seconds
        self._tick = 0

    def fetch(self) -> MonitorSnapshot:
        snapshot = MonitorSnapshot.demo(seed=self._tick, refresh_interval_seconds=self.refresh_interval_seconds)
        self._tick += 1
        return snapshot


class EmptyMonitorSource:
    def __init__(self, refresh_interval_seconds: int = 5, shop_name: str = "YUHOOBO") -> None:
        self.refresh_interval_seconds = refresh_interval_seconds
        self.shop_name = shop_name

    def fetch(self) -> MonitorSnapshot:
        return MonitorSnapshot.empty(
            shop_name=self.shop_name,
            refresh_interval_seconds=self.refresh_interval_seconds,
            source_status="未配置真实账号",
            message="请先在设置中配置店铺账号后再刷新",
        )
