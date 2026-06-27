from __future__ import annotations

import argparse
import itertools
import math
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageTk


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_DIR = ROOT / "\u53bb\u5370\u82b1\u7ed3\u679c"
DEFAULT_PRINT_DIR = ROOT / "\u5370\u82b1\u56fe"
DEFAULT_OUTPUT_DIR = ROOT / "\u6279\u91cf\u8d34\u56fe\u7ed3\u679c"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


@dataclass
class Placement:
    center_x: float = 0.50
    center_y: float = 0.43
    width: float = 0.30
    opacity: float = 0.92
    rotation: float = 0.0
    shadow_strength: float = 0.32
    wave_strength: float = 0.012
    remove_white_bg: bool = True


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)


def safe_stem(path: Path) -> str:
    text = re.sub(r"[^\w\-.]+", "_", path.stem, flags=re.UNICODE)
    return text.strip("_") or "image"


def load_rgba(path: Path) -> Image.Image:
    return ImageOps.exif_transpose(Image.open(path)).convert("RGBA")


def remove_near_white_background(img: Image.Image, threshold: int = 242) -> Image.Image:
    rgba = np.asarray(img.convert("RGBA")).copy()
    rgb = rgba[..., :3].astype(np.int16)
    near_white = (rgb[..., 0] > threshold) & (rgb[..., 1] > threshold) & (rgb[..., 2] > threshold)
    color_spread = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    near_white &= color_spread < 22
    rgba[..., 3] = np.where(near_white, 0, rgba[..., 3])
    return Image.fromarray(rgba, "RGBA")


def crop_to_alpha(img: Image.Image, padding: int = 8) -> Image.Image:
    bbox = img.getbbox()
    if not bbox:
        return img
    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(img.width, right + padding)
    bottom = min(img.height, bottom + padding)
    return img.crop((left, top, right, bottom))


def wave_displace(img: Image.Image, strength: float) -> Image.Image:
    if strength <= 0:
        return img
    arr = np.asarray(img).copy()
    h, w = arr.shape[:2]
    max_shift = max(1, int(w * strength))
    out = np.zeros_like(arr)
    for y in range(h):
        phase = (y / max(1, h)) * math.tau * 2.2
        shift = int(math.sin(phase) * max_shift)
        out[y] = np.roll(arr[y], shift, axis=0)
        if shift > 0:
            out[y, :shift, 3] = 0
        elif shift < 0:
            out[y, shift:, 3] = 0
    return Image.fromarray(out, "RGBA")


def fit_print(print_img: Image.Image, base_size: tuple[int, int], placement: Placement) -> Image.Image:
    if placement.remove_white_bg:
        print_img = remove_near_white_background(print_img)
    print_img = crop_to_alpha(print_img)

    target_w = max(1, int(base_size[0] * placement.width))
    ratio = target_w / max(1, print_img.width)
    target_h = max(1, int(print_img.height * ratio))
    print_img = print_img.resize((target_w, target_h), Image.Resampling.LANCZOS)

    if placement.wave_strength:
        print_img = wave_displace(print_img, placement.wave_strength)

    if placement.rotation:
        print_img = print_img.rotate(
            placement.rotation,
            expand=True,
            resample=Image.Resampling.BICUBIC,
            fillcolor=(0, 0, 0, 0),
        )

    if placement.opacity < 1:
        r, g, b, a = print_img.split()
        a = ImageEnhance.Brightness(a).enhance(max(0, min(1, placement.opacity)))
        print_img = Image.merge("RGBA", (r, g, b, a))
    return print_img


