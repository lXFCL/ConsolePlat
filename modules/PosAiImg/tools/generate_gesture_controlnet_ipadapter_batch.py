from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))

import comfy_print_batch  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
COMFY = ROOT / "ComfyUI"
COMFY_INPUT = COMFY / "input"
OUT_ROOT = ROOT / "印花图_透明底"
REFERENCE = ROOT / "爆款印花知识库" / "爆款1" / "3636a61b5561417c830a0982d6bf42da-goods.jpeg"
ALT_REFERENCE = (
    ROOT
    / "印花图_透明底"
    / "康康以下克上正面黑白手势_final_2026-06-13"
    / "康康以下克上正面黑白手势.png"
)
CHECKPOINT = "RealVisXL_V5.0_fp16.safetensors"


@dataclass(frozen=True)
class GestureSpec:
    key: str
    name: str
    prompt: str
    control_kind: str


def specs() -> list[GestureSpec]:
    return [
        GestureSpec(
            "tiger_hand_seal",
            "Tiger hand seal inspired gesture",
            "two front-facing realistic hands forming a sharp tiger hand seal inspired gesture, both index fingers vertical together in the center, fingers interlocked below, compact symmetrical ninja hand seal structure",
            "tiger",
        ),
        GestureSpec(
            "snake_hand_seal",
            "Snake hand seal inspired gesture",
            "two front-facing realistic hands forming a snake hand seal inspired gesture, fingers interlaced tightly, knuckles and rings visible, compact horizontal interlocked structure",
            "snake",
        ),
        GestureSpec(
            "index_finger_up",
            "One index finger pointing upward",
            "one front-facing realistic hand with index finger pointing straight upward, other fingers folded, strong vertical streetwear hand sign, rings visible",
            "point_up",
        ),
        GestureSpec(
            "finger_frame",
            "Two hands finger frame",
            "two front-facing realistic hands forming a rectangular finger frame, thumbs horizontal and index fingers vertical, clean centered high street gesture",
            "frame",
        ),
        GestureSpec(
            "ok_gesture",
            "OK gesture front view",
            "one front-facing realistic hand making an OK gesture, thumb and index finger form a circle, other three fingers raised, rings and bracelet visible",
            "ok",
        ),
    ]


def safe_specs() -> list[GestureSpec]:
    return [
        GestureSpec(
            "tiger_hand_seal",
            "Tiger hand seal inspired gesture",
            "cropped disembodied hands only, two front-facing realistic hands forming a sharp tiger hand seal inspired gesture, both index fingers vertical together in the center, fingers interlocked below, compact symmetrical ninja hand seal structure",
            "tiger",
        ),
        GestureSpec(
            "snake_hand_seal",
            "Snake hand seal inspired gesture",
            "cropped disembodied hands only, two front-facing realistic hands forming a snake hand seal inspired gesture, fingers interlaced tightly, knuckles and rings visible, compact horizontal interlocked structure",
            "snake",
        ),
        GestureSpec(
            "double_index_up",
            "Two index fingers pointing upward",
            "cropped disembodied hands only, two separate front-facing realistic hands, both index fingers pointing straight upward, all other fingers folded, strong symmetrical streetwear hand sign",
            "point_up",
        ),
        GestureSpec(
            "crossed_wrist_prayer",
            "Crossed wrist prayer-like hand sign",
            "cropped disembodied hands only, two front-facing realistic hands crossing at the wrists, palms close together, jewelry on wrists, compact high street gesture print",
            "tiger",
        ),
        GestureSpec(
            "ok_gesture",
            "OK gesture front view",
            "cropped disembodied hand only, one front-facing realistic hand making an OK gesture, thumb and index finger form a circle, other three fingers raised, rings and bracelet visible",
            "ok",
        ),
    ]


