# AI Edit Preview Splitter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current text-only manual split dialog with a preview-based splitter for AI edit transparent collage rounds that opens with default 5x5 guides, lets the user drag horizontal and vertical lines to fine-tune them, and saves/re-splits the current transparent collage image.

**Architecture:** Keep the existing `SplitProfile` data model and `split_collage_image_with_guides(...)` flow unchanged. Upgrade the dialog layer in `consoleplat/ui/ai_edit_page.py` by adding a dedicated preview canvas widget that renders the transparent collage image with draggable guide overlays, then save the updated `x_guides` and `y_guides` back through the existing `AIEditPage.edit_split_profile(...)` entrypoint.

**Tech Stack:** Python, PyQt5, Pillow, pytest

---

## File Structure

- Modify: `consoleplat/ui/ai_edit_page.py`
  - Extend the existing manual split dialog into a preview-based editor.
  - Add a focused preview canvas widget for image rendering, guide drawing, and mouse interaction.
  - Reuse existing `SplitProfileEditorDialog`, `AIEditTaskDetailDialog`, and `AIEditPage.edit_split_profile(...)` flow instead of introducing a new module.
- Modify: `tests/test_ai_edit_page_recovery.py`
  - Add dialog/widget-level regression tests for default 5x5 guide generation, guide persistence, and current-round source routing.
- Verify only: `consoleplat/services/ai_image_edit_cli.py`
  - No new behavior planned here in this round; existing guide-based splitter remains the execution target and is re-verified by tests.

### Task 1: Preview Dialog Defaults

**Files:**
- Modify: `consoleplat/ui/ai_edit_page.py`
- Test: `tests/test_ai_edit_page_recovery.py`

- [ ] **Step 1: Write the failing test for default 5x5 guides**

```python
def test_split_profile_editor_dialog_builds_default_5x5_guides_from_image_size(tmp_path):
    app = QApplication.instance() or QApplication([])

    image_path = tmp_path / "edited_round_01_transparent.png"
    Image.new("RGBA", (1000, 1000), (0, 0, 0, 0)).save(image_path)
    record = AIEditTaskRecord(
        task_id="20260623170000",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体", split_collage=True, split_count=25),
        split_profile={},
    )

    from consoleplat.ui.ai_edit_page import SplitProfileEditorDialog

    dialog = SplitProfileEditorDialog(record, str(image_path))

    assert dialog.parsed_guides() == ([200, 400, 600, 800], [200, 400, 600, 800])

    dialog.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_split_profile_editor_dialog_builds_default_5x5_guides_from_image_size -q`

Expected: FAIL because the current dialog only echoes stored text values and does not derive default 5x5 guides from the image size.

- [ ] **Step 3: Implement default guide derivation in the dialog**

Implementation shape:

```python
class SplitProfileEditorDialog(QDialog):
    def __init__(self, record: AIEditTaskRecord, source_path: str, parent: QWidget | None = None) -> None:
        ...
        self._image_size = self._load_image_size(source_path)
        default_x_guides, default_y_guides = self._default_guides()
        x_guides = list(record.split_profile.get("x_guides") or default_x_guides)
        y_guides = list(record.split_profile.get("y_guides") or default_y_guides)
        ...

    def _load_image_size(self, source_path: str) -> tuple[int, int]:
        with Image.open(source_path) as image:
            return image.size

    def _default_guides(self) -> tuple[list[int], list[int]]:
        width, height = self._image_size
        columns = rows = 5
        x_guides = [round(width * index / columns) for index in range(1, columns)]
        y_guides = [round(height * index / rows) for index in range(1, rows)]
        return x_guides, y_guides
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_split_profile_editor_dialog_builds_default_5x5_guides_from_image_size -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add consoleplat/ui/ai_edit_page.py tests/test_ai_edit_page_recovery.py
git commit -m "feat: add default 5x5 preview split guides"
```

### Task 2: Preview Canvas with Draggable Guides

**Files:**
- Modify: `consoleplat/ui/ai_edit_page.py`
- Test: `tests/test_ai_edit_page_recovery.py`

- [ ] **Step 1: Write the failing test for resetting guides to default**

```python
def test_split_profile_editor_dialog_can_reset_guides_to_default_grid(tmp_path):
    app = QApplication.instance() or QApplication([])

    image_path = tmp_path / "edited_round_01_transparent.png"
    Image.new("RGBA", (500, 1000), (0, 0, 0, 0)).save(image_path)
    record = AIEditTaskRecord(
        task_id="20260623170100",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体", split_collage=True, split_count=25),
        split_profile={"x_guides": [111], "y_guides": [222]},
    )

    from consoleplat.ui.ai_edit_page import SplitProfileEditorDialog

    dialog = SplitProfileEditorDialog(record, str(image_path))
    dialog.reset_guides()

    assert dialog.parsed_guides() == ([100, 200, 300, 400], [200, 400, 600, 800])

    dialog.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_split_profile_editor_dialog_can_reset_guides_to_default_grid -q`

