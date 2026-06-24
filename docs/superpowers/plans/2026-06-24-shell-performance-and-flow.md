# ConsolePlat 卡顿治理与流程优化实施计划

> **For agentic workers / 给 Codex 等 AI 执行器:** REQUIRED SUB-SKILL: 用 `superpowers:executing-plans`(或 `superpowers:subagent-driven-development`)按 Task 逐条实现。**本计划任务多、彼此独立,强制派 subagent 执行**:每个 Task 起一个独立 subagent 落地(读相关文件→改→自测),主进程只做调度、合并、跨 Task 一致性把关。每个 Task 用 `- [ ]` 复选框跟踪,每个 Task 结束都要 `py_compile` + 相关 pytest 验证后再进入下一个。全程简体中文:注释、提交信息、日志文案、计划勾选都用中文。涉及真实网站动作(唤起上架、占用正式货号)严格遵守 `AGENTS.md` 的自动化安全边界,本计划不改动任何真实发布逻辑,只优化性能与体验。

**Goal:** 软件用着卡顿、流程割裂。本计划分两大块根治:

1. **卡顿治理(P0,最高优先级)** —— 当前三处明确的性能瓶颈:
   - **启动慢**:`MainWindow._build_content` 启动时一次性创建全部 7 个页面,其中 `PutawayPage`/`ApplyGoodsPage` 在构造函数里**同步** `importlib.exec_module` 整个外部项目(PutawayAiRobot / ApplyGoods),首屏迟迟不出。
   - **运行中卡 + 列表闪烁**:生图/改图子进程每打印一行 stdout,就触发"全量 JSON 写盘 ×2 + 任务列表 `clear()` 全量重建",高频输出时 UI 明显卡顿。
   - **表单输入逐字卡 + 切页停顿**:`SettingsStore.load()` 被当廉价 getter 高频调用,每次都走 Windows DPAPI 解密;`_save_preferences` 绑在每个控件信号上,文本框逐字符落盘;切页 `showEvent` 每次全量读盘重建列表。

2. **流程优化(P1/P2)** —— 让流程既连贯又好用:
   - 监控→发布两条线断开,用户得自己脑补衔接(P1)。
   - 源项目路径全硬编码到 `E:/1PythonProject/`,换机即崩(P1)。
   - 体验增强:全局加载态/忙碌指示、统一的"任务中心"可见性、内嵌页加载占位动画(P2,含我补充的体验想法)。

**Architecture:** 不引入新框架、不重写四个源项目、不合并三套执行器(发布/生图/改图各自的 `QProcess` + 任务列表是已确认的务实折中,风险太大)。核心手法三条:① **懒加载**——页面与内嵌外部项目改成首次切到才构建;② **去抖 + 增量更新**——把"进度推进"与"持久化/重建"解耦,落盘走去抖 `QTimer`,列表改单项更新;③ **缓存**——设置在页面内缓存一份 `self.settings`,避免重复 `load()` 与重复 DPAPI 解密。流程层只做"引导式衔接"(给入口、传上下文),不做改变真实网站状态的全自动串联。

**Tech Stack:** Python 3、PyQt5(`QStackedWidget` / `QProcess` / `QTimer` / `showEvent`)、JSON 任务文件(`TaskStore`)、DPAPI(`config.py`)、pytest(headless QApplication,monkeypatch `SettingsStore`)、`py_compile` 静态验证。

---

## 背景:执行前必须读懂的现状(不要凭空发明,复用已有机制)

- `consoleplat/ui/main_window.py`
  - `_build_content`(134-138):`for item in DEFAULT_NAV_ITEMS: page=self._create_page(item.key); stack.addWidget(page)` —— 启动即建全部页面,**这是启动慢的根因**。
  - `_create_page`(141-163):逐 key 返回真实页面实例。
  - `activate_page`(165-174):仅 `stack.setCurrentIndex` + 刷新导航按钮态,不通知页面。懒加载要挂在这里。
