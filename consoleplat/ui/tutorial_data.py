from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TutorialStep:
    target: str
    title: str
    body: str
    goal: str = ""
    actions: tuple[str, ...] = ()
    expected: str = ""
    tips: tuple[str, ...] = ()
    safety_note: str = ""
    screenshot: str = ""


MONITOR_SHOT = "assets/images/tutorial/monitor.png"
PUBLISH_SHOT = "assets/images/tutorial/publish.png"
LOCAL_IMAGE_SHOT = "assets/images/tutorial/local_image.png"
AI_EDIT_SHOT = "assets/images/tutorial/ai_edit.png"
PUTAWAY_SHOT = "assets/images/tutorial/putaway.png"
APPLY_SHOT = "assets/images/tutorial/apply.png"
SETTINGS_SHOT = "assets/images/tutorial/settings.png"


TUTORIALS: dict[str, tuple[TutorialStep, ...]] = {
    "monitor": (
        TutorialStep(
            "monitorMetricsAnchor",
            "看懂监控概览",
            "监控页用于读取 Temu Agent Seller 的紧急备货/待发货信息，并把结果交给拿货表和发布流程。",
            goal="先判断当前店铺有没有需要处理的数据，以及刷新结果是否来自真实页面。",
            actions=(
                "查看四个数字卡片：待发货、备货件数、高优先级、异常提醒。",
                "查看右上角来源文字，确认是等待刷新、读取失败，还是真实页面数据。",
                "如果数值一直为 0，先不要下结论，继续看刷新控制区和事件流。",
            ),
            expected="正常读取后，来源会显示店铺、地区和页面状态；有新数据时表格会出现待处理商品。",
            tips=(
                "监控页本身只读取页面和生成本地文件，不会点击发货、提交或加入发货台。",
                "如果想改默认店铺、Chrome 调试地址或拿货表导出目录，到 设置 > 监控 修改。",
            ),
            safety_note="遇到登录、短信或滑块验证时，需要人工在浏览器里完成验证。",
            screenshot=MONITOR_SHOT,
        ),
        TutorialStep(
            "monitorControlsAnchor",
            "配置刷新和店铺",
            "这里决定软件读哪个店铺、多久读一次页面，以及是否立即读取一次。",
            goal="让监控读取正确店铺，并避免过快刷新影响登录态或人工操作。",
            actions=(
                "在“店铺”下拉框选择当前要监控的店铺。",
                "在秒数框设置刷新间隔；默认 5 秒，页面不稳定时可以调大。",
                "点击“立即刷新”只读取一次；点击“开始监控”会按间隔循环读取。",
                "如果 Chrome 调试地址不对，到 设置 > 监控 修改 Chrome 调试地址。",
            ),
            expected="点击刷新后，来源状态会变成正在读取页面，完成后事件流会记录读取结果。",
            tips=(
                "Chrome 调试地址默认可用 http://127.0.0.1:9222，但必须与你实际打开的浏览器一致。",
                "拿货表导出目录在 设置 > 监控 > 拿货表导出目录 修改。",
            ),
            screenshot=MONITOR_SHOT,
        ),
        TutorialStep(
            "monitorOrdersAnchor",
            "导出拿货表并交接发布",
            "待处理商品表格出现数据后，可以导出备货单，再把线索带到发布页。",
            goal="确认表格内容来自最新刷新，再生成本地拿货表文件。",
            actions=(
                "先看待处理商品表格的备货单、货号、SKU、颜色、尺码和件数。",
                "点击“导出备货单”会调用 SendGoods 规则生成 Excel。",
                "导出成功后会出现“去发布”入口，可把店铺、数量和输出路径带到发布页。",
                "如果想改 Excel 存放位置，到 设置 > 监控 > 拿货表导出目录 修改。",
            ),
            expected="导出成功后，事件流和来源状态会显示结果，发布页能自动带入任务线索。",
            tips=(
                "导出动作只写本地文件，不会修改 Temu 页面状态。",
                "如果表格为空，先完成页面登录并重新刷新。",
            ),
            screenshot=MONITOR_SHOT,
        ),
    ),
    "publish": (
        TutorialStep(
            "publishHeaderAnchor",
            "发布页负责串联流程",
            "发布页不是直接上架按钮，而是把拿货表、生图、改图、校验和上架交接组织成一个任务。",
            goal="明确当前页的定位：先确认本地任务，再逐步衔接后续工具。",
            actions=(
                "从监控页导出备货单后，可以点击“去发布”进入这里。",
                "先看顶部提示，确认当前版本不会自动点击真实发布。",
                "如果从监控页带入信息，检查任务名称、店铺前缀和计划数量是否正确。",
            ),
            expected="发布页应显示待确认任务，而不是直接执行真实网站发布。",
            tips=(
                "默认产品标题和发布页默认数量在 设置 > 发布 修改。",
                "生图相关目录仍在 设置 > 生图 / 改图 修改，不在发布页改。",
            ),
            screenshot=PUBLISH_SHOT,
        ),
        TutorialStep(
            "publishFormAnchor",
            "填写任务模板",
            "任务模板决定本轮生成多少产品、从哪个货号开始、走本地生图还是 AI 改图。",
            goal="在开始任务前确认数量、货号和模式，避免产物目录和表格对不上。",
            actions=(
                "选择店铺前缀，例如 BO 或 SZW。",
                "检查任务名称，建议包含店铺、批次或备货单线索。",
                "设置起始货号和计划张数。",
                "选择生图方式：本地生图或 AI 改图。",
                "保持测试模式时，不应占用正式货号或自动衔接真实发布。",
            ),
            expected="任务摘要应能说明本轮会生成什么、数量是多少、后续交给哪个流程。",
            tips=(
                "正式图集目录在 设置 > 生图 / 改图 > 图库目录 修改。",
                "最终产品图目录在 设置 > 生图 / 改图 > 产品图目录 修改。",
                "XLSX 目录在 设置 > 生图 / 改图 > XLSX 目录 修改。",
            ),
            screenshot=PUBLISH_SHOT,
        ),
        TutorialStep(
            "publishActionsAnchor",
            "开始前确认安全范围",
            "这里的开始按钮会启动本地任务或改图任务，并在完成后准备同步到上架目录。",
            goal="启动前确认这次任务是否只生成本地文件，还是要继续交接到上架。",
            actions=(
                "确认任务参数无误后点击“同意并开始”。",
                "如果不想自动衔接上架，勾选上架前暂停。",
                "任务执行中可用“停止任务”中断本地进程。",
            ),
            expected="流程状态会从待确认进入生图、产物校验、同步投放目录等阶段。",
            tips=(
                "上架投放图片目录在 设置 > 上架 > 上架 data 目录 对应项目下管理。",
                "同步到 PutawayAiRobot 前，必须确认产品图数量、货号和 xlsx 表头。",
            ),
            safety_note="发布页不会替你直接提交真实商品；真实发布仍由上架工具内部流程控制。",
            screenshot=PUBLISH_SHOT,
        ),
    ),
    "local_image": (
        TutorialStep(
            "localImageConfigAnchor",
            "配置本地生图批次",
            "本地生图页用于调用 PosAiImg 的本地/ComfyUI 批次能力，生成透明底印花、产品图和表格。",
            goal="让每个批次的店铺、风格、数量和货号范围清楚可追踪。",
            actions=(
                "选择店铺前缀 BO 或 SZW。",
                "选择风格，设置张数、起始货号、采样步数和随机种子。",
                "测试模式适合试图；正式批次应关闭测试模式并核对货号。",
                "如果 ComfyUI 路径或模型路径不对，到 设置 > 生图 / 改图 > PosAiImg 资源 修改。",
            ),
            expected="点击开始后，任务会进入后台运行，任务清单显示当前进度。",
            tips=(
                "正式透明底图集存放位置由 设置 > 生图 / 改图 > 图库目录 决定。",
                "最终产品图存放位置由 设置 > 生图 / 改图 > 产品图目录 决定。",
                "衣物对应 xlsx 存放位置由 设置 > 生图 / 改图 > XLSX 目录 决定。",
            ),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
        TutorialStep(
            "localImageStatusAnchor",
            "查看任务和产物",
            "任务清单保存本地生图批次的状态、日志和输出路径。",
            goal="任务结束后能找到产物目录，并判断是否可以进入发布/上架。",
            actions=(
                "单击或双击任务，打开任务详情。",
                "在详情里查看透明底、产品图和 xlsx 路径。",
                "失败时先看日志，不要直接复制半成品到上架目录。",
            ),
            expected="完成的任务应能打开透明底目录、产品图目录，并生成对应 xlsx。",
            tips=(
                "正式批次完成前要校验数量、货号连续性、重复货号和表头。",
                "如果输出目录不符合预期，先回 设置 > 生图 / 改图 检查三个根目录。",
            ),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
    ),
    "ai_edit": (
        TutorialStep(
            "aiEditImagesAnchor",
            "添加参考图片",
            "AI 改图页用于把已有图片按要求改成可进入后续产品图流程的素材。",
            goal="先确认输入图片正确，避免把无关图、账号截图或敏感页面送入 AI 接口。",
            actions=(
                "点击“添加图片”选择需要改图的本地图片。",
                "在参考图片列表里确认图片数量和文件名。",
                "如选错，使用“清空参考图”重新选择。",
            ),
            expected="参考图片区域会显示已选文件，任务开始后会按这些图片提交改图。",
            tips=(
                "AI 接口配置在 设置 > 生图 / 改图 > AI 接口配置 修改。",
                "不要把账号、订单、Cookie、Token 或 API Key 截图作为参考图。",
            ),
            screenshot=AI_EDIT_SHOT,
        ),
        TutorialStep(
            "aiEditRequestAnchor",
            "填写改图要求",
            "改图要求决定 AI 输出的风格、主体、透明底和是否适合后续贴图。",
            goal="让提示词足够明确，减少生成结果无法使用的概率。",
            actions=(
                "描述要保留的主体、要改变的风格和不要出现的内容。",
                "确认本次生成轮数、起始货号和是否自动切割。",
                "如果默认提示词不合适，到 设置 > 生图 / 改图 > 默认改图要求 修改。",
            ),
            expected="开始改图后，任务队列会显示每轮请求、输出和失败原因。",
            tips=(
                "API Key、接口地址、模型名称在 设置 > 生图 / 改图 > AI 接口配置 修改。",
                "正式输出目录仍使用 设置 > 生图 / 改图 的 图库目录、产品图目录、XLSX 目录。",
            ),
            screenshot=AI_EDIT_SHOT,
        ),
        TutorialStep(
            "aiEditQueueAnchor",
            "检查改图结果",
            "任务队列用于追踪 AI 改图是否完成，以及结果是否进入后处理。",
            goal="判断这批改图能否进入透明底、产品图和 xlsx 生成流程。",
            actions=(
                "查看状态标签，确认任务是等待、运行、完成还是失败。",
                "失败时先删除失败任务或调整提示词后重试。",
                "完成后检查输出目录，再决定是否同步到发布或上架。",
            ),
            expected="成功任务应能找到改图结果、后处理产物和对应货号。",
            tips=(
                "如果产物数量不对，先不要投放到 PutawayAiRobot。",
                "如果输出路径不对，回 设置 > 生图 / 改图 检查目录配置。",
            ),
            screenshot=AI_EDIT_SHOT,
        ),
    ),
    "putaway": (
        TutorialStep(
            "putawayEmbedAnchor",
            "进入自动上架工具",
            "上架页内嵌 PutawayAiRobot，用来读取投放目录中的图片和 xlsx 并执行上架流程。",
            goal="确认上架工具已加载，并且读取的数据目录是本轮产物同步的位置。",
            actions=(
                "等待状态显示已加载 PutawayAiRobot 内嵌界面。",
                "如果从发布页交接过来，检查产品数据页是否已导入最新 Excel。",
                "如果目录不对，到 设置 > 上架 修改上架项目目录、上架 data 目录和上架日志目录。",
            ),
            expected="内嵌界面正常显示后，才能继续用 PutawayAiRobot 的流程处理产品数据。",
            tips=(
                "图片投放目录通常在 上架 data 目录 下的 pic/1。",
                "xlsx 文件通常放在 设置 > 上架 > 上架 data 目录。",
            ),
            screenshot=PUTAWAY_SHOT,
        ),
        TutorialStep(
            "putawayStatusAnchor",
            "处理加载失败",
            "如果 PutawayAiRobot 路径或依赖不正确，页面会显示加载失败原因。",
            goal="优先修正本地路径和环境，不要直接修改上架流程代码。",
            actions=(
                "查看顶部状态和错误信息。",
                "打开 设置 > 上架，确认 PutawayAiRobot 项目目录是否正确。",
                "确认上架 data 目录指向实际投放目录。",
                "必要时仍可单独启动原 PutawayAiRobot 程序处理。",
            ),
            expected="路径修正后重新进入上架页，应能加载内嵌界面。",
            tips=(
                "PutawayAiRobot 的账号密码仍按原项目配置，不应改成明文存储。",
                "真实发布动作有外部影响，执行前要确认店铺、数量和数据文件范围。",
            ),
            safety_note="自动上架会影响真实店铺商品，未确认范围前不要执行批量发布。",
            screenshot=PUTAWAY_SHOT,
        ),
    ),
    "apply": (
        TutorialStep(
            "applyEmbedAnchor",
            "进入申请/合规工具",
            "合规页内嵌 ApplyGoods，用于套版组、合规上传、JIT、库存和期望到货区域等后置流程。",
            goal="确认 ApplyGoods 已加载，并知道这些动作会改变真实商品状态。",
            actions=(
                "等待状态显示已加载 ApplyGoods 内嵌界面。",
                "按 ApplyGoods 页面内流程连接浏览器和选择任务。",
                "如果项目路径不对，到 设置 > 合规 修改合规项目目录。",
            ),
            expected="内嵌界面正常显示后，可以按 ApplyGoods 原流程继续操作。",
            tips=(
                "合规页不会替你跳过人工确认点。",
                "等待时间、是否自动继续等后续策略应在相关流程配置中明确。",
            ),
            screenshot=APPLY_SHOT,
        ),
        TutorialStep(
            "applySafetyAnchor",
            "确认真实状态变更",
            "合规、JIT、库存、地址修改都属于真实外部状态变更。",
            goal="在执行前明确动作范围，避免误操作真实店铺。",
            actions=(
                "先确认本次要处理的店铺、商品数量和流程步骤。",
                "涉及上传、申请、库存、地址修改时，保留人工确认。",
                "如果路径加载失败，到 设置 > 合规 检查 ApplyGoods 项目目录。",
            ),
            expected="每个外部动作执行前，你都能知道即将影响哪些商品或店铺。",
            tips=(
                "默认不应无确认自动跑完整后置链路。",
                "大批量任务先用小样本运行，例如 1 条或当前页。",
            ),
            safety_note="合规上传、JIT、库存和地址修改会改变真实平台状态。",
            screenshot=APPLY_SHOT,
        ),
    ),
    "settings": (
        TutorialStep(
            "settingsBrowserAnchor",
            "先配置监控模块",
            "设置页的默认打开区域是监控模块，这里决定 Temu 页面读取和拿货表输出。",
            goal="把监控需要的店铺、浏览器连接和导出目录配对正确。",
            actions=(
                "在 设置 > 监控 选择监控店铺。",
                "填写 Chrome 调试地址；默认常见值是 http://127.0.0.1:9222。",
                "设置刷新间隔。",
                "设置拿货表导出目录，这会影响监控页导出备货单的位置。",
            ),
            expected="保存后回到监控页，立即刷新会使用这些配置。",
            tips=(
                "如果浏览器不是用调试端口启动，监控页可能无法读取真实页面。",
                "拿货表导出目录建议放在清楚的本地输出目录，不要放到仓库里。",
            ),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsPathsAnchor",
            "自动定位和检查源项目",
            "这个按钮用于尝试定位 SendGoods、PosAiImg、PutawayAiRobot、ApplyGoods 等源项目路径。",
            goal="减少手动填错路径导致页面加载失败或产物写错目录。",
            actions=(
                "点击“自动定位源项目”。",
                "逐个检查监控、生图/改图、上架、合规模块里的路径状态。",
                "如果自动定位不准，切到对应设置 Tab 手动选择目录。",
            ),
            expected="路径状态标签应显示找到项目或指出缺失项。",
            tips=(
                "PosAiImg 的 图库目录、产品图目录、XLSX 目录 在 设置 > 生图 / 改图 修改。",
                "PutawayAiRobot 的 上架 data 目录 在 设置 > 上架 修改。",
                "ApplyGoods 项目目录在 设置 > 合规 修改。",
            ),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsSecurityAnchor",
            "保护敏感信息",
            "敏感信息不要写进仓库、日志或普通配置文件。",
            goal="确认账号、Cookie、Token、API Key 不会因为配置或截图外泄。",
            actions=(
                "账号密码按原项目安全策略保存。",
                "AI API Key 在 设置 > 生图 / 改图 > AI 接口配置 中填写时，不要截图传播。",
                "浏览器 profile 目录可能包含登录态，不要提交或复制。",
            ),
            expected="配置保存后能正常使用，但敏感字段不会进入 Git 提交或普通日志。",
            tips=(
                "如果临时写入配置文件，应确认 `.gitignore` 已覆盖。",
                "教程截图应使用空状态或测试配置，不包含真实订单、库存或账号。",
            ),
            safety_note="任何 Cookie、Token、LocalStorage、API Key 都不应出现在教程截图或提交记录里。",
            screenshot=SETTINGS_SHOT,
        ),
    ),
}


def get_tutorial_steps(page_key: str) -> tuple[TutorialStep, ...]:
    return TUTORIALS.get(page_key, ())
