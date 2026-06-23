# ConsolePlat 项目协作说明

## 沟通与判断原则

- 回答问题时避免过分夸赞，优先保证准确性。
- 不默认认定用户或 Codex 的判断一定正确；遇到页面变化、路径冲突、字段缺失、自动化结果不确定时，先列证据，再给结论。
- 输出保持结构化：先给结论，再给依据、风险和下一步。
- 涉及真实店铺、账号、批量上架、批量提交、发货、上传、删除、修改库存、修改地址等有外部影响的动作时，必须明确动作范围；除非用户已明确授权，不要直接执行。
- 区分“已从代码/文件验证”和“基于现有流程推断”。不要把推断写成事实。
- 中文路径和中文 UI 文案很多，读取文件时优先使用 UTF-8；PowerShell 终端乱码不能直接证明源文件损坏。

## 项目定位

`ConsolePlat` 目标是做一个 Windows PyQt 桌面集成软件，用统一界面串联以下四个现有项目能力：

- `E:\1PythonProject\SendGoods`：Temu Agent Seller 待发货/备货页面读取、SKU/颜色/尺码/件数采集、高清图下载、按模板生成拿货表。
- `E:\1PythonProject\PosAiImg`：本地/AI 印花生成、AI 改图、透明底处理、批量贴图、产品图命名、货号分配、xlsx 生成、同步投放目录。
- `E:\1PythonProject\PutawayAiRobot`：店小秘/TEMU 创建产品页面自动上架，读取 `data` 目录中的产品图和 xlsx，执行批量发布流程。
- `E:\1PythonProject\ApplyGoods`：Temu Agent Seller 商品申请、套版组管理、批量合规上传、开通 JIT、期望到货区域、库存设置等后置流程。

本项目不是简单复制四个项目的代码，而是先做“集成中台”：统一配置、任务编排、进度展示、日志、状态监控和人工确认点。老项目在迁移完成前必须保持可独立运行。

## 目标主流程

整体业务链路按以下顺序设计：

1. 店铺监控
   - 监控 Temu Agent Seller 店铺页面，重点关注紧急备货/待发货/销量或其他可配置指标。
   - 默认参考页面：`https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency`。
   - 页面刷新间隔默认 5 秒，但必须允许用户自定义。
   - 监控到新待处理数据时，在软件内给出提示，并可触发 `SendGoods` 采集采购数据。

2. 拿货表生成
   - 复用 `SendGoods` 的页面读取、滚动去重、SKU 拆分、高清图处理和 Excel 写入规则。
   - 默认只读页面和生成本地文件，不点击提交、发货、打印、加入发货台等会改变网站状态的按钮。

3. 印花/产品图生产
   - 复用 `PosAiImg` 的提示词、风格批次、货号、透明底、贴图、xlsx 产物规则。
   - 软件内至少拆成两个页面：
     - 本地生图：选择风格、张数、店铺、起始货号或自动续号。
     - AI 改图：上传/选择若干图片，配置 API Key 和改图要求，使用 image-to-image 类能力生成结果。
   - 两类任务都必须显示任务进度、当前步骤、日志、输出目录和失败清单。
   - 完成后继续执行图片命名、货号分配、产品图生成、xlsx 生成、结果校验和投放目录同步。

4. 自动上架
   - 复用 `PutawayAiRobot` 当前已较完整的程序能力。
   - 前期可由 `ConsolePlat` 启动/唤起 `PutawayAiRobot`，并把 `PosAiImg` 产物同步到 `E:\1PythonProject\PutawayAiRobot\data`。
   - 后续再逐步抽象为可调用任务接口，不要一开始大规模搬迁其复杂 Playwright 流程。

5. 申请商品与后置设置
   - 自动上架完成后，按可配置等待时间衔接 `ApplyGoods` 的流程。
   - 默认后置顺序参考：套版组管理、合规上传、JIT、申请相关流程、等待约 15 分钟、修改常驻地址、修改库存。
   - 每一步自动衔接都必须能配置等待时间、是否自动继续、失败时是否暂停等待人工处理。

## 推荐 PyQt 页面结构

主界面建议采用左侧导航 + 右侧工作区，不做营销式首页。优先保证密集信息可扫描、状态清楚、按钮含义明确。

建议页面：

