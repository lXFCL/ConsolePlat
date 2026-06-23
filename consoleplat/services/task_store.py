from __future__ import annotations

import json
from pathlib import Path


class TaskStore:
    def __init__(self, program_data_dir: str | Path, name: str) -> None:
        self.program_data_dir = Path(program_data_dir)
        self.name = name

    @property
    def path(self) -> Path:
        return self.program_data_dir / "tasks" / f"{self.name}.json"

    def load(self) -> list[dict]:
        if not self.path.exists():
            return []
        text = self.path.read_text(encoding="utf-8")
        if not text.strip():
            return []
        try:
            return list(json.loads(text))
        except json.JSONDecodeError:
            return []

    def save(self, records: list[dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
