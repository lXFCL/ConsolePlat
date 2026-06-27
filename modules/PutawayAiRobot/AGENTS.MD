# PutawayAiRobot 协作说明

## 项目定位

这是一个 Windows 桌面端 Python 工具，用 PyQt5 提供控制界面，通过 Playwright 连接浏览器 CDP，自动操作店小秘的 TEMU 创建产品页面，批量完成商品上架相关步骤。

核心特点：

- 入口是 `browser_dom_automation.py`，主窗口类是 `MainWindow`。
- 后台任务集中在 `workers.py`，使用 `QtCore.QThread` 避免阻塞 UI。
- 店小秘页面自动化集中在 `dianxiaomi_flows.py` 及若干 `*_flow.py` 子流程。
- 数据保存在 `%APPDATA%\PutawayAiRobot`，素材图片来自项目内 `data/pic`。
- 该项目强依赖真实网页 DOM、中文按钮文案、Ant Design / Element UI 组件结构；修改选择器时必须小步验证。

## 运行与构建

常用命令优先使用 conda 环境 `flask`：

```powershell
conda run -n flask python verify_startup.py
conda run -n flask python browser_dom_automation.py
```

如需补装依赖或浏览器：

```powershell
conda run -n flask python -m pip install -r requirements.txt
conda run -n flask python -m playwright install chromium
```

打包：

```powershell
.\build_exe.bat
```

注意：

- `requirements.txt` 包含 `PyQt5`、`openpyxl`、`numpy`、`Pillow`、`playwright`、`paddleocr`、`pytesseract`。
- `verify_startup.py` 只检查部分依赖，不检查 OCR 相关依赖。
- 当前已确认 `flask` conda 环境包含项目依赖；`base`/默认 `python` 可能缺少 `playwright`，不要用默认环境判断项目不可运行。
- `build_exe.bat` 会删除 `build` 和 `dist\PutawayAiRobot` 后重新打包；不要在这些目录内放需要保留的手工文件。
- `build_exe.bat` 目前尝试复制 `环境重建与启动指南.md`，当前项目根目录未必存在该文件，构建验证时要留意。
- 项目不是 git 仓库时，不要假设可以用 git 恢复文件。

## 文件地图

- `browser_dom_automation.py`：PyQt5 主 UI。管理浏览器启动、CDP 标签页列表、账号配置、产品数据表、运行设置、手动清理、批量上架按钮。
- `workers.py`：后台线程。`BrowserWorker` 启动持久化浏览器；`CdpActionWorker` 执行单次动作；`AlbumCleanupWorker` 清理图片空间；`BatchPublishWorker` 并发批量上架、写日志、按成功数触发清理。
- `dianxiaomi_flows.py`：主自动化流程。包含登录填写、进入创建产品页、选择店铺/分类、引用模板、标题、素材图、变种颜色、SKC、自动选图，并串联后续子流程和发布。
- `album_cleanup_flow.py`：图片空间清理流程，连接现有 CDP 浏览器，打开/复用图片空间页面，批量删除素材。
- `config_store.py`：配置存储。账号密码使用 Windows DPAPI 加密，产品数据和运行设置写入 `%APPDATA%\PutawayAiRobot`。
- `browser_launch.py`：检测 Chrome / Edge，支持环境变量 `PUTAWAY_BROWSER_PATH` 指定浏览器 exe，启动 Playwright persistent context。
- `cdp_utils.py`：通过 CDP HTTP 接口列出、新建、关闭标签页。
- `excel_importer.py`：导入 Excel 产品数据。
- `image_resolver.py`：根据 SKU 和颜色解析本地图片素材。
- `element_ui_select.py`：Element UI 下拉框读取、打开、选择工具。
- `size_chart_flow.py`：添加尺码表模板。
- `model_info_flow.py`：选择模特试穿尺码。
- `sku_advanced_flow.py`：按 SKU 拆分并填写高级前后缀。
- `declare_price_flow.py`：批量填写申报价格。
- `package_size_flow.py`：批量填写包裹尺寸。
- `weight_flow.py`：按序列填写重量。
- `suggest_price_flow.py`：批量填写建议价格。
- `product_description_flow.py`：打开产品描述编辑器，批量上传详情图并保存。
- `publish_flow.py`：点击发布并选择立即发布，等待发布受理信号。
- `publish_logger.py`：在 `log/YYYYMMDD/*.log` 写批量上架日志。
- `window_text_locator.py`：独立的窗口截图/OCR 定位实验工具，不是主入口。
- `cleanup_control_window.py`：独立清理控制窗口。
- `app_version.py`：版本与窗口标题。
- `data/test(9).xlsx`：示例 Excel。
- `data/pic/1`：SKU 主图目录。
- `data/pic/2`：颜色套图目录。

