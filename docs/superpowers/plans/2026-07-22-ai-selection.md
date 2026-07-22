# AI 选品 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a manual, read-only Temu selection workflow that searches configured keywords through the user's CDP browser, ranks visible sales results, downloads one search-card image per candidate, and stores reviewable batches in the configured program data directory.

**Architecture:** Keep parsing, ranking, persistence, export, and image download in a pure service. Run Playwright CDP reads in a JSON CLI subprocess so the PyQt UI stays responsive. Extend the existing settings store and lazy navigation.

**Tech Stack:** Python, PyQt5, Playwright sync API, openpyxl, urllib, pytest.

---

## File Structure

- Create `consoleplat/services/ai_selection_service.py`: candidate model, sales parsing, ranking, output and image download.
- Create `consoleplat/services/ai_selection_fetch_cli.py`: read-only CDP collector and JSON CLI entry point.
- Create `consoleplat/ui/ai_selection_page.py`: process-backed page, logs, results, history and local actions.
- Create `tests/test_ai_selection_service.py`, `tests/test_ai_selection_fetch_cli.py`, `tests/test_ai_selection_page_ui.py`.
- Modify `consoleplat/config.py`, `consoleplat/ui/settings_page.py`, `consoleplat/models.py`, `consoleplat/ui/main_window.py`, `consoleplat/runtime.py`, and relevant existing tests.

### Task 1: Service records, sales parser, and ranking

**Files:**
- Create: `tests/test_ai_selection_service.py`
- Create: `consoleplat/services/ai_selection_service.py`

- [ ] **Step 1: Write the failing tests**

```python
from consoleplat.services.ai_selection_service import SelectionCandidate, parse_sales_count, rank_candidates


def test_parse_sales_count_supports_k_wan_and_plain_counts():
    assert parse_sales_count("1.2K sold") == 1200
    assert parse_sales_count("已售 3.4万") == 34000
    assert parse_sales_count("销量 98") == 98
    assert parse_sales_count("无销量") is None


def test_rank_candidates_deduplicates_canonical_links_and_keeps_top_30():
    rows = [SelectionCandidate(f"商品 {i}", f"已售 {i}", i, "$9", f"https://www.temu.com/goods-{i}.html?ref=x", "", "黑白T恤") for i in range(35)]
    rows.append(SelectionCandidate("重复", "已售 999", 999, "$8", "https://www.temu.com/goods-34.html", "", "黑白T恤"))
    result = rank_candidates(rows, limit=30)
    assert len(result) == 30
    assert result[0].sales_count == 999
    assert result[0].rank == 1
    assert result[-1].rank == 30
```

- [ ] **Step 2: Verify the test is red**

Run: `python -m pytest tests/test_ai_selection_service.py -q`

Expected: import error for `consoleplat.services.ai_selection_service`.

- [ ] **Step 3: Implement the minimal service contract**

```python
@dataclass
class SelectionCandidate:
    title: str
    sales_text: str
    sales_count: int | None
    price: str
    product_url: str
    image_url: str
    keyword: str
    rank: int = 0
    status: str = "待下载"
    error: str = ""
    local_image_path: str = ""


def parse_sales_count(text: str) -> int | None: ...
def canonical_product_url(url: str) -> str: ...
def rank_candidates(candidates: Iterable[SelectionCandidate], limit: int = 30) -> list[SelectionCandidate]: ...
```

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_ai_selection_service.py -q`

Expected: `2 passed`.

- [ ] **Step 5: Commit**

Run: `git add tests/test_ai_selection_service.py consoleplat/services/ai_selection_service.py; git commit -m "feat: add AI selection ranking service"`

### Task 2: Batch persistence, CSV/XLSX export, and image failure isolation

**Files:**
- Modify: `tests/test_ai_selection_service.py`
- Modify: `consoleplat/services/ai_selection_service.py`

- [ ] **Step 1: Add the failing output tests**

```python
def test_create_batch_requires_configured_program_data_dir():
    with pytest.raises(ValueError, match="程序数据目录"):
        create_batch("", ["黑白T恤"])


