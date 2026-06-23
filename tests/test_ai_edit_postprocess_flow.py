from pathlib import Path

from PIL import Image
from PyQt5.QtWidgets import QApplication

from consoleplat.adapters.posaiimg_adapter import AIEditJob
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.services.ai_edit_formalize_service import AIEditFormalizeSummary
from consoleplat.services.ai_edit_postprocess_service import prepare_ai_edit_print_assets
from consoleplat.services.putaway_sync_service import PutawaySyncSummary
from consoleplat.ui.ai_edit_page import AIEditPage, AIEditTaskRecord


def _page_with_temp_store(tmp_path, monkeypatch, settings=None):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(settings or AppSettings(ai_edit_api_key="stored-key"))
    monkeypatch.setattr("consoleplat.ui.ai_edit_page.SettingsStore", lambda: SettingsStore(path))
    return AIEditPage(), path


def test_ai_edit_page_save_persists_ai_edit_controls(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            publish_prefix="BO",
            publish_start_number=1421,
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )

    page.prefix_combo.setCurrentText("SZW")
    page.start_spin.setValue(3113)
    page.total_return_count_spin.setValue(6)
    page.split_collage_check.setChecked(True)
    page.split_count_spin.setValue(9)
    page.test_mode_check.setChecked(False)
    page._save_preferences()

    saved = SettingsStore(path).load()

    assert saved.publish_prefix == "SZW"
    assert saved.publish_start_number == 3113
    assert saved.ai_edit_total_return_count == 6
    assert saved.ai_edit_split_collage is True
    assert saved.ai_edit_split_count == 9
    assert saved.local_image_test_mode is False

    page.close()


def test_ai_edit_page_formal_mode_converts_and_splits_before_formalize(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    source = tmp_path / "edited_round_01.png"
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(source)

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            default_ai_provider_id="provider-1",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "main",
                    "api_key": "stored-key",
                    "api_base": "https://api.openai.com/v1",
                    "model": "gpt-image-2",
                    "size": "1024x1024",
                }
            ],
            bo_product_title="BO fixed title",
            putaway_data_dir=str(tmp_path / "putaway-data"),
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    page.current_task = AIEditTaskRecord(
        task_id="20260623130200",
        title="AI edit BO-1661",
        job=AIEditJob(
            images=[],
            prompt="keep subject",
            output_dir=tmp_path / "output",
            prefix="BO",
            start_number=1661,
            total_return_count=1,
            split_collage=True,
            split_count=2,
            test_mode=False,
        ),
        output_dir=str(tmp_path / "output"),
        outputs=[str(source)],
        final_transparent_dir=str(tmp_path / "final-transparent"),
        final_product_dir=str(tmp_path / "final-product"),
        xlsx_path=str(tmp_path / "final-product.xlsx"),
    )

    converted = source.parent / "edited_round_01_transparent.png"
    part_a = source.parent / "edited_round_01_transparent_split" / "edited_round_01_transparent_part_01.png"
    part_b = source.parent / "edited_round_01_transparent_split" / "edited_round_01_transparent_part_02.png"
    called: dict[str, object] = {}

    def fake_convert(path, output_dir=None):
        converted.parent.mkdir(parents=True, exist_ok=True)
        converted.write_bytes(b"transparent")
        called["convert_path"] = str(path)
        called["convert_output_dir"] = str(output_dir) if output_dir is not None else None
        return str(converted)

    def fake_split(path, output_dir, split_count, x_guides=None, y_guides=None):
        part_a.parent.mkdir(parents=True, exist_ok=True)
        part_a.write_bytes(b"a")
        part_b.write_bytes(b"b")
        called["split_path"] = str(path)
        called["split_output_dir"] = str(output_dir)
        called["split_count"] = split_count
        return [str(part_a), str(part_b)]

    def fake_formalize(**kwargs):
        called["formalize_split_paths"] = [Path(item) for item in kwargs["split_paths"]]
        return AIEditFormalizeSummary(
            ok=True,
            renamed_outputs=[
                str(tmp_path / "final-transparent" / "BO-1661.png"),
                str(tmp_path / "final-transparent" / "BO-1662.png"),
            ],
            product_outputs=[str(tmp_path / "final-product" / "BO-1661_BO fixed title.png")],
            xlsx_path=str(tmp_path / "final-product.xlsx"),
            putaway=PutawaySyncSummary(ok=True, message="synced"),
            color_assignments={"BO-1661": "black"},
            message="formalize done",
        )

    monkeypatch.setattr("consoleplat.services.ai_edit_postprocess_service.convert_image_to_transparent_background", fake_convert)
    monkeypatch.setattr("consoleplat.services.ai_edit_postprocess_service.split_collage_image_with_guides", fake_split)
    monkeypatch.setattr("consoleplat.ui.ai_edit_page.formalize_ai_edit_outputs", fake_formalize)

    page._run_prepare_post_process()
    page._run_formalize_post_process()

    assert called["convert_path"] == str(source)
    assert called["split_path"] == str(converted)
    assert called["split_count"] == 2
    assert called["formalize_split_paths"] == [
        tmp_path / "final-transparent" / "BO-1661.png",
        tmp_path / "final-transparent" / "BO-1662.png",
    ]
    assert page.current_task.round_sources == [
        str(tmp_path / "final-transparent" / "BO-1661.png"),
        str(tmp_path / "final-transparent" / "BO-1662.png"),
    ]
    assert page.current_task.outputs == [str(tmp_path / "final-product" / "BO-1661_BO fixed title.png")]

    page.close()


def test_prepare_ai_edit_print_assets_renames_split_outputs_into_final_transparent_dir(tmp_path, monkeypatch):
    source = tmp_path / "edited_round_01.png"
    Image.new("RGBA", (64, 64), (255, 255, 255, 255)).save(source)

    converted = tmp_path / "edited_round_01_transparent.png"
    split_dir = tmp_path / "edited_round_01_transparent_split"
    raw_part_a = split_dir / "edited_round_01_transparent_part_01.png"
    raw_part_b = split_dir / "edited_round_01_transparent_part_02.png"

    def fake_convert(path, output_dir=None):
        Image.new("RGBA", (64, 64), (0, 0, 0, 0)).save(converted)
        return str(converted)

    def fake_split(path, output_dir, split_count, x_guides=None, y_guides=None):
        split_dir.mkdir(parents=True, exist_ok=True)
        Image.new("RGBA", (20, 20), (255, 0, 0, 255)).save(raw_part_a)
        Image.new("RGBA", (20, 20), (0, 0, 255, 255)).save(raw_part_b)
        return [str(raw_part_a), str(raw_part_b)]

    monkeypatch.setattr("consoleplat.services.ai_edit_postprocess_service.convert_image_to_transparent_background", fake_convert)
    monkeypatch.setattr("consoleplat.services.ai_edit_postprocess_service.split_collage_image_with_guides", fake_split)

    assets = prepare_ai_edit_print_assets(
        source_paths=[source],
        final_transparent_dir=tmp_path / "final-transparent",
        prefix="BO",
        start_number=1661,
        split_collage=True,
        split_count=2,
    )

    assert len(assets) == 1
    assert assets[0].transparent_path == converted
    assert [path.name for path in assets[0].split_paths] == ["BO-1661.png", "BO-1662.png"]
    assert all(path.parent == tmp_path / "final-transparent" for path in assets[0].split_paths)