- `consoleplat/ui/putaway_page.py`:`__init__`(13-21)构造即 `_build_ui`,`_build_ui`(62)同步 `adapter.build_embedded_widget()`,后者 `importlib` 加载整个 PutawayAiRobot。`ApplyGoodsPage` 同理(`apply_goods_page.py` 构造即内嵌)。
- `consoleplat/ui/product_publish_page.py`
  - `_save_and_refresh`(1261-1266):`_save_task_history()`(全量写盘)+ `_sync_mirror_task()`(再 load 一个镜像文件+全量 save,1268-1280)+ `_rebuild_task_list()`(1407-1415,`clear()` 后全量 `addItem`)+ `_select_record` + `_set_status`。被 stdout 高频触发。
  - `_rebuild_task_list`(1407-1415):`self.task_list.clear()` 全清重建。
  - `_load_preferences`(1422)/`_save_preferences`:每次 `self.settings_store.load()`;`_save_preferences` 绑在十几个控件 `valueChanged/textChanged/toggled` 上。
- `consoleplat/config.py`:`SettingsStore.load()`(约 205-288)每次 `read_text` 整个 JSON,对账号密码、每个 AI 接口 api_key 逐个 `decrypt_secret`(DPAPI ctypes)。被各页面当廉价 getter 频繁调用。
- `consoleplat/ui/ai_edit_page.py`/`local_image_page.py`:`showEvent → reload_tasks_from_store → task_store.load() → 全量重建列表`,每次切页全量读盘。同样有 stdout→写盘→重建模式。
- `consoleplat/ui/monitor_page.py`:`apply_snapshot`(约 432-449)每次刷新 `setRowCount` 后逐格新建 `QTableWidgetItem`(≤100 行×8 列),配合 ≥2s 定时刷新。
- `consoleplat/models.py:DEFAULT_NAV_ITEMS`:7 个导航项与 key。

关键认知:整体架构没问题,重活都在子进程/线程。卡顿来自"启动全建 + 高频全量 IO/重建 + 频繁 DPAPI 解密"。本计划**只做减负,不动业务逻辑与安全边界**。

---

## File Structure

**P0 卡顿治理**
- 修改:`consoleplat/ui/main_window.py` —— 页面懒加载:`_build_content` 只为每个 key 放轻量占位 widget,`activate_page` 首次切到才真正 `_create_page` 并替换占位。维护 `_built: set[str]`。
- 修改:`consoleplat/ui/putaway_page.py`、`consoleplat/ui/apply_goods_page.py` —— 内嵌外部项目延迟到首次 `showEvent` 才 `build_embedded_widget`,构造时只显示占位/加载提示。
- 修改:`consoleplat/ui/product_publish_page.py` —— stdout 高频路径去抖:进度到达只更新内存 + 当前选中项文本;落盘与 `_rebuild_task_list` 改去抖 `QTimer`(约 500ms 合并);`_rebuild_task_list` 改单项 `setText`。页面内缓存 `self.settings`,`_save_preferences` 对文本框去抖。
- 修改:`consoleplat/ui/local_image_page.py`、`consoleplat/ui/ai_edit_page.py` —— 同样的 stdout 去抖 + 增量更新;`showEvent` 加文件 mtime 判断,未变则跳过重建。
- 修改:`consoleplat/config.py` —— `SettingsStore` 内部按文件 mtime 缓存解密结果,重复 `load()` 命中缓存直接返回(文件未变时)。
- 创建:`tests/test_lazy_page_loading.py` —— headless 断言:启动时内嵌页未构建,切到后才构建。
- 创建/追加:`tests/test_settings_store_cache.py` —— 断言未变更时 `load()` 命中缓存、不重复解密(可对 `decrypt_secret` 计数 monkeypatch)。

**P1 流程衔接 + 路径配置**
- 修改:`consoleplat/ui/monitor_page.py`、`consoleplat/ui/product_publish_page.py`、`consoleplat/ui/main_window.py` —— 监控导出备货单后,提供"去发布"引导入口,把导出上下文(店铺/货号线索)传给发布页预填(引导式,不自动跑真实动作)。
- 修改:`consoleplat/config.py`、`consoleplat/ui/settings_page.py` —— 路径默认值改为"首次启动探测 + 相对/可迁移",或提供"一键定位四个源项目目录"。去掉硬编码 `E:/1PythonProject/` 的强依赖(缺失时给清晰引导,而非静默失败)。
- 追加:`tests/test_monitor_to_publish_handoff.py`、`tests/test_settings_paths.py`。

