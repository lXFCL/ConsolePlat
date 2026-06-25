from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
from collections import deque
from dataclasses import dataclass
from math import ceil, sqrt
from pathlib import Path

import httpx
from PIL import Image


@dataclass(frozen=True)
class GeneratedImageResult:
    image_bytes: bytes
    revised_prompt: str = ""


def _estimate_border_color(image: Image.Image) -> tuple[int, int, int] | None:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    samples: list[tuple[int, int, int]] = []
    for x in range(width):
        for y in (0, height - 1):
            red, green, blue, alpha = pixels[x, y]
            if alpha > 200:
                samples.append((red, green, blue))
    for y in range(1, height - 1):
        for x in (0, width - 1):
            red, green, blue, alpha = pixels[x, y]
            if alpha > 200:
                samples.append((red, green, blue))
    if not samples:
        return None
    samples.sort()
    middle = len(samples) // 2
    return (
        samples[middle][0],
        samples[middle][1],
        samples[middle][2],
    )


def _background_candidate_mask(image: Image.Image) -> list[list[bool]]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    border_color = _estimate_border_color(rgba)
    mask: list[list[bool]] = [[False] * width for _ in range(height)]
    for y in range(height):
        for x in range(width):
            red, green, blue, alpha = pixels[x, y]
            if alpha <= 8:
                mask[y][x] = True
                continue
            spread = max(red, green, blue) - min(red, green, blue)
            near_white = red >= 244 and green >= 244 and blue >= 244 and spread < 24
            near_border = False
            if border_color is not None:
                br, bg, bb = border_color
                distance = ((red - br) ** 2 + (green - bg) ** 2 + (blue - bb) ** 2) ** 0.5
                near_border = distance <= 42.0
            mask[y][x] = near_white or near_border
    return mask


def _edge_connected_background(mask: list[list[bool]]) -> list[list[bool]]:
    height = len(mask)
    width = len(mask[0]) if height else 0
    connected: list[list[bool]] = [[False] * width for _ in range(height)]
    queue: deque[tuple[int, int]] = deque()
    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(1, height - 1):
        queue.append((0, y))
        queue.append((width - 1, y))
    while queue:
        x, y = queue.popleft()
        if x < 0 or y < 0 or x >= width or y >= height:
            continue
        if connected[y][x] or not mask[y][x]:
            continue
        connected[y][x] = True
        queue.append((x - 1, y))
        queue.append((x + 1, y))
        queue.append((x, y - 1))
        queue.append((x, y + 1))
    return connected


def convert_image_to_transparent_background(source_image: str | Path, output_dir: str | Path | None = None) -> str:
    source = Path(source_image)
    target_dir = Path(output_dir) if output_dir else source.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{source.stem}_transparent.png"
    image = Image.open(source).convert("RGBA")
    width, height = image.size
    pixels = image.load()
    background = _edge_connected_background(_background_candidate_mask(image))
    for y in range(height):
        for x in range(width):
            if background[y][x]:
                red, green, blue, _alpha = pixels[x, y]
                pixels[x, y] = (red, green, blue, 0)
    image.save(target)
    return str(target)


def _grid_boxes(width: int, height: int, split_count: int) -> list[tuple[int, int, int, int]]:
    columns = max(1, ceil(sqrt(max(1, split_count))))
    rows = max(1, ceil(max(1, split_count) / columns))
    boxes: list[tuple[int, int, int, int]] = []
    for row in range(rows):
        top = round(row * height / rows)
        bottom = round((row + 1) * height / rows)
        for column in range(columns):
            left = round(column * width / columns)
            right = round((column + 1) * width / columns)
            boxes.append((left, top, right, bottom))
    return boxes


def _guide_boxes(
    width: int,
    height: int,
    x_guides: list[int] | None,
    y_guides: list[int] | None,
) -> list[tuple[int, int, int, int]]:
    x_edges = [0] + sorted({int(value) for value in (x_guides or []) if 0 < int(value) < width}) + [width]
    y_edges = [0] + sorted({int(value) for value in (y_guides or []) if 0 < int(value) < height}) + [height]
    boxes: list[tuple[int, int, int, int]] = []
    for top, bottom in zip(y_edges, y_edges[1:]):
        for left, right in zip(x_edges, x_edges[1:]):
            boxes.append((left, top, right, bottom))
    return boxes


def _has_visible_pixels(image: Image.Image) -> bool:
    alpha = image.getchannel("A")
    return alpha.getbbox() is not None


def _extract_component_boxes(image: Image.Image) -> list[tuple[int, int, int, int]]:
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = rgba.load()
    visited: list[list[bool]] = [[False] * width for _ in range(height)]
    boxes: list[tuple[int, int, int, int]] = []
    for y in range(height):
        for x in range(width):
            if visited[y][x] or pixels[x, y][3] <= 8:
                continue
            queue: deque[tuple[int, int]] = deque([(x, y)])
            visited[y][x] = True
            min_x = max_x = x
            min_y = max_y = y
            while queue:
                current_x, current_y = queue.popleft()
                min_x = min(min_x, current_x)
                max_x = max(max_x, current_x)
                min_y = min(min_y, current_y)
                max_y = max(max_y, current_y)
                for next_x, next_y in (
                    (current_x - 1, current_y),
                    (current_x + 1, current_y),
                    (current_x, current_y - 1),
                    (current_x, current_y + 1),
                ):
                    if next_x < 0 or next_y < 0 or next_x >= width or next_y >= height:
                        continue
                    if visited[next_y][next_x] or pixels[next_x, next_y][3] <= 8:
                        continue
                    visited[next_y][next_x] = True
                    queue.append((next_x, next_y))
            boxes.append((min_x, min_y, max_x + 1, max_y + 1))
    boxes.sort(key=lambda item: (item[1], item[0]))
    return boxes


