from __future__ import annotations

import unittest

from main import compliance_upload_steps, run_compliance_upload_steps


class ComplianceBatchRunnerTest(unittest.TestCase):
    def test_runs_all_compliance_steps_in_order_with_selected_page_size_and_continues_after_failure(self) -> None:
        calls: list[str] = []
        logs: list[str] = []

        class FakeWorker:
            def upload_california_65_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"california:{target_page_size}")
                return 1

            def upload_manufacturer_attribute_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"manufacturer_attribute:{target_page_size}")
                raise RuntimeError("制造商属性失败")

            def upload_production_shelf_life_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"shelf_life:{target_page_size}")
                return 2

            def upload_warning_safety_supplement_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"warning:{target_page_size}")
                return 3

            def upload_packaging_material_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"packaging:{target_page_size}")
                return 4

            def upload_turkey_responsible_person_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"turkey:{target_page_size}")
                return 5

            def upload_manufacturer_info_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"manufacturer_info:{target_page_size}")
                return 6

            def upload_eu_responsible_person_compliance_info(self, *, target_page_size: int) -> int:
                calls.append(f"eu:{target_page_size}")
                return 7

            def upload_product_identifier_file(self, *, target_page_size: int):
                calls.append(f"identifier:{target_page_size}")

                class Result:
                    spu_count = 8

                return Result()

            def upload_compliant_live_photos(self, *, submit: bool) -> int:
                calls.append(f"live_photos:{submit}")
                return 9

        results = run_compliance_upload_steps(FakeWorker(), logs.append, target_page_size=50)

        self.assertEqual(
            calls,
            [
                "california:50",
                "manufacturer_attribute:50",
                "shelf_life:50",
                "warning:50",
                "packaging:50",
                "turkey:50",
                "manufacturer_info:50",
                "eu:50",
                "identifier:50",
                "live_photos:True",
            ],
        )
        self.assertEqual([result.name for result in results], [
            "批量上传加州65号提案",
            "批量上传制造商属性",
            "批量上传生产/保质期",
            "批量上传警告或安全信息",
            "批量上传包装材料信息",
            "批量上传土耳其负责人",
            "批量上传制造商信息",
            "批量上传欧盟负责人",
            "批量上传商品识别码",
            "批量上传商品合规图",
        ])
        self.assertFalse(results[1].success)
        self.assertTrue(results[-1].success)
        self.assertIn("失败：批量上传制造商属性：制造商属性失败", logs)

    def test_compliance_steps_do_not_hardcode_100_page_size(self) -> None:
        class FakeWorker:
            def upload_product_identifier_file(self, *, target_page_size: int):
                class Result:
                    spu_count = f"identifier:{target_page_size}"

                return Result()

            def upload_compliant_live_photos(self, *, submit: bool) -> str:
                return "live_photos:50"

            def __getattr__(self, name: str):
                if name.startswith("upload_"):
                    return lambda *, target_page_size: f"{name}:{target_page_size}"
                raise AttributeError(name)

        messages = [action() for _name, action in compliance_upload_steps(FakeWorker(), target_page_size=50)]

        self.assertTrue(all(":50" in message for message in messages))
        self.assertFalse(any(":100" in message for message in messages))

    def test_compliance_steps_stop_before_next_step_when_requested(self) -> None:
        calls: list[str] = []

        class FakeWorker:
            def upload_california_65_compliance_info(self, *, target_page_size: int) -> int:
                calls.append("california")
                return 1

            def upload_manufacturer_attribute_compliance_info(self, *, target_page_size: int) -> int:
                calls.append("manufacturer_attribute")
                return 1

            def __getattr__(self, name: str):
                if name.startswith("upload_"):
                    return lambda **_kwargs: calls.append(name) or 1
                raise AttributeError(name)

        checks = iter([False, True])
        results = run_compliance_upload_steps(
            FakeWorker(),
            lambda _message: None,
            target_page_size=50,
            should_stop=lambda: next(checks, True),
        )

        self.assertEqual(calls, ["california"])
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
