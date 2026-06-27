from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from tools.remove_print_bg import remove_white_bg


def test_remove_white_bg_removes_enclosed_fake_checkerboard(tmp_path: Path) -> None:
    src = tmp_path / "checker_source.png"
    out = tmp_path / "checker_out.png"

    size = 96
    tile = 8
    img = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    draw = ImageDraw.Draw(img)
    for y in range(0, size, tile):
        for x in range(0, size, tile):
            color = (238, 238, 238, 255) if ((x // tile + y // tile) % 2) else (248, 248, 248, 255)
            draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=color)

    # A dark printed outline encloses some of the fake checkerboard. The enclosed
    # area should still become transparent because it is background, not artwork.
    draw.rectangle((24, 24, 72, 72), outline=(10, 10, 10, 255), width=5)
    draw.line((18, 80, 78, 18), fill=(20, 20, 20, 255), width=4)
    img.save(src)

    remove_white_bg(src, out)

    result = Image.open(out).convert("RGBA")
    alpha = np.asarray(result)[..., 3]

    assert alpha[60, 60] == 0
    assert alpha[24, 48] == 255
    assert alpha[80, 18] == 255