def cloth_blend(base: Image.Image, print_img: Image.Image, x: int, y: int, placement: Placement) -> Image.Image:
    base_rgba = base.convert("RGBA")
    crop_box = (
        max(0, x),
        max(0, y),
        min(base_rgba.width, x + print_img.width),
        min(base_rgba.height, y + print_img.height),
    )
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        return base_rgba

    px0 = crop_box[0] - x
    py0 = crop_box[1] - y
    px1 = px0 + (crop_box[2] - crop_box[0])
    py1 = py0 + (crop_box[3] - crop_box[1])
    print_crop = print_img.crop((px0, py0, px1, py1))
    base_crop = base_rgba.crop(crop_box)

    p = np.asarray(print_crop).astype(np.float32)
    b = np.asarray(base_crop).astype(np.float32)
    alpha = (p[..., 3:4] / 255.0) * max(0.0, min(1.0, placement.opacity))

    luminance = (0.2126 * b[..., 0:1] + 0.7152 * b[..., 1:2] + 0.0722 * b[..., 2:3]) / 255.0
    mean_luma = float(np.mean(luminance)) if luminance.size else 0.5
    fabric_factor = 1.0 + (luminance - mean_luma) * placement.shadow_strength * 2.2
    fabric_factor = np.clip(fabric_factor, 0.58, 1.28)

    print_rgb = np.clip(p[..., :3] * fabric_factor, 0, 255)
    mixed_rgb = b[..., :3] * (1.0 - alpha) + print_rgb * alpha
    out = b.copy()
    out[..., :3] = mixed_rgb
    out[..., 3] = 255

    patch = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    mask = print_crop.split()[-1].filter(ImageFilter.GaussianBlur(radius=0.6))
    base_rgba.paste(patch, crop_box[:2], mask)
    return base_rgba


def composite_one(model_path: Path, print_path: Path, output_path: Path, placement: Placement) -> None:
    base = load_rgba(model_path)
    design = load_rgba(print_path)
    design = fit_print(design, base.size, placement)
    x = int(base.width * placement.center_x - design.width / 2)
    y = int(base.height * placement.center_y - design.height / 2)
    result = cloth_blend(base, design, x, y, placement)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)


def batch_generate(model_dir: Path, print_dir: Path, output_dir: Path, placement: Placement) -> list[Path]:
    models = list_images(model_dir)
    prints = list_images(print_dir)
    if not models:
        raise FileNotFoundError(f"No model images found: {model_dir}")
    if not prints:
        raise FileNotFoundError(f"No print images found: {print_dir}")

    output_paths: list[Path] = []
    for model_path, print_path in itertools.product(models, prints):
        filename = f"{safe_stem(model_path)}__{safe_stem(print_path)}.png"
        output_path = output_dir / filename
        composite_one(model_path, print_path, output_path, placement)
        output_paths.append(output_path)
    return output_paths