**P2 体验增强(含补充想法)**
- 修改:`consoleplat/ui/main_window.py` 及各页面 —— 全局忙碌/加载指示(切到未构建页时显示"加载中…",内嵌项目加载用占位动画);可选的轻量"任务中心"角标,显示有任务在跑。
- 不强制新建大量文件,以小改动叠加体验为主。

> 注:具体行号见各 Task。subagent 落地前务必先 `Read` 目标文件确认当前行号(代码可能已变动),不要盲目按计划行号 patch。

---

## 执行顺序与 subagent 分派

- **P0 必须先全部做完并验证**(Task 1~5),这是用户能立刻感知的卡顿来源。每个 Task 派一个独立 subagent;Task 1(懒加载)与 Task 4(config 缓存)互不冲突可并行,Task 2/3(各页 stdout 去抖)依赖 Task 4 的缓存接口,建议 Task 4 先落地。
- **P1**(Task 6~7)在 P0 验证通过后再做,涉及流程衔接与配置,改动面较大但不碰真实发布。
- **P2**(Task 8)收尾,纯体验增强。
- 每个 Task 完成 → `py_compile` + 该 Task 的 pytest + 一次全量 `python -m pytest tests/ -q` 防回归 → 勾选复选框 → commit(中文信息)。**不要把多个 Task 攒成一个大提交**,逐 Task 提交便于回滚。

---

## Task 1: 页面懒加载,首屏只建当前页

- [x] **Files:** Modify `consoleplat/ui/main_window.py`;Create `tests/test_lazy_page_loading.py`

**说明:** 启动慢的根因是 `_build_content`(134-138)一次性 `_create_page` 全部 7 页,其中 Putaway/ApplyGoods 构造即同步加载整个外部项目。改成懒加载:启动只建当前页(默认 `monitor`),其余切到才建。

**实现:**
1. `_build_content`(134-138):不再循环 `_create_page`。改为对每个 key `addWidget` 一个**轻量占位 widget**(一个带"加载中…"`QLabel` 的 `QWidget`,或直接 `QWidget()`),记录 `self.page_indexes[key]=index`。同时维护 `self._page_placeholders: dict[str, QWidget]` 和 `self._built: set[str]`。
2. 新增 `_ensure_page_built(key)`:若 `key not in self._built`,调 `_create_page(key)` 得到真实页面,用 `stack.insertWidget(old_index, real_page)` + 移除占位(或 `stack.replaceWidget`,注意 PyQt5 用 `removeWidget`+`insertWidget` 并更新 `page_indexes`),加入 `self._built`。把真实页面引用存起来供 `closeEvent`/`findChildren` 用。
3. `activate_page`(165):在 `setCurrentIndex` 之前先 `self._ensure_page_built(key)`,再用最新 index 切换。
4. 启动时(`__init__` 末尾或 `_build_content` 后)对默认页调用一次 `activate_page(默认 key)`,保证首屏是真实页面而非占位。
5. **注意 `closeEvent`(175-178)**:`findChildren(MonitorPage)` 依赖页面已实例化。懒加载后未构建的页面不会被找到——这是期望行为(没建就没有要清理的浏览器)。确认逻辑仍正确即可。

**测试(headless,monkeypatch SettingsStore 避免真实加载外部项目):**
- 构造 `MainWindow` 后,断言 `_built` 只含默认页,`PutawayPage`/`ApplyGoodsPage` 实例尚未创建(可对 `PutawayAdapter.build_embedded_widget` monkeypatch 计数,断言初始为 0)。
- 调 `activate_page("putaway")` 后断言该页已构建、计数为 1;再切走再切回不重复构建(计数仍为 1)。

**Verify:**
```bash
python -m py_compile consoleplat/ui/main_window.py
python -m pytest tests/test_lazy_page_loading.py -q
python -m pytest tests/ -q
```

## Task 2: 内嵌外部项目延迟到首次显示才加载

- [x] **Files:** Modify `consoleplat/ui/putaway_page.py`、`consoleplat/ui/apply_goods_page.py`