def print_friendly_specs() -> list[GestureSpec]:
    return [
        GestureSpec(
            "front_prayer_seal",
            "Front prayer seal",
            "two cropped front-facing hands only, palms pressed together in a compact prayer hand seal, short clean wrists, centered symmetrical t-shirt print, no long arms",
            "tiger",
        ),
        GestureSpec(
            "interlocked_fingers",
            "Interlocked fingers",
            "two cropped front-facing hands only, fingers interlocked together, compact knuckle pattern, short clean wrists, centered t-shirt print, no long arms",
            "snake",
        ),
        GestureSpec(
            "double_index_up",
            "Double index up",
            "two cropped front-facing hands only, both index fingers pointing upward, other fingers folded, short clean wrists, symmetrical hand sign print, no face no body",
            "point_up",
        ),
        GestureSpec(
            "finger_frame_compact",
            "Compact finger frame",
            "two cropped front-facing hands only forming a small rectangular finger frame, thumbs horizontal and index fingers vertical, short clean wrists, centered print",
            "frame",
        ),
        GestureSpec(
            "ok_front",
            "OK front hand",
            "one cropped front-facing hand only making an OK gesture, thumb and index finger form a clean circle, other fingers raised, short clean wrist, centered print",
            "ok",
        ),
    ]


STYLE = (
    "isolated disembodied hands only, wrists cut off cleanly, front-facing hands, "
    "black white gray realistic streetwear t-shirt print graphic, "
    "high contrast monochrome silkscreen print, realistic but clean hand anatomy, detailed knuckles and fingernails, "
    "a few simple silver rings, subtle bracelet detail, not too much jewelry, "
    "centered composition on pure white background, print asset only, no body, no face, "
    "no person, no arms beyond very short wrists, no clothing, no shirt, no text, no logo, "
    "no watermark, no border, no rectangle, no circular decoration, no mandala, no anime character, "
    "clean printable silhouette, not creepy, not horror, not surreal"
)

NEGATIVE = (
    "full person, portrait, human face, face, eyes, nose, mouth, head, hair, torso, chest, shoulders, arms, sleeve, shirt, t-shirt, clothing, mannequin, "
    "anime, cartoon, illustration, flat vector, official character, Naruto character, Kakashi, "
    "text, logo, watermark, frame, border, circle, mandala, background scene, black background, "
    "extra fingers, missing fingers, fused fingers, mutated hands, extra hands, cropped fingertips, "
    "low quality, blurry, colored image, strong color tint"
)


def http_json(method: str, url: str, payload: dict | None = None, timeout: int = 300) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def wait_server(timeout_seconds: int = 120) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            http_json("GET", "http://127.0.0.1:8188/system_stats", timeout=5)
            return
        except Exception:
            time.sleep(2)
    raise RuntimeError("ComfyUI is not available at http://127.0.0.1:8188")


def queue_prompt(workflow: dict) -> str:
    result = http_json("POST", "http://127.0.0.1:8188/prompt", {"prompt": workflow}, timeout=60)
    return result["prompt_id"]


def wait_prompt(prompt_id: str, timeout_seconds: int) -> dict:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        history = http_json("GET", f"http://127.0.0.1:8188/history/{prompt_id}", timeout=30)
        if prompt_id in history:
            return history[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"Timed out waiting for prompt {prompt_id}")


def copy_to_input(source: Path, name: str) -> str:
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    target = COMFY_INPUT / name
    if not target.exists() or target.stat().st_size != source.stat().st_size:
        shutil.copy2(source, target)
    return name


def line(draw: ImageDraw.ImageDraw, points: list[tuple[float, float]], width: int = 13) -> None:
    draw.line(points, fill=(255, 255, 255), width=width, joint="curve")
    r = max(3, width // 3)
    for x, y in points:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255))


def draw_hand(draw: ImageDraw.ImageDraw, wrist: tuple[float, float], palm: tuple[float, float], fingers: list[float]) -> None:
    line(draw, [wrist, palm], width=16)
    base_x, base_y = palm
    for angle_deg in fingers:
        angle = math.radians(angle_deg)
        length = 170
        mid = (base_x + math.cos(angle) * length * 0.55, base_y + math.sin(angle) * length * 0.55)
        tip = (base_x + math.cos(angle) * length, base_y + math.sin(angle) * length)
        line(draw, [palm, mid, tip], width=12)


