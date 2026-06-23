from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavItem:
    key: str
    title: str
    icon: str
    description: str


@dataclass(frozen=True)
class TaskCard:
    title: str
    subtitle: str
    project_key: str
    accent: str
    status: str = "框架占位"


@dataclass
class ShellState:
    active_page: str = "monitor"


DEFAULT_NAV_ITEMS: tuple[NavItem, ...] = (
    NavItem("monitor", "监控", "⌂", "店铺实时状态与待处理提醒"),
    NavItem("publish", "发布", "□", "产品任务模板、确认与上架衔接"),
    NavItem("local_image", "生图", "✦", "本地印花生成与风格批次"),
    NavItem("ai_edit", "改图", "✎", "AI 图片改造与参考图任务"),
    NavItem("putaway", "上架", "▷", "轻集成 PutawayAiRobot 启动和同步"),
    NavItem("apply", "合规", "✓", "衔接 ApplyGoods 后置流程"),
    NavItem("settings", "设置", "⚙", "路径、浏览器、等待时间和密钥"),
)


DEFAULT_TASK_CARDS: tuple[TaskCard, ...] = (
    TaskCard("实时监控", "Temu 店铺待发货与销量提醒", "sendgoods", "#ff8bbd"),
    TaskCard("产品发布", "模板确认、生图分流与上架衔接", "consoleplat", "#7aa7ff"),
    TaskCard("本地生图", "风格、张数、店铺与货号批次", "posaiimg", "#8ad7c4"),
    TaskCard("AI 改图", "图片输入、要求描述、任务进度", "posaiimg", "#b998ff"),
    TaskCard("自动上架", "投放目录与 PutawayAiRobot 启动", "putaway", "#ffbd63"),
    TaskCard("申请合规", "ApplyGoods 一条龙与等待时间", "applygoods", "#7bdc8d"),
)


PAGE_TITLES: dict[str, str] = {
    "monitor": "实时监控",
    "publish": "产品任务发布",
    "local_image": "本地生图",
    "ai_edit": "AI 改图",
    "putaway": "自动上架",
    "apply": "申请 / 合规",
    "settings": "设置",
}
