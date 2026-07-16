"""Versioned update protocol models and trust-boundary validation."""

from __future__ import annotations

import json
import hashlib
import re
import stat
import zipfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, ClassVar, Mapping, TypeVar

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey


_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
_APP_VERSION_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_Record = TypeVar("_Record", bound="StrictRecord")
SUPPORTED_UPDATE_PROTOCOL_VERSION = 1


def validate_managed_path(path: str) -> str:
    """Return a canonical release path or reject unsafe Windows semantics."""
    if not isinstance(path, str) or not path:
        raise ValueError("managed path must be a non-empty string")
    if "\\" in path or ":" in path or path.startswith("/") or path.endswith("/"):
        raise ValueError(f"unsafe managed path: {path!r}")

    parts = path.split("/")
    for part in parts:
        if not part or part in {".", ".."} or part.endswith((" ", ".")):
            raise ValueError(f"unsafe managed path component: {part!r}")
        if part.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
            raise ValueError(f"reserved Windows path component: {part!r}")
    return "/".join(parts)


def _validate_nonempty(value: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _validate_positive_integer(value: int, name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise ValueError(f"{name} must be a positive integer")


@dataclass(frozen=True)
class StrictRecord:
    """Dataclass record with strict dictionary deserialization."""

    _nested_fields: ClassVar[Mapping[str, type["StrictRecord"]]] = {}
    _tuple_fields: ClassVar[frozenset[str]] = frozenset()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls: type[_Record], payload: Mapping[str, Any]) -> _Record:
        if not isinstance(payload, Mapping):
            raise ValueError(f"{cls.__name__} must be a JSON object")
        expected = {item.name for item in fields(cls)}
        unknown = set(payload) - expected
        missing = expected - set(payload)
        if unknown:
            raise ValueError(f"unknown fields for {cls.__name__}: {sorted(unknown)}")
        if missing:
            raise ValueError(f"missing fields for {cls.__name__}: {sorted(missing)}")

        values = dict(payload)
        for name, record_type in cls._nested_fields.items():
            raw_items = values[name]
            if not isinstance(raw_items, (list, tuple)):
                raise ValueError(f"{name} must be an array")
            values[name] = tuple(record_type.from_dict(item) for item in raw_items)
        for name in cls._tuple_fields:
            raw_items = values[name]
            if not isinstance(raw_items, (list, tuple)):
                raise ValueError(f"{name} must be an array")
            values[name] = tuple(raw_items)
        try:
            return cls(**values)
        except TypeError as exc:
            raise ValueError(f"invalid {cls.__name__}: {exc}") from exc


@dataclass(frozen=True)
class ManifestFile(StrictRecord):
    path: str
    size: int
    sha256: str
    chunk: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", validate_managed_path(self.path))
        if not isinstance(self.size, int) or isinstance(self.size, bool) or self.size < 0:
            raise ValueError("manifest file size must be a non-negative integer")
        if not isinstance(self.sha256, str) or not _SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError("manifest file sha256 must be a lowercase SHA-256 digest")
        if validate_managed_path(self.chunk) != self.chunk or "/" in self.chunk or not self.chunk.endswith(".zip"):
            raise ValueError("manifest chunk must be a safe ZIP asset name")


@dataclass(frozen=True)
class AppManifest(StrictRecord):
    protocol_version: int
    schema_version: int
    source_versions: tuple[str, ...]
    target_version: str
    release_tag: str
    commit_sha: str
    workflow_run: str
    built_at: str
    minimum_launcher_version: str
    key_id: str
    files: tuple[ManifestFile, ...]

    _nested_fields: ClassVar[Mapping[str, type[StrictRecord]]] = {"files": ManifestFile}
    _tuple_fields: ClassVar[frozenset[str]] = frozenset({"source_versions"})

    def __post_init__(self) -> None:
        if not isinstance(self.protocol_version, int) or self.protocol_version < 1:
            raise ValueError("protocol_version must be a positive integer")
        if not isinstance(self.schema_version, int) or self.schema_version < 1:
            raise ValueError("schema_version must be a positive integer")
        for name in (
            "target_version",
            "release_tag",
            "commit_sha",
            "workflow_run",
            "built_at",
            "minimum_launcher_version",
            "key_id",
        ):
            _validate_nonempty(getattr(self, name), name)
        if not _APP_VERSION_PATTERN.fullmatch(self.target_version):
            raise ValueError("target_version must be a three-part numeric version")
        if not isinstance(self.source_versions, tuple) or not self.source_versions:
            raise ValueError("source_versions must not be empty")
        if any(not isinstance(version, str) or not version for version in self.source_versions):
            raise ValueError("source_versions entries must be non-empty strings")
        if not isinstance(self.files, tuple) or any(not isinstance(item, ManifestFile) for item in self.files):
            raise ValueError("files must contain ManifestFile records")
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise ValueError("manifest contains duplicate managed paths")

    def to_dict(self) -> dict[str, Any]:
        payload = super().to_dict()
        payload["files"] = [item.to_dict() for item in sorted(self.files, key=lambda item: item.path)]
        payload["source_versions"] = list(self.source_versions)
        return payload


@dataclass(frozen=True)
class CurrentVersionPointer(StrictRecord):
    schema_version: int
    current_version: str
    previous_healthy_version: str

    def __post_init__(self) -> None:
        _validate_positive_integer(self.schema_version, "schema_version")
        _validate_nonempty(self.current_version, "current_version")
        _validate_nonempty(self.previous_healthy_version, "previous_healthy_version")


@dataclass(frozen=True)
class SwitchTransaction(StrictRecord):
    schema_version: int
    transaction_id: str
    from_version: str
    to_version: str
    state: str
    created_at: str

    def __post_init__(self) -> None:
        _validate_positive_integer(self.schema_version, "schema_version")
        for name in ("transaction_id", "from_version", "to_version", "state", "created_at"):
            _validate_nonempty(getattr(self, name), name)


@dataclass(frozen=True)
class ActivityRecord(StrictRecord):
    schema_version: int
    activity_id: str
    kind: str
    page: str
    title: str
    started_at: str
    blocks_update: bool
    pid: int

    def __post_init__(self) -> None:
        _validate_positive_integer(self.schema_version, "schema_version")
        for name in ("activity_id", "kind", "page", "title", "started_at"):
            _validate_nonempty(getattr(self, name), name)
        if not isinstance(self.blocks_update, bool):
            raise ValueError("blocks_update must be a boolean")
        if not isinstance(self.pid, int) or isinstance(self.pid, bool) or self.pid < 0:
            raise ValueError("pid must be a non-negative integer")


@dataclass(frozen=True)
class StartupHealthRecord(StrictRecord):
    schema_version: int
    protocol_version: int
    token: str
    version: str
    confirmed_at: str

    def __post_init__(self) -> None:
        _validate_positive_integer(self.schema_version, "schema_version")
        _validate_positive_integer(self.protocol_version, "protocol_version")
        for name in ("token", "version", "confirmed_at"):
            _validate_nonempty(getattr(self, name), name)


def canonical_manifest_bytes(manifest: AppManifest) -> bytes:
    """Serialize a manifest into the exact byte representation that is signed."""
    if not isinstance(manifest, AppManifest):
        raise TypeError("manifest must be an AppManifest")
    text = json.dumps(manifest.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (text + "\n").encode("utf-8")


def load_and_verify_manifest(
    manifest_path: Path,
    signature_path: Path,
    public_key: Ed25519PublicKey,
) -> AppManifest:
    """Verify the original manifest bytes before parsing untrusted content."""
    payload = Path(manifest_path).read_bytes()
    signature = Path(signature_path).read_bytes()
    try:
        public_key.verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise ValueError("manifest signature verification failed") from exc

    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("signed manifest is not valid UTF-8 JSON") from exc
    manifest = AppManifest.from_dict(decoded)
    if manifest.protocol_version != SUPPORTED_UPDATE_PROTOCOL_VERSION:
        raise ValueError(f"unsupported update protocol: {manifest.protocol_version}")
    return manifest


def verify_chunk_archive(chunk_path: Path, expected_files: tuple[ManifestFile, ...]) -> None:
    """Verify archive membership and content against its signed manifest entries."""
    expected = {item.path: item for item in expected_files}
    if len(expected) != len(expected_files):
        raise ValueError("chunk contains duplicate expected paths")
    try:
        with zipfile.ZipFile(chunk_path) as archive:
            seen: set[str] = set()
            for info in archive.infolist():
                path = validate_managed_path(info.filename)
                if path in seen:
                    raise ValueError(f"duplicate archive member: {path}")
                seen.add(path)
                if info.is_dir() or stat.S_ISLNK(info.external_attr >> 16):
                    raise ValueError(f"unsupported archive member: {path}")
                item = expected.get(path)
                if item is None:
                    raise ValueError(f"unexpected archive member: {path}")
                payload = archive.read(info)
                if len(payload) != item.size:
                    raise ValueError(f"archive member size mismatch: {path}")
                if hashlib.sha256(payload).hexdigest() != item.sha256:
                    raise ValueError(f"archive member hash mismatch: {path}")
    except zipfile.BadZipFile as exc:
        raise ValueError("chunk archive is not a valid ZIP file") from exc
    missing = set(expected) - seen
    if missing:
        raise ValueError(f"chunk archive is missing members: {sorted(missing)}")
