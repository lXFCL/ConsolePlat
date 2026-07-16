from __future__ import annotations

import json
import zipfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from consoleplat.services.update_protocol import load_and_verify_manifest
from scripts.build_update_assets import build_update_assets


def _private_key_bytes(private_key: Ed25519PrivateKey) -> bytes:
    return private_key.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )


def test_build_update_assets_is_deterministic_and_signed(tmp_path):
    source = tmp_path / "runtime"
    (source / "modules").mkdir(parents=True)
    (source / "ConsolePlatApp.exe").write_bytes(b"launcher payload")
    (source / "modules" / "worker.py").write_text("print('ok')\n", encoding="utf-8")
    private_key = Ed25519PrivateKey.from_private_bytes(bytes(range(32)))

    first = build_update_assets(
        source,
        tmp_path / "first",
        source_versions=("1.8.1",),
        target_version="1.8.2",
        release_tag="v1.8.2",
        commit_sha="a" * 40,
        workflow_run="12345",
        built_at="2026-07-16T10:00:00Z",
        minimum_launcher_version="1.0.0",
        key_id="test-2026",
        private_key_bytes=_private_key_bytes(private_key),
        chunk_size=20,
    )
    second = build_update_assets(
        source,
        tmp_path / "second",
        source_versions=("1.8.1",),
        target_version="1.8.2",
        release_tag="v1.8.2",
        commit_sha="a" * 40,
        workflow_run="12345",
        built_at="2026-07-16T10:00:00Z",
        minimum_launcher_version="1.0.0",
        key_id="test-2026",
        private_key_bytes=_private_key_bytes(private_key),
        chunk_size=20,
    )

    assert first.manifest_path.read_bytes() == second.manifest_path.read_bytes()
    assert first.signature_path.read_bytes() == second.signature_path.read_bytes()
    assert [path.read_bytes() for path in first.chunk_paths] == [path.read_bytes() for path in second.chunk_paths]
    manifest = load_and_verify_manifest(first.manifest_path, first.signature_path, private_key.public_key())
    assert [item.path for item in manifest.files] == ["ConsolePlatApp.exe", "modules/worker.py"]
    assert len(first.chunk_paths) == 2

    with zipfile.ZipFile(first.chunk_paths[0]) as archive:
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())


def test_build_update_assets_rejects_symlink(tmp_path):
    source = tmp_path / "runtime"
    source.mkdir()
    target = tmp_path / "outside.txt"
    target.write_text("private", encoding="utf-8")
    link = source / "linked.txt"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows environment")

    with pytest.raises(ValueError, match="link"):
        build_update_assets(
            source,
            tmp_path / "release",
            source_versions=("1.8.1",),
            target_version="1.8.2",
            release_tag="v1.8.2",
            commit_sha="a" * 40,
            workflow_run="12345",
            built_at="2026-07-16T10:00:00Z",
            minimum_launcher_version="1.0.0",
            key_id="test-2026",
            private_key_bytes=bytes(range(32)),
        )


def test_build_update_assets_does_not_emit_private_key(tmp_path):
    source = tmp_path / "runtime"
    source.mkdir()
    (source / "app.exe").write_bytes(b"app")
    private_key = bytes(range(32))

    result = build_update_assets(
        source,
        tmp_path / "release",
        source_versions=("1.8.1",),
        target_version="1.8.2",
        release_tag="v1.8.2",
        commit_sha="a" * 40,
        workflow_run="12345",
        built_at="2026-07-16T10:00:00Z",
        minimum_launcher_version="1.0.0",
        key_id="test-2026",
        private_key_bytes=private_key,
    )

    assert private_key not in result.manifest_path.read_bytes()
    assert not any("key" in path.name.lower() for path in result.output_dir.iterdir())
    assert json.loads(result.manifest_path.read_text(encoding="utf-8"))["key_id"] == "test-2026"


def test_build_update_assets_rejects_output_inside_runtime(tmp_path):
    source = tmp_path / "runtime"
    source.mkdir()
    (source / "app.exe").write_bytes(b"app")

    with pytest.raises(ValueError, match="output directory"):
        build_update_assets(
            source,
            source / "release",
            source_versions=("1.8.1",),
            target_version="1.8.2",
            release_tag="v1.8.2",
            commit_sha="a" * 40,
            workflow_run="12345",
            built_at="2026-07-16T10:00:00Z",
            minimum_launcher_version="1.0.0",
            key_id="test-2026",
            private_key_bytes=bytes(range(32)),
        )
