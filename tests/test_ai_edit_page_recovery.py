from pathlib import Path
import site
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from PyQt5.QtWidgets import QApplication, QDialog, QWidget
from openpyxl import Workbook, load_workbook
from PIL import Image

from consoleplat.adapters.posaiimg_adapter import AIEditJob
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.services.ai_edit_formalize_service import AIEditFormalizeSummary
from consoleplat.services.putaway_sync_service import PutawaySyncSummary
from consoleplat.ui.ai_edit_page import AIEditPage, AIEditTaskDetailDialog, AIEditTaskRecord, BackgroundTaskResult


def _page_with_temp_store(tmp_path, monkeypatch, settings=None):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(settings or AppSettings(ai_edit_api_key="stored-key"))
    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SettingsStore", lambda: SettingsStore(path))
    return AIEditPage(), path


def test_ai_edit_page_builds_job_and_persists_preferences(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image = tmp_path / "input.png"
    image.write_bytes(b"fake")
    page, path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            ai_edit_api_base="https://example.test/v1",
            ai_edit_model="demo-image-edit",
            ai_edit_size="1536x1024",
            default_ai_provider_id="provider-2",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "old-key",
                    "api_base": "https://old.example/v1",
                    "model": "old-model",
                    "size": "1024x1024",
                },
                {
                    "provider_id": "provider-2",
                    "name": "备用接口",
                    "api_key": "stored-key",
                    "api_base": "https://example.test/v1",
                    "model": "demo-image-edit",
                    "size": "1536x1024",
                },
            ],
            posai_gallery_root=str(tmp_path / "gallery-root"),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )

    page._add_image_item(str(image))
    page.prompt_edit.setPlainText("keep subject")
    page.split_collage_check.setChecked(True)
    page.split_count_spin.setValue(12)
    page.total_return_count_spin.setValue(8)
    page.prefix_combo.setCurrentText("SZW")
    page.start_spin.setValue(3113)
    page.test_mode_check.setChecked(False)

    job = page.build_job()
    saved = SettingsStore(path).load()

    assert isinstance(job, AIEditJob)
    assert job.images == [image]
    assert job.api_key == "stored-key"
    assert job.api_base == "https://example.test/v1"
    assert job.model == "demo-image-edit"
    assert job.size == "1536x1024"
    assert job.split_collage is True
    assert job.split_count == 12
    assert job.total_return_count == 8
    assert job.prefix == "SZW"
    assert job.start_number == 3113
    assert job.test_mode is False
    assert str(job.output_dir).startswith(str(tmp_path / "gallery-root" / "SZW"))
    assert saved.ai_edit_split_collage is True
    assert saved.ai_edit_split_count == 12
    assert saved.ai_edit_total_return_count == 8

    page.close()


def test_ai_edit_page_save_persists_prompt_and_reference_dir(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image = tmp_path / "refs" / "input.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"fake")
    page, path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            ai_edit_prompt="old prompt",
            ai_edit_reference_dir="",
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )

    page._add_image_item(str(image))
    page.prompt_edit.setPlainText("new prompt")
    page._save_preferences()

    saved = SettingsStore(path).load()

    assert saved.ai_edit_prompt == "new prompt"
    assert saved.ai_edit_reference_dir == str(image.parent)

    page.close()


def test_ai_edit_page_save_persists_ai_edit_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            publish_prefix="BO",
            publish_start_number=1421,
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )

    page.prefix_combo.setCurrentText("SZW")
    page.start_spin.setValue(3113)
    page.total_return_count_spin.setValue(6)
    page.split_collage_check.setChecked(True)
    page.split_count_spin.setValue(9)
    page.test_mode_check.setChecked(False)
    page._save_preferences()

    saved = SettingsStore(path).load()

    assert saved.publish_prefix == "SZW"
    assert saved.publish_start_number == 3113
    assert saved.ai_edit_total_return_count == 6
    assert saved.ai_edit_split_collage is True
    assert saved.ai_edit_split_count == 9
    assert saved.local_image_test_mode is False

    page.close()