Expected: FAIL because the current dialog has no reset behavior.

- [ ] **Step 3: Add a dedicated preview canvas widget and reset behavior**

Implementation shape:

```python
class SplitGuidePreviewWidget(QWidget):
    guidesChanged = pyqtSignal(list, list)

    def __init__(self, source_path: str, x_guides: list[int], y_guides: list[int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pixmap = QPixmap(source_path)
        self._x_guides = sorted(set(int(value) for value in x_guides))
        self._y_guides = sorted(set(int(value) for value in y_guides))
        self._selected_axis: str | None = None
        self._selected_index = -1
        self._dragging = False
        self.setMinimumSize(640, 640)

    def set_guides(self, x_guides: list[int], y_guides: list[int]) -> None:
        self._x_guides = sorted(set(int(value) for value in x_guides))
        self._y_guides = sorted(set(int(value) for value in y_guides))
        self.guidesChanged.emit(list(self._x_guides), list(self._y_guides))
        self.update()
```

Dialog integration shape:

```python
class SplitProfileEditorDialog(QDialog):
    def __init__(...):
        ...
        self.preview = SplitGuidePreviewWidget(source_path, x_guides, y_guides, self)
        self.preview.guidesChanged.connect(self._sync_guide_fields)
        ...
        self.reset_button = QPushButton("恢复默认 5x5")
        self.reset_button.clicked.connect(self.reset_guides)

    def reset_guides(self) -> None:
        x_guides, y_guides = self._default_guides()
        self.preview.set_guides(x_guides, y_guides)
        self._sync_guide_fields(x_guides, y_guides)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_split_profile_editor_dialog_can_reset_guides_to_default_grid -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add consoleplat/ui/ai_edit_page.py tests/test_ai_edit_page_recovery.py
git commit -m "feat: add preview split guide canvas"
```

### Task 3: Drag-to-Adjust Interaction

**Files:**
- Modify: `consoleplat/ui/ai_edit_page.py`
- Test: `tests/test_ai_edit_page_recovery.py`

- [ ] **Step 1: Write the failing test for guide list synchronization**

```python
def test_split_profile_editor_dialog_updates_text_fields_when_guides_change(tmp_path):
    app = QApplication.instance() or QApplication([])

    image_path = tmp_path / "edited_round_01_transparent.png"
    Image.new("RGBA", (1000, 1000), (0, 0, 0, 0)).save(image_path)
    record = AIEditTaskRecord(
        task_id="20260623170200",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体", split_collage=True, split_count=25),
        split_profile={},
    )

    from consoleplat.ui.ai_edit_page import SplitProfileEditorDialog

    dialog = SplitProfileEditorDialog(record, str(image_path))
    dialog.preview.set_guides([210, 420, 620, 810], [190, 390, 610, 805])

    assert dialog.x_guides_edit.text() == "210,420,620,810"
    assert dialog.y_guides_edit.text() == "190,390,610,805"

    dialog.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_split_profile_editor_dialog_updates_text_fields_when_guides_change -q`

Expected: FAIL because the current dialog has no preview widget driving the text fields.

- [ ] **Step 3: Implement guide synchronization and drag interaction**

Implementation shape:

```python
class SplitGuidePreviewWidget(QWidget):
    def mousePressEvent(self, event) -> None:  # noqa: N802
        axis, index = self._hit_test(event.pos())
        self._selected_axis = axis
        self._selected_index = index
        self._dragging = axis is not None and index >= 0
        self.update()

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if not self._dragging:
            return
        image_x, image_y = self._widget_to_image(event.pos())
        if self._selected_axis == "x":
            self._x_guides[self._selected_index] = self._clamp_x(image_x)
        elif self._selected_axis == "y":
            self._y_guides[self._selected_index] = self._clamp_y(image_y)
        self._normalize_guides()
        self.guidesChanged.emit(list(self._x_guides), list(self._y_guides))
        self.update()

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802
        self._dragging = False
```

Dialog synchronization shape:

```python
class SplitProfileEditorDialog(QDialog):
    def _sync_guide_fields(self, x_guides: list[int], y_guides: list[int]) -> None:
        self.x_guides_edit.setText(",".join(str(value) for value in x_guides))
        self.y_guides_edit.setText(",".join(str(value) for value in y_guides))
        self.stats_label.setText(self._stats_text(x_guides, y_guides))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_split_profile_editor_dialog_updates_text_fields_when_guides_change -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add consoleplat/ui/ai_edit_page.py tests/test_ai_edit_page_recovery.py
git commit -m "feat: sync preview split guides with dialog fields"
```

### Task 4: Save-and-Resplit Current Transparent Round

**Files:**
- Modify: `consoleplat/ui/ai_edit_page.py`
- Test: `tests/test_ai_edit_page_recovery.py`

- [ ] **Step 1: Write the failing test for dialog save routing through the current round**