def make_control(kind: str, path: Path, size: int = 896) -> None:
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = size / 2
    if kind == "tiger":
        line(draw, [(350, 760), (395, 560), (420, 420), (430, 245)], 13)
        line(draw, [(546, 760), (505, 560), (476, 420), (466, 245)], 13)
        line(draw, [(395, 560), (455, 585), (505, 560)], 12)
        line(draw, [(380, 640), (455, 680), (520, 640)], 12)
        line(draw, [(420, 420), (448, 515), (476, 420)], 12)
    elif kind == "snake":
        for y in (420, 485, 550):
            line(draw, [(310, y), (390, y + 25), (500, y - 20), (585, y + 10)], 13)
            line(draw, [(585, y + 38), (500, y + 12), (395, y + 58), (310, y + 28)], 11)
        line(draw, [(330, 720), (390, 600), (505, 600), (565, 720)], 16)
    elif kind == "point_up":
        draw_hand(draw, (cx, 800), (cx, 610), [-90, -28, 0, 28])
        line(draw, [(cx, 610), (cx, 430), (cx, 220)], 17)
    elif kind == "frame":
        line(draw, [(250, 725), (300, 555), (300, 300)], 16)
        line(draw, [(646, 725), (596, 555), (596, 300)], 16)
        line(draw, [(300, 555), (448, 555), (596, 555)], 16)
        line(draw, [(300, 300), (360, 300)], 14)
        line(draw, [(596, 300), (536, 300)], 14)
        line(draw, [(315, 650), (420, 665)], 11)
        line(draw, [(581, 650), (476, 665)], 11)
    elif kind == "ok":
        draw_hand(draw, (cx, 800), (cx, 610), [-100, -70, -40])
        draw.ellipse((350, 430, 515, 595), outline=(255, 255, 255), width=16)
        line(draw, [(cx, 610), (520, 500), (610, 430)], 13)
    else:
        raise ValueError(kind)
    img = img.filter(ImageFilter.GaussianBlur(0.3))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def make_canny_like_control(kind: str, path: Path, size: int = 896) -> None:
    img = Image.new("RGB", (size, size), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    if kind == "tiger":
        draw.rounded_rectangle((315, 365, 435, 720), radius=46, outline=(255, 255, 255), width=9)
        draw.rounded_rectangle((461, 365, 581, 720), radius=46, outline=(255, 255, 255), width=9)
        for x in (352, 386, 420, 480, 514, 548):
            draw.rounded_rectangle((x - 14, 210, x + 14, 445), radius=16, outline=(255, 255, 255), width=8)
        draw.arc((332, 455, 564, 690), 200, 340, fill=(255, 255, 255), width=10)
    elif kind == "snake":
        draw.rounded_rectangle((250, 390, 646, 640), radius=52, outline=(255, 255, 255), width=10)
        for y in (425, 485, 545):
            draw.arc((280, y - 55, 616, y + 72), 8, 175, fill=(255, 255, 255), width=9)
            draw.arc((280, y - 18, 616, y + 98), 188, 355, fill=(255, 255, 255), width=9)
        draw.rounded_rectangle((330, 610, 565, 770), radius=36, outline=(255, 255, 255), width=9)
    elif kind == "point_up":
        draw.rounded_rectangle((380, 420, 516, 755), radius=48, outline=(255, 255, 255), width=10)
        draw.rounded_rectangle((421, 145, 475, 470), radius=25, outline=(255, 255, 255), width=10)
        for x in (365, 505, 545):
            draw.rounded_rectangle((x - 20, 495, x + 18, 665), radius=20, outline=(255, 255, 255), width=8)
    elif kind == "frame":
        draw.rounded_rectangle((235, 260, 360, 730), radius=42, outline=(255, 255, 255), width=10)
        draw.rounded_rectangle((536, 260, 661, 730), radius=42, outline=(255, 255, 255), width=10)
        draw.rounded_rectangle((300, 265, 596, 360), radius=36, outline=(255, 255, 255), width=10)
        draw.rounded_rectangle((300, 535, 596, 630), radius=36, outline=(255, 255, 255), width=10)
    elif kind == "ok":
        draw.rounded_rectangle((360, 430, 540, 750), radius=56, outline=(255, 255, 255), width=10)
        draw.ellipse((340, 320, 510, 490), outline=(255, 255, 255), width=12)
        for x, top in ((450, 135), (510, 160), (565, 210)):
            draw.rounded_rectangle((x - 22, top, x + 22, 480), radius=22, outline=(255, 255, 255), width=9)
        draw.rounded_rectangle((515, 405, 680, 465), radius=26, outline=(255, 255, 255), width=9)
    else:
        raise ValueError(kind)
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def make_workflow(
    prompt: str,
    seed: int,
    reference_image: str,
    control_image: str,
    control_model: str,
    width: int,
    height: int,
    steps: int,
    ip_weight: float,
    control_strength: float,
) -> dict:
    positive = f"{prompt}, {STYLE}"
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "2": {"class_type": "IPAdapterUnifiedLoader", "inputs": {"model": ["1", 0], "preset": "PLUS (high strength)"}},
        "3": {"class_type": "LoadImage", "inputs": {"image": reference_image}},
        "4": {
            "class_type": "IPAdapterAdvanced",
            "inputs": {
                "model": ["2", 0],
                "ipadapter": ["2", 1],
                "image": ["3", 0],
                "weight": ip_weight,
                "weight_type": "style transfer precise",
                "combine_embeds": "concat",
                "start_at": 0.0,
                "end_at": 0.70,
                "embeds_scaling": "V only",
            },
        },
        "5": {"class_type": "LoadImage", "inputs": {"image": control_image}},
        "6": {"class_type": "ImageScale", "inputs": {"image": ["5", 0], "upscale_method": "nearest-exact", "width": width, "height": height, "crop": "disabled"}},
        "7": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": control_model}},
        "8": {"class_type": "CLIPTextEncode", "inputs": {"text": positive, "clip": ["1", 1]}},
        "9": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "10": {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["9", 0],
                "control_net": ["7", 0],
                "image": ["6", 0],
                "strength": control_strength,
                "start_percent": 0.0,
                "end_percent": 0.82,
            },
        },
        "11": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "12": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["4", 0],
                "seed": seed,
                "steps": steps,
                "cfg": 6.0,
                "sampler_name": "dpmpp_2m",
                "scheduler": "karras",
                "positive": ["10", 0],
                "negative": ["10", 1],
                "latent_image": ["11", 0],
                "denoise": 1.0,
            },
        },
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["1", 2]}},
        "14": {"class_type": "SaveImage", "inputs": {"filename_prefix": "gesture_ipadapter", "images": ["13", 0]}},
    }