def test_ai_edit_page_restores_tasks_and_deletes_failed(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    settings_path = tmp_path / "settings.json"
    program_data_dir = tmp_path / "ConsolePlatData"
    SettingsStore(settings_path).save(AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(program_data_dir)))
    tasks_dir = program_data_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "ai_edit_tasks.json").write_text(
        '[{"task_id":"20260623120000","title":"failed","status":"失败","stage_text":"失败","progress_percent":0,"logs":[],'
        '"output_dir":"E:/out/a","outputs":[],"failed":[],"warnings":[],"round_sources":[],"active_round_index":0,'
        '"final_transparent_dir":"","final_product_dir":"","xlsx_path":"","split_profile":{},'
        '"job":{"images":[],"prompt":"a","api_key":"","api_base":"https://api.openai.com/v1","model":"gpt-image-2",'
        '"output_dir":"E:/out/a","size":"1024x1024","split_collage":true,"split_count":10,"total_return_count":2,'
        '"prefix":"BO","start_number":1661,"test_mode":true,"gallery_root":"E:/gallery","mockup_root":"E:/mockup","xlsx_root":"E:/xlsx"}},'
        '{"task_id":"20260623120100","title":"success","status":"完成","stage_text":"已完成","progress_percent":100,"logs":[],'
        '"output_dir":"E:/out/b","outputs":[],"failed":[],"warnings":[],"round_sources":[],"active_round_index":0,'
        '"final_transparent_dir":"","final_product_dir":"","xlsx_path":"","split_profile":{},'
        '"job":{"images":[],"prompt":"b","api_key":"","api_base":"https://api.openai.com/v1","model":"gpt-image-2",'
        '"output_dir":"E:/out/b","size":"1024x1024","split_collage":true,"split_count":10,"total_return_count":2,'
        '"prefix":"BO","start_number":1662,"test_mode":true,"gallery_root":"E:/gallery","mockup_root":"E:/mockup","xlsx_root":"E:/xlsx"}}]',
        encoding="utf-8",
    )
    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SettingsStore", lambda: SettingsStore(settings_path))

    page = AIEditPage()

    assert page.task_list.count() == 2

    page.delete_failed_tasks()

    assert [record.title for record in page.tasks] == ["success"]
    saved = (tasks_dir / "ai_edit_tasks.json").read_text(encoding="utf-8")
    assert '"title": "failed"' not in saved

    page.close()


def test_ai_edit_page_copy_split_outputs_and_detail_dialog(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(ai_edit_api_key="stored-key", posai_gallery_root=str(tmp_path / "gallery")),
    )
    record = AIEditTaskRecord(
        task_id="20260623123000",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="prompt",
            split_collage=True,
            split_count=2,
            prefix="BO",
            start_number=1661,
            gallery_root=str(tmp_path / "gallery"),
            mockup_root=str(tmp_path / "mockup"),
            xlsx_root=str(tmp_path / "xlsx"),
        ),
        output_dir=str(tmp_path / "output"),
    )
    split_dir = tmp_path / "output"
    split_dir.mkdir(parents=True)
    split_a = split_dir / "edited_transparent_part_01.png"
    split_b = split_dir / "edited_transparent_part_02.png"
    split_a.write_bytes(b"a")
    split_b.write_bytes(b"b")

    outputs = page._copy_split_outputs_to_final_gallery(record, [split_a, split_b])
    record.outputs = [str(path) for path in outputs]
    record.round_sources = [str(path) for path in outputs]
    dialog = AIEditTaskDetailDialog(record, page)

    assert [path.name for path in outputs] == ["BO-1661.png", "BO-1662.png"]
    assert dialog.start_split_button.isEnabled() is True
    assert dialog.convert_transparent_button.isEnabled() is True
    assert dialog.export_product_button.isEnabled() is False
    assert dialog.export_xlsx_button.isEnabled() is False
    assert dialog.sync_putaway_button.isEnabled() is False
    assert dialog.batch_path_button.text() == str(tmp_path / "output")
    assert dialog.transparent_path_button.text() == str(tmp_path / "output")

    dialog.close()
    page.close()


def test_ai_edit_task_detail_enables_batch_action_buttons_when_outputs_exist(tmp_path):
    app = QApplication.instance() or QApplication([])

    product_dir = tmp_path / "final-product"
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "BO-1661_title.png").write_bytes(b"image")
    xlsx_path = tmp_path / "batch.xlsx"
    xlsx_path.write_bytes(b"xlsx")
    source = tmp_path / "edited_round_01_transparent.png"
    source.write_bytes(b"image")

    record = AIEditTaskRecord(
        task_id="20260623123001",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="prompt", prefix="BO", start_number=1661),
        round_sources=[str(source)],
        final_product_dir=str(product_dir),
        xlsx_path=str(xlsx_path),
    )

    dialog = AIEditTaskDetailDialog(record)

    assert dialog.export_product_button.isEnabled() is True
    assert dialog.export_xlsx_button.isEnabled() is True
    assert dialog.sync_putaway_button.isEnabled() is True

    dialog.close()


def test_ai_edit_page_finalize_task_schedules_post_process_in_background(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(tmp_path / "ConsolePlatData")),
    )
    page.current_task = AIEditTaskRecord(
        task_id="20260623192000",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="keep subject",
            split_collage=True,
            split_count=2,
            prefix="BO",
            start_number=1661,
            test_mode=False,
        ),
        output_dir=str(tmp_path),
    )

    scheduled = {}

    def fake_start_post_process(task):
        scheduled["task_id"] = task.task_id

    monkeypatch.setattr(page, "_start_post_process_job", fake_start_post_process)

    class _Summary:
        ok = True
        output_dir = str(tmp_path)
        outputs = [str(tmp_path / "edited_round_01.png")]
        failed = []
        warnings = []
        message = "done"

    page._finalize_task(_Summary(), 0)

    assert scheduled["task_id"] == "20260623192000"

    page.close()