**说明:** 即便 Task 1 让页面懒建,首次切到 Putaway/ApplyGoods 时仍会同步 `exec_module` 整个外部项目卡住主线程。把内嵌动作从 `__init__`/`_build_ui` 移到首次 `showEvent`,构造时只摆好占位与"加载中"提示,让页面先出来再补内嵌。

**实现(以 `putaway_page.py` 为参考,`apply_goods_page.py` 同构):**
1. `_build_ui`(23-75):保留容器、`status_label`、`error_label` 的搭建,但**移除**构造时的 `self.adapter.build_embedded_widget(...)`(61-74)。`status_label` 初始显示"准备加载内嵌上架界面…",新增 `self._embed_loaded = False`。
2. 重写 `showEvent`:首次显示(`not self._embed_loaded`)时:先 `status_label.setText("正在加载内嵌上架界面,请稍候…")` 并 `QApplication.processEvents()`(让占位先绘制),再 `try` 调 `build_embedded_widget` 内嵌,成功置 `_embed_loaded=True` 并 `addWidget`,失败走原有 `error_label` 降级。用 `QTimer.singleShot(0, self._load_embedded)` 把加载推到事件循环下一拍,避免 `showEvent` 内同步阻塞导致窗口"假死黑屏"。
3. 失败后允许重试:`error_label` 旁可加一个"重试加载"按钮(可选,低优先,不做也行)。

**测试:** headless 构造页面后断言 `_embed_loaded is False` 且 `build_embedded_widget` 未被调用;手动触发 `show()`/`showEvent` 后(monkeypatch `build_embedded_widget` 返回假 widget)断言被调用一次、再次 `showEvent` 不重复加载。

**Verify:**
```bash
python -m py_compile consoleplat/ui/putaway_page.py consoleplat/ui/apply_goods_page.py
python -m pytest tests/ -q
```

## Task 3: stdout 高频路径去抖——进度推进与持久化/重建解耦

- [x] **Files:** Modify `consoleplat/ui/product_publish_page.py`、`consoleplat/ui/local_image_page.py`、`consoleplat/ui/ai_edit_page.py`

**说明:** 运行中卡顿 + 列表闪烁的根因:子进程每打印一行 stdout → `_update_progress_from_text` → `_save_and_refresh`(1261),后者一次做 2 次全量 JSON 写盘 + `clear()` 全量重建列表 + 重选 + 重设状态。生图/改图进度日志极频繁,这串重活被高频触发。要把"实时更新选中项文案/进度条"(每次都做,轻)与"落盘 + 重建列表"(去抖合并,重)拆开。

**实现(`product_publish_page.py` 为主,另两页同构):**
1. 新增去抖定时器:`self._persist_timer = QTimer(self); self._persist_timer.setSingleShot(True); self._persist_timer.setInterval(500); self._persist_timer.timeout.connect(self._flush_persist)`。再加 `self._dirty_records: set[str]`(待落盘 task_id)。
2. 拆分现有 `_save_and_refresh(record)`:
   - 新增轻量 `_touch_record(record)`:只更新**当前选中项**的状态文本/进度条/日志(`_set_status(record)` 中只刷当前选中相关的部分,不 `clear()` 列表),并更新该 record 在列表里对应 item 的 `setText`(见第 4 点)。把 record.task_id 加入 `_dirty_records`,`self._persist_timer.start()`(重启计时,合并连续输出)。
   - 新增 `_flush_persist()`:真正执行 `_save_task_history()` + 对 `_dirty_records` 里的记录 `_sync_mirror_task`,然后清空 `_dirty_records`。**注意 `_sync_mirror_task`(1268)目前每次 load+save 镜像文件,flush 里对同一文件多个 record 应合并一次读写**(按 mode 分组,一次性写)。
3. **stdout 回调(`_read_stdout` 等)** 改调 `_touch_record` 而非 `_save_and_refresh`。**阶段性变化点**(任务开始、生图完成、校验完成、唤起、终态 DONE/FAILED/ABORTED)仍直接调一次 `_flush_persist()` + 必要时 `_rebuild_task_list()`(状态机切换、增删任务时才需要整表重排)。
4. `_rebuild_task_list`(1407)保留,但新增 `_update_task_item(record)`:遍历 `task_list` 找到 `data(Qt.UserRole)==record.task_id` 的 item,`setText(...)` 就地更新文案,不 `clear()`。仅在"任务新增/删除/排序变化"时才调用全量 `_rebuild_task_list`。
5. `closeEvent` / 任务终态:确保退出前 `_flush_persist()` 把未落盘的脏数据写下去(别丢进度)。
6. `local_image_page.py` / `ai_edit_page.py`:对各自的 `readyRead → 写盘 + 重建` 路径做同样的去抖 + 单项更新改造,复用同样的命名与模式,保持三页一致。