def test_export_batch_writes_history_under_program_data_dir(tmp_path):
    batch = create_batch(tmp_path, ["黑白T恤"], created_at="2026-07-22T15:30:00")
    result = export_batch(batch, [])
    assert result.csv_path.exists()
    assert result.xlsx_path.exists()
    assert result.failure_path.exists()
    assert result.batch_dir.parent == tmp_path / "AI选品"
    assert load_batches(tmp_path)[0].batch_dir == result.batch_dir
```

- [ ] **Step 2: Verify the output test is red**

Run: `python -m pytest tests/test_ai_selection_service.py -q`

Expected: missing batch functions.

- [ ] **Step 3: Implement batch output**

```python
RESULT_HEADERS = ("排名", "商品标题", "销量", "销量数值", "价格", "商品链接", "搜索关键词", "采集时间", "主图链接", "本地主图", "状态", "失败原因")


def create_batch(program_data_dir: str | Path, keywords: list[str], created_at: str | None = None) -> SelectionBatch: ...
def export_batch(batch: SelectionBatch, candidates: list[SelectionCandidate], failures: list[str] | None = None) -> ExportResult: ...
def load_batches(program_data_dir: str | Path) -> list[SelectionBatch]: ...
```

The batch root must be `<program_data_dir>/AI选品/<batch-name>`, never `%APPDATA%` or `C:` fallback.

- [ ] **Step 4: Add the failing per-image test and implement isolation**

```python
def test_download_images_keeps_good_candidate_when_another_image_fails(tmp_path, monkeypatch):
    def fake_download(url, target, timeout=20):
        if url.endswith("bad.jpg"):
            raise OSError("network")
        Path(target).write_bytes(b"image")
    monkeypatch.setattr("consoleplat.services.ai_selection_service.download_image", fake_download)
    good = SelectionCandidate("good", "已售 2", 2, "$9", "https://www.temu.com/good.html", "https://img/good.jpg", "黑白T恤")
    bad = SelectionCandidate("bad", "已售 1", 1, "$9", "https://www.temu.com/bad.html", "https://img/bad.jpg", "黑白T恤")
    download_candidate_images([good, bad], tmp_path)
    assert Path(good.local_image_path).exists()
    assert bad.status == "主图下载失败"
    assert "network" in bad.error
```

- [ ] **Step 5: Verify green and commit**

Run: `python -m pytest tests/test_ai_selection_service.py -q; git add tests/test_ai_selection_service.py consoleplat/services/ai_selection_service.py; git commit -m "feat: persist AI selection batches"`

Expected: all service tests pass before commit.

### Task 3: Read-only collector CLI

**Files:**
- Create: `tests/test_ai_selection_fetch_cli.py`
- Create: `consoleplat/services/ai_selection_fetch_cli.py`
- Modify: `consoleplat/runtime.py`

- [ ] **Step 1: Write the failing parser and empty-page policy tests**

```python
from consoleplat.services.ai_selection_fetch_cli import parse_search_cards, should_stop_after_page


def test_parse_search_cards_marks_missing_sales_as_failures():
    cards, failures = parse_search_cards([
        {"title": "A", "sales_text": "已售 1.2K", "price": "$9", "href": "/goods-a.html", "image_url": "https://img/a.jpg"},
        {"title": "B", "sales_text": "", "price": "$8", "href": "/goods-b.html", "image_url": "https://img/b.jpg"},
    ], keyword="黑白T恤")
    assert len(cards) == 1
    assert cards[0].sales_count == 1200
    assert failures == ["商品 B 未读取到销量"]


def test_should_stop_only_after_two_empty_pages():
    assert should_stop_after_page(1) is False
    assert should_stop_after_page(2) is True
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_ai_selection_fetch_cli.py -q`

Expected: module import failure.

- [ ] **Step 3: Implement the restricted collector**

```python
TEMU_HOME_URL = "https://www.temu.com/us-zh-Hans"
MAX_PAGES = 3

