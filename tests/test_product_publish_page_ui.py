from pathlib import Path

from PyQt5.QtWidgets import QApplication, QListWidget, QMessageBox

from consoleplat.adapters.posaiimg_adapter import AIEditJob, LocalImageJob
from consoleplat.services.putaway_sync_service import PutawaySyncSummary
from consoleplat.config import AppSettings, SettingsStore
from consoleplat.ui.product_publish_page import (
    PRODUCT_TASK_STATUSES,
    ProductPublishPage,
    ProductTaskRecord,
    validate_publish_outputs,
)


def _page_with_temp_store(tmp_path, monkeypatch, settings=None):
    path = tmp_path / "settings.json"
    SettingsStore(path).save(settings or AppSettings(program_data_dir=str(tmp_path / "ConsolePlatData")))
    monkeypatch.setattr("consoleplat.ui.product_publish_page.SettingsStore", lambda: SettingsStore(path))
    return ProductPublishPage(), path


def test_product_publish_page_exposes_default_draft(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            bo_product_title="BO default title",
            szw_product_title="SZW default title",
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )

    assert page.prefix_combo.currentText() == "BO"
    assert page.task_name_edit.text()
    assert not hasattr(page, "product_title_edit")
    assert not hasattr(page, "product_title_label")
    assert page.count_spin.value() == 10
    assert page.test_mode_check.isChecked()
    assert page.handoff_combo.currentText() == "同步并唤起"
    assert [button.text() for button in page.primary_action_buttons] == ["同意并开始", "停止任务"]
    assert page.stop_button.isEnabled() is False
    assert page.batch_delete_toggle.isChecked() is False
    assert page.batch_delete_button.isEnabled() is False
    assert page.task_list.count() == 0

    page.close()


def test_product_publish_page_toggles_generation_parameters(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)

    page.generation_mode_combo.setCurrentText("本地生图")

    assert not page.local_params_panel.isHidden()
    assert page.ai_params_panel.isHidden()

    page.generation_mode_combo.setCurrentIndex(1)

    assert page.generation_mode_combo.currentText() == "AI 改图"
    assert not page.ai_params_panel.isHidden()
    assert page.local_params_panel.isHidden()
    assert page.count_label.text() == "本次轮数"
    assert page.count_spin.value() == 2
    assert page.count_spin.suffix() == " 轮"

    page.close()


def test_product_publish_page_moves_generation_mode_above_count_and_updates_label(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)

    labels = [page.form_layout.labelForField(widget).text() for widget in (page.generation_mode_combo, page.count_spin)]
    assert labels == ["生图方式", "计划张数"]

    page.generation_mode_combo.setCurrentIndex(1)

    labels = [page.form_layout.labelForField(widget).text() for widget in (page.generation_mode_combo, page.count_spin)]
    assert labels == ["生图方式", "本次轮数"]
    assert page.count_spin.value() == 2
    assert page.count_spin.suffix() == " 轮"

    page.generation_mode_combo.setCurrentIndex(0)

    assert page.count_label.text() == "计划张数"
    assert page.count_spin.value() == 10
    assert page.count_spin.suffix() == " 张"

    page.close()


def test_product_publish_page_batch_delete_toggle_matches_ai_page_pattern(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)

    assert page.task_list.selectionMode() == QListWidget.SingleSelection
    assert page.batch_delete_button.isEnabled() is False

    page.batch_delete_toggle.setChecked(True)

    assert page.task_list.selectionMode() == QListWidget.MultiSelection
    assert page.batch_delete_button.isEnabled() is True

    page.batch_delete_toggle.setChecked(False)

    assert page.task_list.selectionMode() == QListWidget.SingleSelection
    assert page.batch_delete_button.isEnabled() is False

    page.close()


