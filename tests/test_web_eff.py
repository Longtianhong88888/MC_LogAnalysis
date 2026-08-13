"""联网 EFF（戰情中心 CMS 接口）接入测试。"""

import os
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from models.analysis import (
    _finalize_status,
    summarize_eff_coretech,
    summarize_machine_eff,
    web_runlog_records,
)
from models.log_model import LogModel


def runlog_row(**kw):
    base = {
        "happentime": "2026-08-12 08:00:00",
        "endtime": "2026-08-12 08:18:57",
        "status": "DOWN",
        "reasonid": "0000010792",
        "downFlag": "Routine downtime",
        "spendTime": 18.95,
    }
    base.update(kw)
    return base


class WebRunlogRecordsTest(unittest.TestCase):
    def test_convert_segments(self):
        rows = [
            runlog_row(),
            runlog_row(happentime="2026-08-12 08:18:57", endtime="2026-08-12 08:19:08",
                       status="RUN", reasonid="", downFlag="", spendTime=0.1833),
            runlog_row(happentime="2026-08-12 08:19:08", endtime="2026-08-12 08:22:06",
                       status="RUN", reasonid="0000010780", downFlag="RU00F"),
            # endtime 缺失 → 用 spendTime 分钟回退
            runlog_row(happentime="2026-08-12 08:22:06", endtime="",
                       status="IDLE", reasonid="0000010000", spendTime=0.0667),
            # 纯日期 happentime 按当天 00:00
            runlog_row(happentime="2026-08-12", endtime="2026-08-12 01:00:00",
                       status="IDLE", reasonid="0000010000", spendTime=60),
        ]
        records = web_runlog_records(rows, "CAW7203")
        self.assertEqual(len(records), 5)
        self.assertEqual(records[0]["FileName"], "CAW7203")
        self.assertEqual(records[0]["Status"], "DOWN")
        self.assertEqual(records[0]["DurationSeconds"], 1137.0)
        self.assertEqual(records[0]["DownFlag"], "Routine downtime")
        # spendTime 回退：0.0667 分钟 = 4.002 秒
        self.assertAlmostEqual(records[3]["DurationSeconds"], 4.002, delta=0.01)
        # 纯日期 start
        self.assertEqual(records[4]["StartTime"], "2026-08-12 00:00:00.000")
        self.assertEqual(records[4]["DurationSeconds"], 3600.0)

    def test_skip_invalid(self):
        records = web_runlog_records([
            {"happentime": "bad", "status": "RUN"},
            {"happentime": "2026-08-12 00:00:00", "endtime": "2026-08-12 00:01:00", "status": "RU001"},
            {"happentime": "2026-08-12 00:00:00", "endtime": "2026-08-12 00:00:00", "status": "DOWN", "spendTime": 0},
            {"happentime": "2026-08-12 00:00:00", "endtime": "", "status": "DOWN", "spendTime": None},
        ], "M1")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["Status"], "RUN")  # RU001 归一化

    def test_eff_coretech_with_downflag(self):
        records = web_runlog_records([
            runlog_row(),
            runlog_row(happentime="2026-08-12 08:18:57", endtime="2026-08-12 08:33:17",
                       status="RUN", downFlag=""),
            runlog_row(happentime="2026-08-12 08:33:17", endtime="2026-08-12 08:33:58",
                       status="DOWN", reasonid="0000010629", downFlag="Unplanned Downtime"),
        ], "CAW7203")
        summary, _, detail = _finalize_status(records)
        self.assertIn("DownFlag", detail.columns)
        eff = summarize_eff_coretech(
            summary, detail,
            planned_down_flags=("Routine downtime", "Routine Downtime", "Planned"),
        )
        r0 = eff.iloc[0]
        self.assertEqual(r0["计划停机pDT(秒)"], 1137.0)   # Routine downtime
        self.assertEqual(r0["非计划停机uDT(秒)"], 41.0)   # Unplanned Downtime


class SummarizeMachineEffTest(unittest.TestCase):
    def test_normalize(self):
        df = summarize_machine_eff([
            {
                "machineNO": "CAW7203", "machineType": "CAW", "deviceName": "AKC",
                "opno": "CAW", "status": "RUN", "runTime": "650.17", "idleTime": "39.90",
                "errorTime": "749.93", "plannedDT": "100.00", "unPlannedDT": "649.93",
                "eff": "47.92%", "uph": "1234",
                "outputList": [{"data": "2026/08/12", "value": 11036},
                               {"data": "2026/08/11", "value": 18587}],
            }
        ], begin_time="2026/08/12 06:00:00", end_time="2026/08/13 06:00:00")
        r0 = df.iloc[0]
        self.assertEqual(r0["机台号"], "CAW7203")
        self.assertEqual(r0["产出(个)"], 29623)
        self.assertEqual(r0["运行时间RUN(秒)"], 650.17 * 60)
        self.assertEqual(r0["EFF(%)"], "47.92%")
        self.assertIn("2026/08/12", r0["时间范围"])


