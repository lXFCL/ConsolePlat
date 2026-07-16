from __future__ import annotations

import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from consoleplat.services.update_protocol import (
    ActivityRecord,
    AppManifest,
    CurrentVersionPointer,
    ManifestFile,
    StartupHealthRecord,
    SwitchTransaction,
    canonical_manifest_bytes,
    load_and_verify_manifest,
    validate_managed_path,
    verify_chunk_archive,
)


def _manifest(files: tuple[ManifestFile, ...] = ()) -> AppManifest:
    return AppManifest(
        protocol_version=1,
        schema_version=1,
        source_versions=("1.8.1",),
        target_version="1.8.2",
        release_tag="v1.8.2",
        commit_sha="a" * 40,
        workflow_run="12345",
        built_at="2026-07-16T10:00:00Z",
        minimum_launcher_version="1.0.0",
        key_id="test-2026",
        files=files,
    )


@pytest.mark.parametrize(
    "path",
    [
        "../outside.exe",
        "app/../../outside.exe",
        "/absolute/file.exe",
        "C:/Windows/system.ini",
        "C:\\Windows\\system.ini",
        "modules/file.py:payload",
        "modules//file.py",
        "modules/./file.py",
        "modules/file.py/",
        "CON.txt",
    ],
)
def test_validate_managed_path_rejects_unsafe_windows_paths(path):
    with pytest.raises(ValueError):
        validate_managed_path(path)


def test_validate_managed_path_normalizes_safe_relative_path():
    assert validate_managed_path("modules/SendGoods/main.py") == "modules/SendGoods/main.py"


def test_manifest_canonical_bytes_are_independent_of_input_file_order():
    first = ManifestFile("modules/b.py", 1, "b" * 64, "chunk-b.zip")
    second = ManifestFile("ConsolePlatApp.exe", 2, "a" * 64, "chunk-a.zip")

    left = canonical_manifest_bytes(_manifest((first, second)))
    right = canonical_manifest_bytes(_manifest((second, first)))

    assert left == right
    assert left.endswith(b"\n")
    assert json.loads(left)["files"][0]["path"] == "ConsolePlatApp.exe"


@pytest.mark.parametrize("target_version", ["../escape", "1.8", "v1.8.2", "1.8.2/asset"])
def test_manifest_rejects_non_semver_target_version(target_version):
    with pytest.raises(ValueError, match="target_version"):
        AppManifest.from_dict({**_manifest().to_dict(), "target_version": target_version})


