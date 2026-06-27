import os
import tempfile
import time
import unittest

from excel_importer import find_latest_xlsx_in_directory


class FindLatestXlsxInDirectoryTest(unittest.TestCase):
    def test_returns_newest_xlsx_and_ignores_temp_excel_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = os.path.join(tmp, "old.xlsx")
            temp_path = os.path.join(tmp, "~$editing.xlsx")
            new_path = os.path.join(tmp, "new.xlsx")
            for path in [old_path, temp_path, new_path]:
                with open(path, "wb") as f:
                    f.write(b"placeholder")

            now = time.time()
            os.utime(old_path, (now - 20, now - 20))
            os.utime(temp_path, (now + 20, now + 20))
            os.utime(new_path, (now, now))

            self.assertEqual(find_latest_xlsx_in_directory(tmp), new_path)

    def test_raises_when_directory_has_no_excel_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "未找到Excel文件"):
                find_latest_xlsx_in_directory(tmp)


if __name__ == "__main__":
    unittest.main()
