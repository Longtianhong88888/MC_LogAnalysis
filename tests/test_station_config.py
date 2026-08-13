"""站位配置与机台过滤测试。"""

import json
import os
import tempfile
import unittest

from models.station_config import (
    DEFAULT_STATIONS,
    filter_machines_by_station,
    load_stations,
    load_web_report_memory,
    save_stations,
    save_web_report_memory,
)


class StationConfigTest(unittest.TestCase):
    def test_defaults_when_missing(self):
        tmp = tempfile.mkdtemp()
        stations = load_stations(os.path.join(tmp, "none.json"))
        self.assertEqual(stations, DEFAULT_STATIONS)

    def test_save_load_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "stations.json")
        save_stations(["LM", "SA", "ACF", "FR", "CAW", "自定义"], path)
        self.assertEqual(
            load_stations(path), ["LM", "SA", "ACF", "FR", "CAW", "自定义"]
        )

    def test_corrupt_file_falls_back(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "bad.json")
        with open(path, "w", encoding="utf-8") as f:
            f.write("{not json")
        self.assertEqual(load_stations(path), DEFAULT_STATIONS)

    def test_filter_machines_by_station(self):
        machines = [
            {"machineNo": "CAW7203", "machine": "CAW"},
            {"machineNo": "CAW7205", "machine": "CAW"},
            {"machineNo": "LM4401", "machine": "LM"},
            {"machineNo": "SA4401N", "machineType": "SA"},
            {"machineNo": "NONE", "machine": None},
        ]
        self.assertEqual(
            filter_machines_by_station(machines, "caw"), ["CAW7203", "CAW7205"]
        )
        self.assertEqual(
            filter_machines_by_station(machines, "SA"), ["SA4401N"]
        )
        self.assertEqual(filter_machines_by_station(machines, ""), [])

    def test_web_report_memory_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "memory.json")
        scheme = {
            "station": "FR",
            "machine_nos": "AR6401,AR6403",
            "begin_time": "2026/07/02 06:00:00",
            "end_time": "2026/07/03 06:00:00",
        }
        save_web_report_memory(scheme, path)
        self.assertEqual(load_web_report_memory(path), scheme)

    def test_web_report_memory_missing(self):
        tmp = tempfile.mkdtemp()
        self.assertEqual(load_web_report_memory(os.path.join(tmp, "none.json")), {})


if __name__ == "__main__":
    unittest.main()