def test_ai_edit_page_split_current_round_schedules_background_job(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(tmp_path / "ConsolePlatData")),
    )
    transparent = tmp_path / "edited_round_01_transparent.png"
    Image.new("RGBA", (1000, 1000), (0, 0, 0, 0)).save(transparent)
    record = AIEditTaskRecord(
        task_id="20260623192100",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="keep subject",
            split_collage=True,
            split_count=2,
            prefix="BO",
            start_number=1661,
        ),
        output_dir=str(tmp_path),
    )

    scheduled = {}

    def fake_start_background_job(action, current_record):
        scheduled["action"] = action
        scheduled["task_id"] = current_record.task_id

    monkeypatch.setattr(page, "_start_background_job", fake_start_background_job)

    page.split_current_round(record, str(transparent))

    assert scheduled == {"action": "split_current_round", "task_id": "20260623192100"}

    page.close()


def test_ai_edit_page_start_background_job_retains_worker_reference(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(tmp_path / "ConsolePlatData")),
    )
    record = AIEditTaskRecord(
        task_id="20260623192200",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="keep subject", prefix="BO", start_number=1661),
        output_dir=str(tmp_path),
    )

    started = {}

    def fake_start(self):
        started["called"] = True

    monkeypatch.setattr("consoleplat.ui.ai_edit_page.QThread.start", fake_start)

    page._start_background_job("post_process", record)

    assert started["called"] is True
    assert len(page._background_threads) == 1
    assert len(page._background_workers) == 1

    page.close()


def test_ai_edit_page_background_post_process_result_updates_formal_outputs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(tmp_path / "ConsolePlatData")),
    )
    record = AIEditTaskRecord(
        task_id="20260623192300",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="keep subject", prefix="BO", start_number=1661, test_mode=False),
        output_dir=str(tmp_path),
        final_transparent_dir=str(tmp_path / "final-transparent"),
        final_product_dir=str(tmp_path / "final-product"),
        xlsx_path=str(tmp_path / "batch.xlsx"),
    )
    page.tasks = [record]
    page.current_task = record

    result = BackgroundTaskResult(
        action="post_process",
        task_id="20260623192300",
        outputs=[str(tmp_path / "final-product" / "BO-1661_title.png")],
        round_sources=[str(tmp_path / "final-transparent" / "BO-1661.png")],
        final_transparent_dir=str(tmp_path / "final-transparent"),
        final_product_dir=str(tmp_path / "final-product"),
        xlsx_path=str(tmp_path / "batch.xlsx"),
        warnings=["synced"],
        logs=["formalize done"],
    )

    page._on_background_job_finished(result)

    assert page.current_task.outputs == [str(tmp_path / "final-product" / "BO-1661_title.png")]
    assert page.current_task.round_sources == [str(tmp_path / "final-transparent" / "BO-1661.png")]
    assert page.current_task.final_transparent_dir == str(tmp_path / "final-transparent")
    assert page.current_task.final_product_dir == str(tmp_path / "final-product")
    assert page.current_task.xlsx_path == str(tmp_path / "batch.xlsx")
    assert "synced" in page.current_task.warnings
    assert any("formalize done" in line for line in page.current_task.logs)

    page.close()


def test_ai_edit_task_detail_dialog_shows_failed_and_warning_messages(tmp_path):
    app = QApplication.instance() or QApplication([])

    record = AIEditTaskRecord(
        task_id="20260623123100",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="prompt", prefix="BO", start_number=1661),
        status="失败",
        stage_text="后处理失败",
        progress_percent=0,
        logs=["12:00:00  运行结束"],
        failed=["未找到可正式入库的改图产物"],
        warnings=["已同步 0 张图片"],
    )

    dialog = AIEditTaskDetailDialog(record)
    text = dialog.log.toPlainText()

    assert "未找到可正式入库的改图产物" in text
    assert "已同步 0 张图片" in text
    assert "运行结束" in text

    dialog.close()


def test_ai_edit_page_refreshes_open_task_detail_dialog(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    record = AIEditTaskRecord(
        task_id="20260623123200",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="prompt", prefix="BO", start_number=1661),
        status="运行中",
        stage_text="准备启动",
        progress_percent=5,
        logs=["12:00:00  启动任务"],
    )
    page.current_task = record
    dialog = AIEditTaskDetailDialog(record, page)
    page.task_detail_dialog = dialog

    page._update_current_task(status="失败", stage_text="后处理失败", progress_percent=0)
    page.current_task.failed = ["未找到可正式入库的改图产物"]
    page._append_log("正式模式后处理失败：未找到可正式入库的改图产物")

    assert "后处理失败" in dialog.meta_label.text()
    assert "未找到可正式入库的改图产物" in dialog.log.toPlainText()

    dialog.close()
    page.close()


