from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class SplitProfile:
    source_image: str
    split_count: int = 10
    columns: int = 1
    rows: int = 1
    x_guides: list[int] | None = None
    y_guides: list[int] | None = None
    updated_at: str = ""


class SplitProfileStore:
    def __init__(self, program_data_dir: str | Path) -> None:
        self.program_data_dir = Path(program_data_dir)

    @property
    def path(self) -> Path:
        return self.program_data_dir / "tasks" / "split_profiles.json"

    def load_all(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return dict(json.loads(self.path.read_text(encoding="utf-8") or "{}"))
        except json.JSONDecodeError:
            return {}

    def load(self, source_image: str) -> SplitProfile | None:
        payload = self.load_all().get(source_image)
        if not isinstance(payload, dict):
            return None
        return SplitProfile(
            source_image=source_image,
            split_count=max(1, int(payload.get("split_count") or 10)),
            columns=max(1, int(payload.get("columns") or 1)),
            rows=max(1, int(payload.get("rows") or 1)),
            x_guides=[int(item) for item in (payload.get("x_guides") or [])],
            y_guides=[int(item) for item in (payload.get("y_guides") or [])],
            updated_at=str(payload.get("updated_at") or ""),
        )

    def save(self, profile: SplitProfile) -> None:
        all_profiles = self.load_all()
        all_profiles[profile.source_image] = {
            "split_count": max(1, int(profile.split_count or 1)),
            "columns": max(1, int(profile.columns or 1)),
            "rows": max(1, int(profile.rows or 1)),
            "x_guides": list(profile.x_guides or []),
            "y_guides": list(profile.y_guides or []),
            "updated_at": profile.updated_at or datetime.now().isoformat(timespec="seconds"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(all_profiles, ensure_ascii=False, indent=2), encoding="utf-8")