**测试:** 模拟连续多行 stdout(直接调 `_touch_record` 多次),断言 `_save_task_history` 在 500ms 窗口内不被多次调用(可 monkeypatch 计数 + 手动 `_persist_timer.timeout.emit()` 或直接调 `_flush_persist`);断言列表项被 `setText` 更新而 `clear` 未被调用。

**Verify:**
```bash
python -m py_compile consoleplat/ui/product_publish_page.py consoleplat/ui/local_image_page.py consoleplat/ui/ai_edit_page.py
python -m pytest tests/ -q
```

## Task 4: SettingsStore 按 mtime 缓存,消除重复 DPAPI 解密

- [x] **Files:** Modify `consoleplat/config.py`;Create `tests/test_settings_store_cache.py`

**说明:** `SettingsStore.load()`(约 205-288)被各页面当廉价 getter 频繁调用(`ai_edit_page` 就有 11 处),每次都读整个 JSON 并对账号密码、每个 AI 接口 api_key 逐个走 DPAPI 解密。表单逐字符输入触发的 `_save_preferences` 里也是先 load。这是表单卡顿与切页停顿的放大器。

**实现:**
1. 在 `SettingsStore` 内加缓存:`self._cache: AppSettings | None`、`self._cache_mtime: float | None`、`self._cache_path: str`。
2. `load()` 开头:`stat` 配置文件取 `mtime`。若 `_cache` 存在且 `mtime` 未变且路径未变,直接 `return self._cache`(返回同一对象或深拷贝——若调用方会原地改字段后 save,则返回**深拷贝**更安全,避免缓存被意外篡改;`_save_preferences` 模式正是 load→改→save,建议 `copy.deepcopy`)。
3. 解析+解密后,填充 `_cache` 与 `_cache_mtime` 再返回。
4. `save()` 写盘后:更新 `_cache` 与 `_cache_mtime`(用新写入的对象和新 `mtime`),让紧随其后的 `load()` 命中。
5. 文件不存在/损坏的分支保持原有兜底逻辑,不缓存异常态。
6. **不要破坏** `load` 对旧单接口配置迁移到 `ai_providers` 的兼容逻辑——迁移结果同样进缓存。

**测试(monkeypatch 计数 `decrypt_secret`):**
- 连续两次 `load()`(文件未变):`decrypt_secret` 只在第一次被调,第二次命中缓存不再解密。
- `save()` 后再 `load()`:返回最新值。
- 修改文件 mtime(或重写文件)后 `load()`:缓存失效,重新解密。

**Verify:**
```bash
python -m py_compile consoleplat/config.py
python -m pytest tests/test_settings_store_cache.py -q
python -m pytest tests/ -q
```

## Task 5: 表单去抖 + 切页 mtime 跳过重建

- [x] **Files:** Modify `consoleplat/ui/product_publish_page.py`、`consoleplat/ui/ai_edit_page.py`、`consoleplat/ui/local_image_page.py`

**说明:** 收尾 P0。Task 4 已让重复 `load()` 变廉价,这里再消除两个具体热点:① 文本框逐字符 `_save_preferences` 落盘;② 切页 `showEvent` 每次全量读盘重建。