```python
def test_ai_edit_page_edit_split_profile_saves_preview_guides_and_replaces_split_outputs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image_path = tmp_path / "edited_round_01_transparent.png"
    Image.new("RGBA", (1000, 1000), (0, 0, 0, 0)).save(image_path)
    page, _ = _page_with_temp_store(tmp_path, monkeypatch)
    record = AIEditTaskRecord(
        task_id="20260623170300",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体", split_collage=True, split_count=25),
        output_dir=str(tmp_path),
        outputs=[str(image_path)],
    )

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return QDialog.Accepted

        def parsed_guides(self):
            return [210, 420, 630, 840], [205, 405, 615, 825]

    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SplitProfileEditorDialog", _FakeDialog)
    captured = {}

    def fake_split(source_path, output_dir, split_count, x_guides, y_guides):
        captured["source_path"] = source_path
        captured["x_guides"] = x_guides
        captured["y_guides"] = y_guides
        return []

    monkeypatch.setattr("consoleplat.ui.ai_edit_page.split_collage_image_with_guides", fake_split)

    page.edit_split_profile(record, str(image_path))

    assert captured["source_path"] == str(image_path)
    assert captured["x_guides"] == [210, 420, 630, 840]
    assert captured["y_guides"] == [205, 405, 615, 825]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_ai_edit_page_edit_split_profile_saves_preview_guides_and_replaces_split_outputs -q`

Expected: FAIL because the dialog currently only saves text-entered values and lacks the preview-guided workflow assumptions from this test.

- [ ] **Step 3: Finalize dialog save flow and keep current round routing intact**

Implementation shape:

```python
class SplitProfileEditorDialog(QDialog):
    def parsed_guides(self) -> tuple[list[int], list[int]]:
        return self.preview.guides()


class AIEditPage(QWidget):
    def edit_split_profile(self, record: AIEditTaskRecord, source_path: str) -> None:
        ...
        dialog = SplitProfileEditorDialog(record, source_path, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        x_guides, y_guides = dialog.parsed_guides()
        profile = SplitProfile(
            source_image=source_path,
            split_count=record.job.split_count,
            columns=columns,
            rows=rows,
            x_guides=x_guides,
            y_guides=y_guides,
            updated_at=datetime.now().isoformat(timespec="seconds"),
        )
        self.split_profile_store.save(profile)
        record.split_profile = profile.to_payload()
        self.split_current_round(record, source_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ai_edit_page_recovery.py::test_ai_edit_page_edit_split_profile_saves_preview_guides_and_replaces_split_outputs -q`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add consoleplat/ui/ai_edit_page.py tests/test_ai_edit_page_recovery.py
git commit -m "feat: save preview split guides and resplit round"
```

### Task 5: Full Regression Verification and Backup

**Files:**
- Modify: `consoleplat/ui/ai_edit_page.py`
- Modify: `tests/test_ai_edit_page_recovery.py`
- Verify: `tests/test_ai_image_edit_cli.py`
- Verify: `consoleplat/services/ai_image_edit_cli.py`

- [ ] **Step 1: Run focused AI edit regression tests**

Run: `python -m pytest tests/test_ai_image_edit_cli.py tests/test_ai_edit_page_recovery.py -q`

Expected: PASS with the new preview dialog tests plus the previously added round-source and tiny-fragment regressions.

- [ ] **Step 2: Run broader page/service verification**

Run: `python -m pytest tests/test_ai_edit_postprocess_flow.py tests/test_settings_store.py tests/test_product_publish_page_ui.py -q`

Expected: PASS

- [ ] **Step 3: Run syntax verification**

Run: `python -m py_compile consoleplat/ui/ai_edit_page.py consoleplat/services/ai_image_edit_cli.py consoleplat/services/ai_edit_postprocess_service.py`

Expected: no output, exit code 0

- [ ] **Step 4: Create the backup commit**

```bash
git add consoleplat/ui/ai_edit_page.py tests/test_ai_edit_page_recovery.py
git commit -m "feat: add preview-based AI edit split guide editor"
```

- [ ] **Step 5: Push to the backup branch**

```bash
git push origin HEAD:codex/ai-edit-backup-20260623
```

## Self-Review

- Spec coverage:
  - Preview image for current transparent collage round: covered by Tasks 2 and 4.
  - Open with default 5x5 guides instead of requiring manual line creation: covered by Task 1.
  - Drag horizontal and vertical lines to fine-tune positions: covered by Task 3.
  - Save guides through existing split profile storage and re-split immediately: covered by Task 4.
  - Preserve existing splitter and regression behavior: covered by Task 5.
- Placeholder scan:
  - No `TODO`, `TBD`, or “appropriate handling” placeholders remain.
- Type consistency:
  - `SplitProfileEditorDialog.parsed_guides()`, `SplitGuidePreviewWidget.set_guides(...)`, and `AIEditPage.edit_split_profile(...)` use the same `list[int]` guide shape throughout.
