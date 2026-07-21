# 自动上架五档自定义克重 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 PutawayAiRobot 的批量上架流程中，保存并按用户配置的五个独立克重依次填写五个重量输入框。

**Architecture:** `config_store.py` 作为五档克重的唯一默认值与规范化边界；PyQt 界面在开始任务前生成不可变快照；worker 和页面流程只传递该快照。`weight_flow.py` 保留现有 DOM 等待和输入策略，但改为接受明确的五项列表。

**Tech Stack:** Python 3、PyQt5、Playwright sync API、pytest、unittest。

---

### Task 1: 五档克重配置

**Files:**
- Modify: `modules/PutawayAiRobot/config_store.py:233-315`
- Test: `modules/PutawayAiRobot/tests/test_config_store.py`

- [x] **Step 1: 编写失败测试**

```python
def test_missing_weights_uses_default_sequence(self):
    # 只写旧运行设置时，读取结果仍包含 [142, 147, 152, 157, 162]。

def test_saves_and_loads_five_custom_weights(self):
    # 保存 (140, 145, 150, 155, 160)，读取和 JSON 文件均保留该列表。

def test_invalid_weights_fall_back_to_default_sequence(self):
    # 长度不是五项、零、负数、小数或非数字均回退默认值。
```

- [x] **Step 2: 运行失败测试**

Run: `conda run -n flask python -m pytest tests/test_config_store.py -q`

Expected: FAIL，因为 `weights` 尚不存在或保存接口不接受第八个参数。

- [x] **Step 3: 实现最小配置边界**

```python
DEFAULT_WEIGHTS = (142, 147, 152, 157, 162)

def normalize_weights(value, default=DEFAULT_WEIGHTS):
    # 仅接受恰好五个正整数，其他情况返回 list(default)。
```

在 `load_runtime_settings()` 默认值和读取结果增加 `weights`，在 `save_runtime_settings()` 的末尾增加 `weights=DEFAULT_WEIGHTS` 并写入规范化列表。

- [x] **Step 4: 运行配置测试**

Run: `conda run -n flask python -m pytest tests/test_config_store.py -q`

Expected: PASS。

### Task 2: 重量流程按五项填写

**Files:**
- Modify: `modules/PutawayAiRobot/weight_flow.py:1-51`
- Create: `modules/PutawayAiRobot/tests/test_weight_flow.py`

- [x] **Step 1: 编写失败测试**

```python
def test_fill_weights_fills_each_visible_input_in_order():
    # 模拟五个输入框，断言依次收到 140、141、150、155、166。

def test_fill_weights_rejects_values_that_are_not_five_positive_integers():
    # 传入四项、零、小数时，断言在操作页面前抛出 ValueError。
```

- [x] **Step 2: 运行失败测试**

Run: `conda run -n flask python -m pytest tests/test_weight_flow.py -q`

Expected: FAIL，因为 `fill_weights` 尚不存在。

- [x] **Step 3: 实现逐项填写函数**

```python
def fill_weights(page, weights=DEFAULT_WEIGHTS, progress=None):
    normalized = normalize_weights(weights)
    if list(weights) != normalized:
        raise ValueError("重量必须是五个正整数")
    # 等待至少 len(normalized) 个 input[name="weight"]，再按 nth(i) 逐项填写。
```

保留 `fill_weight_sequence()` 作为兼容包装器，以默认序列调用 `fill_weights()`，避免其他潜在调用者立即失效。

- [x] **Step 4: 运行重量流程测试**

Run: `conda run -n flask python -m pytest tests/test_weight_flow.py -q`

Expected: PASS。

### Task 3: 运行设置界面与批量任务快照

**Files:**
- Modify: `modules/PutawayAiRobot/browser_dom_automation.py:10-20,175-196,470-555`
- Modify: `modules/PutawayAiRobot/tests/test_embedded_widget.py`

- [x] **Step 1: 编写失败测试**

```python
def test_publish_controls_show_configured_custom_weights(monkeypatch):
    # 设置返回 [140, 145, 150, 155, 160]，断言五个 QSpinBox 显示这些值。

def test_publish_confirmation_snapshots_custom_weights(monkeypatch):
    # 将五个控件设为自定义值，断言确认框、worker kwargs、状态文字均使用相同顺序。
```

- [x] **Step 2: 运行失败测试**

Run: `conda run -n flask python -m pytest tests/test_embedded_widget.py -q`

Expected: FAIL，因为五个克重控件和 `weights` 传参尚不存在。

