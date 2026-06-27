from __future__ import annotations

import inspect
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


_MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
sys.path.insert(0, str(_MAIN_PATH.parent))
_SPEC = spec_from_file_location("main", _MAIN_PATH)
assert _SPEC and _SPEC.loader
_MODULE = module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)

ApplyGoodsEmbeddedWidget = _MODULE.ApplyGoodsEmbeddedWidget
MainWindow = _MODULE.MainWindow
SingleComplianceDialog = _MODULE.SingleComplianceDialog


class MainUiSourceTest(unittest.TestCase):
    def test_main_compliance_button_and_dialog_button_are_present(self) -> None:
        source = inspect.getsource(ApplyGoodsEmbeddedWidget)

        self.assertIn('QPushButton("批量上传合规信息")', source)
        self.assertIn('QPushButton("单项合规上传")', source)
        self.assertIn('QPushButton("停止当前任务")', source)
        self.assertIn('self.summary_label.setMaximumWidth(120)', source)
        self.assertIn('self.summary_label.setToolTip(f"{title}：运行中…")', source)
        self.assertIn('self.summary_label.setToolTip("正在停止当前任务…")', source)
        self.assertIn('self.summary_label.setToolTip(result.summary)', source)
        self.assertNotIn('QPushButton("批量上传加州65号提案")', source)
        self.assertNotIn('QPushButton("批量上传欧盟负责人")', source)
        self.assertNotIn('identifier_btn = QPushButton("批量上传商品识别码")', source)
        self.assertNotIn('live_photos_btn = QPushButton("批量上传商品合规图")', source)

    def test_long_running_entry_points_dispatch_background_tasks(self) -> None:
        for method_name in [
            "open_browser",
            "apply_template_group",
            "run_full_chain",
            "upload_all_compliance_info",
            "upload_product_identifier",
            "upload_compliant_live_photos",
            "batch_open_jit_management",
            "batch_set_expected_arrival_area",
            "upload_inventory_setting",
        ]:
            source = inspect.getsource(getattr(ApplyGoodsEmbeddedWidget, method_name))
            self.assertTrue(
                "self.run_worker_task(" in source or "self.run_single_count_task(" in source,
                method_name,
            )

    def test_embedded_widget_has_visual_layout_helpers(self) -> None:
        source = inspect.getsource(ApplyGoodsEmbeddedWidget)

        self.assertIn("def _apply_visual_style", source)
        self.assertIn("def _create_section", source)
        self.assertIn("def _create_workflow_step", source)
        self.assertIn("def _create_operation_group", source)
        self.assertIn("def _create_action_button", source)
        self.assertIn('status_col = QVBoxLayout()', source)
        self.assertIn("step.setMinimumWidth(170)", source)
        self.assertIn('form_cards = QVBoxLayout()', source)
        self.assertIn('operations_card = QFrame()', source)

    def test_embedded_widget_stop_task_and_close_browser_controls_are_present(self) -> None:
        source = inspect.getsource(ApplyGoodsEmbeddedWidget)

        self.assertIn("def stop_current_task", source)
        self.assertIn("def close_controlled_browser", source)
        self.assertIn("self.stop_button", source)
        self.assertIn("request_stop()", source)
        self.assertIn("terminate()", source)

    def test_stop_task_does_not_close_browser_directly(self) -> None:
        source = inspect.getsource(ApplyGoodsEmbeddedWidget.stop_current_task)

        self.assertNotIn("close_controlled_browser", source)
        self.assertNotIn("close_remote_browser", source)
        self.assertNotIn("关闭浏览器", source)

    def test_stop_task_uses_immediate_force_stop_without_three_second_grace_period(self) -> None:
        stop_source = inspect.getsource(ApplyGoodsEmbeddedWidget.stop_current_task)
        force_source = inspect.getsource(ApplyGoodsEmbeddedWidget.force_stop_worker_thread)

        self.assertIn("self.force_stop_worker_thread()", stop_source)
        self.assertNotIn("QTimer.singleShot(3000", stop_source)
        self.assertNotIn("wait(3000)", force_source)

    def test_single_compliance_dialog_contains_identifier_and_live_photo_actions(self) -> None:
        source = inspect.getsource(SingleComplianceDialog)

        self.assertIn('("批量上传商品识别码", parent.upload_product_identifier)', source)
        self.assertIn('("批量上传商品合规图", parent.upload_compliant_live_photos)', source)

    def test_login_account_settings_are_present_and_passed_to_worker(self) -> None:
        source = inspect.getsource(ApplyGoodsEmbeddedWidget)
        worker_source = inspect.getsource(__import__("main").WorkerTask)

        self.assertIn("login_phone_edit", source)
        self.assertIn("login_password_edit", source)
        self.assertIn("登录账号", source)
        self.assertIn("登录密码", source)
        self.assertIn("set_login_credentials", source)
        self.assertIn("login_phone", worker_source)
        self.assertIn("login_password", worker_source)

    def test_main_window_wraps_embedded_widget(self) -> None:
        source = inspect.getsource(MainWindow)

        self.assertIn("create_apply_goods_widget(self)", source)
        self.assertIn("setCentralWidget(self.embedded_widget)", source)


if __name__ == "__main__":
    unittest.main()
