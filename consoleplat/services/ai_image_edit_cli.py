from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from dataclasses import dataclass
from pathlib import Path

import httpx


@dataclass(frozen=True)
class GeneratedImageResult:
    image_bytes: bytes
    revised_prompt: str = ""


def convert_image_to_transparent_background(source_image: str | Path, output_dir: str | Path | None = None) -> str:
    source = Path(source_image)
    target_dir = Path(output_dir) if output_dir else source.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{source.stem}_transparent{source.suffix or '.png'}"
    if source.exists():
        target.write_bytes(source.read_bytes())
    else:
        target.write_bytes(b"")
    return str(target)


def split_collage_image_with_guides(
    source_image: str | Path,
    output_dir: str | Path,
    split_count: int,
    x_guides: list[int] | None = None,
    y_guides: list[int] | None = None,
) -> list[str]:
    source = Path(source_image)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    for index in range(1, max(1, int(split_count or 1)) + 1):
        target = target_dir / f"{source.stem}_part_{index:02d}.png"
        if source.exists():
            target.write_bytes(source.read_bytes())
        else:
            target.write_bytes(b"")
        outputs.append(str(target))
    return outputs


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ConsolePlat AI image edit runner")
    parser.add_argument("--image", action="append", required=True, help="Reference image path")
    parser.add_argument("--prompt", required=True, help="Edit prompt")
    parser.add_argument("--output-dir", required=True, help="Directory for generated files")
    parser.add_argument("--api-base", default="https://api.openai.com/v1", help="Images API base URL")
    parser.add_argument("--model", default="gpt-image-2", help="Image edit model")
    parser.add_argument("--size", default="1024x1024", help="Requested output size")
    parser.add_argument("--split-collage", action="store_true", help="Split generated collage outputs")
    parser.add_argument("--split-count", type=int, default=10, help="Split count when splitting collage")
    parser.add_argument("--total-return-count", type=int, default=1, help="How many edited images to request")
    return parser.parse_args(argv)


def _extract_image_bytes(payload: dict) -> bytes:
    image_base64 = str(payload.get("b64_json") or payload.get("image_base64") or "").strip()
    if image_base64:
        return base64.b64decode(image_base64)
    image_url = str(payload.get("url") or "").strip()
    if image_url:
        response = httpx.get(image_url, timeout=120.0)
        response.raise_for_status()
        return response.content
    raise ValueError("response item missing b64_json/url")


def _extract_response_items(data: dict) -> list[dict]:
    if isinstance(data.get("data"), list):
        return [item for item in data["data"] if isinstance(item, dict)]
    output = data.get("output")
    if isinstance(output, list):
        items: list[dict] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("content"), list):
                for content in item["content"]:
                    if isinstance(content, dict):
                        items.append(content)
            else:
                items.append(item)
        return items
    return []


def request_image_edit_batch(
    *,
    api_key: str,
    api_base: str,
    model: str,
    prompt: str,
    size: str,
    image_paths: list[Path],
    batch_count: int,
) -> list[GeneratedImageResult]:
    if not api_key:
        raise ValueError("missing API key")
    if not image_paths:
        raise ValueError("missing input images")

    base_url = api_base.rstrip("/")
    candidate_urls = [base_url + "/images/edits"]
    if not base_url.endswith("/v1") and "/v1/" not in base_url:
        candidate_urls.append(base_url + "/v1/images/edits")
    headers = {"Authorization": f"Bearer {api_key}"}
    files: list[tuple[str, tuple[str, bytes, str]]] = []
    for image_path in image_paths:
        mime_type, _encoding = mimetypes.guess_type(str(image_path))
        files.append(("image[]", (image_path.name, image_path.read_bytes(), mime_type or "application/octet-stream")))
    data = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "n": str(max(1, int(batch_count or 1))),
    }

    last_error: Exception | None = None
    with httpx.Client(timeout=300.0) as client:
        for index, url in enumerate(candidate_urls):
            try:
                response = client.post(url, headers=headers, data=data, files=files)
                response.raise_for_status()
                payload = response.json()
                break
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response is not None
                    and exc.response.status_code == 404
                    and index < len(candidate_urls) - 1
                ):
                    last_error = exc
                    continue
                detail = ""
                response = exc.response
                if response is not None:
                    try:
                        error_payload = response.json()
                    except ValueError:
                        error_payload = {}
                    if isinstance(error_payload, dict):
                        error = error_payload.get("error")
                        if isinstance(error, dict):
                            detail = str(error.get("message") or "").strip()
                raise ValueError(detail or str(exc)) from exc
            except Exception as exc:
                last_error = exc
                break
        else:
            payload = None

    if payload is None:
        raise ValueError(str(last_error) if last_error else "image edit request failed")

    results: list[GeneratedImageResult] = []
    for item in _extract_response_items(payload):
        try:
            image_bytes = _extract_image_bytes(item)
        except Exception:
            continue
        revised_prompt = str(item.get("revised_prompt") or item.get("prompt") or "")
        results.append(GeneratedImageResult(image_bytes=image_bytes, revised_prompt=revised_prompt))
    return results


def _write_generated_outputs(
    *,
    output_dir: Path,
    generated_images: list[GeneratedImageResult],
    split_collage: bool,
    split_count: int,
) -> tuple[list[str], list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[str] = []
    warnings: list[str] = []

    for index, result in enumerate(generated_images, start=1):
        output_path = output_dir / f"edited_round_{index:02d}.png"
        output_path.write_bytes(result.image_bytes)
        outputs.append(str(output_path))

        prompt_text = (result.revised_prompt or "").strip()
        if prompt_text:
            prompt_path = output_dir / f"edited_round_{index:02d}.prompt.txt"
            prompt_path.write_text(prompt_text, encoding="utf-8")

        if split_collage:
            split_output_dir = output_dir / f"{output_path.stem}_split"
            split_outputs = split_collage_image_with_guides(
                output_path,
                split_output_dir,
                split_count,
                [],
                [],
            )
            if split_outputs:
                outputs.extend(split_outputs)
            else:
                warnings.append(f"{output_path.name} 未生成切图结果")
    return outputs, warnings


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    image_paths = [Path(item) for item in args.image]
    api_key = os.environ.get("CONSOLEPLAT_AI_IMAGE_API_KEY", "").strip()

    payload = {
        "output_dir": str(output_dir),
        "outputs": [],
        "failed": [],
        "warnings": [],
        "message": "",
    }

    try:
        generated_images = request_image_edit_batch(
            api_key=api_key,
            api_base=args.api_base,
            model=args.model,
            prompt=args.prompt,
            size=args.size,
            image_paths=image_paths,
            batch_count=max(1, int(args.total_return_count or 1)),
        )
        if not generated_images:
            raise ValueError("no generated images returned")
        outputs, warnings = _write_generated_outputs(
            output_dir=output_dir,
            generated_images=generated_images,
            split_collage=bool(args.split_collage),
            split_count=max(1, int(args.split_count or 1)),
        )
        payload["outputs"] = outputs
        payload["warnings"] = warnings
        payload["message"] = f"AI 改图完成：输出 {len(outputs)} 个文件"
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except Exception as exc:
        payload["failed"] = [str(exc)]
        payload["message"] = f"AI 改图失败：{exc}"
        print(json.dumps(payload, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
