from pathlib import Path

from PIL import Image

from tools import render_dog_text_print_batch as dog_batch


def test_generate_dog_text_prints_creates_transparent_batch(tmp_path: Path) -> None:
    result = dog_batch.generate_batch(tmp_path, count=50, seed=1234)

    final_dir = tmp_path / "最终透明底"
    test_dir = tmp_path / "测试"
    print_files = sorted(final_dir.glob("dog_text_*.png"))

    assert len(print_files) == 50
    assert result.final_dir == final_dir
    assert result.overview_path == test_dir / "_overview_checker.jpg"
    assert result.overview_path.exists()
    assert result.manifest_path.exists()

    manifest_text = result.manifest_path.read_text(encoding="utf-8")
    assert "language\ttext" in manifest_text
    assert "\tko\t" in manifest_text
    assert "\ten\t" in manifest_text

    sample = Image.open(print_files[0]).convert("RGBA")
    assert sample.size == dog_batch.CANVAS_SIZE
    assert sample.getpixel((0, 0))[3] == 0
    assert sample.getpixel((sample.width - 1, sample.height - 1))[3] == 0
    assert sample.getchannel("A").getbbox() is not None