- [x] **Step 3: 实现界面和快照传递**

```python
self.weight_inputs = []
for index, default in enumerate(DEFAULT_WEIGHTS, start=1):
    input_box = QtWidgets.QSpinBox()
    input_box.setRange(1, 999999)
    input_box.setValue(default)
    self.weight_inputs.append(input_box)
    runtime_form.addRow(f"第{index}档克重（g）：", input_box)
```

从加载结果填充控件；保存时传递五项列表。开始批量上架前调用 `normalize_weights()`，在确认文字和状态显示 `克重：140/145/150/155/160g`，并将元组传入 `BatchPublishWorker(weights=weights)`。

- [x] **Step 4: 运行界面测试**

Run: `conda run -n flask python -m pytest tests/test_embedded_widget.py -q`

Expected: PASS。

### Task 4: Worker 与页面流程传递

**Files:**
- Modify: `modules/PutawayAiRobot/workers.py:1-20,128-180,204-490`
- Modify: `modules/PutawayAiRobot/dianxiaomi_flows.py:889-1045,1642-1695`
- Modify: `modules/PutawayAiRobot/tests/test_workers_declare_price.py`

- [x] **Step 1: 编写失败测试**

```python
def test_single_action_forwards_custom_weights(monkeypatch):
    # CdpActionWorker 将 (140, 145, 150, 155, 160) 原样传入流程。

def test_batch_worker_snapshots_and_forwards_custom_weights(monkeypatch):
    # BatchPublishWorker 规范化并将五项原样传入流程。
```

- [x] **Step 2: 运行失败测试**

Run: `conda run -n flask python -m pytest tests/test_workers_declare_price.py -q`

Expected: FAIL，因为 worker 尚未接受或传递 `weights`。

- [x] **Step 3: 实现参数传递和页面替换**

在 `CdpActionWorker`、`BatchPublishWorker`、`select_shop_category_flow()`、`_select_shop_and_category()` 末尾增加可选 `weights=DEFAULT_WEIGHTS` 参数。构造 worker 时调用 `normalize_weights()`，调用页面流程时传入 tuple。

将 `_select_shop_and_category()` 的两处：

```python
fill_weight_sequence(page, 142, 5, 5, progress=progress)
```

替换为：

```python
fill_weights(page, weights, progress=progress)
```

- [x] **Step 4: 运行 worker 测试**

Run: `conda run -n flask python -m pytest tests/test_workers_declare_price.py -q`

Expected: PASS。

### Task 5: 版本、集成验证与版本留档

**Files:**
- Modify: `modules/PutawayAiRobot/app_version.py`
- Modify: `docs/superpowers/plans/2026-07-21-putaway-custom-weights.md`

- [x] **Step 1: 递增应用版本**

按 `modules/PutawayAiRobot/AGENTS.md` 的约定，将 `APP_VERSION` 递增一个小版本，保持标题由现有拼接逻辑生成。

- [x] **Step 2: 运行完整验证**

Run:

```powershell
conda run -n flask python -m pytest tests/test_config_store.py tests/test_weight_flow.py tests/test_embedded_widget.py tests/test_workers_declare_price.py -q
conda run -n flask python verify_startup.py
conda run -n flask python -m py_compile (Get-ChildItem -Filter *.py).FullName
```

Expected: 所有命令退出码为 0。

- [x] **Step 3: 进行无发布 PyQt 冒烟检查**

Run: 创建 `PutawayEmbeddedWidget`，处理一次 Qt 事件循环后销毁；不点击“开始批量上架”。

Expected: 退出码为 0，五个克重控件可构造。

- [x] **Step 4: 提交并推送**

```powershell
git add modules/PutawayAiRobot/config_store.py modules/PutawayAiRobot/weight_flow.py modules/PutawayAiRobot/browser_dom_automation.py modules/PutawayAiRobot/workers.py modules/PutawayAiRobot/dianxiaomi_flows.py modules/PutawayAiRobot/app_version.py modules/PutawayAiRobot/tests/test_config_store.py modules/PutawayAiRobot/tests/test_weight_flow.py modules/PutawayAiRobot/tests/test_embedded_widget.py modules/PutawayAiRobot/tests/test_workers_declare_price.py docs/superpowers/plans/2026-07-21-putaway-custom-weights.md
git commit -m "feat: add custom publish weights"
git push origin HEAD:refs/heads/codex/2026-07-14-custom-monitor-shops
```