- `实时监控`：店铺状态卡片、待处理列表、最近变化、刷新间隔、监控开关、触发记录。
- `拿货表`：浏览器连接状态、采集按钮、SKU 明细表、异常清单、Excel 输出路径。
- `本地生图`：店铺、风格、张数、起始货号、输出目录、任务队列、进度日志。
- `AI 改图`：API Key 配置、输入图片、提示词/要求、任务队列、结果预览。
- `批次产物`：透明底数量、产品图数量、xlsx 校验、投放目录同步状态。
- `自动上架`：PutawayAiRobot 启动状态、数据目录、批量上架进度、失败行。
- `申请/合规`：ApplyGoods 后置任务、等待时间、人工确认点、执行日志。
- `设置`：项目路径、浏览器/CDP 地址、刷新间隔、等待时间、店铺配置、API Key 存储策略。

## 架构原则

- UI 主线程只负责展示和发起动作；Playwright、图片处理、Excel 写入、ComfyUI/API 调用等耗时任务必须放入后台线程或任务队列。
- 后台任务通过 Qt signal 或统一事件总线回传 `progress`、`log`、`warning`、`failed`、`finished`。
- 每个外部项目先封装为 adapter，不直接把其 UI 代码塞进主窗口：
  - `SendGoodsAdapter`
  - `PosAiImgAdapter`
  - `PutawayAdapter`
  - `ApplyGoodsAdapter`
- adapter 的第一阶段职责可以是调用现有脚本、读取现有产物、校验目录；第二阶段再抽取核心函数。
- 所有跨模块数据交接必须落到清晰的文件或数据模型，不依赖剪贴板作为唯一数据来源。
- 自动化步骤要支持暂停、停止、失败重试和人工接管。停止任务时不要轻易关闭用户正在登录的浏览器，除非该浏览器由本任务专门启动且用户确认。

## 数据与产物约定

### SendGoods

- 目标页面：`https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency`。
- 采集字段至少包括：备货单号、备货母单号、商品货号、SKU 货号、颜色、尺码、备货件数、高清图片地址。
- Excel 模板参考：`E:\1PythonProject\SendGoods\1.cleaned.xlsx`。
- 黑色写左侧区域，白色写右侧区域；同货号同颜色同尺码数量累加；合计公式不能被覆盖。
- 不使用 180x 缩略图作为最终图片。

### PosAiImg

- 正式印花素材使用新目录：
  - `E:\1PythonProject\PosAiImg\图库\<店铺>\<年份>\<月份>\<批次>\最终透明底`
- 正式产品图使用新目录：
  - `E:\1PythonProject\PosAiImg\批量贴图结果\<店铺>\<年份>\<月份>\<批次>\最终产品图`
- xlsx 输出目录：
  - BO：`E:\1PythonProject\PosAiImg\衣物对应的xlsx\BO`
  - SZW：`E:\1PythonProject\PosAiImg\衣物对应的xlsx\SZW`
- 投放目录：
  - 图片：`E:\1PythonProject\PutawayAiRobot\data\pic\1`
  - xlsx：`E:\1PythonProject\PutawayAiRobot\data`
- 正式批次完成前必须校验数量、货号连续性、重复货号、xlsx 表头、首末货号、店铺名、产品标题与文件名一致性，并做视觉抽查。

### PutawayAiRobot

- 入口参考：`E:\1PythonProject\PutawayAiRobot\browser_dom_automation.py`。
- 现有后台任务集中在 `workers.py`，主自动化流程在 `dianxiaomi_flows.py` 和各 `*_flow.py`。
- 配置位于 `%APPDATA%\PutawayAiRobot`，账号密码使用 Windows DPAPI；不要改成明文存储。
- 读取产品数据时必须满足其 Excel 表头要求：`店铺名称、产品分类、产品标题、产品序列号、颜色`。

### ApplyGoods

- 入口参考：`E:\1PythonProject\ApplyGoods\main.py`。
- 自动化核心参考：`temu_goods.py`、`browser_session.py`。
- 目标页面包括商品列表、套版组、合规上传、JIT、库存、期望到货区域等页面。
- 批量合规、JIT、库存、地址修改等都属于真实外部状态变更，必须保留人工确认点或明确的自动执行配置。

## 配置与敏感信息

- 不要把账号、密码、Cookie、Token、LocalStorage、API Key 写入仓库、日志或普通配置文件。
- API Key 建议优先使用 Windows Credential Manager、DPAPI 加密文件或用户每次输入；如果临时写入配置，必须明确标注风险并加入 `.gitignore`。
- 浏览器 profile 目录可能包含登录态，不要提交、复制或随意删除。
- 默认 CDP 地址可使用 `http://127.0.0.1:9222`，但必须允许用户配置。

## 开发环境

当前四个项目已有多个 conda 环境约定：

