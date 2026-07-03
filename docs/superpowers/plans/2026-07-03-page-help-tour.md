# Page Help Tour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-page `?` help buttons that launch a highlit in-page guided tutorial with locally generated screenshots.

**Architecture:** Store tutorial copy in a small data module, render it with a reusable PyQt overlay component, and have `MainWindow` launch the overlay for the active page. Page classes only expose stable `objectName` anchors; they do not own tutorial state.

**Tech Stack:** Python 3, PyQt5, pytest, existing ConsolePlat theme/style system, local PNG assets under `assets/images/tutorial/`.

---

## File Structure

- Create `consoleplat/ui/tutorial_data.py`: dataclasses and `TUTORIALS` mapping keyed by page key.
- Create `consoleplat/ui/tutorial_overlay.py`: `TutorialOverlay` widget and target-geometry lookup.
- Modify `consoleplat/ui/main_window.py`: add top-right `?` button and launch overlay for active page.
- Modify `consoleplat/ui/theme.py`: add light/dark styles for tutorial button and overlay card.
- Modify page files to add stable tutorial anchors:
  - `consoleplat/ui/monitor_page.py`
  - `consoleplat/ui/product_publish_page.py`
  - `consoleplat/ui/local_image_page.py`
  - `consoleplat/ui/ai_edit_page.py`
  - `consoleplat/ui/putaway_page.py`
  - `consoleplat/ui/apply_goods_page.py`
  - `consoleplat/ui/settings_page.py`
- Create `scripts/capture_tutorial_screenshots.py`: render pages with test settings and save PNGs.
- Create `tests/test_tutorial_data.py`: validate tutorial data quality and screenshot references.
- Create `tests/test_tutorial_overlay.py`: validate overlay navigation and fallback behavior.
- Modify `tests/test_main_window_ui.py`: validate `?` button exists and launches current page tutorial.

## Task 1: Tutorial Data

**Files:**
- Create: `consoleplat/ui/tutorial_data.py`
- Create: `tests/test_tutorial_data.py`

- [ ] **Step 1: Write the failing tests**

Add `tests/test_tutorial_data.py`:

```python
from consoleplat.models import DEFAULT_NAV_ITEMS
from consoleplat.ui.tutorial_data import TUTORIALS, TutorialStep, get_tutorial_steps


def test_each_nav_page_has_tutorial_steps():
    page_keys = {item.key for item in DEFAULT_NAV_ITEMS}

    assert set(TUTORIALS) == page_keys
    for key in page_keys:
        assert get_tutorial_steps(key), key


def test_tutorial_steps_have_required_text():
    for page_key, steps in TUTORIALS.items():
        for step in steps:
            assert isinstance(step, TutorialStep)
            assert step.title.strip(), page_key
            assert step.body.strip(), page_key
            assert step.target.strip(), page_key


def test_unknown_page_returns_empty_steps():
    assert get_tutorial_steps("missing") == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_tutorial_data.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'consoleplat.ui.tutorial_data'`.

- [ ] **Step 3: Write minimal implementation**

Create `consoleplat/ui/tutorial_data.py`:

```python
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
        TutorialStep("monitorMetricsAnchor", "先看店铺状态", "这里汇总待发货、备货件数和异常提醒。教程只说明页面，不会提交或发货。"),
        TutorialStep("monitorControlsAnchor", "控制刷新节奏", "选择店铺和刷新间隔后，可以手动刷新或开始监控。5 秒只是默认值，可以在设置中调整。"),
        TutorialStep("monitorOrdersAnchor", "查看待处理商品", "刷新成功后，待处理商品会显示在表格里，后续可导出备货单并交接到发布页。"),
    ),
    "publish": (
        TutorialStep("publishHeaderAnchor", "确认发布任务", "发布页承接监控导出的线索，用来确认批次、数量和后续生图分流。"),
        TutorialStep("publishFormAnchor", "填写任务信息", "这里配置店铺、任务名称、产品数量和输入来源。发布前需要人工确认范围。"),
        TutorialStep("publishActionsAnchor", "进入下一步", "确认后可准备本地生图、AI 改图或同步到上架流程。"),
    ),
    "local_image": (
        TutorialStep("localImageConfigAnchor", "配置本地生图", "选择店铺、风格、张数和货号范围，生成任务会在后台运行。"),
        TutorialStep("localImageStatusAnchor", "关注进度和输出", "这里显示任务状态、输出目录和日志，失败项会保留在清单中。"),
    ),
    "ai_edit": (
        TutorialStep("aiEditImagesAnchor", "选择输入图片", "先添加需要 AI 改图的图片，避免把账号或敏感截图放入任务。"),
        TutorialStep("aiEditRequestAnchor", "填写改图要求", "在提示词中描述目标效果，API Key 应通过设置或安全输入管理。"),
        TutorialStep("aiEditQueueAnchor", "查看任务结果", "任务队列会显示进度、失败原因和输出路径。"),
    ),
    "putaway": (
        TutorialStep("putawayEmbedAnchor", "连接自动上架工具", "这里嵌入或唤起 PutawayAiRobot，读取投放目录中的图片和 xlsx。"),
        TutorialStep("putawayStatusAnchor", "处理失败提示", "如果嵌入失败或依赖缺失，状态区会显示原因，原项目仍可独立运行。"),
    ),
    "apply": (
        TutorialStep("applyEmbedAnchor", "进入申请合规流程", "这里承接 ApplyGoods 的申请、合规、JIT 和库存等后置能力。"),
        TutorialStep("applySafetyAnchor", "注意人工确认点", "合规上传、库存、地址修改等会改变真实状态，必须保留确认或明确自动配置。"),
    ),
    "settings": (
        TutorialStep("settingsPathsAnchor", "检查项目路径", "确认四个源项目路径、输出目录和投放目录正确。"),
        TutorialStep("settingsBrowserAnchor", "配置浏览器连接", "默认 CDP 地址可用 127.0.0.1:9222，但应按实际浏览器调整。"),
        TutorialStep("settingsSecurityAnchor", "保护敏感信息", "账号、Cookie、Token 和 API Key 不应写入日志或普通配置文件。"),
    ),
}


def get_tutorial_steps(page_key: str) -> tuple[TutorialStep, ...]:
    return TUTORIALS.get(page_key, ())
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/test_tutorial_data.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

Do not commit yet if executing in one session; keep this change staged later with the full feature.

## Task 2: Tutorial Overlay Component

**Files:**
- Create: `consoleplat/ui/tutorial_overlay.py`
- Create: `tests/test_tutorial_overlay.py`
- Modify: `consoleplat/ui/theme.py`

- [ ] **Step 1: Write the failing tests**

Add `tests/test_tutorial_overlay.py`:

```python
from PyQt5.QtWidgets import QApplication, QLabel, QWidget

from consoleplat.ui.tutorial_data import TutorialStep
from consoleplat.ui.tutorial_overlay import TutorialOverlay


def test_tutorial_overlay_shows_first_step():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(640, 420)
    target = QLabel("target", parent)
    target.setObjectName("targetAnchor")
    target.setGeometry(40, 50, 160, 60)
    overlay = TutorialOverlay(
        parent,
        (TutorialStep("targetAnchor", "第一步", "说明文字"), TutorialStep("missing", "第二步", "后续说明")),
    )

    overlay.start()

    assert overlay.isVisible()
    assert overlay.title_label.text() == "1/2 第一 步".replace(" 第一 步", " 第一步")
    assert overlay.body_label.text() == "说明文字"
    assert overlay.highlight_rect.isValid()


def test_tutorial_overlay_navigation_and_finish():
    app = QApplication.instance() or QApplication([])
    parent = QWidget()
    parent.resize(640, 420)
    overlay = TutorialOverlay(
        parent,
        (TutorialStep("missing", "第一步", "说明"), TutorialStep("missing", "第二步", "更多")),
    )

    overlay.start()
    overlay.next_step()
    assert overlay.title_label.text() == "2/2 第二步"

    overlay.previous_step()
    assert overlay.title_label.text() == "1/2 第一步"

    overlay.finish()
    assert overlay.isHidden()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_tutorial_overlay.py -q
