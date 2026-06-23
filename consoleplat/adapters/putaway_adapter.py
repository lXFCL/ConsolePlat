from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PutawayAdapter:
    project_dir: Path
    data_dir_path: Path
    log_dir_path: Path

    def launch_command(self) -> tuple[str, list[str], Path]:
        entry = self.project_dir / "browser_dom_automation.py"
        if entry.exists():
            return sys.executable, [str(entry)], self.project_dir
        return sys.executable, ["-c", "print('PutawayAiRobot placeholder launch')"], self.project_dir
