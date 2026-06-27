from __future__ import annotations

import unittest
import inspect

from models import GoodsListResult
from main import run_chain_steps, run_full_chain_steps, run_template_group_management
from temu_goods import TemuGoodsList


class FullChainRunnerTest(unittest.TestCase):
    def test_template_group_management_collects_skc_before_applying_template(self) -> None:
        calls: list[tuple[str, object]] = []

        class FakeWorker:
            def prepare_and_collect_skc_ids(self, *, copy_to_clipboard: bool, target_page_size: int) -> GoodsListResult:
                calls.append(("copy", copy_to_clipboard, target_page_size))
                return GoodsListResult(
                    total_count=2,
                    page_size=target_page_size,
                    selected=True,
                    skc_ids=["1001", "1002"],
                    copied_to_clipboard=copy_to_clipboard,
                    raw_skc_text="1001\n1002",
                )

            def apply_to_template_group(self, skc_text: str) -> int:
                calls.append(("template", skc_text))
                return 2

        result, added_count = run_template_group_management(FakeWorker(), page_size=50)

        self.assertEqual(
            calls,
            [
                ("copy", True, 50),
                ("template", "1001\n1002"),
            ],
        )
        self.assertEqual(result.skc_count, 2)
        self.assertEqual(added_count, 2)

    def test_continues_after_failure_and_records_failed_steps(self) -> None:
        calls: list[str] = []
        logs: list[str] = []

        def fail_copy() -> str:
            calls.append("copy")
            raise RuntimeError("复制失败")

        def fail_template() -> str:
            calls.append("template")
            raise RuntimeError("缺少 SKC ID")

        def later_step() -> str:
            calls.append("jit")
            return "已开通 3 个商品"

        results = run_chain_steps(
            [
                ("批量复制SKC ID", fail_copy),
                ("套版组管理", fail_template),
                ("开通JIT", later_step),
            ],
            logs.append,
        )

        self.assertEqual(calls, ["copy", "template", "jit"])
        self.assertEqual([result.name for result in results if not result.success], ["批量复制SKC ID", "套版组管理"])
        self.assertEqual(results[0].message, "复制失败")
        self.assertEqual(results[1].message, "缺少 SKC ID")
        self.assertTrue(results[2].success)
        self.assertIn("失败：批量复制SKC ID：复制失败", logs)

    def test_full_chain_runs_three_business_phases_and_cleans_site_popups_between_steps(self) -> None:
        calls: list[str] = []
        logs: list[str] = []

        class FakeWorker:
            def dismiss_transient_site_popups(self) -> int:
                calls.append("cleanup")
                return 1

            def prepare_and_collect_skc_ids(self, *, copy_to_clipboard: bool, target_page_size: int) -> GoodsListResult:
                calls.append(f"copy:{copy_to_clipboard}:{target_page_size}")
                return GoodsListResult(
                    total_count=2,
                    page_size=target_page_size,
                    selected=True,
                    skc_ids=["1001", "1002"],
                    copied_to_clipboard=copy_to_clipboard,
                    raw_skc_text="1001\n1002",
                )

            def apply_to_template_group(self, skc_text: str) -> int:
                calls.append(f"template:{skc_text}")
                return 2

            def upload_california_65_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"california:{target_page_size}")
                return 0

            def upload_manufacturer_attribute_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"manufacturer_attribute:{target_page_size}")
                return 0

            def upload_production_shelf_life_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"shelf_life:{target_page_size}")
                return 0

            def upload_warning_safety_supplement_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"warning:{target_page_size}")
                return 0

            def upload_packaging_material_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"packaging:{target_page_size}")
                return 0

            def upload_turkey_responsible_person_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"turkey:{target_page_size}")
                return 0

            def upload_manufacturer_info_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"manufacturer_info:{target_page_size}")
                return 0

            def upload_eu_responsible_person_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"eu:{target_page_size}")
                return 0

            def upload_product_identifier_file(self, *, target_page_size: int):
                calls.append(f"identifier:{target_page_size}")

                class Result:
                    spu_count = 0

                return Result()

            def upload_compliant_live_photos(self, *, submit: bool) -> int:
                calls.append(f"live_photos:{submit}")
                return 0

            def batch_open_jit_management(self, *, submit: bool, target_page_size: int) -> int:
                calls.append(f"jit:{submit}:{target_page_size}")
                return 2

        results = run_full_chain_steps(FakeWorker(), logs.append, target_page_size=50)

        self.assertEqual(
            [result.name for result in results],
            ["套版组管理", "批量上传合规信息", "批量开通JIT管理"],
        )
        self.assertEqual(calls[0], "cleanup")
        self.assertEqual(calls[-1], "cleanup")
        self.assertIn("template:1001\n1002", calls)
        self.assertLess(calls.index("template:1001\n1002"), calls.index("california:50"))
        self.assertLess(calls.index("live_photos:True"), calls.index("jit:True:50"))
        self.assertGreaterEqual(calls.count("cleanup"), 4)
        self.assertTrue(all(result.success for result in results))
        self.assertIn("已清理网站弹窗", "\n".join(logs))

    def test_transient_popup_cleanup_protects_business_modals(self) -> None:
        source = inspect.getsource(TemuGoodsList)

        self.assertIn("def dismiss_transient_site_popups", source)
        self.assertIn("def _click_transient_site_popup_close", source)
        self.assertIn("批量上传合规信息", source)
        self.assertIn("批量开通JIT", source)
        self.assertIn("添加同面料套版", source)
        self.assertIn("稍后再说", source)
        self.assertIn("我知道了", source)

    def test_full_chain_marks_compliance_phase_failed_when_any_inner_compliance_step_fails(self) -> None:
        calls: list[str] = []

        class FakeWorker:
            def dismiss_transient_site_popups(self) -> int:
                return 0

            def prepare_and_collect_skc_ids(self, *, copy_to_clipboard: bool, target_page_size: int) -> GoodsListResult:
                return GoodsListResult(
                    total_count=1,
                    page_size=target_page_size,
                    selected=True,
                    skc_ids=["1001"],
                    copied_to_clipboard=copy_to_clipboard,
                    raw_skc_text="1001",
                )

            def apply_to_template_group(self, skc_text: str) -> int:
                return 1

            def upload_california_65_compliance_info(self, *, target_page_size: int) -> int:
                raise RuntimeError("加州失败")

            def batch_open_jit_management(self, *, submit: bool, target_page_size: int) -> int:
                calls.append("jit")
                return 1

            def __getattr__(self, name: str):
                if name.startswith("upload_"):
                    return lambda **_kwargs: 0
                raise AttributeError(name)

        results = run_full_chain_steps(FakeWorker(), lambda _message: None, target_page_size=50)

        self.assertTrue(results[0].success)
        self.assertEqual(results[1].name, "批量上传合规信息")
        self.assertFalse(results[1].success)
        self.assertIn("加州失败", results[1].message)
        self.assertEqual(calls, ["jit"])
        self.assertTrue(results[2].success)


if __name__ == "__main__":
    unittest.main()