**实现:**
1. **页面缓存 settings:** 各页 `__init__` 存 `self.settings = self.settings_store.load()` 一次,后续逻辑优先用 `self.settings`,只在确有外部变更(如设置页保存后)才刷新。`_load_preferences`(1422)里 `self.settings_store.load()` 复用 Task 4 缓存即可,不必每个回调都 load。
2. **文本框去抖:** `_save_preferences` 拆成"即时存内存 self.settings 字段" + "去抖落盘"。对 `ai_prompt_edit`/`task_name_edit` 等文本框,`textChanged` 只更新内存,挂一个 `self._pref_save_timer`(singleShot,800ms)在停止输入后统一 `settings_store.save()`。`valueChanged/toggled`(开关、数字)变化不频繁,可即时存(走 Task 4 缓存,代价已很低)。保留现有 `_loading_preferences` 守卫避免回填触发保存。
3. **切页 mtime 跳过:** `ai_edit_page` / `local_image_page` 的 `showEvent → reload_tasks_from_store`:记录上次读取的任务文件 `mtime`(`self._tasks_file_mtime`),`showEvent` 时先比对,未变化直接 `return` 不重建列表;变化才读盘 + 增量更新(复用 Task 3 的 `_update_task_item`,而非全量 `clear` 重建)。
4. **关闭时 flush:** 确保去抖的偏好保存在 `closeEvent` 前 flush 一次(别丢用户最后的输入)。

**测试:** 模拟文本框连续 `textChanged`,断言 `settings_store.save` 在去抖窗口内不被多次调用;`showEvent` 在文件 mtime 未变时不调用列表重建。

**Verify:**
```bash
python -m py_compile consoleplat/ui/product_publish_page.py consoleplat/ui/ai_edit_page.py consoleplat/ui/local_image_page.py
python -m pytest tests/ -q
```

## Task 6: 监控→发布引导式衔接(P1)

- [x] **Files:** Modify `consoleplat/ui/monitor_page.py`、`consoleplat/ui/product_publish_page.py`、`consoleplat/ui/main_window.py`

**说明:** 当前监控到紧急备货后只能手动点"导出备货单",导出结果(SendGoods 产物)与发布页的生图/上架流程**没有任何衔接**,用户得自己脑补。本 Task 做**引导式衔接**——不自动触发任何真实网站动作,只把"下一步去哪、带什么上下文"接起来,降低操作断层。

**实现:**
1. 监控页导出备货单成功后(`apply_export_result` / 导出回调附近),在事件流/状态区显示一条可点击引导:"备货单已导出 → 去发布页生图上架",并暴露一个信号 `request_open_publish(context: dict)`,`context` 带导出目录、店铺、可推断的货号前缀/数量线索。
2. `main_window` 连接该信号:`activate_page("publish")` 并调用发布页新增的 `prefill_from_monitor(context)`。
3. 发布页 `prefill_from_monitor`:把 context 里的线索**预填到草稿面板对应控件**(前缀/数量/任务名等),并在面板顶部提示"已从监控导出结果带入,请确认后开始"。**只预填、不自动开始**——`confirm_and_start` 仍需用户显式点击(遵守 `AGENTS.md` 安全边界)。
4. 字段不全时给空缺项合理默认,不报错、不卡流程。

**测试:** headless 触发 `request_open_publish(context)`,断言主窗口切到 publish 且控件被预填;断言不会自动调用 `confirm_and_start`/不起任何子进程。

**Verify:**
```bash
python -m py_compile consoleplat/ui/monitor_page.py consoleplat/ui/product_publish_page.py consoleplat/ui/main_window.py
python -m pytest tests/ -q
```

## Task 7: 源项目路径去硬编码,支持迁移(P1)

- [x] **Files:** Modify `consoleplat/config.py`、`consoleplat/ui/settings_page.py`

**说明:** 所有源项目路径默认值写死成 `E:/1PythonProject/...`,换机器/换盘符必须先进设置逐项改,打包分发脆弱。改成"可探测 + 可一键定位 + 缺失有清晰引导"。

**实现:**
1. `config.py`:路径字段默认值改为空串或 `None`,新增一个解析函数 `resolve_project_dir(name, configured)`:configured 非空则用它;否则按候选根目录探测(如 ConsolePlat 同级、`%USERPROFILE%`、当前盘 `1PythonProject`),命中返回,否则返回 None。**保留向后兼容**:已存在的 `settings.json` 里旧硬编码路径若仍有效,继续生效。
2. 各页面用 `resolve_project_dir` 取路径(替代 `or r"E:\1PythonProject\..."` 硬编码),取不到时不崩溃:内嵌页走已有 `error_label` 降级并提示"未找到 X 项目,请在设置中指定目录"。
3. `settings_page.py`:四个源项目路径各加"浏览…"目录选择按钮(`QFileDialog.getExistingDirectory`),并显示当前解析到的实际路径(区分"已配置/自动探测到/未找到")。可加"一键定位"尝试自动探测全部。
4. 探测/校验只读文件系统,不做任何网络或写操作。