def test_load_and_verify_manifest_accepts_valid_signature(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    manifest_path = tmp_path / "manifest.json"
    signature_path = tmp_path / "manifest.sig"
    payload = canonical_manifest_bytes(_manifest())
    manifest_path.write_bytes(payload)
    signature_path.write_bytes(private_key.sign(payload))

    loaded = load_and_verify_manifest(manifest_path, signature_path, private_key.public_key())

    assert loaded.target_version == "1.8.2"
    assert loaded.key_id == "test-2026"


def test_load_and_verify_manifest_rejects_tampered_manifest(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    manifest_path = tmp_path / "manifest.json"
    signature_path = tmp_path / "manifest.sig"
    payload = canonical_manifest_bytes(_manifest())
    signature_path.write_bytes(private_key.sign(payload))
    manifest_path.write_bytes(payload.replace(b"1.8.2", b"1.8.3"))

    with pytest.raises(ValueError, match="signature"):
        load_and_verify_manifest(manifest_path, signature_path, private_key.public_key())


def test_load_and_verify_manifest_rejects_unsupported_newer_protocol(tmp_path):
    private_key = Ed25519PrivateKey.generate()
    manifest_path = tmp_path / "manifest.json"
    signature_path = tmp_path / "manifest.sig"
    unsupported = AppManifest.from_dict({**_manifest().to_dict(), "protocol_version": 2})
    payload = canonical_manifest_bytes(unsupported)
    manifest_path.write_bytes(payload)
    signature_path.write_bytes(private_key.sign(payload))

    with pytest.raises(ValueError, match="unsupported update protocol"):
        load_and_verify_manifest(manifest_path, signature_path, private_key.public_key())


def test_verify_chunk_archive_rejects_corrupted_file_content(tmp_path):
    import zipfile

    chunk_path = tmp_path / "chunk.zip"
    with zipfile.ZipFile(chunk_path, "w") as archive:
        archive.writestr("app.exe", b"tampered")
    expected = ManifestFile(
        "app.exe",
        len(b"expected"),
        __import__("hashlib").sha256(b"expected").hexdigest(),
        "chunk.zip",
    )

    with pytest.raises(ValueError, match="hash|size"):
        verify_chunk_archive(chunk_path, (expected,))


def test_verify_chunk_archive_rejects_unexpected_or_unsafe_members(tmp_path):
    import zipfile

    chunk_path = tmp_path / "chunk.zip"
    with zipfile.ZipFile(chunk_path, "w") as archive:
        archive.writestr("../outside.exe", b"payload")

    with pytest.raises(ValueError, match="path|member"):
        verify_chunk_archive(chunk_path, ())


def test_runtime_records_have_independent_schemas_and_round_trip():
    pointer = CurrentVersionPointer(schema_version=1, current_version="1.8.2", previous_healthy_version="1.8.1")
    transaction = SwitchTransaction(
        schema_version=2,
        transaction_id="switch-1",
        from_version="1.8.1",
        to_version="1.8.2",
        state="prepared",
        created_at="2026-07-16T10:00:00Z",
    )
    activity = ActivityRecord(
        schema_version=3,
        activity_id="publish-1",
        kind="publish",
        page="product_publish",
        title="发布 5 个商品",
        started_at="2026-07-16T10:01:00Z",
        blocks_update=True,
        pid=1234,
    )
    health = StartupHealthRecord(
        schema_version=4,
        protocol_version=1,
        token="one-time-token",
        version="1.8.2",
        confirmed_at="2026-07-16T10:02:00Z",
    )

    assert CurrentVersionPointer.from_dict(pointer.to_dict()) == pointer
    assert SwitchTransaction.from_dict(transaction.to_dict()) == transaction
    assert ActivityRecord.from_dict(activity.to_dict()) == activity
    assert StartupHealthRecord.from_dict(health.to_dict()) == health
    assert {pointer.schema_version, transaction.schema_version, activity.schema_version, health.schema_version} == {1, 2, 3, 4}


def test_runtime_records_reject_unknown_fields():
    payload = CurrentVersionPointer(schema_version=1, current_version="1.8.2", previous_healthy_version="1.8.1").to_dict()
    payload["security_override"] = True

    with pytest.raises(ValueError, match="unknown fields"):
        CurrentVersionPointer.from_dict(payload)


@pytest.mark.parametrize(
    ("record_type", "payload"),
    [
        (CurrentVersionPointer, {"schema_version": 0, "current_version": "1.8.2", "previous_healthy_version": "1.8.1"}),
        (
            SwitchTransaction,
            {
                "schema_version": 1,
                "transaction_id": "",
                "from_version": "1.8.1",
                "to_version": "1.8.2",
                "state": "prepared",
                "created_at": "2026-07-16T10:00:00Z",
            },
        ),
        (
            ActivityRecord,
            {
                "schema_version": 1,
                "activity_id": "publish-1",
                "kind": "publish",
                "page": "product_publish",
                "title": "publish",
                "started_at": "2026-07-16T10:01:00Z",
                "blocks_update": 1,
                "pid": -1,
            },
        ),
        (
            StartupHealthRecord,
            {
                "schema_version": 1,
                "protocol_version": 0,
                "token": "token",
                "version": "1.8.2",
                "confirmed_at": "2026-07-16T10:02:00Z",
            },
        ),
    ],
)
def test_runtime_records_reject_invalid_security_sensitive_values(record_type, payload):
    with pytest.raises(ValueError):
        record_type.from_dict(payload)