def test_ai_edit_page_process_env_exports_key_and_user_site(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image = tmp_path / "input.png"
    image.write_bytes(b"fake")
    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "stored-key",
                    "api_base": "https://api.openai.com/v1",
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            posai_gallery_root=str(tmp_path / "gallery-root"),
        ),
    )
    page._add_image_item(str(image))
    page.prompt_edit.setPlainText("go")
    captured = {}

    class ReadySignal:
        def connect(self, _callback):
            return None

    class FakeEnv:
        def __init__(self):
            self.values = {}

        def insert(self, key, value):
            self.values[key] = value

        def value(self, key, default=""):
            return self.values.get(key, default)

    class FakeProcess:
        readyReadStandardOutput = ReadySignal()
        readyReadStandardError = ReadySignal()
        finished = ReadySignal()
        errorOccurred = ReadySignal()

        def __init__(self, _parent=None):
            self.env = FakeEnv()

        def setProgram(self, _program):
            return None

        def setArguments(self, _args):
            return None

        def setWorkingDirectory(self, _cwd):
            return None

        def processEnvironment(self):
            return self.env

        def setProcessEnvironment(self, env):
            captured.update(env.values)

        def start(self):
            return None

        def kill(self):
            return None

    monkeypatch.setattr("consoleplat.ui.ai_edit_page.QProcess", FakeProcess)

    page.start_job()

    assert captured["PYTHONUTF8"] == "1"
    assert captured["PYTHONIOENCODING"] == "utf-8"
    assert captured["CONSOLEPLAT_AI_IMAGE_API_KEY"] == "stored-key"
    assert site.getusersitepackages() in captured["PYTHONPATH"]

    page.close()


def test_ai_edit_page_loads_start_number_from_gallery_on_init(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    gallery_root = tmp_path / "gallery"
    batch_dir = gallery_root / "BO" / "2026" / "06" / "demo" / "final"
    batch_dir.mkdir(parents=True)
    (batch_dir / "BO-1660.png").write_bytes(b"x")

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            posai_gallery_root=str(gallery_root),
        ),
    )

    assert page.start_spin.value() == 1661

    page.close()


def test_ai_edit_page_append_log_updates_progress_from_percent_text(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    page.current_task = AIEditTaskRecord(
        task_id="20260620123456",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体"),
        status="运行中",
    )

    page._append_log("准备处理 20%")

    assert page.current_task.progress_percent == 20

    page.close()


def test_ai_edit_task_detail_prefers_transparent_source_for_split(tmp_path):
    app = QApplication.instance() or QApplication([])

    source_image = tmp_path / "edited.png"
    transparent_image = tmp_path / "edited_transparent.png"
    source_image.write_bytes(b"fake")
    transparent_image.write_bytes(b"fake")
    record = AIEditTaskRecord(
        task_id="20260620123456",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="保留主体",
            split_collage=True,
            split_count=4,
            prefix="BO",
            start_number=1661,
        ),
        output_dir=str(tmp_path),
        outputs=[str(source_image), str(transparent_image)],
    )

    dialog = AIEditTaskDetailDialog(record)

    assert dialog._find_split_source(record) == str(transparent_image)

    dialog.close()


def test_ai_edit_task_detail_round_index_uses_transparent_round_sources_only(tmp_path):
    app = QApplication.instance() or QApplication([])

    transparent_a = tmp_path / "edited_round_01_transparent.png"
    transparent_b = tmp_path / "edited_round_02_transparent.png"
    split_a = tmp_path / "edited_round_01_transparent_part_01.png"
    split_b = tmp_path / "edited_round_02_transparent_part_01.png"
    for path in (transparent_a, transparent_b, split_a, split_b):
        path.write_bytes(b"fake")
    record = AIEditTaskRecord(
        task_id="20260620123456",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="保留主体",
            split_collage=True,
            split_count=25,
            total_return_count=2,
            prefix="BO",
            start_number=1661,
        ),
        output_dir=str(tmp_path),
        round_sources=[str(transparent_a), str(transparent_b)],
        outputs=[str(transparent_a), str(split_a), str(transparent_b), str(split_b)],
    )

    dialog = AIEditTaskDetailDialog(record)

    assert dialog.round_index_label.text() == "1/2"
    assert dialog.source_path_label.text() == str(transparent_a)
    dialog.show_next_round()
    assert dialog.round_index_label.text() == "2/2"
    assert dialog.source_path_label.text() == str(transparent_b)

    dialog.close()