def make_sample_prints(print_dir: Path) -> list[Path]:
    print_dir.mkdir(parents=True, exist_ok=True)
    samples: list[Path] = []

    img = Image.new("RGBA", (1200, 900), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((130, 160, 1070, 740), radius=90, fill=(255, 255, 255, 0), outline=(230, 230, 230, 255), width=18)
    draw.ellipse((230, 220, 610, 600), fill=(246, 214, 63, 255))
    draw.rectangle((545, 290, 900, 640), fill=(42, 186, 168, 255))
    draw.polygon([(640, 160), (1020, 520), (800, 760)], fill=(232, 66, 73, 230))
    draw.text((235, 650), "SUMMER CLUB", fill=(245, 245, 245, 255))
    path = print_dir / "sample_summer_club.png"
    img.save(path)
    samples.append(path)

    img = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for i in range(13):
        color = (255, 255 - i * 9, 95 + i * 8, 230)
        draw.arc((130 + i * 18, 150 + i * 18, 870 - i * 18, 850 - i * 18), 205, 520, fill=color, width=18)
    draw.rectangle((290, 435, 710, 575), fill=(20, 20, 20, 220))
    draw.text((350, 474), "RETRO", fill=(255, 255, 255, 255))
    path = print_dir / "sample_retro_arc.png"
    img.save(path)
    samples.append(path)
    return samples


class App:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import filedialog, messagebox

        self.tk = tk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.root = tk.Tk()
        self.root.title("\u0054\u6064\u6279\u91cf\u8d34\u5370\u82b1\u5de5\u5177")
        self.root.geometry("1120x760")

        self.model_dir = tk.StringVar(value=str(DEFAULT_MODEL_DIR))
        self.print_dir = tk.StringVar(value=str(DEFAULT_PRINT_DIR))
        self.output_dir = tk.StringVar(value=str(DEFAULT_OUTPUT_DIR))
        self.center_x = tk.DoubleVar(value=0.50)
        self.center_y = tk.DoubleVar(value=0.43)
        self.width = tk.DoubleVar(value=0.30)
        self.opacity = tk.DoubleVar(value=0.92)
        self.rotation = tk.DoubleVar(value=0.0)
        self.shadow_strength = tk.DoubleVar(value=0.32)
        self.wave_strength = tk.DoubleVar(value=0.012)
        self.remove_white_bg = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="\u5c31\u7eea")
        self.preview_photo: ImageTk.PhotoImage | None = None

        self._build()
        self.refresh_preview()

    def placement(self) -> Placement:
        return Placement(
            center_x=self.center_x.get(),
            center_y=self.center_y.get(),
            width=self.width.get(),
            opacity=self.opacity.get(),
            rotation=self.rotation.get(),
            shadow_strength=self.shadow_strength.get(),
            wave_strength=self.wave_strength.get(),
            remove_white_bg=self.remove_white_bg.get(),
        )

    def _build(self) -> None:
        tk = self.tk
        outer = tk.Frame(self.root, padx=12, pady=12)
        outer.pack(fill="both", expand=True)

        left = tk.Frame(outer, width=360)
        left.pack(side="left", fill="y", padx=(0, 12))
        right = tk.Frame(outer)
        right.pack(side="right", fill="both", expand=True)

        self._folder_row(left, "\u5e72\u51c0\u6a21\u7279\u56fe\u6587\u4ef6\u5939", self.model_dir, 0)
        self._folder_row(left, "\u5370\u82b1\u56fe\u6587\u4ef6\u5939", self.print_dir, 1)
        self._folder_row(left, "\u8f93\u51fa\u7ed3\u679c\u6587\u4ef6\u5939", self.output_dir, 2)

        controls = [
            ("\u5de6\u53f3\u4f4d\u7f6e", self.center_x, 0.25, 0.75, 0.01),
            ("\u4e0a\u4e0b\u4f4d\u7f6e", self.center_y, 0.25, 0.65, 0.01),
            ("\u5370\u82b1\u5927\u5c0f", self.width, 0.12, 0.55, 0.01),
            ("\u4e0d\u900f\u660e\u5ea6", self.opacity, 0.20, 1.00, 0.01),
            ("\u65cb\u8f6c\u89d2\u5ea6", self.rotation, -25.0, 25.0, 1.0),
            ("\u9634\u5f71\u878d\u5408", self.shadow_strength, 0.0, 0.8, 0.01),
            ("\u8936\u76b1\u6ce2\u5f62", self.wave_strength, 0.0, 0.04, 0.001),
        ]
        for label, var, start, end, resolution in controls:
            row = tk.Frame(left)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=label, width=14, anchor="w").pack(side="left")
            scale = tk.Scale(
                row,
                from_=start,
                to=end,
                resolution=resolution,
                orient="horizontal",
                variable=var,
                command=lambda _value: self.refresh_preview(),
                length=210,
            )
            scale.pack(side="left", fill="x", expand=True)

        tk.Checkbutton(
            left,
            text="\u81ea\u52a8\u53bb\u6389\u5370\u82b1\u767d\u5e95",
            variable=self.remove_white_bg,
            command=self.refresh_preview,
        ).pack(anchor="w", pady=8)

        buttons = tk.Frame(left)
        buttons.pack(fill="x", pady=10)
        tk.Button(buttons, text="\u751f\u6210\u793a\u4f8b\u5370\u82b1", command=self.create_samples).pack(fill="x", pady=3)
        tk.Button(buttons, text="\u5237\u65b0\u9884\u89c8", command=self.refresh_preview).pack(fill="x", pady=3)
        tk.Button(buttons, text="\u6279\u91cf\u5bfc\u51fa", command=self.batch_export).pack(fill="x", pady=3)

        tk.Label(left, textvariable=self.status, anchor="w", justify="left", wraplength=340).pack(fill="x", pady=8)

        self.canvas = tk.Label(right, bg="#222")
        self.canvas.pack(fill="both", expand=True)

    def _folder_row(self, parent, label: str, var, row_idx: int) -> None:
        tk = self.tk
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=(0 if row_idx == 0 else 7, 7))
        tk.Label(frame, text=label, anchor="w").pack(fill="x")
        line = tk.Frame(frame)
        line.pack(fill="x")
        tk.Entry(line, textvariable=var).pack(side="left", fill="x", expand=True)
        tk.Button(line, text="...", width=4, command=lambda: self.choose_folder(var)).pack(side="right", padx=(5, 0))

    def choose_folder(self, var) -> None:
        folder = self.filedialog.askdirectory(initialdir=var.get() or str(ROOT))
        if folder:
            var.set(folder)
            self.refresh_preview()

    def first_pair(self) -> tuple[Path, Path] | None:
        models = list_images(Path(self.model_dir.get()))
        prints = list_images(Path(self.print_dir.get()))
        if not models or not prints:
            return None
        return models[0], prints[0]

    def preview_image(self) -> Image.Image | None:
        pair = self.first_pair()
        if not pair:
            return None
        model_path, print_path = pair
        base = load_rgba(model_path)
        design = fit_print(load_rgba(print_path), base.size, self.placement())
        x = int(base.width * self.center_x.get() - design.width / 2)
        y = int(base.height * self.center_y.get() - design.height / 2)
        return cloth_blend(base, design, x, y, self.placement())

    def refresh_preview(self) -> None:
        try:
            image = self.preview_image()
            if image is None:
                self.status.set("\u8bf7\u5148\u653e\u5165\u6a21\u7279\u56fe\u548c\u5370\u82b1\u56fe\uff0c\u7136\u540e\u5237\u65b0\u9884\u89c8\u3002")
                return
            max_w, max_h = 720, 700
            image.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(image)
            self.canvas.configure(image=self.preview_photo)
            self.status.set("\u9884\u89c8\u4f7f\u7528\u7b2c\u4e00\u5f20\u6a21\u7279\u56fe\u548c\u7b2c\u4e00\u5f20\u5370\u82b1\u56fe\u3002")
        except Exception as exc:
            self.status.set(f"\u9884\u89c8\u5931\u8d25\uff1a{exc}")

    def create_samples(self) -> None:
        paths = make_sample_prints(Path(self.print_dir.get()))
        self.status.set(f"\u5df2\u751f\u6210 {len(paths)} \u5f20\u793a\u4f8b\u5370\u82b1\u3002")
        self.refresh_preview()

    def batch_export(self) -> None:
        def work() -> None:
            try:
                paths = batch_generate(
                    Path(self.model_dir.get()),
                    Path(self.print_dir.get()),
                    Path(self.output_dir.get()),
                    self.placement(),
                )
                self.status.set(f"\u5b8c\u6210\uff1a\u5df2\u5bfc\u51fa {len(paths)} \u5f20\u56fe\u5230 {self.output_dir.get()}")
                self.messagebox.showinfo("\u5b8c\u6210", f"\u5df2\u5bfc\u51fa {len(paths)} \u5f20\u56fe\u3002")
            except Exception as exc:
                self.status.set(f"\u5bfc\u51fa\u5931\u8d25\uff1a{exc}")
                self.messagebox.showerror("\u5bfc\u51fa\u5931\u8d25", str(exc))

        self.status.set("\u6b63\u5728\u5bfc\u51fa...")
        threading.Thread(target=work, daemon=True).start()

    def run(self) -> None:
        self.root.mainloop()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch compose print designs onto clean T-shirt model images.")
    parser.add_argument("--model-dir", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--print-dir", type=Path, default=DEFAULT_PRINT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--center-x", type=float, default=0.50)
    parser.add_argument("--center-y", type=float, default=0.43)
    parser.add_argument("--width", type=float, default=0.30)
    parser.add_argument("--opacity", type=float, default=0.92)
    parser.add_argument("--rotation", type=float, default=0.0)
    parser.add_argument("--shadow-strength", type=float, default=0.32)
    parser.add_argument("--wave-strength", type=float, default=0.012)
    parser.add_argument("--keep-white-bg", action="store_true")
    parser.add_argument("--make-samples", action="store_true")
    parser.add_argument("--batch", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.make_samples:
        samples = make_sample_prints(args.print_dir)
        print(f"Created {len(samples)} sample prints in {args.print_dir}")

    if args.batch:
        placement = Placement(
            center_x=args.center_x,
            center_y=args.center_y,
            width=args.width,
            opacity=args.opacity,
            rotation=args.rotation,
            shadow_strength=args.shadow_strength,
            wave_strength=args.wave_strength,
            remove_white_bg=not args.keep_white_bg,
        )
        paths = batch_generate(args.model_dir, args.print_dir, args.output_dir, placement)
        print(f"Exported {len(paths)} images to {args.output_dir}")
        return

    if not args.make_samples:
        App().run()


if __name__ == "__main__":
    main()
