from __future__ import annotations

import json
import urllib.request


PATTERNS = [
    "IPAdapter",
    "Openpose",
    "OpenPose",
    "DWPreprocessor",
    "CannyEdgePreprocessor",
    "SAMLoader",
    "Impact",
    "ControlNet",
]


def main() -> None:
    with urllib.request.urlopen("http://127.0.0.1:8188/object_info", timeout=20) as response:
        data = json.loads(response.read())
    names = sorted(data.keys())
    for pattern in PATTERNS:
        matches = [name for name in names if pattern.lower() in name.lower()]
        print(f"[{pattern}] {len(matches)}")
        for name in matches[:20]:
            print(f"- {name}")


if __name__ == "__main__":
    main()
