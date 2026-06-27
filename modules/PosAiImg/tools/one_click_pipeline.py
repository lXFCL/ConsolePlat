from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
COMFY_DIR = ROOT / "ComfyUI"
PROMPTS_FILE = ROOT / "印花提示词.txt"
PRINT_DIR = ROOT / "印花图"
TRANSPARENT_PRINT_DIR = ROOT / "印花图_透明底"
MODEL_DIR = ROOT / "去印花结果"
OUTPUT_DIR = ROOT / "批量贴图结果"
LOG_DIR = ROOT / "logs"
SERVER = "http://127.0.0.1:8188"


def is_server_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{SERVER}/system_stats", timeout=3) as resp:
            json.loads(resp.read().decode("utf-8"))
        return True
    except Exception:
        return False


def wait_for_server(timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if is_server_ready():
            return
        time.sleep(2)
    raise TimeoutError(f"ComfyUI 未在 {timeout_seconds} 秒内启动：{SERVER}")


def run_step(title: str, command: list[str], cwd: Path) -> None:
    print(f"\n=== {title} ===", flush=True)
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def start_comfyui(timeout_seconds: int) -> subprocess.Popen | None:
    if is_server_ready():
        print(f"ComfyUI 已在运行：{SERVER}")
        return None

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "one_click_comfyui.log"
    log_file = log_path.open("a", encoding="utf-8", errors="replace")
    print(f"正在启动 ComfyUI，日志：{log_path}")
    process = subprocess.Popen(
        [
            "conda",
            "run",
            "-n",
            "posai-comfy",
            "python",
            "main.py",
            "--listen",
            "127.0.0.1",
            "--port",
            "8188",
        ],
        cwd=COMFY_DIR,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    wait_for_server(timeout_seconds)
    print("ComfyUI 已就绪。")
    return process


def stop_comfyui(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if process.poll() is not None:
        return
    print("\n正在关闭本次自动启动的 ComfyUI...")
    process.terminate()
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        process.kill()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="一键生成印花、去白底并批量贴到模特图。")
    parser.add_argument("--prompts", type=Path, default=PROMPTS_FILE)
    parser.add_argument("--model-dir", type=Path, default=MODEL_DIR)
    parser.add_argument("--print-dir", type=Path, default=PRINT_DIR)
    parser.add_argument("--transparent-dir", type=Path, default=TRANSPARENT_PRINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--count", type=int, default=1, help="每条提示词生成几张印花。")
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--width", type=int, default=1024, help="生成印花宽度。")
    parser.add_argument("--height", type=int, default=1024, help="生成印花高度。")
    parser.add_argument("--seed", type=int, default=20260609)
    parser.add_argument("--bg-threshold", type=int, default=244)
    parser.add_argument("--placement-width", type=float, default=0.30, help="贴图宽度占模特图宽度比例。")
    parser.add_argument("--center-x", type=float, default=0.50)
    parser.add_argument("--center-y", type=float, default=0.43)
    parser.add_argument("--opacity", type=float, default=0.92)
    parser.add_argument("--rotation", type=float, default=0.0)
    parser.add_argument("--shadow-strength", type=float, default=0.32)
    parser.add_argument("--wave-strength", type=float, default=0.012)
    parser.add_argument("--comfy-timeout", type=int, default=180)
    parser.add_argument("--keep-comfyui", action="store_true", help="流程结束后保留由本脚本启动的 ComfyUI。")
    parser.add_argument("--skip-generate", action="store_true", help="跳过 AI 生成，只处理已有印花。")
    parser.add_argument("--skip-bg", action="store_true", help="跳过去白底，直接用 print-dir 贴图。")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comfy_process: subprocess.Popen | None = None

    try:
        if not args.model_dir.exists():
            raise FileNotFoundError(f"模特图目录不存在：{args.model_dir}")

        if not args.skip_generate:
            if not args.prompts.exists():
                raise FileNotFoundError(f"提示词文件不存在：{args.prompts}")
            comfy_process = start_comfyui(args.comfy_timeout)
            run_step(
                "1/3 批量生成透明底印花",
                [
                    "conda",
                    "run",
                    "-n",
                    "posai-comfy",
                    "python",
                    str(TOOLS_DIR / "comfy_print_batch.py"),
                    "--prompts",
                    str(args.prompts),
                    "--output-dir",
                    str(args.transparent_dir),
                    "--count",
                    str(args.count),
                    "--steps",
                    str(args.steps),
                    "--width",
                    str(args.width),
                    "--height",
                    str(args.height),
                    "--seed",
                    str(args.seed),
                    "--bg-threshold",
                    str(args.bg_threshold),
                ],
                ROOT,
            )
            compose_print_dir = args.transparent_dir
        else:
            print("跳过 AI 生成，使用已有印花。")
            compose_print_dir = args.print_dir
            if not args.skip_bg:
                run_step(
                    "2/3 已有印花去白底/转透明底",
                    [
                        "conda",
                        "run",
                        "-n",
                        "posai-img",
                        "python",
                        str(TOOLS_DIR / "remove_print_bg.py"),
                        "--input-dir",
                        str(args.print_dir),
                        "--output-dir",
                        str(args.transparent_dir),
                        "--threshold",
                        str(args.bg_threshold),
                    ],
                    ROOT,
                )
                compose_print_dir = args.transparent_dir
            else:
                print("跳过去白底，直接使用原印花目录贴图。")

        run_step(
            "3/3 批量贴到模特图",
            [
                "conda",
                "run",
                "-n",
                "posai-img",
                "python",
                str(TOOLS_DIR / "tshirt_print_tool.py"),
                "--batch",
                "--model-dir",
                str(args.model_dir),
                "--print-dir",
                str(compose_print_dir),
                "--output-dir",
                str(args.output_dir),
                "--center-x",
                str(args.center_x),
                "--center-y",
                str(args.center_y),
                "--width",
                str(args.placement_width),
                "--opacity",
                str(args.opacity),
                "--rotation",
                str(args.rotation),
                "--shadow-strength",
                str(args.shadow_strength),
                "--wave-strength",
                str(args.wave_strength),
            ],
            ROOT,
        )

        print(f"\n完成：结果已输出到 {args.output_dir}")
        return 0
    except Exception as exc:
        print(f"\n失败：{exc}", file=sys.stderr)
        return 1
    finally:
        if comfy_process is not None and not args.keep_comfyui:
            stop_comfyui(comfy_process)


if __name__ == "__main__":
    raise SystemExit(main())
