import os
import tempfile
import unittest
from unittest import mock

from config_store import load_runtime_settings, save_runtime_settings


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


if __name__ == "__main__":
    unittest.main()
