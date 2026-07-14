from __future__ import annotations

import sys
from pathlib import Path

import pytest

from consoleplat import paths
from consoleplat.adapters.applygoods_adapter import ApplyGoodsAdapter
from consoleplat.adapters.putaway_adapter import PutawayAdapter
from consoleplat.runtime import cli_command, script_command


def test_cli_command_uses_module_in_source_mode(monkeypatch):
    monkeypatch.delattr(sys, "frozen", raising=False)

    program, args = cli_command("monitor-fetch", "--close-monitor-pages")

    assert program == sys.executable
    assert args == ["-m", "consoleplat.services.monitor_fetch_cli", "--close-monitor-pages"]


def test_commands_reenter_executable_in_frozen_mode(monkeypatch):
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    _, cli_args = cli_command("sendgoods-export")
    _, script_args = script_command(Path("modules/ApplyGoods/main.py"), "--test")

    assert cli_args == ["--consoleplat-cli", "sendgoods-export"]
    assert script_args == ["--consoleplat-script", "modules\\ApplyGoods\\main.py", "--test"]


def test_project_root_is_executable_directory_when_frozen(monkeypatch, tmp_path):
    executable = tmp_path / "ConsolePlat.exe"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))

    assert paths.project_root() == tmp_path


def test_unknown_cli_command_is_rejected():
    with pytest.raises(ValueError, match="未知 ConsolePlat 子命令"):
        cli_command("missing")


def test_missing_external_entries_still_use_frozen_script_protocol(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    apply_program, apply_args, _ = ApplyGoodsAdapter(tmp_path / "ApplyGoods").launch_command()
    putaway_program, putaway_args, _ = PutawayAdapter(
        tmp_path / "PutawayAiRobot",
        tmp_path / "data",
        tmp_path / "logs",
    ).launch_command()

    assert apply_program == sys.executable
    assert apply_args[:2] == ["--consoleplat-script", str(tmp_path / "ApplyGoods" / "main.py")]
    assert putaway_program == sys.executable
    assert putaway_args[:2] == [
        "--consoleplat-script",
        str(tmp_path / "PutawayAiRobot" / "browser_dom_automation.py"),
    ]
