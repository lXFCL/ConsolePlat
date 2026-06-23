from pathlib import Path
import site

from PyQt5.QtWidgets import QApplication

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
        AppSettings(ai_edit_api_key="stored-key", posai_gallery_root=str(tmp_path / "gallery-root")),
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
