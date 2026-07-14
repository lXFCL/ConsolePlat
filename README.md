# ConsolePlat

Windows PyQt desktop shell for integrating the existing `SendGoods`, `PosAiImg`, `PutawayAiRobot`, and `ApplyGoods` projects.

Current status: UI framework preview only. The pages, navigation, hero banner, task cards, and adapter placeholders are in place; real automation actions are not wired yet.

Version rule: when a software update changes more than 200 lines of code, increase the minor version by `0.1`; otherwise increase the patch version by `0.01`.

## Run

```powershell
python main.py
```

## Portable Release

GitHub Release `v1.7.0` uses a portable source package:

```text
ConsolePlat-v1.7.0-portable.zip
ConsolePlat-prints-v1.7.0.zip
```

After extracting the portable package, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_portable_env.ps1
.\启动ConsolePlat.bat
```

The portable package keeps project defaults inside the extracted folder:

- external modules: `modules/SendGoods`, `modules/PosAiImg`, `modules/PutawayAiRobot`, `modules/ApplyGoods`
- runtime outputs: `runtime/outputs`, `runtime/data`, `runtime/downloads`
- print gallery placeholder: `resources/prints`

The main package does not include ComfyUI, PosAiImg models, browser profiles, account settings, logs, historical outputs, Putaway business data, or generated image caches. Download `ConsolePlat-prints-v1.7.0.zip` separately and extract it into `resources/prints` when local print-gallery matching is needed. Configure or download PosAiImg ComfyUI/models from `设置 -> 生图 / 改图 -> PosAiImg 资源`.

## Windows EXE

Build the self-contained desktop runtime from the existing `flask` conda environment:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1
```

Then launch `dist\ConsolePlat\ConsolePlat.exe`. The adjacent `_internal` directory is the bundled Python runtime and must remain beside the EXE. The build deliberately excludes browser profiles, credentials, logs, historical outputs, Putaway business data, print galleries, ComfyUI, and AI models.

For the real Temu monitor source, the current machine has Playwright available in the `flask` conda environment:

```powershell
conda run -n flask python main.py
```

If dependencies are missing:

```powershell
python -m pip install -r requirements.txt
```

## Verify

```powershell
python -m pytest tests/test_shell_model.py -q
python -m py_compile main.py consoleplat\__init__.py consoleplat\models.py consoleplat\paths.py consoleplat\app.py consoleplat\ui\main_window.py consoleplat\ui\components.py consoleplat\ui\theme.py consoleplat\adapters\base.py
```

## Temu Monitor

Open `设置`, save the `YUHOOBO` account, Chrome CDP address, and refresh interval. Then return to `监控` and click `立即刷新` or `开始监控`.

The monitor opens:

```text
https://agentseller.temu.com/stock/fully-mgt/order-manage-urgency
```

It reads the page DOM and extracts tab counts plus visible urgent stock rows. If login requires SMS, slider, or other manual verification, finish that in the opened browser and refresh again.

When the page is in a login or authorization state, ConsolePlat keeps the browser open and pauses the monitor instead of closing and reopening it. Finish login in the browser, then click `立即刷新`.

Optional read-only Chrome helper extension:

```text
chrome-extension/
```

Load it as an unpacked extension only when debugging page DOM. It exposes `window.__CONSOLEPLAT_MONITOR__` for inspection and does not submit or modify page data.

## Layout

- `main.py`: desktop entry point.
- `consoleplat/models.py`: navigation and task-card shell data.
- `consoleplat/ui/main_window.py`: main PyQt layout.
- `consoleplat/ui/components.py`: hero banner, task cards, reusable panels.
- `consoleplat/adapters/base.py`: placeholders for source project integration.
- `assets/images/dashboard_hero.png`: generated original UI banner asset.
- `tests/test_shell_model.py`: minimal shell model tests.

## GitHub

Target repository provided by user:

```text
https://github.com/lXFCL/ConsolePlat.git
```

At the time this framework was created, the local folder was not a git repository and `git ls-remote` returned no branch refs. Initialize or connect the repository before pushing.
