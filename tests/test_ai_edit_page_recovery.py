from pathlib import Path
import site

from PyQt5.QtWidgets import QApplication
from openpyxl import Workbook, load_workbook
from PIL import Image

from consoleplat.adapters.posaiimg_adapter import AIEditJob
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.ai_edit_page import AIEditPage, AIEditTaskDetailDialog, AIEditTaskRecord


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
    assert dialog.open_output_dir_button.text()

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