**测试:** monkeypatch 文件系统/`exists`,断言 configured 优先、探测兜底、全失败返回 None 且不抛异常;设置页能写入选中目录。

**Verify:**
```bash
python -m py_compile consoleplat/config.py consoleplat/ui/settings_page.py
python -m pytest tests/ -q
```

## Task 8: 体验增强——加载态与忙碌指示(P2)

- [x] **Files:** Modify `consoleplat/ui/main_window.py` 及相关页面(小改动叠加)

**说明:** 纯体验提升,在 P0/P1 稳定后做。让"正在加载/有任务在跑"对用户可见,减少"是不是卡死了"的焦虑。

**实现(择优,不必全做):**
1. **切页加载态:** Task 1 的占位 widget 显示统一的"加载中…"样式;Task 2 内嵌项目加载时占位区显示一个轻量动画或"正在加载 PutawayAiRobot 界面…"文案,加载完平滑替换。
2. **任务运行角标:** 导航栏对应有任务在跑的页面(发布/生图/改图)显示一个小圆点/数字角标,切走也能知道后台在跑。数据来自各页内存中的运行态,不新增轮询。
3. **首屏提速反馈:** 启动后立即可见窗口与导航(Task 1 已保证),首屏不再白屏等外部项目。
4. 配色/文案与现有 `objectName` 样式(`statusPill`/`sectionTitle` 等)保持一致,不引入新主题体系。

**测试:** headless 断言占位文案存在、角标随运行态显隐(可对运行态置位后断言角标可见)。

**Verify:**
```bash
python -m py_compile consoleplat/ui/main_window.py
python -m pytest tests/ -q
```

---

## 验收标准(全部 Task 完成后)

- **启动:** 冷启动到窗口可交互明显变快;首屏不再因加载 Putaway/ApplyGoods 而卡白屏(可主观计时,或在 `_build_content` 前后打点对比)。
- **运行:** 生图/改图高频输出时列表不再闪烁、不再可感知卡顿;进度仍实时更新;任务进度不丢(去抖落盘 + 关闭 flush)。
- **表单:** 提示词/任务名逐字输入流畅不卡;切页无明显停顿。
- **流程:** 监控导出后能一键带上下文跳到发布页预填;换目录/换机后能通过设置定位源项目而非崩溃。
- **回归:** `python -m pytest tests/ -q` 全绿;`py_compile` 覆盖所有改动文件无错。
- **安全边界:** 全程未改动任何真实发布/上架/改库存逻辑,衔接均为"引导 + 预填",真实动作仍需用户显式确认(符合 `AGENTS.md`)。

## 风险与注意

- **懒加载与 `findChildren`/`closeEvent`:** 改懒加载后,未构建页面不在控件树里。确认 `closeEvent`(main_window.py:175)对 MonitorPage 的浏览器清理在"监控页从未被打开"时依然安全(没建=无需清理)。
- **去抖丢数据:** 去抖落盘必须在终态变化和 `closeEvent` 强制 flush,否则最后一段进度/偏好可能不落盘。每个去抖点都要配一个"立即 flush"出口。
- **缓存一致性:** `SettingsStore` 缓存若返回同一对象,调用方原地改字段会污染缓存——本计划要求返回深拷贝。设置页保存后必须更新缓存,避免别的页读到旧值。
- **不合并三套执行器:** 发布/生图/改图各自的 `QProcess` + 任务列表是已知折中,本计划只在各自内部做去抖,**不跨页合并**,不要顺手重构。
- **行号会漂移:** 计划里的行号是参考,subagent 落地前必须 `Read` 当前文件确认,按符号(函数名)定位而非死记行号。
- **版本号:** 完成后按 README 规则更新 `consoleplat/__init__.py:APP_VERSION`(本计划改动 >200 行,`+0.1`)。
- **Git:** 逐 Task 中文提交;无法推 `main` 则推 `codex/` 前缀的日期/主题分支;每轮报告 commit hash、推送目标、验证结果。