def test_split_profile_editor_dialog_parses_guides(tmp_path):
    app = QApplication.instance() or QApplication([])

    record = AIEditTaskRecord(
        task_id="20260620123456",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体"),
        split_profile={"x_guides": [200], "y_guides": [100]},
    )

    from consoleplat.ui.ai_edit_page import SplitProfileEditorDialog

    dialog = SplitProfileEditorDialog(record, str(tmp_path / "edited_round_01_transparent.png"))
    dialog.x_guides_edit.setText("120, 360, 120")
    dialog.y_guides_edit.setText("80，240")

    assert dialog.parsed_guides() == ([120, 360], [80, 240])

    dialog.close()


def test_split_profile_editor_dialog_uses_fixed_default_guides(tmp_path):
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

    assert dialog.parsed_guides() == ([458, 805, 1229, 1638], [482, 852, 1229, 1587])

    dialog.close()


def test_split_profile_editor_dialog_can_reset_guides_to_fixed_defaults(tmp_path):
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

    assert dialog.parsed_guides() == ([458, 805, 1229, 1638], [482, 852, 1229, 1587])

    dialog.close()


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


def test_ai_edit_page_load_split_profile_uses_fixed_default_guides_without_saved_profile(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    page.split_profile_store = None
    job = AIEditJob(images=[], prompt="保留主体", split_collage=True, split_count=25)

    profile = page._load_split_profile_for_job(job)

    assert profile["x_guides"] == [458, 805, 1229, 1638]
    assert profile["y_guides"] == [482, 852, 1229, 1587]
    assert profile["split_count"] == 25
    assert profile["columns"] == 5
    assert profile["rows"] == 5

    page.close()


def test_split_guide_preview_widget_move_guide_clamps_and_sorts(tmp_path):
    app = QApplication.instance() or QApplication([])

    image_path = tmp_path / "edited_round_01_transparent.png"
    Image.new("RGBA", (1000, 1000), (0, 0, 0, 0)).save(image_path)

    from consoleplat.ui.ai_edit_page import SplitGuidePreviewWidget

    widget = SplitGuidePreviewWidget(str(image_path), [200, 400, 600, 800], [200, 400, 600, 800])
    widget.move_guide("x", 2, 50)
    widget.move_guide("y", 1, 1200)

    assert widget.guides() == ([50, 200, 400, 800], [200, 600, 800, 999])


def test_ai_edit_task_detail_manual_split_button_uses_current_round_source(tmp_path):
    app = QApplication.instance() or QApplication([])

    transparent_a = tmp_path / "edited_round_01_transparent.png"
    transparent_b = tmp_path / "edited_round_02_transparent.png"
    for path in (transparent_a, transparent_b):
        path.write_bytes(b"fake")

    record = AIEditTaskRecord(
        task_id="20260620123456",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="保留主体",
            split_collage=True,
            split_count=25,
            total_return_count=2,
            prefix="BO",
            start_number=1661,
        ),
        output_dir=str(tmp_path),
        round_sources=[str(transparent_a), str(transparent_b)],
        outputs=[str(transparent_a), str(transparent_b)],
    )

    class _PageStub(QWidget):
        def __init__(self) -> None:
            super().__init__()
            self.calls: list[tuple[AIEditTaskRecord, str]] = []

        def edit_split_profile(self, current_record, source_path) -> None:
            self.calls.append((current_record, source_path))

    page = _PageStub()
    dialog = AIEditTaskDetailDialog(record, parent=page)

    dialog.show_next_round()
    dialog.edit_split_profile()

    assert len(page.calls) == 1
    assert page.calls[0][0] is record
    assert page.calls[0][1] == str(transparent_b)

    dialog.close()


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
    page.tasks = [record]
    page.split_profile_store = None

    class _ProfileStoreStub:
        def __init__(self) -> None:
            self.saved = None

        def save(self, profile) -> None:
            self.saved = profile

    page.split_profile_store = _ProfileStoreStub()

    class _FakeDialog:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return QDialog.Accepted

        def parsed_guides(self):
            return [210, 420, 630, 840], [205, 405, 615, 825]

    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SplitProfileEditorDialog", _FakeDialog)
    scheduled = {}

    def fake_start_background_job(action, current_record):
        scheduled["action"] = action
        scheduled["task_id"] = current_record.task_id
        scheduled["x_guides"] = list(current_record.split_profile.get("x_guides") or [])
        scheduled["y_guides"] = list(current_record.split_profile.get("y_guides") or [])

    monkeypatch.setattr(page, "_start_background_job", fake_start_background_job)

    page.edit_split_profile(record, str(image_path))

    assert scheduled["action"] == "split_current_round"
    assert scheduled["task_id"] == "20260623170300"
    assert scheduled["x_guides"] == [210, 420, 630, 840]
    assert scheduled["y_guides"] == [205, 405, 615, 825]


