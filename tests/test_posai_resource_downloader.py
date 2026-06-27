from __future__ import annotations

import zipfile

from consoleplat.services.posai_resource_downloader import (
    PosAiResourceDefinition,
    install_posai_resource,
)


def test_install_posai_resource_requires_download_url(tmp_path):
    resource = PosAiResourceDefinition(
        key="posai_models",
        label="PosAiImg models",
        url="",
        install_dir_name="models",
    )

    result = install_posai_resource(
        resource,
        download_dir=tmp_path / "downloads",
        resources_dir=tmp_path / "resources",
    )

    assert result.ok is False
    assert "待配置" in result.message
    assert not (tmp_path / "resources" / "models").exists()


def test_install_posai_resource_downloads_and_extracts_zip_file_url(tmp_path):
    archive = tmp_path / "models.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("model/checkpoint.txt", "ready")
    progress_events = []
    resource = PosAiResourceDefinition(
        key="posai_models",
        label="PosAiImg models",
        url=archive.as_uri(),
        install_dir_name="models",
    )

    result = install_posai_resource(
        resource,
        download_dir=tmp_path / "downloads",
        resources_dir=tmp_path / "resources",
        progress_cb=lambda received, total: progress_events.append((received, total)),
    )

    assert result.ok is True
    assert result.installed_path == str(tmp_path / "resources" / "models")
    assert (tmp_path / "resources" / "models" / "model" / "checkpoint.txt").read_text(encoding="utf-8") == "ready"
    assert progress_events


def test_install_posai_resource_reports_insufficient_space(tmp_path, monkeypatch):
    archive = tmp_path / "comfy.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("ComfyUI/main.py", "print('ready')")
    resource = PosAiResourceDefinition(
        key="comfyui",
        label="ComfyUI",
        url=archive.as_uri(),
        install_dir_name="ComfyUI",
        min_free_bytes=1024,
    )

    monkeypatch.setattr(
        "consoleplat.services.posai_resource_downloader.shutil.disk_usage",
        lambda _path: (2048, 2048, 512),
    )

    result = install_posai_resource(
        resource,
        download_dir=tmp_path / "downloads",
        resources_dir=tmp_path / "resources",
    )

    assert result.ok is False
    assert "空间不足" in result.message