## 数据约定

Excel 第一行必须包含以下中文表头：

- `店铺名称`
- `产品分类`
- `产品标题`
- `产品序列号`
- `颜色`

导入后映射为：

- `shop_name`
- `category`
- `title`
- `sku`
- `color`

图片素材约定：

- `data/pic/1` 是 SKU 主图目录。优先匹配 `{SKU}.jpg|jpeg|png|webp`，如果没有完整文件名，则匹配文件名包含货号的图片，例如 `BO-306_产品标题.png`。
- `data/pic/2/{颜色}{1..4}.jpg|jpeg|png|webp` 是颜色套图。
- 当前 `image_resolver.py` 只内置支持 `白/white/w` 与 `黑/black/b`，其他颜色会报错。
- `resolve_variant_image_paths(sku, color)` 返回 `[SKU主图, 颜色1, 颜色2, 颜色3, 颜色4]`。

运行时配置位置：

- 账号：`%APPDATA%\PutawayAiRobot\config.json`
- 产品数据：`%APPDATA%\PutawayAiRobot\product_data.json`
- 运行设置：`%APPDATA%\PutawayAiRobot\runtime_settings.json`
- 运行设置包含“连续上传失败停止阈值”，默认 3；设为 0 表示关闭保护。

## 主流程顺序

批量上架大致路径：

1. UI 从产品表收集数据。
2. `BatchPublishWorker._valid_rows()` 过滤缺少店铺或分类的行。
3. 开始前调用 `clear_album_space()` 清理图片空间。
4. 按并发数打开 TEMU 创建页。
5. 每行调用 `select_shop_category_flow()`。
6. `_select_shop_and_category()` 执行页面内业务步骤：
   - 选择店铺名称。
   - 选择产品分类，分类字符串会用 `/`、`>`、`、` 或空白拆分后取最后一级。
   - 引用产品模板。
   - 填写产品标题。
   - 上传产品素材图。
   - 选择变种属性模板。
   - 设置颜色并勾选。
   - 填写 SKC 编码。
   - 自动选择图片。
   - 添加尺码表。
   - 选择模特信息。
   - 填写 SKU 高级前后缀。
   - 填写申报价格。
   - 填写包裹尺寸和重量。
   - 填写建议价格。
   - 上传产品描述图片。
   - 立即发布。
7. 成功行会从 UI 表格移除并保存剩余产品数据。
8. 达到 `cleanup_every` 成功数后暂停新任务，等当前并发任务完成，再清理图片空间。
9. 日志写入 `log/YYYYMMDD`。

## 自动化编码原则