```

Expected: FAIL with missing module.

- [ ] **Step 3: Write minimal implementation**

Create `consoleplat/ui/tutorial_overlay.py` with a `QWidget` overlay that:

- stores `steps` and `current_index`;
- uses `findChild(QWidget, step.target)` to locate target widgets;
- draws dim background and rounded highlight in `paintEvent`;
- shows labels and buttons in a child `QFrame`;
- exposes `start()`, `next_step()`, `previous_step()`, `finish()`, and `show_step(index)`.

Use this exact public surface:

```python
class TutorialOverlay(QWidget):
    def __init__(self, host: QWidget, steps: tuple[TutorialStep, ...]) -> None: ...
    def start(self) -> None: ...
    def show_step(self, index: int) -> None: ...
    def next_step(self) -> None: ...
    def previous_step(self) -> None: ...
    def finish(self) -> None: ...
```

Modify `consoleplat/ui/theme.py` by adding styles for:

```css
QPushButton#tutorialButton { ... }
QFrame#tutorialCard { ... }
QLabel#tutorialTitle { ... }
QLabel#tutorialBody { ... }
QLabel#tutorialSafety { ... }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/test_tutorial_overlay.py -q
```

Expected: PASS.

## Task 3: Main Window Entry

**Files:**
- Modify: `consoleplat/ui/main_window.py`
- Modify: `tests/test_main_window_ui.py`

- [ ] **Step 1: Write the failing tests**

Append tests:

```python
def test_main_window_has_tutorial_button(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    assert window.tutorial_button.objectName() == "tutorialButton"
    assert window.tutorial_button.text() == "?"

    window.close()


def test_main_window_tutorial_button_opens_overlay(monkeypatch):
    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    window.activate_page("monitor")
    window.tutorial_button.click()

    assert window.tutorial_overlay is not None
    assert window.tutorial_overlay.isVisible()
    assert window.tutorial_overlay.title_label.text().startswith("1/")

    window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_main_window_ui.py::test_main_window_has_tutorial_button tests/test_main_window_ui.py::test_main_window_tutorial_button_opens_overlay -q
```

Expected: FAIL because `tutorial_button` does not exist.

- [ ] **Step 3: Implement the entry**

In `main_window.py`:

- import `get_tutorial_steps` and `TutorialOverlay`;
- create `self.tutorial_button`;
- place it in the existing header beside `status_pill`;
- add `_open_current_page_tutorial`;
- close any existing overlay before opening a new one;
- close the overlay when page changes.

Required behavior:

```python
def _open_current_page_tutorial(self) -> None:
    page = self.pages.get(self.state.active_page)
    if page is None:
        return
    steps = get_tutorial_steps(self.state.active_page)
    self._close_tutorial_overlay()
    self.tutorial_overlay = TutorialOverlay(page, steps)
    self.tutorial_overlay.start()
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/test_main_window_ui.py::test_main_window_has_tutorial_button tests/test_main_window_ui.py::test_main_window_tutorial_button_opens_overlay -q
```

Expected: PASS.

## Task 4: Page Anchors and Tutorial Data Coverage

**Files:**
- Modify page files listed in File Structure.
- Modify: `tests/test_tutorial_data.py`

- [ ] **Step 1: Write failing anchor tests**

Add to `tests/test_tutorial_data.py`:

```python
from PyQt5.QtWidgets import QApplication

from consoleplat.ui.main_window import MainWindow


def test_tutorial_targets_exist_on_loaded_pages(monkeypatch):
    class FakeSettingsStore:
        def load(self):
            from consoleplat.config import AppSettings

            return AppSettings(startup_width=1280, startup_height=820)

    monkeypatch.setattr("consoleplat.ui.main_window.SettingsStore", lambda: FakeSettingsStore())
    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    for page_key, steps in TUTORIALS.items():
        window.activate_page(page_key)
        page = window.pages[page_key]
        for step in steps:
            assert page.findChild(QWidget, step.target) is not None, f"{page_key}:{step.target}"

    window.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_tutorial_data.py::test_tutorial_targets_exist_on_loaded_pages -q
```

Expected: FAIL for missing anchors.

- [ ] **Step 3: Add objectName anchors**

Add stable names to existing widgets or lightweight container panels:

- `monitor_page.py`: `monitorMetricsAnchor`, `monitorControlsAnchor`, `monitorOrdersAnchor`.
- `product_publish_page.py`: `publishHeaderAnchor`, `publishFormAnchor`, `publishActionsAnchor`.
- `local_image_page.py`: `localImageConfigAnchor`, `localImageStatusAnchor`.
- `ai_edit_page.py`: `aiEditImagesAnchor`, `aiEditRequestAnchor`, `aiEditQueueAnchor`.
- `putaway_page.py`: `putawayEmbedAnchor`, `putawayStatusAnchor`.
- `apply_goods_page.py`: `applyEmbedAnchor`, `applySafetyAnchor`.
- `settings_page.py`: `settingsPathsAnchor`, `settingsBrowserAnchor`, `settingsSecurityAnchor`.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
python -m pytest tests/test_tutorial_data.py::test_tutorial_targets_exist_on_loaded_pages -q
```

Expected: PASS.

## Task 5: Screenshot Capture and Final Verification

**Files:**
- Create: `scripts/capture_tutorial_screenshots.py`
- Create directory: `assets/images/tutorial/`
- Generate PNG files:
  - `assets/images/tutorial/monitor.png`
  - `assets/images/tutorial/publish.png`
  - `assets/images/tutorial/local_image.png`
  - `assets/images/tutorial/ai_edit.png`
  - `assets/images/tutorial/putaway.png`
  - `assets/images/tutorial/apply.png`
  - `assets/images/tutorial/settings.png`

- [ ] **Step 1: Create screenshot script**

Create `scripts/capture_tutorial_screenshots.py`:

```python
from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication

from consoleplat.models import DEFAULT_NAV_ITEMS
from consoleplat.ui.main_window import MainWindow


def main() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.resize(1280, 820)
    output_dir = Path("assets/images/tutorial")
    output_dir.mkdir(parents=True, exist_ok=True)

    for item in DEFAULT_NAV_ITEMS:
        window.activate_page(item.key)
        app.processEvents()
        pixmap = window.grab()
        pixmap.save(str(output_dir / f"{item.key}.png"), "PNG")

    window.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run screenshot script**

Run:

```powershell
python scripts/capture_tutorial_screenshots.py
```

Expected: seven PNG files are created under `assets/images/tutorial/`.

- [ ] **Step 3: Run focused tests**

Run:

```powershell
python -m pytest tests/test_tutorial_data.py tests/test_tutorial_overlay.py tests/test_main_window_ui.py -q
```

Expected: PASS.

- [ ] **Step 4: Run compile verification**

Run:

```powershell
python -m py_compile main.py consoleplat\ui\main_window.py consoleplat\ui\tutorial_data.py consoleplat\ui\tutorial_overlay.py consoleplat\ui\theme.py
```

Expected: no output and exit code 0.

- [ ] **Step 5: Commit and push**

Stage only files changed for this feature:

```powershell
git add consoleplat/ui/tutorial_data.py consoleplat/ui/tutorial_overlay.py consoleplat/ui/main_window.py consoleplat/ui/theme.py consoleplat/ui/monitor_page.py consoleplat/ui/product_publish_page.py consoleplat/ui/local_image_page.py consoleplat/ui/ai_edit_page.py consoleplat/ui/putaway_page.py consoleplat/ui/apply_goods_page.py consoleplat/ui/settings_page.py tests/test_tutorial_data.py tests/test_tutorial_overlay.py tests/test_main_window_ui.py scripts/capture_tutorial_screenshots.py assets/images/tutorial
git commit -m "feat: add page help tour"
git push origin HEAD
```

Expected: local commit succeeds; push succeeds or reports a clear remote/permission error.

## Self-Review

- Spec coverage: The plan covers the right-top `?` entry, highlit overlay, structured tutorial data, page anchors, screenshot assets, safe non-submitting copy, and tests.
- Placeholder scan: No task uses `TBD`, `TODO`, “similar to”, or an unspecified “handle edge cases” instruction.
- Type consistency: The public types are `TutorialStep`, `TUTORIALS`, `get_tutorial_steps`, and `TutorialOverlay`; the same names are used in tests and implementation steps.
