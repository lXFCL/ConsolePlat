from pathlib import Path

from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit

from consoleplat.config import AppSettings, SettingsStore, resolve_project_dir
from consoleplat.paths import default_prints_dir, default_runtime_dir
from consoleplat.ui.settings_page import SettingsPage


def test_resolve_project_dir_prefers_configured_path(tmp_path):
    configured = tmp_path / "custom-putaway"
    configured.mkdir()
    sibling = tmp_path / "PutawayAiRobot"
    sibling.mkdir()

    resolved = resolve_project_dir(
        "putaway",
        str(configured),
        search_roots=[tmp_path],
    )

    assert resolved == configured


def test_resolve_project_dir_falls_back_to_detected_root(tmp_path):
    detected = tmp_path / "1PythonProject" / "ApplyGoods"
    detected.mkdir(parents=True)

    resolved = resolve_project_dir(
        "applygoods",
        "",
        search_roots=[tmp_path / "1PythonProject"],
    )

    assert resolved == detected


def test_resolve_project_dir_prefers_portable_modules_dir(tmp_path):
    root = tmp_path / "ConsolePlat"
    portable = root / "modules" / "SendGoods"
    sibling = tmp_path / "SendGoods"
    portable.mkdir(parents=True)
    sibling.mkdir()

    resolved = resolve_project_dir(
        "sendgoods",
        "",
        search_roots=[root, tmp_path],
    )

    assert resolved == portable


def test_resolve_project_dir_returns_none_when_missing(tmp_path):
    assert resolve_project_dir("sendgoods", "", search_roots=[tmp_path]) is None


def test_portable_runtime_and_print_defaults_stay_under_project_root(monkeypatch, tmp_path):
    root = tmp_path / "ConsolePlat"
    monkeypatch.setattr("consoleplat.paths.project_root", lambda: root)

    assert default_runtime_dir("outputs") == root / "runtime" / "outputs"
    assert default_prints_dir() == root / "resources" / "prints"


def test_settings_store_preserves_blank_external_paths(tmp_path):
    path = tmp_path / "settings.json"
    store = SettingsStore(path)

    store.save(AppSettings())
    loaded = SettingsStore(path).load()

    assert loaded.purchase_export_dir == ""
    assert loaded.posai_gallery_root == ""
    assert loaded.putaway_project_dir == ""
    assert loaded.applygoods_project_dir == ""


def test_settings_page_shows_resolved_path_status(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(putaway_project_dir=""))
    detected = tmp_path / "PutawayAiRobot"
    detected.mkdir()
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    monkeypatch.setattr("consoleplat.ui.settings_page.default_project_search_roots", lambda: [tmp_path])
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()

    labels = [label.text() for label in page.findChildren(QLabel)]
    assert any("自动探测到" in text and str(detected) in text for text in labels)

    page.close()


def test_settings_page_save_allows_blank_external_paths(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(AppSettings(putaway_project_dir="E:/old"))
    monkeypatch.setattr("consoleplat.ui.settings_page.SettingsStore", lambda: SettingsStore(path))
    app = QApplication.instance() or QApplication([])

    page = SettingsPage()
    page.findChild(QLineEdit, "putawayProjectDirEdit").setText("")
    page.save_settings()

    saved = SettingsStore(path).load()
    assert saved.putaway_project_dir == ""

    page.close()
