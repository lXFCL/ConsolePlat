from PyQt5.QtWidgets import QApplication

from consoleplat.config import AppSettings, SettingsStore
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