def test_product_publish_page_builds_local_and_ai_jobs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    image = tmp_path / "reference.png"
    image.write_bytes(b"fake")
    page, _path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            ai_edit_api_key="stored-key",
            default_ai_provider_id="provider-2",
            ai_providers=[
                {
                    "provider_id": "provider-1",
                    "name": "主接口",
                    "api_key": "old-key",
                    "api_base": "https://old.example/v1",
                    "model": "old-model",
                    "size": "1024x1024",
                },
                {
                    "provider_id": "provider-2",
                    "name": "备用接口",
                    "api_key": "stored-key",
                    "api_base": "https://provider-two.example/v1",
                    "model": "provider-two-model",
                    "size": "1536x1024",
                },
            ],
            posai_gallery_root=str(tmp_path / "gallery"),
            posai_mockup_root=str(tmp_path / "mockup"),
            posai_xlsx_root=str(tmp_path / "xlsx"),
            bo_product_title="BO default title",
            szw_product_title="SZW default title",
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    page.prefix_combo.setCurrentText("SZW")
    page.start_spin.setValue(3113)
    page.count_spin.setValue(5)
    page.test_mode_check.setChecked(False)

    local_job = page.build_local_image_job()

    assert isinstance(local_job, LocalImageJob)
    assert local_job.prefix == "SZW"
    assert local_job.start_number == 3113
    assert local_job.count == 5
    assert local_job.test_mode is False

    page.generation_mode_combo.setCurrentIndex(1)
    page._add_reference_image(str(image))
    page.ai_prompt_edit.setPlainText("keep subject and generate print")

    ai_job = page.build_ai_edit_job()

    assert isinstance(ai_job, AIEditJob)
    assert ai_job.images == [image]
    assert ai_job.prompt == "keep subject and generate print"
    assert ai_job.api_key == "stored-key"
    assert ai_job.api_base == "https://provider-two.example/v1"
    assert ai_job.model == "provider-two-model"
    assert ai_job.size == "1536x1024"
    assert ai_job.prefix == "SZW"
    assert ai_job.start_number == 3113
    assert ai_job.total_return_count == 2
    assert ai_job.split_collage is True
    assert ai_job.split_count == 25
    assert ai_job.test_mode is False
    assert not hasattr(page, "split_collage_check")
    assert not hasattr(page, "split_count_spin")

    page.close()


