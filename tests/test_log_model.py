import os
import tempfile
import unittest

import pandas as pd

from models.log_model import LogModel


class LogModelTest(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.mkdtemp()
        self.out = tempfile.mkdtemp()
        with open(os.path.join(self.src, "a.log"), "w", encoding="utf-8") as f:
            f.write("2026-08-05 10:00:01 ERROR: servo timeout\n")
            f.write("2026-08-05 10:00:02 INFO: motion done\n")
        with open(os.path.join(self.src, "b.txt"), "w", encoding="gbk") as f:
            f.write("2026-08-05 10:00:03 ERROR: axis jammed\n")

    def _parse(self, **kwargs):
        return LogModel().process(self.src, self.out, **kwargs)

    def test_no_separator_filter(self):
        path = self._parse(keywords="ERROR")
        xl = pd.ExcelFile(path)
        self.assertEqual(xl.sheet_names, ["AllLogs", "Filtered"])
        self.assertEqual(len(xl.parse("AllLogs")), 3)
        self.assertEqual(len(xl.parse("Filtered")), 2)

    def test_separator_with_keywords(self):
        path = self._parse(keywords="ERROR", separator=",")
        df = pd.ExcelFile(path).parse("Filtered")
        self.assertIn("OriginalContent", df.columns)
        self.assertNotIn("Content", df.columns)

    def test_separator_without_keywords(self):
        path = self._parse(separator=",")
        df = pd.ExcelFile(path).parse("Filtered")
        self.assertIn("Part_1", df.columns)
        self.assertNotIn("Content", df.columns)

    def test_progress_callback_reaches_100(self):
        seen = []
        self._parse(keywords="ERROR", progress_callback=seen.append)
        self.assertEqual(seen[-1], 100)

    def test_read_files_recursive(self):
        from utils.file_utils import read_files
        src = tempfile.mkdtemp()
        sub = os.path.join(src, "day1", "station1")
        os.makedirs(sub)
        with open(os.path.join(sub, "a.log"), "w", encoding="utf-8") as f:
            f.write("2026-07-08 00:00:01.000 [status:RUN]\n")
        with open(os.path.join(src, "b.txt"), "w", encoding="utf-8") as f:
            f.write("hello\n")
        rows = read_files(src)
        names = {r["FileName"] for r in rows}
        self.assertIn("day1/station1/a.log", names)
        self.assertIn("b.txt", names)


if __name__ == "__main__":
    unittest.main()