def parse_search_cards(raw_cards: list[dict], keyword: str) -> tuple[list[SelectionCandidate], list[str]]: ...
def should_stop_after_page(consecutive_empty_pages: int) -> bool: ...
def collect_selection_payload(cdp_endpoint: str, keywords: list[str], max_pages: int = MAX_PAGES) -> dict: ...
```

Connect via `chromium.connect_over_cdp`, navigate to the Temu homepage, fill a visible search field, press Enter, read visible cards, and use only a visible next-page control. Return JSON `{ok, kind, message, candidates, failures, logs}`. Detect login/captcha text and return a paused result. Do not call purchase, cart, favorite, account, upload, or submit endpoints.

- [ ] **Step 4: Register the runtime command and verify green**

Add the `ai-selection-fetch` command following existing `cli_command` conventions.

Run: `python -m pytest tests/test_ai_selection_fetch_cli.py -q; python -m py_compile consoleplat/services/ai_selection_fetch_cli.py consoleplat/runtime.py`

Expected: tests pass; compiler exits 0.

- [ ] **Step 5: Commit**

Run: `git add tests/test_ai_selection_fetch_cli.py consoleplat/services/ai_selection_fetch_cli.py consoleplat/runtime.py; git commit -m "feat: add read-only Temu selection collector"`

### Task 4: Configuration, navigation, and UI shell

**Files:**
- Modify: `consoleplat/config.py`
- Modify: `consoleplat/ui/settings_page.py`
- Modify: `consoleplat/models.py`
- Modify: `consoleplat/ui/main_window.py`
- Create: `consoleplat/ui/ai_selection_page.py`
- Create: `tests/test_ai_selection_page_ui.py`
- Modify: `tests/test_main_window_ui.py`

- [ ] **Step 1: Write the failing page/config tests**

```python
def test_ai_selection_default_keyword():
    assert AppSettings().ai_selection_keywords == ["黑白T恤"]


def test_ai_selection_page_blocks_run_without_program_data_dir(qtbot):
    page = AISelectionPage(settings=AppSettings(program_data_dir=""))
    qtbot.addWidget(page)
    page.start_selection()
    assert "程序数据目录" in page.status_label.text()


def test_main_window_loads_ai_selection_page():
    window = MainWindow()
    window.activate_page("ai_selection")
    assert window.findChildren(AISelectionPage)
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_ai_selection_page_ui.py tests/test_main_window_ui.py -q`

Expected: missing field, module, and navigation key failures.

- [ ] **Step 3: Implement configuration and controls**

Add `ai_selection_keywords: list[str] = field(default_factory=lambda: ["黑白T恤"])` to `AppSettings`. Load/save it as a trimmed nonempty JSON list with the default when empty. Add an `AI 选品关键词` multiline field in settings, one keyword per line. Reuse the existing program-data directory picker; do not create another output-root setting.

- [ ] **Step 4: Implement page shell and lazy route**

Add `NavItem("ai_selection", "选品", "⌕", "按销量采集 Temu 候选商品")`, title `AI 选品`, and `AISelectionPage()` creation. The page must own `process`, keyword editor, start/stop buttons, status label, output label, logs, batch combo and results table. Its start handler validates only local settings before launching the CLI subprocess.

- [ ] **Step 5: Verify green and commit**

Run: `python -m pytest tests/test_ai_selection_page_ui.py tests/test_main_window_ui.py -q; git add consoleplat/config.py consoleplat/ui/settings_page.py consoleplat/models.py consoleplat/ui/main_window.py consoleplat/ui/ai_selection_page.py tests/test_ai_selection_page_ui.py tests/test_main_window_ui.py; git commit -m "feat: add AI selection workspace"`

Expected: all selected UI tests pass before commit.

### Task 5: UI result persistence and history

**Files:**
- Modify: `consoleplat/ui/ai_selection_page.py`
- Modify: `tests/test_ai_selection_page_ui.py`

- [ ] **Step 1: Write the failing result-handler tests**

```python
def test_page_exports_success_payload_and_loads_latest_batch(qtbot, tmp_path):
    page = AISelectionPage(settings=AppSettings(program_data_dir=str(tmp_path)))
    qtbot.addWidget(page)
    page.handle_fetch_payload({"ok": True, "candidates": [{"title": "A", "sales_text": "已售 99", "sales_count": 99, "price": "$9", "product_url": "https://www.temu.com/goods-a.html", "image_url": "", "keyword": "黑白T恤"}], "failures": []})
    assert page.results_table.rowCount() == 1
    assert "AI选品" in page.output_label.text()
    assert page.batch_combo.count() == 1