def _filter_component_boxes(
    boxes: list[tuple[int, int, int, int]],
    *,
    image_width: int,
    image_height: int,
    requested_count: int,
) -> list[tuple[int, int, int, int]]:
    if not boxes:
        return []
    original_count = len(boxes)
    scored: list[tuple[tuple[int, int, int, int], int, int, int]] = []
    min_width = max(12, int(image_width * 0.08))
    min_height = max(12, int(image_height * 0.08))
    min_area = max(256, int(image_width * image_height * 0.015))
    for box in boxes:
        left, top, right, bottom = box
        width = right - left
        height = bottom - top
        area = width * height
        if width < min_width or height < min_height or area < min_area:
            continue
        scored.append((box, area, width, height))
    if scored:
        scored.sort(key=lambda item: (-item[1], item[0][1], item[0][0]))
        kept = [item[0] for item in scored]
        kept.sort(key=lambda item: (item[1], item[0]))
        if len(kept) == 1 and original_count == 1 and requested_count > 1:
            return []
        return kept[: max(1, int(requested_count or 1))]
    boxes.sort(key=lambda item: ((item[2] - item[0]) * (item[3] - item[1]), item[1], item[0]), reverse=True)
    fallback = boxes[: max(1, int(requested_count or 1))]
    fallback.sort(key=lambda item: (item[1], item[0]))
    return fallback


def derive_split_boxes(
    image: Image.Image,
    split_count: int,
    x_guides: list[int] | None = None,
    y_guides: list[int] | None = None,
    *,
    enforce_exact_count: bool = False,
) -> list[tuple[int, int, int, int]]:
    width, height = image.size
    requested_count = max(1, int(split_count or 1))
    boxes = _guide_boxes(width, height, x_guides, y_guides) if (x_guides or y_guides) else []
    if not boxes:
        boxes = _filter_component_boxes(
            _extract_component_boxes(image),
            image_width=width,
            image_height=height,
            requested_count=requested_count,
        )
    if not boxes or (enforce_exact_count and len(boxes) != requested_count):
        boxes = _grid_boxes(width, height, split_count)
    return boxes[:requested_count]


def _crop_and_save_part(image: Image.Image, box: tuple[int, int, int, int], target: Path) -> str | None:
    cropped = image.crop(box)
    alpha_box = cropped.getchannel("A").getbbox()
    if alpha_box is None:
        return None
    result = cropped.crop(alpha_box)
    target.parent.mkdir(parents=True, exist_ok=True)
    result.save(target)
    return str(target)


def split_collage_image_with_guides(
    source_image: str | Path,
    output_dir: str | Path,
    split_count: int,
    x_guides: list[int] | None = None,
    y_guides: list[int] | None = None,
    original_image: str | Path | None = None,
    drop_first: bool = False,
) -> list[str]:
    source = Path(source_image)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    image = Image.open(source).convert("RGBA")
    outputs: list[str] = []
    reference_image = image
    if original_image:
        original_path = Path(original_image)
        if original_path.exists():
            reference_image = Image.open(original_path).convert("RGBA")
    boxes = derive_split_boxes(
        reference_image,
        split_count,
        x_guides,
        y_guides,
        enforce_exact_count=original_image is not None,
    )
    selected_boxes = boxes[: max(1, int(split_count or 1))]
    if drop_first and selected_boxes:
        selected_boxes = selected_boxes[1:]
    for index, box in enumerate(selected_boxes, start=1):
        target = target_dir / f"{source.stem}_part_{index:02d}.png"
        saved = _crop_and_save_part(image, box, target)
        if saved is not None:
            outputs.append(saved)
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


def _truncate_preview(text: str, limit: int = 280) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _response_preview(response: httpx.Response | None) -> str:
    if response is None:
        return ""
    try:
        preview = response.text
    except Exception:
        try:
            preview = response.content.decode("utf-8", errors="replace")
        except Exception:
            preview = ""
    return _truncate_preview(preview)


def _extract_error_detail(response: httpx.Response | None) -> str:
    if response is None:
        return ""
    try:
        error_payload = response.json()
    except ValueError:
        return ""
    if not isinstance(error_payload, dict):
        return ""
    error = error_payload.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "").strip()
    message = error_payload.get("message")
    return str(message or "").strip()


def _format_http_status_error(exc: httpx.HTTPStatusError, *, url: str) -> str:
    response = exc.response
    detail = _extract_error_detail(response)
    status = response.status_code if response is not None else "unknown"
    content_type = ""
    if response is not None:
        content_type = str(response.headers.get("content-type") or "").strip()
    preview = _response_preview(response)

    parts = [
        f"AI 改图请求失败",
        f"url={url}",
        f"status={status}",
    ]
    if content_type:
        parts.append(f"content-type={content_type}")
    if detail:
        parts.append(f"detail={detail}")
    if preview:
        parts.append(f"body={preview}")
    if not detail and not preview:
        fallback = str(exc).strip()
        if fallback:
            parts.append(f"error={fallback}")
    return "; ".join(parts)


def _format_request_exception(exc: Exception, *, url: str) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    return f"AI 改图请求异常; url={url}; error={message}"


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

    last_error_message = ""
    payload: dict | None = None
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
                    last_error_message = _format_http_status_error(exc, url=url)
                    continue
                raise ValueError(_format_http_status_error(exc, url=url)) from exc
            except Exception as exc:
                last_error_message = _format_request_exception(exc, url=url)
                break

    if payload is None:
        raise ValueError(last_error_message or "image edit request failed")

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