def make_overview(paths: list[Path], output: Path, bg: str) -> None:
    tile = 300
    label_h = 42
    cols = 5
    rows = math.ceil(len(paths) / cols)
    sheet = Image.new("RGB", (cols * tile, rows * (tile + label_h)), bg)
    draw = ImageDraw.Draw(sheet)
    label_color = (0, 0, 0) if bg == "white" else (235, 235, 235)
    for i, path in enumerate(paths):
        img = ImageOps.exif_transpose(Image.open(path)).convert("RGBA")
        canvas = Image.new("RGBA", img.size, bg)
        canvas.alpha_composite(img)
        prev = canvas.convert("RGB")
        prev.thumbnail((tile - 30, tile - 30), Image.Resampling.LANCZOS)
        x0 = (i % cols) * tile
        y0 = (i // cols) * (tile + label_h)
        sheet.paste(prev, (x0 + (tile - prev.width) // 2, y0 + (tile - prev.height) // 2))
        draw.text((x0 + 10, y0 + tile + 10), path.stem[:34], fill=label_color)
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, quality=94)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--seed", type=int, default=2026061301)
    parser.add_argument("--count-per-gesture", type=int, default=2)
    parser.add_argument("--steps", type=int, default=30)
    parser.add_argument("--width", type=int, default=896)
    parser.add_argument("--height", type=int, default=896)
    parser.add_argument("--prompt-timeout", type=int, default=1500)
    parser.add_argument("--reference", type=Path, default=REFERENCE)
    parser.add_argument("--use-clean-reference", action="store_true")
    parser.add_argument("--ip-weight", type=float, default=0.38)
    parser.add_argument("--control-strength", type=float, default=0.82)
    parser.add_argument("--control-model", default="controlnet-openpose-sdxl-1.0.safetensors")
    parser.add_argument("--control-style", choices=["openpose", "canny"], default="openpose")
    parser.add_argument("--output-label", default=None)
    parser.add_argument("--safe-action-set", action="store_true")
    parser.add_argument("--print-friendly-set", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    wait_server()
    reference = ALT_REFERENCE if args.use_clean_reference else args.reference
    ref_name = copy_to_input(reference, f"gesture_style_reference{reference.suffix.lower()}")
    label = args.output_label or "控制手势_IPAdapter黑白灰印花二轮"
    out_dir = OUT_ROOT / f"{label}_{args.date}"
    raw_dir = out_dir / "raw"
    control_dir = out_dir / "control"
    out_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[Path] = []
    prompt_lines: list[str] = []
    if args.print_friendly_set:
        gesture_specs = print_friendly_specs()
    elif args.safe_action_set:
        gesture_specs = safe_specs()
    else:
        gesture_specs = specs()
    for spec_index, spec in enumerate(gesture_specs, start=1):
        control_path = control_dir / f"{spec_index:02d}_{spec.key}_control.png"
        if args.control_style == "canny":
            make_canny_like_control(spec.control_kind, control_path, args.width)
        else:
            make_control(spec.control_kind, control_path, args.width)
        control_name = copy_to_input(control_path, control_path.name)
        for variant in range(1, args.count_per_gesture + 1):
            seed = args.seed + spec_index * 1000 + variant * 37
            workflow = make_workflow(
                spec.prompt,
                seed,
                ref_name,
                control_name,
                args.control_model,
                args.width,
                args.height,
                args.steps,
                args.ip_weight,
                args.control_strength,
            )
            prompt_id = queue_prompt(workflow)
            print(f"queued {spec.key} v{variant} seed={seed}", flush=True)
            history = wait_prompt(prompt_id, args.prompt_timeout)
            if history.get("status", {}).get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error for {spec.key}: {history.get('status')}")
            copied = comfy_print_batch.copy_outputs(
                history,
                raw_dir,
                f"{spec_index:02d}_{spec.key}_v{variant}",
                244,
                42.0,
                keep_raw_comfy_output=False,
            )
            if len(copied) != 1:
                raise RuntimeError(f"Expected one output for {spec.key}, got {len(copied)}")
            final = out_dir / f"{spec_index:02d}_{spec.key}_v{variant}.png"
            copied[0].replace(final)
            outputs.append(final)
            prompt_lines.append(f"{final.name}\nseed={seed}\n{spec.name}\n{spec.prompt}\n")
            print(f"saved {final}", flush=True)

    (out_dir / "_prompts.txt").write_text("\n".join(prompt_lines), encoding="utf-8")
    make_overview(outputs, out_dir / "_overview_on_white.jpg", "white")
    make_overview(outputs, out_dir / "_overview_on_black.jpg", "black")
    print(f"Output dir: {out_dir}")
    print(f"White overview: {out_dir / '_overview_on_white.jpg'}")
    print(f"Black overview: {out_dir / '_overview_on_black.jpg'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