- 优先复用现有 helper：`_first_visible`、`_click_first`、`_click_with_retry`、`_action_locators`、`get_el_form_item_value`、`open_el_form_item_dropdown`、`select_el_option_by_text`。
- Playwright 代码尽量使用短超时、多候选定位器、失败后继续尝试的模式；该项目页面结构变化较频繁。
- 修改业务步骤顺序前，先确认是否会影响后续页面状态。例如素材上传、颜色勾选、SKC、自动选图之间存在强依赖。
- 不要在 UI 线程里执行网络、Playwright、文件批量处理等耗时逻辑；新增动作应放到 `workers.py` 的线程或由现有 worker 调用。
- 后台线程向 UI 反馈使用 Qt signal，例如 `progress`、`ok`、`failed`、`row_done`。
- 连接现有浏览器时使用 CDP：`p.chromium.connect_over_cdp(cdp_base_url)`，结束时优先 `browser.disconnect()`。
- 需要新建发布页面时，参考 `BatchPublishWorker._open_target()`，尽量记录 `webSocketDebuggerUrl`，便于精确关闭目标页。
- 对真实页面弹窗统一尽量挂载 `_auto_dismiss_dialog`，避免 JS dialog 阻塞。
- 对用户可见中文错误信息要具体说明缺少哪个按钮、输入框、素材或依赖。

## 中文与编码

- 源码按 UTF-8 读写。PowerShell 默认输出可能把中文显示成乱码；不要仅凭终端乱码判断源码已损坏。
- 修改中文字符串时，用 `Get-Content -Encoding UTF8` 或编辑器确认内容。
- 不要把已经正常的中文文案改成转义串或拼音。

## 修改敏感点

- `config_store.py` 使用 Windows DPAPI，只适合当前 Windows 用户解密；不要改成明文存储。
- 每次完成项目代码更新，都必须同步递增 `app_version.py` 里的 `APP_VERSION`，软件窗口标题 `APP_TITLE` 会随版本自动更新。例如本次版本是 `3.0`，下一次应升到 `3.1`。
- `browser_profile` 是持久化浏览器配置目录，可能包含登录状态；不要随意删除。
- `data/pic` 包含业务素材，避免测试时批量重命名或覆盖。
- `log` 是发布记录，除非明确要求，不要清空。
- `build`、`dist`、`__pycache__`、`.buildvenv` 是生成产物或环境目录，阅读项目时通常跳过。
- `BatchPublishWorker` 失败策略是成功页关闭、一般失败页保留供人工检查；不要轻易改成全部关闭。
- `publish_now()` 把“立即发布未受理”视为错误，`BatchPublishWorker` 对特定错误做非阻塞处理；改错误文案时要同步检查 `_is_non_blocking_publish_error()`。

## 验证清单

改动后至少执行：

```powershell
conda run -n flask python verify_startup.py
conda run -n flask python -m py_compile (Get-ChildItem -Filter *.py).FullName
```

涉及 UI 或真实网页自动化时，尽量再做：

- 启动 `python browser_dom_automation.py`，确认窗口能打开。
- 点击“启动浏览器并打开店小秘”，确认 CDP 地址能刷新标签页。
- 用少量测试数据验证目标步骤，不要直接跑大批量。
- 检查 `log/YYYYMMDD` 中成功/失败记录是否符合预期。

如果没有真实账号、验证码、店小秘页面或素材数据，说明无法完整端到端验证，并列出已完成的静态检查。

## 常见排查

- 缺少 Playwright：先确认是否正在使用 `flask` conda 环境；补装时执行 `conda run -n flask python -m playwright install chromium`。
- 找不到浏览器：在运行设置里选 Edge/Chrome，或设置 `PUTAWAY_BROWSER_PATH` 指向 `chrome.exe` / `msedge.exe`。
- CDP 无页面：确认浏览器由本程序启动，端口默认 `9222`，地址默认 `http://127.0.0.1:9222`。
- Excel 导入失败：检查第一行是否为固定中文表头。
- 图片缺失：检查 SKU 主图在 `data/pic/1`，颜色套图在 `data/pic/2`。
- 选择器失效：优先打开真实页面观察组件库结构，再扩展候选定位器，不要只保留单一 selector。
- 并发发布异常：先将并发数调为 1 验证流程，再逐步增加。

## 回答与协作偏好

- 回答保持结构化、克制，不要过分夸赞。
- 对不确定结论明确标注不确定性，并说明需要什么证据继续判断。
- 修改前先读相关源码，避免基于文件名猜测。
- 涉及真实店铺、账号、发布动作、批量删除图片空间时，要谨慎说明风险；必要时先建议小样本验证。
