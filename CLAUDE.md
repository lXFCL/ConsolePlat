# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Language

始终用简体中文回复。代码注释、提交信息、计划文档和技术说明也用中文。代码标识符(变量名、函数名等)保持原有命名习惯,不强制翻译。

## What this is

ConsolePlat is a Windows PyQt5 desktop shell that integrates four existing Temu seller automation projects (`SendGoods`, `PosAiImg`, `PutawayAiRobot`, `ApplyGoods`) under one UI. It is an integration layer, not a rewrite — the four source projects must stay independently runnable. See `AGENTS.md` for the full domain spec, business flow, data/output conventions per source project, and the automation safety boundaries (which actions may auto-run vs. require explicit user authorization). Read `AGENTS.md` before touching anything that triggers real website actions (submit, upload, publish, modify stock/address, ship).

## Commands

```bash
# Run the desktop app
python main.py
# Real Temu monitoring needs Playwright, available on this machine in the `flask` conda env:
conda run -n flask python main.py    # `flask` is only the env name, not a web framework

# Install deps
python -m pip install -r requirements.txt

# Tests (pytest; no config file, defaults to tests/)
python -m pytest tests/ -q
python -m pytest tests/test_shell_model.py -q          # single file
python -m pytest tests/test_main_window_ui.py::test_main_window_uses_saved_startup_size -q

# Static check used in verification
python -m py_compile main.py consoleplat/app.py consoleplat/ui/main_window.py   # etc.
```

UI tests run headless against real PyQt widgets — they create a `QApplication`, monkeypatch `SettingsStore`, and `findChildren`/`activate_page` to assert. They do not require a display server but do require PyQt5 installed.

## Architecture

**Shell layout.** `main.py` → `consoleplat/app.py:run()` → `consoleplat/ui/main_window.py:MainWindow`. The window is a left sidebar (`NavButton`s) + a `QStackedWidget`. Navigation entries live in `consoleplat/models.py:DEFAULT_NAV_ITEMS`; each `key` maps to a page in `MainWindow._create_page`. To add a page: add a `NavItem`, build a `QWidget` page under `consoleplat/ui/`, and wire the key in `_create_page`.

**Heavy work runs out-of-process, not on the UI thread.** Long tasks (Playwright page reads, image generation, exports) are implemented as CLI worker modules `consoleplat/services/*_cli.py` with a `main()` that prints a single JSON object to stdout (`{"ok": true, ...}` / `{"ok": false, "kind": "login|error", "message": ...}`). UI pages spawn them with `QProcess(sys.executable, ["-m", "consoleplat.services.<name>_cli"])` and parse stdout in the `finished` handler (see `consoleplat/ui/monitor_page.py:refresh_snapshot`). Some pages instead use a `QObject` worker moved onto a `QThread` (see `AIEditBackgroundWorker` in `consoleplat/ui/ai_edit_page.py`). Never block the UI thread with Playwright or subprocess waits.

**Adapters embed external projects.** Each source project gets `consoleplat/adapters/<name>_adapter.py`. The standard "embed" pattern (documented in the `consoleplat-embed-pattern` memory): the source project exposes a factory `create_<name>_widget(parent=None)` returning a `QWidget`; the adapter dynamically loads the source entry file via `importlib.util.spec_from_file_location` after `sys.path.insert(0, project_dir)`, then calls the factory. The page (`consoleplat/ui/<name>_page.py`) calls `adapter.build_embedded_widget(parent)` and falls back to an error label on failure. `PutawayAdapter` is the reference implementation. Source project dirs are user-configurable via settings, not hardcoded in the page.

**Config and secrets.** `consoleplat/config.py` holds the `AppSettings` dataclass and `SettingsStore`, persisted as JSON at `%APPDATA%/ConsolePlat/settings.json`. Secrets (account passwords, AI API keys) are encrypted with Windows DPAPI via `encrypt_secret`/`decrypt_secret` and stored under `*_dpapi` keys — never write plaintext credentials to the JSON, logs, or the repo. `SettingsStore.load` handles legacy single-provider configs migrating to the `ai_providers` list. `consoleplat/paths.py:resource_path` resolves bundled assets and is PyInstaller-aware (`sys._MEIPASS`).

**Temu monitor.** `consoleplat/services/temu_monitor_source.py` is the most complex module: it connects to Chrome over CDP (default `http://127.0.0.1:9222`, launching Chrome if needed), navigates the urgency-stock page, handles login/authorization/shop-switch state machines, sets page size to 100, and extracts rows via injected JS (`EXTRACT_MONITOR_SCRIPT`). It is read-only and raises `LoginRequiredError` rather than closing the user's browser when manual verification is needed. `monitor_service.py` defines the `MonitorSnapshot` data model plus `DemoMonitorSource`/`EmptyMonitorSource` fallbacks. The optional `chrome-extension/` is a read-only DOM debug helper exposing `window.__CONSOLEPLAT_MONITOR__`.

## Conventions

- **Version** lives in `consoleplat/__init__.py:APP_VERSION`. Rule (from README): a change of >200 lines bumps the minor (`+0.1`); otherwise bump the patch (`+0.01`).
- **Encoding:** code, UI text, and data are heavily Chinese. Always read/write files as UTF-8; a garbled PowerShell terminal does not mean the source file is corrupt.
- **Git** (from `AGENTS.md`): after a verified change, commit locally then push to `origin`. If `main` can't be pushed, push to a backup branch prefixed `codex/` with date/topic. Report the commit hash, push target, and verification result each round. Do not commit unfinished/unverified state. Recovery/backup dirs (`_recovered_*`, `_rebuild_v110`, `.browser-profile`, `data/`, `settings.json`) are gitignored — keep them so.
- **Automation safety:** monitoring, reading, and generating local files may auto-run. Anything that changes real website state requires explicit user authorization for the round, an enabled setting that shows the action scope, or test mode. Prefer dry-run / small-sample (1 row, current page) before full batches.

## Agent skills

### Issue tracker

本仓库使用 GitHub Issues 跟踪任务。详见 `docs/agents/issue-tracker.md`。

### Triage labels

分类流程使用五个默认标签：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。详见 `docs/agents/triage-labels.md`。

### Domain docs

本仓库采用 single-context 领域文档布局。详见 `docs/agents/domain.md`。
