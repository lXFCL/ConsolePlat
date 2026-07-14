from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--consoleplat-cli":
        from consoleplat.runtime import run_cli

        return run_cli(sys.argv[2], sys.argv[3:])
    if len(sys.argv) >= 3 and sys.argv[1] == "--consoleplat-script":
        from consoleplat.runtime import run_script

        return run_script(sys.argv[2], sys.argv[3:])

    from consoleplat.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
