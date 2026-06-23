import json
from pathlib import Path

from PIL import Image

from consoleplat.services import ai_image_edit_cli


def _make_png(path: Path, color=(255, 0, 0, 255)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (32, 32), color).save(path)


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
