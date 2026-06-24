from pathlib import Path

from PyQt5.QtGui import QShowEvent
from PyQt5.QtWidgets import QApplication

from consoleplat.config import AppSettings, SettingsStore
from consoleplat.adapters.posaiimg_adapter import LocalImageJob
from consoleplat.ui.local_image_page import LocalImageTaskRecord
from consoleplat.ui.local_image_page import LocalImagePage


def _page_with_temp_store(tmp_path, monkeypatch, settings=None):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(settings or AppSettings(program_data_dir=str(tmp_path / "ConsolePlatData")))
    monkeypatch.setattr("consoleplat.ui.local_image_page.SettingsStore", lambda: SettingsStore(path))
    return LocalImagePage(), path


def test_local_image_page_loads_preferences_and_history(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    settings_path = tmp_path / "settings.json"
    program_data_dir = tmp_path / "ConsolePlatData"
    SettingsStore(settings_path).save(
        AppSettings(
            program_data_dir=str(program_data_dir),
            local_image_auto_start_comfyui=False,
            local_image_keep_comfyui=False,
            local_image_test_mode=False,
        )
    )
    tasks_dir = program_data_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "local_image_tasks.json").write_text(
        '[{"task_id":"20260623110000","mode_text":"完整模式","title":"task B","status":"完成","stage_text":"已完成",'
        '"progress_percent":100,"logs":[],"print_dir":"E:/prints/b","product_dir":"E:/products/b","xlsx_path":"E:/b.xlsx",'
        '"job":{"prefix":"BO","start_number":1661,"count":10,"style_name":"style","steps":28,"width":832,"height":1216,'
        '"seed":1,"test_mode":false,"auto_start_comfyui":false,"keep_comfyui":false,"gallery_root":"E:/gallery",'
        '"mockup_root":"E:/mockup","xlsx_root":"E:/xlsx"}},'
        '{"task_id":"20260623105900","mode_text":"测试模式","title":"task A","status":"等待启动","stage_text":"待启动",'
        '"progress_percent":0,"logs":[],"print_dir":"","product_dir":"","xlsx_path":"",'
        '"job":{"prefix":"SZW","start_number":3113,"count":2,"style_name":"style","steps":28,"width":832,"height":1216,'
        '"seed":2,"test_mode":true,"auto_start_comfyui":true,"keep_comfyui":true,"gallery_root":"E:/gallery",'
        '"mockup_root":"E:/mockup","xlsx_root":"E:/xlsx"}}]',
        encoding="utf-8",
    )
    monkeypatch.setattr("consoleplat.ui.local_image_page.SettingsStore", lambda: SettingsStore(settings_path))

    page = LocalImagePage()

    assert page.auto_start_comfyui_check.isChecked() is False
    assert page.keep_comfyui_check.isChecked() is False
    assert page.test_mode_check.isChecked() is False
    assert page.task_list.count() == 2
    assert "2026.0623.1100.00" in page.task_list.item(0).text()

    page.task_sort_combo.setCurrentText("按时间（旧到新）")

    assert "2026.0623.1059.00" in page.task_list.item(0).text()

    page.close()


def test_local_image_page_show_event_reloads_mirror_tasks(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(tmp_path, monkeypatch)
    program_data_dir = Path(SettingsStore(path).load().program_data_dir)
    tasks_dir = program_data_dir / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / "local_image_tasks.json").write_text(
        '[{"task_id":"20260624153000","mode_text":"完整模式","title":"mirror task","status":"完成","stage_text":"已完成",'
        '"progress_percent":100,"logs":["13:00 done"],"print_dir":"E:/prints","product_dir":"E:/products","xlsx_path":"E:/batch.xlsx",'
        '"job":{"prefix":"BO","start_number":1661,"count":10,"style_name":"style","steps":28,"width":832,"height":1216,'
        '"seed":1,"test_mode":false,"auto_start_comfyui":true,"keep_comfyui":true,"gallery_root":"E:/gallery",'
        '"mockup_root":"E:/mockup","xlsx_root":"E:/xlsx"}}]',
        encoding="utf-8",
    )

    page.showEvent(QShowEvent())

    assert any(record.task_id == "20260624153000" for record in page.tasks)
    assert page.task_list.count() == 1
    assert "mirror task" in page.task_list.item(0).text()

    page.close()


def test_local_image_page_show_event_skips_reload_when_task_file_unchanged(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(tmp_path, monkeypatch)
    program_data_dir = Path(SettingsStore(path).load().program_data_dir)
    tasks_file = program_data_dir / "tasks" / "local_image_tasks.json"
    tasks_file.parent.mkdir(parents=True, exist_ok=True)
    tasks_file.write_text("[]", encoding="utf-8")
    page.showEvent(QShowEvent())
    load_calls = []
    rebuild_calls = []
    monkeypatch.setattr(page.task_store, "load", lambda: load_calls.append("load") or [])
    monkeypatch.setattr(page, "_rebuild_task_list", lambda: rebuild_calls.append("rebuild"))

    page.showEvent(QShowEvent())

    assert load_calls == []
    assert rebuild_calls == []

    page.close()


def test_local_image_page_debounces_log_and_progress_persistence(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    record = LocalImageTaskRecord(
        task_id="20260624170000",
        mode_text="测试模式",
        title="debounce task",
        job=LocalImageJob(prefix="BO", start_number=1661, count=2),
        status="运行中",
        stage_text="准备启动",
        progress_percent=5,
    )
    page.current_task = record
    page.tasks = [record]
    page._rebuild_task_list()
    save_calls = []
    rebuild_calls = []
    monkeypatch.setattr(page, "_save_task_history", lambda: save_calls.append("save"))
    monkeypatch.setattr(page, "_rebuild_task_list", lambda: rebuild_calls.append("rebuild"))

    page._append_log("Queued one\nSaved one")
    page._set_task_progress(36, "排队")
    page._set_task_progress(48, "生成")

    assert save_calls == []
    assert rebuild_calls == []
    assert "生成" in page.task_list.item(0).text()

    page._flush_persist()

    assert save_calls == ["save"]

    page.close()