def test_ai_edit_page_restores_legacy_collage_transparent_sources(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    settings_path = tmp_path / "settings.json"
    program_data_dir = tmp_path / "ConsolePlatData"
    transparent_image = tmp_path / "edited_transparent.png"
    transparent_image.write_bytes(b"fake")
    SettingsStore(settings_path).save(AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(program_data_dir)))
    tasks_dir = program_data_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "ai_edit_tasks.json").write_text(
        (
            "[{"
            "\"task_id\":\"20260623120000\","
            "\"title\":\"AI 改图 BO-1661\\n2 轮 · 正式模式\","
            "\"status\":\"完成\","
            "\"stage_text\":\"已完成\","
            "\"progress_percent\":100,"
            "\"logs\":[],"
            f"\"output_dir\":\"{tmp_path.as_posix()}\","
            "\"outputs\":[],"
            "\"failed\":[],"
            "\"warnings\":[],"
            "\"round_sources\":[],"
            f"\"collage_transparent_sources\":[\"{transparent_image.as_posix()}\"],"
            "\"active_round_index\":0,"
            "\"final_transparent_dir\":\"\","
            "\"final_product_dir\":\"\","
            "\"xlsx_path\":\"\","
            "\"split_profile\":{},"
            "\"job\":{"
            "\"images\":[],"
            "\"prompt\":\"保留主体\","
            "\"api_key\":\"\","
            "\"api_base\":\"https://api.openai.com/v1\","
            "\"model\":\"gpt-image-2\","
            f"\"output_dir\":\"{tmp_path.as_posix()}\","
            "\"size\":\"1024x1024\","
            "\"split_collage\":true,"
            "\"split_count\":10,"
            "\"total_return_count\":2,"
            "\"prefix\":\"BO\","
            "\"start_number\":1661,"
            "\"test_mode\":false,"
            "\"gallery_root\":\"\","
            "\"mockup_root\":\"\","
            "\"xlsx_root\":\"\""
            "}"
            "}]"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SettingsStore", lambda: SettingsStore(settings_path))

    page = AIEditPage()

    assert len(page.tasks[0].round_sources) == 1
    assert Path(page.tasks[0].round_sources[0]) == transparent_image

    page.close()


def test_ai_edit_page_backfills_xlsx_colors_when_restoring_history(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    settings_path = tmp_path / "settings.json"
    program_data_dir = tmp_path / "ConsolePlatData"
    SettingsStore(settings_path).save(AppSettings(ai_edit_api_key="stored-key", program_data_dir=str(program_data_dir)))

    final_transparent_dir = tmp_path / "final_transparent"
    final_transparent_dir.mkdir(parents=True)
    Image.new("RGBA", (32, 32), (0, 0, 0, 255)).save(final_transparent_dir / "SZW-3113.png")
    Image.new("RGBA", (32, 32), (240, 240, 240, 255)).save(final_transparent_dir / "SZW-3114.png")

    xlsx_path = tmp_path / "batch.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.append(["店铺名称", "产品分类", "产品标题", "产品序列号", "颜色"])
    ws.append(["YUHOOBO", "T恤", "固定标题", "SZW-3113", ""])
    ws.append(["YUHOOBO", "T恤", "固定标题", "SZW-3114", ""])
    wb.save(xlsx_path)
    wb.close()

    tasks_dir = program_data_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "ai_edit_tasks.json").write_text(
        (
            "[{"
            "\"task_id\":\"20260623120000\","
            "\"title\":\"AI 改图 SZW-3113\\n2 轮 · 正式模式\","
            "\"status\":\"完成\","
            "\"stage_text\":\"已完成\","
            "\"progress_percent\":100,"
            "\"logs\":[],"
            f"\"output_dir\":\"{tmp_path.as_posix()}\","
            "\"outputs\":[],"
            "\"failed\":[],"
            "\"warnings\":[],"
            "\"round_sources\":[],"
            "\"collage_transparent_sources\":[],"
            "\"active_round_index\":0,"
            f"\"final_transparent_dir\":\"{final_transparent_dir.as_posix()}\","
            "\"final_product_dir\":\"\","
            f"\"xlsx_path\":\"{xlsx_path.as_posix()}\","
            "\"split_profile\":{},"
            "\"job\":{"
            "\"images\":[],"
            "\"prompt\":\"保留主体\","
            "\"api_key\":\"\","
            "\"api_base\":\"https://api.openai.com/v1\","
            "\"model\":\"gpt-image-2\","
            f"\"output_dir\":\"{tmp_path.as_posix()}\","
            "\"size\":\"1024x1024\","
            "\"split_collage\":true,"
            "\"split_count\":10,"
            "\"total_return_count\":2,"
            "\"prefix\":\"SZW\","
            "\"start_number\":3113,"
            "\"test_mode\":false,"
            "\"gallery_root\":\"\","
            "\"mockup_root\":\"\","
            "\"xlsx_root\":\"\""
            "}"
            "}]"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SettingsStore", lambda: SettingsStore(settings_path))

    page = AIEditPage()

    wb = load_workbook(xlsx_path, read_only=True, data_only=True)
    ws = wb.active
    assert ws["E2"].value == "白"
    assert ws["E3"].value == "黑"
    wb.close()

    page.close()


def test_ai_edit_page_reads_remaining_stdout_on_finish(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "stored-key",
                    "api_base": "https://api.openai.com/v1",
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            posai_gallery_root=str(tmp_path / "gallery-root"),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    page.current_task = AIEditTaskRecord(
        task_id="20260623125900",
        title="AI 改图 BO-1661",
        job=AIEditJob(images=[], prompt="保留主体"),
        output_dir=str(tmp_path),
        final_transparent_dir=str(tmp_path / "final-transparent"),
    )

    class FakeProcess:
        def readAllStandardOutput(self):
            return (
                bytes(
                    json.dumps(
                        {
                            "output_dir": str(tmp_path / "out").replace("\\", "/"),
                            "outputs": [str((tmp_path / "out" / "a.png")).replace("\\", "/")],
                            "failed": [],
                            "warnings": [],
                            "message": "ok",
                        }
                    ),
                    "utf-8",
                )
            )

        def readAllStandardError(self):
            return b""

    page.process = FakeProcess()
    page._stdout_buffer = ""
    page._stderr_buffer = ""

    page._on_process_finished(0, None)

    assert page.current_task.status == "完成"
    assert page.current_task.output_dir == str(tmp_path / "out").replace("\\", "/")
    assert page.current_task.outputs

    page.close()


def test_ai_edit_page_formal_mode_passes_model_dir_from_settings(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    model_root = tmp_path / "models"
    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            bo_product_title="BO title",
            putaway_data_dir=str(tmp_path / "putaway-data"),
            posai_model_root=str(model_root),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    transparent_dir = tmp_path / "final-transparent"
    transparent_dir.mkdir(parents=True, exist_ok=True)
    split_path = transparent_dir / "BO-1661.png"
    split_path.write_bytes(b"image")
    page.current_task = AIEditTaskRecord(
        task_id="20260623130110",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="keep subject",
            output_dir=tmp_path / "output",
            prefix="BO",
            start_number=1661,
            split_collage=False,
            split_count=1,
            test_mode=False,
        ),
        output_dir=str(tmp_path / "output"),
        outputs=[str(split_path)],
        final_transparent_dir=str(transparent_dir),
        final_product_dir=str(tmp_path / "final-product"),
        xlsx_path=str(tmp_path / "final-product.xlsx"),
    )

    captured = {}

    def fake_formalize(**kwargs):
        captured["model_dir"] = kwargs["model_dir"]
        return AIEditFormalizeSummary(
            ok=True,
            renamed_outputs=[str(split_path)],
            product_outputs=[str(tmp_path / "final-product" / "BO-1661_title.png")],
            xlsx_path=str(tmp_path / "final-product.xlsx"),
            putaway=PutawaySyncSummary(ok=True, message="synced"),
            message="formalize done",
        )

    monkeypatch.setattr("consoleplat.ui.ai_edit_page.formalize_ai_edit_outputs", fake_formalize)

    page._run_formalize_post_process()

    assert captured["model_dir"] == model_root

    page.close()


def test_ai_edit_page_start_job_runs_cli_and_finishes_success(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image = tmp_path / "input.png"
    Image.new("RGBA", (32, 32), (255, 0, 0, 255)).save(image)

    output_image = tmp_path / "edited.png"
    Image.new("RGBA", (32, 32), (0, 0, 0, 255)).save(output_image)
    image_b64 = base64.b64encode(output_image.read_bytes()).decode("ascii")

    class EditHandler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            if length:
                self.rfile.read(length)
            body = {
                "data": [
                    {
                        "b64_json": image_b64,
                        "revised_prompt": "done",
                    }
                ]
            }
            payload = json.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):  # noqa: A003
            return

    server = HTTPServer(("127.0.0.1", 0), EditHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    api_base = f"http://127.0.0.1:{server.server_port}/v1"

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "stored-key",
                    "api_base": api_base,
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            posai_gallery_root=str(tmp_path / "gallery-root"),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    page._add_image_item(str(image))
    page.prompt_edit.setPlainText("keep subject")
    try:
        page.start_job()

        assert page.process is not None
        finished = page.process.waitForFinished(15000)

        assert finished is True
        assert page.current_task is not None
        assert page.current_task.status == "完成"
        assert page.current_task.outputs
        assert Path(page.current_task.outputs[0]).exists()
    finally:
        page.close()
        server.shutdown()
        server.server_close()


def test_ai_edit_page_start_job_validates_required_inputs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image = tmp_path / "input.png"
    image.write_bytes(b"fake")

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "",
                    "api_base": "https://api.openai.com/v1",
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )

    page.start_job()
    assert page.process is None
    assert page.status_label.text() == "请先添加参考图"

    page._add_image_item(str(image))
    page.prompt_edit.clear()
    page.start_job()
    assert page.process is None
    assert page.status_label.text() == "请先填写改图要求"

    page.prompt_edit.setPlainText("keep subject")
    page.start_job()
    assert page.process is None
    assert page.status_label.text() == "请先配置 API Key"

    page.close()


def test_ai_edit_page_formal_mode_runs_post_process_and_updates_outputs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "stored-key",
                    "api_base": "https://api.openai.com/v1",
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            bo_product_title="BO固定产品标题",
            putaway_data_dir=str(tmp_path / "putaway-data"),
            posai_gallery_root=str(tmp_path / "gallery-root"),
            posai_mockup_root=str(tmp_path / "mockup-root"),
            posai_xlsx_root=str(tmp_path / "xlsx-root"),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    page.current_task = AIEditTaskRecord(
        task_id="20260623130000",
        title="AI 改图 BO-1661",
        job=AIEditJob(
            images=[],
            prompt="保留主体",
            output_dir=tmp_path / "output",
            prefix="BO",
            start_number=1661,
            total_return_count=2,
            split_collage=True,
            split_count=2,
            test_mode=False,
        ),
        output_dir=str(tmp_path / "output"),
        final_transparent_dir=str(tmp_path / "final-transparent"),
        final_product_dir=str(tmp_path / "final-product"),
        xlsx_path=str(tmp_path / "final-product.xlsx"),
    )

    scheduled: dict[str, object] = {}

    def fake_start_post_process(task):
        scheduled["task_id"] = task.task_id
        scheduled["outputs"] = list(task.outputs)

    monkeypatch.setattr(page, "_start_post_process_job", fake_start_post_process)

    class FakeProcess:
        def readAllStandardOutput(self):
            return (
                b'{"output_dir":"E:/tmp/out","outputs":["E:/tmp/out/a_part_1.png"],"failed":[],"warnings":[],"message":"ok"}'
            )

        def readAllStandardError(self):
            return b""

    page.process = FakeProcess()
    page._stdout_buffer = ""
    page._stderr_buffer = ""

    page._on_process_finished(0, None)

    assert scheduled["task_id"] == "20260623130000"
    assert scheduled["outputs"] == ["E:/tmp/out/a_part_1.png"]
    assert page.current_task.status == "完成"
    assert page.current_task.stage_text == "已完成"
    assert page.current_task.progress_percent == 100
    assert page.current_task.final_transparent_dir == str(tmp_path / "final-transparent")
    assert page.current_task.final_product_dir == str(tmp_path / "final-product")
    assert page.current_task.xlsx_path == str(tmp_path / "final-product.xlsx")
    assert page.current_task.outputs == ["E:/tmp/out/a_part_1.png"]

    page.close()


def test_ai_edit_page_formal_mode_accepts_non_split_png_outputs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "stored-key",
                    "api_base": "https://api.openai.com/v1",
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            szw_product_title="SZW固定产品标题",
            putaway_data_dir=str(tmp_path / "putaway-data"),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    page.current_task = AIEditTaskRecord(
        task_id="20260623130100",
        title="AI 改图 SZW-3113",
        job=AIEditJob(
            images=[],
            prompt="保留主体",
            output_dir=tmp_path / "output",
            prefix="SZW",
            start_number=3113,
            total_return_count=1,
            split_collage=False,
            split_count=1,
            test_mode=False,
        ),
        output_dir=str(tmp_path / "output"),
        final_transparent_dir=str(tmp_path / "final-transparent"),
        final_product_dir=str(tmp_path / "final-product"),
        xlsx_path=str(tmp_path / "final-product.xlsx"),
    )

    scheduled: dict[str, object] = {}

    def fake_start_post_process(task):
        scheduled["task_id"] = task.task_id
        scheduled["outputs"] = list(task.outputs)

    monkeypatch.setattr(page, "_start_post_process_job", fake_start_post_process)

    class FakeProcess:
        def readAllStandardOutput(self):
            return (
                b'{"output_dir":"E:/tmp/out","outputs":["E:/tmp/out/transparent_master.png"],"failed":[],"warnings":[],"message":"ok"}'
            )

        def readAllStandardError(self):
            return b""

    page.process = FakeProcess()
    page._stdout_buffer = ""
    page._stderr_buffer = ""

    page._on_process_finished(0, None)

    assert scheduled["task_id"] == "20260623130100"
    assert scheduled["outputs"] == ["E:/tmp/out/transparent_master.png"]
    assert page.current_task.status == "完成"
    assert page.current_task.outputs == ["E:/tmp/out/transparent_master.png"]

    page.close()