def test_product_publish_page_confirm_and_start_enters_generating_state(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(
        tmp_path,
        monkeypatch,
        AppSettings(
            bo_product_title="BO default title",
            szw_product_title="SZW default title",
            program_data_dir=str(tmp_path / "ConsolePlatData"),
        ),
    )
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    starts = []

    def fake_start_generation(record):
        starts.append(record.task_id)
        record.status = "generating"
        record.stage_text = "生图中"
        record.progress_percent = 30
        page._append_record_log(record, "已进入生图阶段")
        page._save_and_refresh(record)

    monkeypatch.setattr(page, "_start_generation", fake_start_generation)

    page.confirm_and_start()

    saved = (Path(SettingsStore(path).load().program_data_dir) / "tasks" / "product_publish_tasks.json").read_text(
        encoding="utf-8"
    )
    assert starts == [page.tasks[0].task_id]
    assert page.task_list.count() == 1
    assert page.tasks[0].status == "generating"
    assert page.tasks[0].stage_text == "生图中"
    assert page.tasks[0].handoff_mode == "同步并唤起"
    assert page.tasks[0].product_title == "BO default title"
    assert "产品标题" not in page.tasks[0].confirmation_summary
    assert "不会自动点击真实发布按钮" in page.tasks[0].confirmation_summary
    assert "generating" in saved

    page.close()


def test_product_publish_page_stop_button_kills_running_task(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    record = ProductTaskRecord(
        task_id="20260623112000",
        task_name="stop task",
        prefix="BO",
        start_number=1001,
        count=2,
        generation_mode="本地生图",
        product_title="fixed title",
        status="generating",
        stage_text="生图中",
        progress_percent=30,
    )
    page.current_task = record
    page.tasks = [record]
    page.stop_button.setEnabled(True)

    class FakeProcess:
        def __init__(self):
            self.killed = False

        def kill(self):
            self.killed = True

    fake_process = FakeProcess()
    page.process = fake_process

    page.stop_job()

    assert fake_process.killed is True
    assert page._stopping_task_id == "20260623112000"

    page.close()


def test_product_publish_page_restores_persisted_tasks(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    settings_path = tmp_path / "settings.json"
    program_data_dir = tmp_path / "ConsolePlatData"
    SettingsStore(settings_path).save(AppSettings(program_data_dir=str(program_data_dir)))
    tasks_dir = program_data_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (tasks_dir / "product_publish_tasks.json").write_text(
        '[{"task_id":"20260622120000","task_name":"BO publish task","prefix":"BO","start_number":1661,'
        '"count":10,"generation_mode":"本地生图","handoff_mode":"同步并唤起","test_mode":true,'
        '"product_title":"fixed title","status":"synced","stage_text":"已同步","progress_percent":80,'
        '"logs":["12:00 done"],"product_dir":"E:/products","xlsx_path":"E:/batch.xlsx",'
        '"failure_reason":"","confirmation_summary":"不会自动点击真实发布按钮"}]',
        encoding="utf-8",
    )
    monkeypatch.setattr("consoleplat.ui.product_publish_page.SettingsStore", lambda: SettingsStore(settings_path))

    page = ProductPublishPage()

    assert page.task_list.count() == 1
    assert page.tasks[0].status == "synced"
    assert page.tasks[0].product_dir == "E:/products"

    page.close()


def test_validate_publish_outputs_requires_images_xlsx_and_matching_count(tmp_path):
    product_dir = tmp_path / "products"
    product_dir.mkdir()
    (product_dir / "BO-1001.png").write_bytes(b"image")
    xlsx_path = tmp_path / "batch.xlsx"
    xlsx_path.write_bytes(b"xlsx")

    ok = validate_publish_outputs(
        product_dir=product_dir,
        xlsx_path=xlsx_path,
        expected_count=1,
        prefix="BO",
        start_number=1001,
    )

    assert ok.ok is True
    assert ok.image_count == 1

    bad = validate_publish_outputs(
        product_dir=product_dir,
        xlsx_path=xlsx_path,
        expected_count=2,
        prefix="BO",
        start_number=1001,
    )

    assert bad.ok is False
    assert "图片数量" in bad.message


def test_product_publish_page_sync_stops_when_validation_fails(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    calls = []
    monkeypatch.setattr("consoleplat.ui.product_publish_page.sync_putaway_assets", lambda **kwargs: calls.append(kwargs))
    record = ProductTaskRecord(
        task_id="20260622120000",
        task_name="BO publish task",
        prefix="BO",
        start_number=1001,
        count=2,
        generation_mode="本地生图",
        product_title="fixed title",
        product_dir=str(tmp_path / "missing-products"),
        xlsx_path=str(tmp_path / "missing.xlsx"),
    )

    result = page.validate_and_sync(record)

    assert result.ok is False
    assert calls == []
    assert record.status == "failed"
    assert record.failure_reason

    page.close()


def test_product_publish_page_finish_local_generation_auto_syncs_and_handoffs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    launches = []
    sync_calls = []

    record = ProductTaskRecord(
        task_id="20260622123000",
        task_name="BO publish task",
        prefix="BO",
        start_number=1001,
        count=2,
        generation_mode="本地生图",
        product_title="fixed title",
        test_mode=False,
    )

    class Summary:
        ok = True
        print_dir = str(tmp_path / "prints")
        raw_dir = ""
        mockup_dir = str(tmp_path / "products")
        xlsx_path = str(tmp_path / "batch.xlsx")
        message = "本地生图完成"

    monkeypatch.setattr("consoleplat.ui.product_publish_page.PosAiImgAdapter.parse_finished_result", lambda *_args, **_kwargs: Summary())

    def fake_validate_and_sync(target):
        sync_calls.append(target.task_id)
        target.status = "synced"
        target.stage_text = "已同步"
        target.progress_percent = 80
        return PutawaySyncSummary(ok=True, message="同步完成")

    monkeypatch.setattr(page, "validate_and_sync", fake_validate_and_sync)
    monkeypatch.setattr(page, "_launch_putaway_record", lambda target: launches.append(target.task_id))

    page._finish_local_generation(record, 0)

    assert sync_calls == ["20260622123000"]
    assert launches == ["20260622123000"]

    page.close()


def test_product_publish_page_finish_ai_generation_auto_formalizes_and_handoffs(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    launches = []
    formalize_calls = []
    record = ProductTaskRecord(
        task_id="20260622124500",
        task_name="SZW publish task",
        prefix="SZW",
        start_number=3213,
        count=2,
        generation_mode="AI 改图",
        product_title="fixed title",
        test_mode=False,
    )
    record.job_payload = {
        "images": [str(tmp_path / "ref.png")],
        "prompt": "keep subject",
        "api_base": "https://api.openai.com/v1",
        "model": "gpt-image-2",
        "output_dir": str(tmp_path / "gallery" / "SZW" / "2026" / "6月" / "AI改图_SZW-3213-SZW-3262_2026.0622.2040.30" / "临时输出"),
        "size": "1024x1024",
        "split_collage": True,
        "split_count": 25,
        "total_return_count": 2,
    }

    class AISummary:
        ok = True
        output_dir = str(tmp_path / "gallery" / "output")
        outputs = ["one_part_01.png", "one_part_02.png"]
        failed = []
        warnings = []
        message = "AI 改图完成"

    monkeypatch.setattr("consoleplat.ui.product_publish_page.PosAiImgAdapter.parse_ai_edit_result", lambda *_args, **_kwargs: AISummary())

    def fake_formalize(target, outputs):
        formalize_calls.append((target.task_id, list(outputs)))
        target.product_dir = str(tmp_path / "products")
        target.xlsx_path = str(tmp_path / "batch.xlsx")
        target.status = "synced"
        target.stage_text = "已同步"
        target.progress_percent = 80
        return True

    monkeypatch.setattr(page, "_formalize_ai_outputs", fake_formalize)
    monkeypatch.setattr(page, "_launch_putaway_record", lambda target: launches.append(target.task_id))

    page._finish_ai_generation(record, 0)

    assert formalize_calls == [("20260622124500", ["one_part_01.png", "one_part_02.png"])]
    assert launches == ["20260622124500"]

    page.close()


def test_product_publish_page_syncs_mirror_task_store_for_local_and_ai(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(tmp_path, monkeypatch)
    local_record = ProductTaskRecord(
        task_id="20260622130000",
        task_name="local publish",
        prefix="BO",
        start_number=1661,
        count=10,
        generation_mode="本地生图",
        product_title="fixed title",
        status="generated",
        stage_text="生图完成",
        progress_percent=55,
        product_dir="E:/products",
        xlsx_path="E:/local.xlsx",
        job_payload={
            "style_name": "仿油彩名画风格竖版印花",
            "steps": 28,
            "seed": 2026061702,
            "test_mode": False,
            "auto_start_comfyui": True,
            "keep_comfyui": True,
            "gallery_root": "E:/gallery",
            "mockup_root": "E:/mockup",
            "xlsx_root": "E:/xlsx",
        },
    )
    ai_record = ProductTaskRecord(
        task_id="20260622130100",
        task_name="ai publish",
        prefix="SZW",
        start_number=3213,
        count=2,
        generation_mode="AI 改图",
        product_title="fixed title",
        status="synced",
        stage_text="已同步",
        progress_percent=80,
        output_dir="E:/ai/output",
        product_dir="E:/ai/products",
        xlsx_path="E:/ai.xlsx",
        job_payload={
            "images": ["E:/ref.png"],
            "prompt": "keep subject",
            "api_base": "https://api.openai.com/v1",
            "model": "gpt-image-2",
            "output_dir": "E:/ai/output",
            "size": "1024x1024",
            "split_collage": True,
            "split_count": 25,
            "total_return_count": 2,
            "gallery_root": "E:/gallery",
            "mockup_root": "E:/mockup",
            "xlsx_root": "E:/xlsx",
        },
    )

    page._sync_mirror_task(local_record)
    page._sync_mirror_task(ai_record)

    program_data_dir = Path(SettingsStore(path).load().program_data_dir)
    local_saved = (program_data_dir / "tasks" / "local_image_tasks.json").read_text(encoding="utf-8")
    ai_saved = (program_data_dir / "tasks" / "ai_edit_tasks.json").read_text(encoding="utf-8")

    assert "20260622130000" in local_saved
    assert "20260622130100" in ai_saved

    page.close()


def test_product_publish_page_auto_saves_adjustable_config(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    settings_path = tmp_path / "settings.json"
    SettingsStore(settings_path).save(AppSettings(program_data_dir=str(tmp_path / "ConsolePlatData")))
    monkeypatch.setattr("consoleplat.ui.product_publish_page.SettingsStore", lambda: SettingsStore(settings_path))

    page = ProductPublishPage()
    reference = tmp_path / "ref.png"
    reference.write_bytes(b"fake")

    page.prefix_combo.setCurrentText("SZW")
    page.task_name_edit.setText("自动保存任务")
    page.start_spin.setValue(4321)
    page.generation_mode_combo.setCurrentIndex(1)
    page.count_spin.setValue(3)
    page.test_mode_check.setChecked(False)
    page._add_reference_image(str(reference))
    page.ai_prompt_edit.setPlainText("save ai prompt")
    page.generation_mode_combo.setCurrentIndex(0)
    page.count_spin.setValue(12)
    page.steps_spin.setValue(33)
    page.seed_spin.setValue(123456)
    page.auto_start_comfyui_check.setChecked(False)
    page.keep_comfyui_check.setChecked(False)
    page.close()

    restored = ProductPublishPage()

    assert restored.prefix_combo.currentText() == "SZW"
    assert restored.task_name_edit.text() == "自动保存任务"
    assert restored.start_spin.value() == 4321
    assert restored.generation_mode_combo.currentText() == "本地生图"
    assert restored.count_spin.value() == 12
    assert restored.test_mode_check.isChecked() is False
    assert restored.steps_spin.value() == 33
    assert restored.seed_spin.value() == 123456
    assert restored.auto_start_comfyui_check.isChecked() is False
    assert restored.keep_comfyui_check.isChecked() is False
    assert restored._reference_images == [reference]
    assert restored.ai_prompt_edit.toPlainText() == "save ai prompt"

    restored.generation_mode_combo.setCurrentIndex(1)
    assert restored.count_spin.value() == 3

    restored.close()


def test_product_publish_page_delete_task_removes_files_and_history(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(tmp_path, monkeypatch)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    batch_dir = tmp_path / "gallery" / "BO" / "2026" / "6月" / "AI改图_BO-1661-BO-1710_2026.0623.1010.10"
    output_dir = batch_dir / "临时输出"
    final_transparent_dir = batch_dir / "最终透明底"
    product_batch_dir = tmp_path / "mockup" / "BO" / "2026" / "6月" / batch_dir.name
    final_product_dir = product_batch_dir / "最终产品图"
    xlsx_path = tmp_path / "xlsx" / "BO" / f"{batch_dir.name}.xlsx"
    for folder in (output_dir, final_transparent_dir, final_product_dir):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "sample.png").write_bytes(b"image")
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    xlsx_path.write_bytes(b"xlsx")

    record = ProductTaskRecord(
        task_id="20260623101010",
        task_name="delete publish task",
        prefix="BO",
        start_number=1661,
        count=2,
        generation_mode="AI 改图",
        product_title="fixed title",
        status="handoff",
        stage_text="已唤起上架",
        progress_percent=100,
        output_dir=str(output_dir),
        product_dir=str(final_product_dir),
        xlsx_path=str(xlsx_path),
        job_payload={
            "output_dir": str(output_dir),
            "batch_dir": str(batch_dir),
            "final_transparent_dir": str(final_transparent_dir),
            "final_product_dir": str(final_product_dir),
            "xlsx_root": str(tmp_path / "xlsx"),
            "mockup_root": str(tmp_path / "mockup"),
            "gallery_root": str(tmp_path / "gallery"),
        },
    )
    page.tasks = [record]
    page._save_task_history()
    page._sync_mirror_task(record)
    page._rebuild_task_list()
    page._select_record(record)

    page.delete_selected_tasks()

    program_data_dir = Path(SettingsStore(path).load().program_data_dir)
    publish_saved = (program_data_dir / "tasks" / "product_publish_tasks.json").read_text(encoding="utf-8")
    ai_saved = (program_data_dir / "tasks" / "ai_edit_tasks.json").read_text(encoding="utf-8")

    assert page.task_list.count() == 0
    assert "20260623101010" not in publish_saved
    assert "20260623101010" not in ai_saved
    assert not batch_dir.exists()
    assert not final_product_dir.exists()
    assert not xlsx_path.exists()

    page.close()


def test_product_publish_page_delete_local_task_removes_local_mirror_record(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, path = _page_with_temp_store(tmp_path, monkeypatch)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    print_dir = tmp_path / "prints"
    product_dir = tmp_path / "products"
    xlsx_path = tmp_path / "batch.xlsx"
    for folder in (print_dir, product_dir):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "sample.png").write_bytes(b"image")
    xlsx_path.write_bytes(b"xlsx")

    record = ProductTaskRecord(
        task_id="20260623101500",
        task_name="local delete task",
        prefix="BO",
        start_number=2001,
        count=10,
        generation_mode="本地生图",
        product_title="fixed title",
        status="generated",
        stage_text="生图完成",
        progress_percent=55,
        output_dir=str(print_dir),
        product_dir=str(product_dir),
        xlsx_path=str(xlsx_path),
        job_payload={
            "style_name": "仿油彩名画风格竖版印花",
            "steps": 28,
            "seed": 2026061702,
            "test_mode": False,
            "auto_start_comfyui": True,
            "keep_comfyui": True,
            "gallery_root": str(tmp_path / "gallery"),
            "mockup_root": str(tmp_path / "mockup"),
            "xlsx_root": str(tmp_path / "xlsx"),
        },
    )
    page.tasks = [record]
    page._save_task_history()
    page._sync_mirror_task(record)
    page._rebuild_task_list()
    page._select_record(record)

    page.delete_selected_tasks()

    program_data_dir = Path(SettingsStore(path).load().program_data_dir)
    local_saved = (program_data_dir / "tasks" / "local_image_tasks.json").read_text(encoding="utf-8")

    assert "20260623101500" not in local_saved
    assert not print_dir.exists()
    assert not product_dir.exists()
    assert not xlsx_path.exists()

    page.close()


def test_product_publish_page_delete_task_ignores_empty_or_workspace_paths(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    page, _path = _page_with_temp_store(tmp_path, monkeypatch)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.Yes)

    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")

    record = ProductTaskRecord(
        task_id="20260623110000",
        task_name="unsafe delete task",
        prefix="BO",
        start_number=3001,
        count=2,
        generation_mode="本地生图",
        product_title="fixed title",
        output_dir="",
        product_dir=".",
        xlsx_path="",
    )
    page.tasks = [record]
    page._rebuild_task_list()
    page._select_record(record)

    page.delete_selected_tasks()

    assert sentinel.exists()

    page.close()


def test_product_task_statuses_are_fixed():
    assert PRODUCT_TASK_STATUSES == (
        "draft",
        "confirmed",
        "generating",
        "generated",
        "validating",
        "synced",
        "handoff",
        "failed",
    )
