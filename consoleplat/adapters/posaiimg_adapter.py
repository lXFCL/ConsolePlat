from __future__ import annotations

import json
import sys
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LocalImageJob:
    prefix: str = "BO"
    start_number: int = 1421
    count: int = 10
    style_name: str = "仿油彩名画风格竖版印花"
    steps: int = 28
    width: int = 832
    height: int = 1216
    seed: int = 2026061702
    test_mode: bool = True
    auto_start_comfyui: bool = False
    keep_comfyui: bool = True
    gallery_root: str = "E:/1PythonProject/PosAiImg/图库"
    mockup_root: str = "E:/1PythonProject/PosAiImg/批量贴图结果"
    xlsx_root: str = "E:/1PythonProject/PosAiImg/衣物对应的xlsx"


@dataclass(frozen=True)
class LocalImageSummary:
    ok: bool
    batch_name: str = ""
    print_dir: str = ""
    raw_dir: str = ""
    mockup_dir: str = ""
    xlsx_path: str = ""
    prompt_path: str = ""
    product_count: int = 0
    message: str = ""


@dataclass(frozen=True)
class AIEditJob:
    images: list[Path]
    prompt: str
    api_key: str = ""
    api_base: str = "https://api.openai.com/v1"
    model: str = "gpt-image-2"
    output_dir: Path | None = None
    size: str = "1024x1024"
    split_collage: bool = False
    split_count: int = 10
    total_return_count: int = 10
    prefix: str = "BO"
    start_number: int = 1421
    test_mode: bool = True
    gallery_root: str = "E:/1PythonProject/PosAiImg/图库"
    mockup_root: str = "E:/1PythonProject/PosAiImg/批量贴图结果"
    xlsx_root: str = "E:/1PythonProject/PosAiImg/衣物对应的xlsx"


@dataclass(frozen=True)
class AIEditSummary:
    ok: bool
    output_dir: str = ""
    outputs: list[str] | None = None
    failed: list[str] | None = None
    warnings: list[str] | None = None
    message: str = ""


