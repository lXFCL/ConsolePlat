"""Build deterministic, signed assets for the versioned update protocol."""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import stat
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from consoleplat.services.update_protocol import AppManifest, ManifestFile, canonical_manifest_bytes, validate_managed_path


DEFAULT_CHUNK_SIZE = 32 * 1024 * 1024
_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


@dataclass(frozen=True)
class UpdateAssetBuild:
    output_dir: Path
    manifest_path: Path
    signature_path: Path
    chunk_paths: tuple[Path, ...]


@dataclass(frozen=True)
class _SourceFile:
    path: str
    source: Path
    size: int
    sha256: str


def _is_link_or_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    attributes = getattr(path.lstat(), "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _source_files(source_dir: Path) -> tuple[_SourceFile, ...]:
    if not source_dir.is_dir():
        raise ValueError(f"runtime source directory does not exist: {source_dir}")
    collected: list[_SourceFile] = []
    for path in sorted(source_dir.rglob("*"), key=lambda item: item.relative_to(source_dir).as_posix()):
        if _is_link_or_reparse_point(path):
            raise ValueError(f"runtime source contains a link or reparse point: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f"runtime source contains an unsupported entry: {path}")
        relative = validate_managed_path(path.relative_to(source_dir).as_posix())
        payload = path.read_bytes()
        collected.append(_SourceFile(relative, path, len(payload), hashlib.sha256(payload).hexdigest()))
    return tuple(collected)


def _chunks(files: Iterable[_SourceFile], chunk_size: int) -> tuple[tuple[_SourceFile, ...], ...]:
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    groups: list[tuple[_SourceFile, ...]] = []
    current: list[_SourceFile] = []
    current_size = 0
    for item in files:
        if current and current_size + item.size > chunk_size:
            groups.append(tuple(current))
            current = []
            current_size = 0
        current.append(item)
        current_size += item.size
    if current:
        groups.append(tuple(current))
    return tuple(groups)


def _zip_bytes(files: tuple[_SourceFile, ...]) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for item in files:
            info = zipfile.ZipInfo(item.path, _ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100644 & 0xFFFF) << 16
            archive.writestr(info, item.source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return output.getvalue()


def build_update_assets(
    source_dir: Path,
    output_dir: Path,
    *,
    source_versions: tuple[str, ...],
    target_version: str,
    release_tag: str,
    commit_sha: str,
    workflow_run: str,
    built_at: str,
    minimum_launcher_version: str,
    key_id: str,
    private_key_bytes: bytes,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> UpdateAssetBuild:
    """Build content-addressed chunks and a signed canonical manifest."""
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir == source_dir or source_dir in output_dir.parents:
        raise ValueError("output directory must be outside the runtime source directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    files = _source_files(source_dir)

    manifest_files: list[ManifestFile] = []
    chunk_paths: list[Path] = []
    for group in _chunks(files, chunk_size):
        payload = _zip_bytes(group)
        chunk_name = f"app-chunk-{hashlib.sha256(payload).hexdigest()}.zip"
        chunk_path = output_dir / chunk_name
        chunk_path.write_bytes(payload)
        chunk_paths.append(chunk_path)
        manifest_files.extend(ManifestFile(item.path, item.size, item.sha256, chunk_name) for item in group)

    manifest = AppManifest(
        protocol_version=1,
        schema_version=1,
        source_versions=source_versions,
        target_version=target_version,
        release_tag=release_tag,
        commit_sha=commit_sha,
        workflow_run=workflow_run,
        built_at=built_at,
        minimum_launcher_version=minimum_launcher_version,
        key_id=key_id,
        files=tuple(manifest_files),
    )
    manifest_payload = canonical_manifest_bytes(manifest)
    private_key = Ed25519PrivateKey.from_private_bytes(private_key_bytes)
    signature = private_key.sign(manifest_payload)
    manifest_path = output_dir / f"app-manifest-v{target_version}.json"
    signature_path = output_dir / f"app-manifest-v{target_version}.sig"
    manifest_path.write_bytes(manifest_payload)
    signature_path.write_bytes(signature)
    return UpdateAssetBuild(output_dir, manifest_path, signature_path, tuple(chunk_paths))


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--source-version", action="append", required=True, dest="source_versions")
    parser.add_argument("--target-version", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--workflow-run", required=True)
    parser.add_argument("--built-at", required=True)
    parser.add_argument("--minimum-launcher-version", required=True)
    parser.add_argument("--key-id", required=True)
    parser.add_argument("--private-key-env", default="CONSOLEPLAT_UPDATE_PRIVATE_KEY_HEX")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    key_hex = os.environ.get(args.private_key_env)
    if not key_hex:
        raise SystemExit(f"missing private key environment variable: {args.private_key_env}")
    try:
        private_key_bytes = bytes.fromhex(key_hex)
    except ValueError as exc:
        raise SystemExit("private key environment variable must contain hexadecimal bytes") from exc
    build_update_assets(
        args.source_dir,
        args.output_dir,
        source_versions=tuple(args.source_versions),
        target_version=args.target_version,
        release_tag=args.release_tag,
        commit_sha=args.commit_sha,
        workflow_run=args.workflow_run,
        built_at=args.built_at,
        minimum_launcher_version=args.minimum_launcher_version,
        key_id=args.key_id,
        private_key_bytes=private_key_bytes,
        chunk_size=args.chunk_size,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