- `SendGoods`、`ApplyGoods`、`PutawayAiRobot` 多处说明优先使用 `flask` 环境；这里的 `flask` 只是环境名，不表示项目是 Flask Web 服务。
- `PosAiImg` 使用 `posai-img` 执行图片脚本，`posai-comfy` 启动 ComfyUI。
- 新项目使用哪个环境需要后续确认；在未确认前，不要直接假设所有依赖在默认 Python 中可用。

常见依赖方向：

- PyQt5
- Playwright
- openpyxl
- Pillow
- requests/httpx
- pydantic 或 dataclasses
- pytest

如果新增依赖，先说明用途和影响，再更新依赖文件。

## 代码组织建议

后续实现时建议从以下结构开始：

```text
ConsolePlat/
  AGENTS.md
  README.md
  requirements.txt
  main.py
  consoleplat/
    app.py
    config.py
    paths.py
    models.py
    task_queue.py
    adapters/
      sendgoods_adapter.py
      posaiimg_adapter.py
      putaway_adapter.py
      applygoods_adapter.py
    ui/
      main_window.py
      monitor_page.py
      purchase_page.py
      image_generate_page.py
      image_edit_page.py
      batch_outputs_page.py
      putaway_page.py
      apply_goods_page.py
      settings_page.py
    services/
      browser_session.py
      monitor_service.py
      notification_service.py
      validation_service.py
  tests/
```

这是建议结构，不是必须一次性创建。每次实现应按当前任务最小化改动。

## 自动化安全边界

- 监控、读取、生成本地文件默认可自动执行。
- 触发网站提交、上传、发布、申请、修改库存、修改地址、开通 JIT、批量删除、发货等动作前，必须满足以下至少一种条件：
  - 用户在本轮明确要求执行该动作；
  - 设置中已显式启用对应自动化，并且界面显示即将执行的范围；
  - 当前处于测试模式，不会提交到真实网站。
- 新增自动化流程时优先提供 dry-run 或只读验证模式。
- 大批量任务先支持小样本运行，例如 1 条、5 条、当前页，再扩大到整批。

## 验证要求

根据改动范围选择验证：

- 文档或配置改动：检查路径、模块名、流程顺序是否与现有项目文件一致。
- Python 代码改动：至少运行 `python -m py_compile` 或对应测试。
- PyQt UI 改动：启动窗口确认不阻塞、不闪退，主要按钮可见且文案不溢出。
- Playwright 改动：优先在真实页面小范围验证；无法登录或无页面权限时，说明已完成的静态检查和未验证项。
- 图片/批次改动：检查数量、货号、透明通道、xlsx、投放目录，并打开总览或抽样图做视觉确认。
- Excel 改动：重新读取生成文件确认表头、公式、图片、行数和异常清单。

## 当前已知风险与待澄清项

- 店铺监控页面的“销量”等指标是否来自同一个 Temu 页面，还是需要额外页面/接口，尚未确认。
- 5 秒刷新如果直接反复刷新网页，可能触发页面限流、登录态异常或影响人工操作；优先考虑读取 DOM/接口并允许用户调整间隔。
- `PosAiImg` 的 AI 改图 API 具体供应商、模型名称、image-to-image 参数、输出规格尚未确定。
- `PutawayAiRobot` 当前是完整 PyQt 程序，短期更稳妥的集成方式是启动/投放数据/监听日志；深度内嵌需要单独拆分。
- `ApplyGoods` 后置流程会改变真实商品状态，默认不应无确认自动运行整条链路。
- 四个项目的依赖环境不完全一致，新项目打包前需要统一依赖和浏览器策略。

## 修改原则

- 修改前先读相关源项目的 `AGENTS.md`/`AGENTS.MD`、`README.md` 和目标代码，不要只凭文件名猜测。
- 优先复用已验证的业务逻辑，不重写复杂选择器和页面流程。
- 不要无关修改四个源项目的生成目录、浏览器 profile、日志、dist/build、ComfyUI 上游代码。
- 跨项目复制代码时要标明来源，并尽快收敛成 adapter 或共享模块，避免多份逻辑长期分叉。
- 新增页面或任务时必须有明确日志、进度、失败原因和结果路径。
- 每次涉及真实业务链路的改动，都要考虑“能否回退到原项目单独运行”。

## Git 提交约定

- 以后在本项目中完成一轮代码实现后，默认要做一次本地 Git 提交，除非用户在本轮明确要求不要提交。
- 提交前必须先完成与改动范围匹配的验证；不要把明显未完成、未验证或已知失败的中间状态提交进去。
- 默认只做本地 commit，不自动 push；是否推送到远端由用户单独确认。
- 涉及恢复现场、临时备份、会话导出、重建目录等辅助材料时，先确认是否应加入 `.gitignore`，避免把恢复残留一并提交。