@dataclass(frozen=True)
class PosAiImgAdapter:
    project_dir: Path = Path("E:/1PythonProject/PosAiImg")
    conda_env: str = "posai-img"

    def local_image_command(self, job: LocalImageJob) -> tuple[str, list[str], Path]:
        if job.test_mode:
            return self._test_mode_command(job)
        return self._complete_mode_command(job)

    def ai_edit_command(self, job: AIEditJob) -> tuple[str, list[str], Path]:
        output_dir = job.output_dir or (self.project_dir / "_consoleplat_ai_edits")
        args = [
            "-u",
            "-m",
            "consoleplat.services.ai_image_edit_cli",
            "--prompt",
            job.prompt,
            "--output-dir",
            str(output_dir),
            "--api-base",
            job.api_base,
            "--model",
            job.model,
            "--size",
            job.size,
        ]
        if job.split_collage:
            args.extend(["--split-collage", "--split-count", str(job.split_count)])
        args.extend(["--total-return-count", str(max(1, int(job.total_return_count or 1)))])
        for image in job.images:
            args.extend(["--image", str(image)])
        return sys.executable, args, Path("E:/1PythonProject/ConsolePlat")

    def _test_mode_command(self, job: LocalImageJob) -> tuple[str, list[str], Path]:
        output_dir = self.project_dir / "_consoleplat_tests" / job.prefix / f"{job.style_name}_{job.count}张"
        args = [
            "run",
            "--no-capture-output",
            "-n",
            self.conda_env,
            "python",
            "-u",
            "tools/comfy_print_batch.py",
            "--output-dir",
            str(output_dir),
            "--count",
            str(job.count),
            "--steps",
            str(job.steps),
            "--width",
            "1024",
            "--height",
            "1024",
            "--seed",
            str(job.seed),
        ]
        if job.auto_start_comfyui:
            args.append("--auto-start-comfyui")
        if job.keep_comfyui:
            args.append("--keep-comfyui")
        return "conda", args, self.project_dir

    def _complete_mode_command(self, job: LocalImageJob) -> tuple[str, list[str], Path]:
        args = [
            "run",
            "--no-capture-output",
            "-n",
            self.conda_env,
            "python",
            "-u",
            "tools/generate_bo_painterly_master_batch.py",
            "--prefix",
            job.prefix,
            "--start",
            str(job.start_number),
            "--count",
            str(job.count),
            "--steps",
            str(job.steps),
            "--width",
            str(job.width),
            "--height",
            str(job.height),
            "--seed",
            str(job.seed),
        ]
        if job.auto_start_comfyui:
            args.append("--auto-start-comfyui")
        if job.keep_comfyui:
            args.append("--keep-comfyui")
        return "conda", args, self.project_dir

    def parse_stdout_payload(self, stdout: str) -> dict[str, Any]:
        text = (stdout or "").strip()
        if not text:
            return {}
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                payload = json.loads(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("batch"):
                return payload
        return {}

    def parse_finished_payload(self, payload: dict[str, Any]) -> LocalImageSummary:
        batch = str(payload.get("batch") or "")
        product_count = int(payload.get("product_count") or 0)
        return LocalImageSummary(
            ok=bool(batch),
            batch_name=batch,
            print_dir=str(payload.get("print_dir") or ""),
            raw_dir=str(payload.get("raw_dir") or ""),
            mockup_dir=str(payload.get("mockup_dir") or ""),
            xlsx_path=str(payload.get("xlsx") or ""),
            prompt_path=str(payload.get("prompt") or ""),
            product_count=product_count,
            message=(f"本地生图完成：{batch}，产品图 {product_count} 张" if batch else "未读取到有效批次结果"),
        )

    def parse_finished_result(self, stdout: str, job: LocalImageJob) -> LocalImageSummary:
        payload = self.parse_stdout_payload(stdout)
        if payload:
            return self.parse_finished_payload(payload)
        if job.test_mode:
            return self._parse_test_mode_result(stdout)
        return LocalImageSummary(ok=False, message="未读取到有效批次结果")

    def parse_ai_edit_result(self, stdout: str) -> AIEditSummary:
        payload = self._parse_ai_edit_payload(stdout)
        if not payload:
            return AIEditSummary(ok=False, outputs=[], failed=[], message="未读取到 AI 改图结果")
        outputs = [str(item) for item in (payload.get("outputs") or [])]
        failed = [str(item) for item in (payload.get("failed") or [])]
        warnings = [str(item) for item in (payload.get("warnings") or [])]
        ok = bool(outputs) and not failed
        if ok and warnings:
            message = f"AI 改图完成：成功 {len(outputs)} 张，警告 {len(warnings)} 条"
        elif ok:
            message = f"AI 改图完成：成功 {len(outputs)} 张，失败 {len(failed)} 张"
        else:
            detail = failed[0] if failed else ""
            message = f"AI 改图失败：{detail}" if detail else "AI 改图未生成有效图片"
        return AIEditSummary(
            ok=ok,
            output_dir=str(payload.get("output_dir") or ""),
            outputs=outputs,
            failed=failed,
            warnings=warnings,
            message=message,
        )

    def _parse_ai_edit_payload(self, stdout: str) -> dict[str, Any]:
        text = (stdout or "").strip()
        if not text:
            return {}
        for index, char in enumerate(text):
            if char != "{":
                continue
            try:
                payload = json.loads(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and "outputs" in payload:
                return payload
        return {}

    def _parse_test_mode_result(self, stdout: str) -> LocalImageSummary:
        match = re.search(r"Done\. Exported\s+(\d+)\s+image\(s\)\s+to\s+(.+)", stdout or "")
        if not match:
            return LocalImageSummary(ok=False, message="测试模式已结束，但没有识别到导出结果")
        product_count = int(match.group(1))
        print_dir = match.group(2).strip()
        return LocalImageSummary(
            ok=True,
            print_dir=print_dir,
            product_count=product_count,
            message=f"测试模式完成：已导出 {product_count} 张印花，目录 {print_dir}",
        )