class AnalyzeEffWebTest(unittest.TestCase):
    MACHINES = [
        {"machineNo": "CAW7203", "machine": "CAW"},
        {"machineNo": "CAW7205", "machine": "CAW"},
        {"machineNo": "LM4401", "machine": "LM"},
    ]

    EFF_ROWS = [{
        "machineNO": "CAW7203", "machineType": "CAW", "deviceName": "AKC",
        "opno": "CAW", "status": "RUN", "runTime": "650.17", "idleTime": "39.90",
        "errorTime": "749.93", "plannedDT": "100.00", "unPlannedDT": "649.93",
        "eff": "47.92%", "uph": "1234",
        "outputList": [{"data": "2026/08/12", "value": 11036}],
    }]

    RUNLOG = [
        runlog_row(),
        runlog_row(happentime="2026-08-12 08:18:57", endtime="2026-08-12 08:19:08",
                   status="RUN", reasonid="", downFlag="", spendTime=0.1833),
        runlog_row(happentime="2026-08-12 08:19:08", endtime="2026-08-12 08:22:06",
                   status="RUN", reasonid="0000010780", downFlag="RU00F", spendTime=2.9667),
        runlog_row(happentime="2026-08-12 08:22:06", endtime="2026-08-12 08:22:10",
                   status="IDLE", reasonid="0000010000", downFlag="", spendTime=0.0667),
        runlog_row(happentime="2026-08-12 08:22:10", endtime="2026-08-12 08:33:17",
                   status="RUN", reasonid="", downFlag="", spendTime=11.1167),
        runlog_row(happentime="2026-08-12 08:33:17", endtime="2026-08-12 08:33:58",
                   status="DOWN", reasonid="0000010629", downFlag="Unplanned Downtime",
                   spendTime=0.6833),
    ]

    def test_end_to_end_web(self):
        out = tempfile.mkdtemp()
        calls = {"runlog": []}

        def fake_machines(base_url, plant_id, **kw):
            return self.MACHINES

        def fake_eff(base_url, plant_id, machine_type="", machine_no="", **kw):
            if machine_type == "CAW":
                return self.EFF_ROWS
            return []

        def fake_runlog(base_url, plant_id, machine_no, machine_type="", **kw):
            calls["runlog"].append((machine_no, machine_type))
            if machine_no == "CAW7203":
                return self.RUNLOG
            return []

        with patch("models.web_api.fetch_machines", side_effect=fake_machines), \
             patch("models.web_api.fetch_machine_eff", side_effect=fake_eff), \
             patch("models.web_api.fetch_run_log", side_effect=fake_runlog):
            result = LogModel().analyze_eff(
                source_dir="", output_dir=out, eff_source="web",
                web_api_url="http://10.151.128.35:8098", web_plant_id="8S01",
                web_machine_type="CAW", web_machine_nos="",
                web_begin_time="2026/08/12 06:00:00", web_end_time="2026/08/13 06:00:00",
            )

        self.assertTrue(os.path.exists(result.split("（")[0]))
        self.assertEqual(set(calls["runlog"]), {("CAW7203", "CAW"), ("CAW7205", "CAW")})
        xl = pd.ExcelFile(result.split("（")[0])
        self.assertIn("Summary", xl.sheet_names)
        self.assertIn("MachineEff", xl.sheet_names)
        self.assertIn("Detail", xl.sheet_names)
        self.assertIn("DOWN_Pareto", xl.sheet_names)
        summary = xl.parse("Summary").iloc[0]
        self.assertEqual(summary["计划停机pDT(秒)"], 1137.0)
        self.assertEqual(summary["非计划停机uDT(秒)"], 41.0)
        self.assertEqual(summary["运行时间RUN(秒)"], 856.0)
        self.assertEqual(summary["待机时间IDLE(秒)"], 4.0)
        self.assertAlmostEqual(summary["EFF(%)"], (856 + 4) / 2038 * 100, delta=0.01)
        me = xl.parse("MachineEff")
        self.assertEqual(len(me), 1)
        self.assertEqual(me.iloc[0]["机台号"], "CAW7203")

    def test_requires_type_or_no(self):
        with self.assertRaises(ValueError):
            LogModel()._analyze_eff_web(
                output_dir=tempfile.mkdtemp(), api_url="http://x", plant_id="8S01",
                machine_type="", machine_nos="",
            )

    def test_normalize_window(self):
        b, e = LogModel._normalize_web_window("2026-08-12 06:00:00", None)
        self.assertEqual(b, "2026/08/12 06:00:00")
        self.assertTrue(e.endswith("06:00:00"))
        with self.assertRaises(ValueError):
            LogModel._normalize_web_window("bad", None)


if __name__ == "__main__":
    unittest.main()
