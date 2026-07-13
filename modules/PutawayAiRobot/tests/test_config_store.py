import json
import os
import tempfile
import unittest
from unittest import mock

from config_store import load_runtime_settings, runtime_settings_path, save_runtime_settings


class RuntimeSettingsTest(unittest.TestCase):
    def test_saves_and_loads_latest_excel_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            appdata = os.path.join(tmp, "appdata")
            excel_dir = os.path.join(tmp, "excels")
            os.makedirs(excel_dir)

            with mock.patch.dict(os.environ, {"APPDATA": appdata}):
                save_runtime_settings(1, 50, 40, "auto", 3, excel_dir)
                settings = load_runtime_settings()

            self.assertEqual(settings["latest_excel_dir"], excel_dir)

    def test_missing_declare_price_uses_new_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            appdata = os.path.join(tmp, "appdata")

            with mock.patch.dict(os.environ, {"APPDATA": appdata}):
                os.makedirs(os.path.dirname(runtime_settings_path()), exist_ok=True)
                with open(runtime_settings_path(), "w", encoding="utf-8") as f:
                    json.dump({"parallel_count": 2}, f)

                settings = load_runtime_settings()

            self.assertEqual(settings["declare_price"], "14")

    def test_saves_declare_price_as_canonical_decimal(self):
        with tempfile.TemporaryDirectory() as tmp:
            appdata = os.path.join(tmp, "appdata")

            with mock.patch.dict(os.environ, {"APPDATA": appdata}):
                save_runtime_settings(1, 50, 40, "auto", 3, "", "14.50")
                settings = load_runtime_settings()
                with open(runtime_settings_path(), "r", encoding="utf-8") as f:
                    stored = json.load(f)

            self.assertEqual(settings["declare_price"], "14.5")
            self.assertEqual(stored["declare_price"], "14.5")

    def test_invalid_declare_prices_fall_back_to_default(self):
        invalid_values = ["0", "-1", "14.555", "not-a-price"]

        for invalid_value in invalid_values:
            with self.subTest(invalid_value=invalid_value), tempfile.TemporaryDirectory() as tmp:
                appdata = os.path.join(tmp, "appdata")
                with mock.patch.dict(os.environ, {"APPDATA": appdata}):
                    os.makedirs(os.path.dirname(runtime_settings_path()), exist_ok=True)
                    with open(runtime_settings_path(), "w", encoding="utf-8") as f:
                        json.dump({"declare_price": invalid_value}, f)

                    settings = load_runtime_settings()

                self.assertEqual(settings["declare_price"], "14")


if __name__ == "__main__":
    unittest.main()
