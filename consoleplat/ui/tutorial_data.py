from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialStep:
    target: str
    title: str
    body: str
    safety_note: str = ""
    screenshot: str = ""


TUTORIALS: dict[str, tuple[TutorialStep, ...]] = {
    "monitor": (
        TutorialStep(
            "monitorMetricsAnchor",
            "先看店铺状态",
            "这里汇总待发货、备货件数和异常提醒。教程只说明页面，不会提交或发货。",
            screenshot="assets/images/tutorial/monitor.png",
        ),
        TutorialStep(
            "monitorControlsAnchor",
            "控制刷新节奏",
            "选择店铺和刷新间隔后，可以手动刷新或开始监控。5 秒只是默认值，可以在设置中调整。",
            screenshot="assets/images/tutorial/monitor.png",
        ),
        TutorialStep(
            "monitorOrdersAnchor",
            "查看待处理商品",
            "刷新成功后，待处理商品会显示在表格里，后续可导出备货单并交接到发布页。",
            screenshot="assets/images/tutorial/monitor.png",
        ),
    ),
    "publish": (
        TutorialStep(
            "publishHeaderAnchor",
            "确认发布任务",
            "发布页承接监控导出的线索，用来确认批次、数量和后续生图分流。",
            screenshot="assets/images/tutorial/publish.png",
        ),
        TutorialStep(
            "publishFormAnchor",
            "填写任务信息",
            "这里配置店铺、任务名称、产品数量和输入来源。发布前需要人工确认范围。",
            screenshot="assets/images/tutorial/publish.png",
        ),
        TutorialStep(
            "publishActionsAnchor",
            "进入下一步",
            "确认后可准备本地生图、AI 改图或同步到上架流程。",
            screenshot="assets/images/tutorial/publish.png",
        ),
    ),
    "local_image": (
        TutorialStep(
            "localImageConfigAnchor",
            "配置本地生图",
            "选择店铺、风格、张数和货号范围，生成任务会在后台运行。",
            screenshot="assets/images/tutorial/local_image.png",
        ),
        TutorialStep(
            "localImageStatusAnchor",
            "关注进度和输出",
            "这里显示任务状态、输出目录和日志，失败项会保留在清单中。",
            screenshot="assets/images/tutorial/local_image.png",
        ),
    ),
    "ai_edit": (
        TutorialStep(
            "aiEditImagesAnchor",
            "选择输入图片",
            "先添加需要 AI 改图的图片，避免把账号或敏感截图放入任务。",
            screenshot="assets/images/tutorial/ai_edit.png",
        ),
        TutorialStep(
            "aiEditRequestAnchor",
            "填写改图要求",
            "在提示词中描述目标效果，API Key 应通过设置或安全输入管理。",
            screenshot="assets/images/tutorial/ai_edit.png",
        ),
        TutorialStep(
            "aiEditQueueAnchor",
            "查看任务结果",
            "任务队列会显示进度、失败原因和输出路径。",
            screenshot="assets/images/tutorial/ai_edit.png",
        ),
    ),
    "putaway": (
        TutorialStep(
            "putawayEmbedAnchor",
            "连接自动上架工具",
            "这里嵌入或唤起 PutawayAiRobot，读取投放目录中的图片和 xlsx。",
            screenshot="assets/images/tutorial/putaway.png",
        ),
        TutorialStep(
            "putawayStatusAnchor",
            "处理失败提示",
            "如果嵌入失败或依赖缺失，状态区会显示原因，原项目仍可独立运行。",
            screenshot="assets/images/tutorial/putaway.png",
        ),
    ),
    "apply": (
        TutorialStep(
            "applyEmbedAnchor",
            "进入申请合规流程",
            "这里承接 ApplyGoods 的申请、合规、JIT 和库存等后置能力。",
            screenshot="assets/images/tutorial/apply.png",
        ),
        TutorialStep(
            "applySafetyAnchor",
            "注意人工确认点",
            "合规上传、库存、地址修改等会改变真实状态，必须保留确认或明确自动配置。",
            screenshot="assets/images/tutorial/apply.png",
        ),
    ),
    "settings": (
        TutorialStep(
            "settingsPathsAnchor",
            "检查项目路径",
            "确认四个源项目路径、输出目录和投放目录正确。",
            screenshot="assets/images/tutorial/settings.png",
        ),
        TutorialStep(
            "settingsBrowserAnchor",
            "配置浏览器连接",
            "默认 CDP 地址可用 127.0.0.1:9222，但应按实际浏览器调整。",
            screenshot="assets/images/tutorial/settings.png",
        ),
        TutorialStep(
            "settingsSecurityAnchor",
            "保护敏感信息",
            "账号、Cookie、Token 和 API Key 不应写入日志或普通配置文件。",
            screenshot="assets/images/tutorial/settings.png",
        ),
    ),
}


def get_tutorial_steps(page_key: str) -> tuple[TutorialStep, ...]:
    return TUTORIALS.get(page_key, ())