def test_page_pauses_on_login_payload(qtbot, tmp_path):
    page = AISelectionPage(settings=AppSettings(program_data_dir=str(tmp_path)))
    qtbot.addWidget(page)
    page.handle_fetch_payload({"ok": False, "kind": "login", "message": "请完成登录"})
    assert "请完成登录" in page.status_label.text()
    assert page.start_button.isEnabled()
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_ai_selection_page_ui.py -q`

Expected: missing `handle_fetch_payload` or missing batch widgets.

- [ ] **Step 3: Implement JSON handling and safe actions**

```python
def handle_fetch_payload(self, payload: dict) -> None:
    if not payload.get("ok"):
        self._show_pause_or_error(payload)
        return
    batch = create_batch(self.settings.program_data_dir, self.current_keywords())
    candidates = rank_candidates(candidates_from_payload(payload), limit=30)
    download_candidate_images(candidates, batch.image_dir)
    result = export_batch(batch, candidates, payload.get("failures") or [])
    self._load_batch(result.batch_dir)
```

Use `QDesktopServices.openUrl` only after an explicit user click on a selected URL or local path. Preserve each fetch failure in the batch failure CSV. On login/captcha do not create a partial batch and leave start enabled.

- [ ] **Step 4: Verify green and commit**

Run: `python -m pytest tests/test_ai_selection_service.py tests/test_ai_selection_fetch_cli.py tests/test_ai_selection_page_ui.py -q; python -m py_compile consoleplat/services/ai_selection_service.py consoleplat/services/ai_selection_fetch_cli.py consoleplat/ui/ai_selection_page.py; git add consoleplat/ui/ai_selection_page.py tests/test_ai_selection_page_ui.py; git commit -m "feat: export AI selection results"`

Expected: feature tests pass and compilation exits 0 before commit.

### Task 6: Full verification and backup push

**Files:**
- Modify only when verification exposes a defect in the feature files.

- [ ] **Step 1: Run the focused full suite**

Run: `python -m pytest tests/test_ai_selection_service.py tests/test_ai_selection_fetch_cli.py tests/test_ai_selection_page_ui.py tests/test_main_window_ui.py tests/test_settings_store.py tests/test_settings_page_ui.py -q`

Expected: zero failures.

- [ ] **Step 2: Verify actual window creation offscreen**

Run: `$env:QT_QPA_PLATFORM='offscreen'; python -c "from PyQt5.QtWidgets import QApplication; from consoleplat.ui.main_window import MainWindow; app=QApplication([]); window=MainWindow(); window.activate_page('ai_selection'); assert window.pages['ai_selection'].start_button.isVisible(); window.close()"`

Expected: exit code 0 without visiting Temu.

- [ ] **Step 3: Review scope before final versioning**

Run: `git diff --check; git status --short; git log -5 --oneline`

Expected: no whitespace errors; all known pre-existing untracked files remain unmodified and unstaged.

- [ ] **Step 4: Push a backup branch after verified commits**

Run: `git push origin HEAD:codex/2026-07-22-ai-selection`

Expected: remote reports the named backup branch. On failure, preserve local commits and report the exact remote error.

- [ ] **Step 5: Optional one-page live read validation**

Only when Chrome is already running at the configured CDP endpoint and the user has an active Temu session, run: `python -m consoleplat.services.ai_selection_fetch_cli --keywords 黑白T恤 --max-pages 1`

Expected: a structured JSON read-only result. For `login` or `captcha`, stop and report the paused state; do not bypass verification.
