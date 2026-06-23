import json
from pathlib import Path

import httpx
from PIL import Image

from consoleplat.services import ai_image_edit_cli


def _make_png(path: Path, color=(255, 0, 0, 255)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (32, 32), color).save(path)


def _make_collage_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (160, 80), (255, 255, 255, 255))
    for x in range(18, 58):
        for y in range(18, 62):
            image.putpixel((x, y), (220, 40, 40, 255))
    for x in range(102, 142):
        for y in range(18, 62):
            image.putpixel((x, y), (40, 40, 220, 255))
    image.save(path)


def _make_collage_with_tiny_fragment(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (240, 120), (255, 255, 255, 255))
    for x in range(20, 90):
        for y in range(20, 100):
            image.putpixel((x, y), (220, 40, 40, 255))
    for x in range(140, 220):
        for y in range(18, 104):
            image.putpixel((x, y), (40, 40, 220, 255))
    for x in range(112, 118):
        for y in range(10, 16):
            image.putpixel((x, y), (255, 210, 60, 255))
    image.save(path)


def test_ai_image_edit_cli_emits_json_and_writes_outputs(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.png"
    _make_png(source)

    def fake_request(*, api_key, api_base, model, prompt, size, image_paths, batch_count):
        assert api_key == "test-key"
        assert api_base == "https://api.example.test/v1"
        assert model == "gpt-image-2"
        assert prompt == "keep subject"
        assert size == "1024x1024"
        assert image_paths == [source]
        assert batch_count == 2
        return [
            ai_image_edit_cli.GeneratedImageResult(image_bytes=b"first", revised_prompt="round 1"),
            ai_image_edit_cli.GeneratedImageResult(image_bytes=b"second", revised_prompt="round 2"),
        ]

    monkeypatch.setattr(ai_image_edit_cli, "request_image_edit_batch", fake_request)
    monkeypatch.setenv("CONSOLEPLAT_AI_IMAGE_API_KEY", "test-key")

    exit_code = ai_image_edit_cli.main(
        [
            "--image",
            str(source),
            "--prompt",
            "keep subject",
            "--output-dir",
            str(tmp_path / "outputs"),
            "--api-base",
            "https://api.example.test/v1",
            "--model",
            "gpt-image-2",
            "--size",
            "1024x1024",
            "--total-return-count",
            "2",
        ]
    )

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert exit_code == 0
    assert payload["failed"] == []
    assert payload["warnings"] == []
    assert len(payload["outputs"]) == 2
    assert Path(payload["outputs"][0]).read_bytes() == b"first"
    assert Path(payload["outputs"][1]).read_bytes() == b"second"


def test_ai_image_edit_cli_split_collage_writes_part_outputs(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.png"
    _make_png(source, color=(0, 0, 0, 255))

    def fake_request(**_kwargs):
        return [ai_image_edit_cli.GeneratedImageResult(image_bytes=source.read_bytes(), revised_prompt="ok")]

    monkeypatch.setattr(ai_image_edit_cli, "request_image_edit_batch", fake_request)
    monkeypatch.setenv("CONSOLEPLAT_AI_IMAGE_API_KEY", "test-key")

    exit_code = ai_image_edit_cli.main(
        [
            "--image",
            str(source),
            "--prompt",
            "split it",
            "--output-dir",
            str(tmp_path / "outputs"),
            "--split-collage",
            "--split-count",
            "3",
            "--total-return-count",
            "1",
        ]
    )

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    outputs = [Path(item) for item in payload["outputs"]]

    assert exit_code == 0
    assert len(outputs) == 4
    assert outputs[0].name == "edited_round_01.png"
    assert [path.name for path in outputs[1:]] == [
        "edited_round_01_part_01.png",
        "edited_round_01_part_02.png",
        "edited_round_01_part_03.png",
    ]
    assert all(path.exists() for path in outputs)


def test_request_image_edit_batch_uses_matching_mime_types(tmp_path, monkeypatch):
    jpg_path = tmp_path / "one.jpg"
    png_path = tmp_path / "two.png"
    jpg_path.write_bytes(b"jpg")
    png_path.write_bytes(b"png")
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"b64_json": base64_bytes("ok")}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, data=None, files=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["data"] = data
            captured["files"] = files
            return FakeResponse()

    monkeypatch.setattr(ai_image_edit_cli.httpx, "Client", FakeClient)

    results = ai_image_edit_cli.request_image_edit_batch(
        api_key="test-key",
        api_base="https://api.example.test/v1",
        model="gpt-image-2",
        prompt="keep subject",
        size="1024x1024",
        image_paths=[jpg_path, png_path],
        batch_count=1,
    )

    files = captured["files"]
    assert results[0].image_bytes == b"ok"
    assert files[0][0] == "image[]"
    assert files[0][1][2] == "image/jpeg"
    assert files[1][1][2] == "image/png"


def test_ai_image_edit_cli_emits_api_error_details(tmp_path, monkeypatch, capsys):
    source = tmp_path / "source.png"
    _make_png(source)

    class FakeClient:
        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            request = httpx.Request("POST", "https://api.example.test/v1/images/edits")
            response = httpx.Response(
                400,
                request=request,
                json={"error": {"message": "invalid image payload"}},
            )
            raise httpx.HTTPStatusError("bad request", request=request, response=response)

    monkeypatch.setattr(ai_image_edit_cli.httpx, "Client", FakeClient)
    monkeypatch.setenv("CONSOLEPLAT_AI_IMAGE_API_KEY", "test-key")

    exit_code = ai_image_edit_cli.main(
        [
            "--image",
            str(source),
            "--prompt",
            "keep subject",
            "--output-dir",
            str(tmp_path / "outputs"),
        ]
    )

    payload = json.loads(capsys.readouterr().out.strip().splitlines()[-1])

    assert exit_code == 1
    assert payload["failed"]
    assert "invalid image payload" in payload["failed"][0]


def test_request_image_edit_batch_retries_v1_endpoint_after_404(tmp_path, monkeypatch):
    source = tmp_path / "source.png"
    source.write_bytes(b"png")
    calls: list[str] = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": [{"b64_json": base64_bytes("ok")}]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            return None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, data=None, files=None):
            calls.append(url)
            if url == "https://api.geek2api.com/images/edits":
                request = httpx.Request("POST", url)
                response = httpx.Response(404, request=request, text="not found")
                raise httpx.HTTPStatusError("not found", request=request, response=response)
            return FakeResponse()

    monkeypatch.setattr(ai_image_edit_cli.httpx, "Client", FakeClient)

    results = ai_image_edit_cli.request_image_edit_batch(
        api_key="test-key",
        api_base="https://api.geek2api.com",
        model="gpt-image-2",
        prompt="keep subject",
        size="1024x1024",
        image_paths=[source],
        batch_count=1,
    )

    assert calls == [
        "https://api.geek2api.com/images/edits",
        "https://api.geek2api.com/v1/images/edits",
    ]
    assert results[0].image_bytes == b"ok"


def test_convert_image_to_transparent_background_removes_border_background(tmp_path):
    source = tmp_path / "collage.png"
    _make_collage_png(source)

    output = Path(ai_image_edit_cli.convert_image_to_transparent_background(source))
    image = Image.open(output).convert("RGBA")

    assert output.name == "collage_transparent.png"
    assert image.getpixel((0, 0))[3] == 0
    assert image.getpixel((35, 35))[3] == 255


def test_split_collage_image_with_guides_exports_individual_prints(tmp_path):
    source = tmp_path / "collage.png"
    _make_collage_png(source)
    transparent = Path(ai_image_edit_cli.convert_image_to_transparent_background(source))

    outputs = [
        Path(path)
        for path in ai_image_edit_cli.split_collage_image_with_guides(
            transparent,
            tmp_path / "split",
            2,
        )
    ]

    assert [path.name for path in outputs] == [
        "collage_transparent_part_01.png",
        "collage_transparent_part_02.png",
    ]
    assert all(path.exists() for path in outputs)
    first = Image.open(outputs[0]).convert("RGBA")
    second = Image.open(outputs[1]).convert("RGBA")
    assert first.width < Image.open(transparent).width
    assert second.width < Image.open(transparent).width
    assert first.getpixel((first.width // 2, first.height // 2))[0] > 150
    assert second.getpixel((second.width // 2, second.height // 2))[2] > 150


def test_split_collage_image_ignores_tiny_fragment_components(tmp_path):
    source = tmp_path / "collage.png"
    _make_collage_with_tiny_fragment(source)
    transparent = Path(ai_image_edit_cli.convert_image_to_transparent_background(source))

    outputs = [
        Path(path)
        for path in ai_image_edit_cli.split_collage_image_with_guides(
            transparent,
            tmp_path / "split",
            3,
        )
    ]

    assert len(outputs) == 2
    assert [path.name for path in outputs] == [
        "collage_transparent_part_01.png",
        "collage_transparent_part_02.png",
    ]


def base64_bytes(text: str) -> str:
    import base64

    return base64.b64encode(text.encode("utf-8")).decode("ascii")
