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
            "monitorControlsAnchor",
            "浏览器连接与店铺",
            "监控能否读取真实 Temu 页面，主要取决于店铺选择和浏览器 CDP 连接配置。",
            goal="先保证软件连接的是正在登录 Temu Agent Seller 的浏览器。",
            actions=(
                "在当前页选择要监控的店铺。",
                "到 设置 > 监控 检查 Chrome 调试地址；常见 CDP 地址是 http://127.0.0.1:9222。",
                "如果读取失败，先确认浏览器确实用调试端口启动并已完成登录。",
            ),
            expected="来源状态能显示店铺、地区和页面读取结果，而不是持续停在登录或连接失败。",
            tips=(
                "店铺、刷新间隔、Chrome 调试地址都在 设置 > 监控 维护。",
                "监控页只读取页面，不会提交、发货或改动网站状态。",
            ),
            safety_note="遇到短信、滑块或账号验证时，必须人工在浏览器里完成。",
            screenshot=MONITOR_SHOT,
        ),
        TutorialStep(
            "monitorControlsAnchor",
            "刷新间隔",
            "刷新间隔决定软件多久读一次页面，过快可能影响登录态或人工操作。",
            goal="让页面读取足够及时，同时不对浏览器造成不必要压力。",
            actions=(
                "日常监控可使用默认间隔。",
                "页面不稳定、登录频繁失效或人工正在操作时，把间隔调大。",
                "长期默认值可到 设置 > 监控 > 刷新间隔 维护。",
            ),
            expected="事件流按设定节奏记录刷新结果，页面不会因过快读取而频繁异常。",
            tips=("5 秒只是默认值，不是必须值。",),
            screenshot=MONITOR_SHOT,
        ),
        TutorialStep(
            "monitorOrdersAnchor",
            "拿货表导出目录",
            "监控读到待处理商品后，会把备货信息交给 SendGoods 规则生成本地 Excel。",
            goal="确认拿货表会保存到你能找到、也不会误提交到仓库的位置。",
            actions=(
                "到 设置 > 监控 > 拿货表导出目录 修改 Excel 输出位置。",
                "在当前页核对备货单、SKU、颜色、尺码和件数。",
                "导出后从事件流确认输出路径。",
            ),
            expected="导出的备货表路径清楚可追踪，并可作为发布页任务线索。",
            tips=("导出只生成本地文件，不会修改 Temu 页面。",),
            screenshot=MONITOR_SHOT,
        ),
        TutorialStep(
            "monitorOrdersAnchor",
            "导出后交接发布",
            "拿货表生成后，监控页可以把店铺、数量和输出路径带到发布页。",
            goal="减少重复录入，避免发布页任务数量和拿货表不一致。",
            actions=(
                "导出成功后进入发布页交接。",
                "在发布页核对任务名称、店铺前缀和计划数量。",
                "如果交接信息不对，回到监控页重新确认导出结果。",
            ),
            expected="发布页能看到从监控页带入的任务线索，并继续配置生图或改图。",
            tips=("监控页负责读取和导出，发布页负责组织后续产物链路。",),
            screenshot=MONITOR_SHOT,
        ),
    ),
    "publish": (
        TutorialStep(
            "publishHeaderAnchor",
            "发布页定位",
            "发布页用于组织拿货表、生图/改图、产物校验和上架交接，不直接替你提交真实商品。",
            goal="明确这里配置的是本地任务链路，不是网站最终发布确认。",
            actions=(
                "从监控页交接任务后，先核对顶部提示和任务状态。",
                "确认当前任务是否处于测试模式。",
                "真实发布动作仍在 PutawayAiRobot 流程中完成。",
            ),
            expected="任务处于待确认状态，后续阶段会按本地流程推进。",
            tips=("默认产品标题和默认任务参数在 设置 > 发布 维护。",),
            safety_note="发布页不应被理解为无确认批量提交入口。",
            screenshot=PUBLISH_SHOT,
        ),
        TutorialStep(
            "publishFormAnchor",
            "默认任务参数",
            "任务名称、店铺前缀、默认数量和默认生图方式影响每一轮产物生成。",
            goal="让每个批次的命名、数量和模式在开始前就固定下来。",
            actions=(
                "在当前页核对店铺前缀、任务名称、起始货号和计划张数。",
                "到 设置 > 发布 修改 BO/SZW 固定产品标题、默认任务名和默认数量。",
                "正式批次开始前确认测试模式是否符合本轮目标。",
            ),
            expected="任务摘要能说明本轮会生成多少产品、从哪个货号开始、使用哪种模式。",
            tips=("任务参数错误会直接影响图片文件名、xlsx 内容和上架数据。",),
            screenshot=PUBLISH_SHOT,
        ),
        TutorialStep(
            "publishFormAnchor",
            "生图或改图模式",
            "发布页只选择本轮走本地生图还是 AI 改图；具体目录和接口不在这里维护。",
            goal="把任务分流到正确的图片生产方式。",
            actions=(
                "本地生图适合从风格批次直接生成印花。",
                "AI 改图适合基于参考图片进行 image-to-image。",
                "到 设置 > 生图 / 改图 配置 图库目录、产品图目录、XLSX 目录、API Key 和 ComfyUI 资源。",
            ),
            expected="开始后流程会进入对应的本地生图或 AI 改图阶段。",
            tips=("模式选错会让任务进入错误的脚本和输出目录。",),
            screenshot=PUBLISH_SHOT,
        ),
        TutorialStep(
            "publishActionsAnchor",
            "同步到上架投放目录",
            "产物通过校验后，发布页会准备把图片和 xlsx 同步给 PutawayAiRobot。",
            goal="确认同步目标是正确的上架投放目录。",
            actions=(
                "在 设置 > 上架 检查上架 data 目录。",
                "确认图片投放目录与 PutawayAiRobot 实际读取目录一致。",
                "同步前核对产品图数量、货号连续性和 xlsx 表头。",
            ),
            expected="上架页能够从同一投放目录读取本轮产品图和 xlsx。",
            tips=("投放目录配置错误会导致上架工具读取旧批次或空目录。",),
            safety_note="同步产物不等于真实发布；上架前仍要人工确认范围。",
            screenshot=PUBLISH_SHOT,
        ),
    ),
    "local_image": (
        TutorialStep(
            "localImageConfigAnchor",
            "图集目录",
            "图集目录用于保存正式透明底印花，是本地生图后续贴图和归档的来源。",
            goal="确保透明底素材进入正确店铺、年份、月份和批次目录。",
            actions=(
                "到 设置 > 生图 / 改图 > 图库目录 修改根目录。",
                "当前页只配置本轮店铺前缀、风格、张数和货号。",
                "正式批次开始前确认测试模式状态。",
            ),
            expected="任务完成后，透明底素材应出现在设置中指定的图集目录体系下。",
            tips=("图集目录错误会影响后续产品图生成和历史批次追踪。",),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
        TutorialStep(
            "localImageConfigAnchor",
            "产品图目录",
            "产品图目录用于保存贴到衣服模板后的最终上架图片。",
            goal="确认最终产品图和透明底素材分开管理。",
            actions=(
                "到 设置 > 生图 / 改图 > 产品图目录 修改根目录。",
                "保持产品图目录与 PutawayAiRobot 投放目录分开，先校验再同步。",
                "批次完成后从任务详情查看最终产品图路径。",
            ),
            expected="任务完成后，产品图数量应与计划张数一致。",
            tips=("不要直接把未校验的产品图目录当作上架投放目录。",),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
        TutorialStep(
            "localImageConfigAnchor",
            "XLSX 目录",
            "XLSX 目录保存衣物对应表格，后续上架会依赖表头和货号。",
            goal="让图片文件名、货号和 xlsx 记录保持一致。",
            actions=(
                "到 设置 > 生图 / 改图 > XLSX 目录 修改根目录。",
                "BO 和 SZW 可以使用不同子目录。",
                "正式批次完成后检查 xlsx 表头、首末货号和店铺名。",
            ),
            expected="xlsx 文件能被 PutawayAiRobot 识别，并与产品图货号对应。",
            tips=("PutawayAiRobot 需要固定表头：店铺名称、产品分类、产品标题、产品序列号、颜色。",),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
        TutorialStep(
            "localImageConfigAnchor",
            "ComfyUI 与模型资源",
            "本地生图依赖 PosAiImg 的 ComfyUI 和模型资源配置。",
            goal="确保本地生成任务有可用的运行环境。",
            actions=(
                "到 设置 > 生图 / 改图 > PosAiImg 资源 配置 ComfyUI 安装目录。",
                "配置模型目录和下载目录。",
                "资源缺失时先用设置页的检测功能定位问题。",
            ),
            expected="本地生图任务可以启动并持续输出日志，而不是立即报路径或模型缺失。",
            tips=("ComfyUI 环境和 ConsolePlat 环境可能不是同一个 Python 环境。",),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
        TutorialStep(
            "localImageStatusAnchor",
            "任务输出位置",
            "任务清单用于回看本轮透明底、产品图和 xlsx 的实际输出路径。",
            goal="完成后能按路径找到产物，并判断是否可以进入发布或上架。",
            actions=(
                "打开任务详情查看透明底、产品图和表格路径。",
                "失败任务先看日志和失败原因。",
                "数量、货号、表头通过校验后，再同步到上架投放目录。",
            ),
            expected="每个完成批次都有清晰的输出目录和可复查日志。",
            tips=("输出目录不符合预期时，优先回 设置 > 生图 / 改图 检查三个根目录。",),
            screenshot=LOCAL_IMAGE_SHOT,
        ),
    ),
    "ai_edit": (
        TutorialStep(
            "aiEditRequestAnchor",
            "AI 接口与 API Key",
            "AI 改图需要先配置接口名称、API Key、接口地址、模型和默认尺寸。",
            goal="让改图请求发往正确供应商和模型。",
            actions=(
                "到 设置 > 生图 / 改图 > AI 接口配置 维护 API Key。",
                "同一区域维护接口地址、模型名称和默认尺寸。",
                "不要把 API Key 写进日志、截图或提交记录。",
            ),
            expected="任务开始后能正常返回图片结果，而不是接口认证或模型错误。",
            tips=("接口配置属于敏感信息，截图教程应使用空状态或测试配置。",),
            safety_note="API Key 不应出现在教程截图、Git 提交或普通配置备份里。",
            screenshot=AI_EDIT_SHOT,
        ),
        TutorialStep(
            "aiEditImagesAnchor",
            "输入图片范围",
            "输入图片决定 AI 改图的参考内容，也决定后续结果是否能进入产品图流程。",
            goal="只把可用于改图的素材交给 AI 接口。",
            actions=(
                "选择本地参考图片。",
                "排除账号、订单、库存、聊天记录等敏感截图。",
                "检查列表中的文件数量和本轮计划是否匹配。",
            ),
            expected="参考图片清单只包含本轮要处理的素材。",
            tips=("输入图质量会影响透明底处理和后续贴图效果。",),
            screenshot=AI_EDIT_SHOT,
        ),
        TutorialStep(
            "aiEditRequestAnchor",
            "默认改图要求",
            "默认改图要求决定输出风格、主体保留和是否适合后续透明底处理。",
            goal="减少每次任务重复填写提示词，并保持批次风格一致。",
            actions=(
                "到 设置 > 生图 / 改图 > 默认改图要求 修改常用提示词。",
                "当前页可按本轮任务微调提示词。",
                "正式任务前确认不包含敏感或无关描述。",
            ),
            expected="任务队列中的输出风格与本轮产品目标一致。",
            tips=("提示词不清楚会增加失败重试和后处理成本。",),
            screenshot=AI_EDIT_SHOT,
        ),
        TutorialStep(
            "aiEditQueueAnchor",
            "改图产物目录",
            "AI 改图结果仍要进入图集目录、产品图目录和 XLSX 目录的产物链路。",
            goal="确认改图结果能被正式批次归档和上架使用。",
            actions=(
                "到 设置 > 生图 / 改图 检查 图库目录、产品图目录、XLSX 目录。",
                "完成后在任务队列查看输出路径。",
                "投放到上架目录前先校验数量和货号。",
            ),
            expected="改图结果、后处理产品图和 xlsx 都能在指定目录中找到。",
            tips=("AI 改图成功不代表已经可以上架，仍需产物校验。",),
            screenshot=AI_EDIT_SHOT,
        ),
        TutorialStep(
            "aiEditQueueAnchor",
            "失败处理",
            "失败任务通常与接口配置、输入图片、提示词或输出目录有关。",
            goal="用失败原因定位配置问题，而不是盲目重复提交。",
            actions=(
                "接口错误先查 API Key、接口地址和模型名称。",
                "文件错误先查输入图片和输出目录。",
                "效果不符合预期时调整默认改图要求后再重试。",
            ),
            expected="失败清单能指向可修复的配置项或素材问题。",
            tips=("连续失败时先小批量测试，不要直接跑整批。",),
            screenshot=AI_EDIT_SHOT,
        ),
    ),
    "putaway": (
        TutorialStep(
            "putawayEmbedAnchor",
            "Putaway 项目目录",
            "自动上架页依赖 PutawayAiRobot 原项目，ConsolePlat 只是内嵌和交接。",
            goal="确保内嵌界面来自正确的 PutawayAiRobot 项目。",
            actions=(
                "到 设置 > 上架 修改上架项目目录。",
                "项目目录应包含 PutawayAiRobot 的主程序和现有配置。",
                "路径异常时优先修设置，不要复制上架代码到 ConsolePlat。",
            ),
            expected="进入上架页后，内嵌界面能正常加载。",
            tips=("账号密码仍由 PutawayAiRobot 原有 DPAPI 配置管理。",),
            screenshot=PUTAWAY_SHOT,
        ),
        TutorialStep(
            "putawayEmbedAnchor",
            "投放目录",
            "投放目录是发布页同步产物和 PutawayAiRobot 读取产品数据之间的交接点。",
            goal="让图片和 xlsx 落到同一个上架工具会读取的位置。",
            actions=(
                "到 设置 > 上架 > 上架 data 目录 修改投放根目录。",
                "图片通常进入该目录下的 pic/1。",
                "xlsx 文件通常放在上架 data 目录根部。",
            ),
            expected="上架工具能读取本轮同步过来的产品图和 xlsx。",
            tips=("投放目录不对时，上架页可能读取旧文件或空目录。",),
            screenshot=PUTAWAY_SHOT,
        ),
        TutorialStep(
            "putawayStatusAnchor",
            "文件规则",
            "PutawayAiRobot 对 xlsx 表头和产品图命名有固定要求。",
            goal="在真实上架前确认数据文件可被原工具识别。",
            actions=(
                "检查 xlsx 表头包含店铺名称、产品分类、产品标题、产品序列号、颜色。",
                "检查产品图货号与 xlsx 产品序列号一致。",
                "检查图片数量与任务计划数量一致。",
            ),
            expected="导入产品数据时不会因为表头、货号或图片缺失失败。",
            tips=("数据不完整时不要进入批量发布。",),
            screenshot=PUTAWAY_SHOT,
        ),
        TutorialStep(
            "putawayStatusAnchor",
            "上架前确认",
            "自动上架会影响真实店铺商品，必须在执行前确认范围。",
            goal="避免把错误批次、错误店铺或测试产物发布出去。",
            actions=(
                "确认店铺、数量、产品标题和货号范围。",
                "先用小样本验证流程。",
                "失败时保留原 PutawayAiRobot 独立运行的回退方式。",
            ),
            expected="真实发布前，操作者知道即将影响哪些商品和店铺。",
            tips=("ConsolePlat 不应跳过 PutawayAiRobot 内部必要确认。",),
            safety_note="真实上架、发布、提交都属于外部状态变更。",
            screenshot=PUTAWAY_SHOT,
        ),
    ),
    "apply": (
        TutorialStep(
            "applyEmbedAnchor",
            "ApplyGoods 项目目录",
            "申请/合规页依赖 ApplyGoods 原项目，路径错误会导致内嵌界面无法加载。",
            goal="确保合规流程来自正确的 ApplyGoods 代码和配置。",
            actions=(
                "到 设置 > 合规 修改合规项目目录。",
                "路径应指向包含 main.py、temu_goods.py、browser_session.py 的项目。",
                "加载失败时先查看状态区错误信息。",
            ),
            expected="路径正确后，合规页能加载 ApplyGoods 内嵌界面。",
            tips=("ApplyGoods 在迁移完成前仍应能独立运行。",),
            screenshot=APPLY_SHOT,
        ),
        TutorialStep(
            "applyEmbedAnchor",
            "浏览器连接",
            "合规流程需要连接已登录的 Temu Agent Seller 浏览器会话。",
            goal="让 ApplyGoods 操作正确账号和页面。",
            actions=(
                "按 ApplyGoods 内嵌界面的浏览器连接配置操作。",
                "确认浏览器已登录目标店铺账号。",
                "遇到验证码、短信或授权页时人工处理。",
            ),
            expected="页面能进入商品列表、套版组、合规上传、JIT 或库存相关页面。",
            tips=("不要关闭用户正在使用的登录浏览器，除非该浏览器由任务专门启动且已确认。",),
            screenshot=APPLY_SHOT,
        ),
        TutorialStep(
            "applySafetyAnchor",
            "合规与 JIT 确认点",
            "合规上传、开通 JIT 和申请流程会改变真实商品状态。",
            goal="每一步自动衔接前都明确是否继续、处理哪些商品。",
            actions=(
                "确认本次商品范围和店铺。",
                "保留人工确认点或在设置中显式启用对应自动化。",
                "失败时暂停等待人工处理，不要直接跳到下一步。",
            ),
            expected="流程日志能说明当前步骤、处理范围和失败原因。",
            tips=("大批量前先用 1 条、5 条或当前页验证。",),
            safety_note="合规上传和 JIT 属于真实外部状态变更。",
            screenshot=APPLY_SHOT,
        ),
        TutorialStep(
            "applySafetyAnchor",
            "库存和地址修改",
            "库存、常驻地址、期望到货区域等后置设置风险更高。",
            goal="把高风险动作放在明确授权和可回查日志之后。",
            actions=(
                "确认等待时间、是否自动继续、失败时是否暂停。",
                "核对目标商品和目标区域。",
                "保留执行日志和失败清单。",
            ),
            expected="执行前能清楚看到动作范围，执行后能从日志回查结果。",
            tips=("默认不应无确认自动跑完整后置链路。",),
            safety_note="库存和地址修改会影响真实履约状态。",
            screenshot=APPLY_SHOT,
        ),
    ),
    "settings": (
        TutorialStep(
            "settingsBrowserAnchor",
            "监控配置地图",
            "设置 > 监控 维护店铺、Chrome 调试地址、刷新间隔和拿货表导出目录。",
            goal="先把页面读取和拿货表输出配置正确。",
            actions=(
                "配置监控店铺。",
                "配置 Chrome 调试地址；也可称为 CDP 地址。",
                "配置刷新间隔和拿货表导出目录。",
            ),
            expected="监控页刷新、循环监控和导出 Excel 都使用这些设置。",
            tips=("监控读取失败时，优先检查这个 Tab。",),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsPathsAnchor",
            "生图/改图配置地图",
            "设置 > 生图 / 改图 维护 PosAiImg 目录、AI 接口和资源路径。",
            goal="集中管理所有图片生产相关配置。",
            actions=(
                "维护 图库目录、产品图目录、XLSX 目录。",
                "维护 API Key、接口地址、模型和默认改图要求。",
                "维护 ComfyUI 安装目录、模型目录和下载目录。",
            ),
            expected="本地生图、AI 改图和发布页产物校验都使用这些路径。",
            tips=("图片产物路径不对时，优先检查这个 Tab。",),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsPathsAnchor",
            "发布配置地图",
            "设置 > 发布 维护产品标题、默认店铺前缀、默认任务名和默认数量。",
            goal="让发布页每次新任务都有可控的默认值。",
            actions=(
                "维护 BO 和 SZW 固定产品标题。",
                "维护默认任务名和默认生图方式。",
                "维护本地生图默认张数和 AI 改图默认轮数。",
            ),
            expected="发布页新任务会带入这些默认配置。",
            tips=("这里不维护图片目录，图片目录在 设置 > 生图 / 改图。",),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsPathsAnchor",
            "上架配置地图",
            "设置 > 上架 维护 PutawayAiRobot 项目目录、上架 data 目录和日志目录。",
            goal="保证发布页同步产物和上架页读取数据使用同一投放目录。",
            actions=(
                "维护上架项目目录。",
                "维护上架 data 目录，也就是投放目录根路径。",
                "维护上架日志目录。",
            ),
            expected="上架页能加载 PutawayAiRobot，并读取同步后的图片和 xlsx。",
            tips=("上架 data 目录错误是读取不到产品数据的常见原因。",),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsPathsAnchor",
            "合规配置地图",
            "设置 > 合规 维护 ApplyGoods 项目目录。",
            goal="让申请/合规页能加载正确的后置流程工具。",
            actions=(
                "维护合规项目目录。",
                "路径异常时使用自动定位源项目辅助检查。",
                "合规流程内部的真实动作仍按 ApplyGoods 页面确认。",
            ),
            expected="申请/合规页能加载 ApplyGoods 内嵌界面。",
            tips=("合规、JIT、库存、地址修改都需要额外确认范围。",),
            screenshot=SETTINGS_SHOT,
        ),
        TutorialStep(
            "settingsSecurityAnchor",
            "外观、更新与敏感信息",
            "设置页还包含程序外观、更新检查和敏感信息相关配置。",
            goal="区分普通偏好设置和可能泄露账号状态的配置。",
            actions=(
                "外观 Tab 维护主题和背景图。",
                "更新 Tab 维护版本检查和代理。",
                "账号、Cookie、Token、API Key、浏览器 profile 不应进入 Git、日志或教程截图。",
            ),
            expected="普通配置可保存，敏感信息不会出现在提交记录或截图材料中。",
            tips=("如果临时写入配置文件，先确认 `.gitignore` 覆盖。",),
            safety_note="任何 Cookie、Token、LocalStorage、API Key 都不应出现在教程截图或提交记录里。",
            screenshot=SETTINGS_SHOT,
        ),
    ),
}


def get_tutorial_steps(page_key: str) -> tuple[TutorialStep, ...]:
    return TUTORIALS.get(page_key, ())
