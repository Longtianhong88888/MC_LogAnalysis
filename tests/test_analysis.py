import os
import tempfile
import unittest

import pandas as pd

from models.analysis import (
    analyze_status,
    build_cycles_df,
    down_pareto,
    parse_em_production,
    summarize_alarms,
    summarize_eff_coretech,
    summarize_uph,
    summarize_uph_ame,
)
from models.log_model import LogModel


def row(content, fname="a.log"):
    return {"FileName": fname, "Content": content}


CYCLE_ROWS = [
    row("2026-07-08 02:30:29.020   动作时间:02:30:29.006;模块名称:取料2(工位7);动作名称:放生料完成;;;;"),
    row("2026-07-08 02:30:39.020   动作时间:02:30:39.006;模块名称:取料2(工位7);动作名称:放生料完成;;;;"),
    row("2026-07-08 02:30:59.020   动作时间:02:30:59.006;模块名称:取料2(工位7);动作名称:放生料完成;;;;"),
    row("2026-07-08 02:35:00.000   动作时间:02:35:00;模块名称:取料2(工位7);动作名称:放生料完成;;;;"),
]


class AnalysisTest(unittest.TestCase):
    def test_parse_ts(self):
        from models.analysis import parse_ts
        ts = parse_ts("2026-07-08 02:30:29.020   动作时间...")
        self.assertIsNotNone(ts)
        self.assertEqual(ts.hour, 2)
        self.assertEqual(ts.second, 29)

    def test_trigger_boundary(self):
        # MarkEnd1 不应匹配 MarkEnd1_0
        rows = [
            row("2026-07-08 00:00:01.000 MarkEnd1"),
            row("2026-07-08 00:00:02.000 MarkEnd1_0"),
            row("2026-07-08 00:00:04.000 MarkEnd1"),
        ]
        df = build_cycles_df(rows, "MarkEnd1")
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['CycleSeconds'], 3.0)

    def test_cycle_classification(self):
        df = build_cycles_df(CYCLE_ROWS, "放生料完成,放熟料完成")
        self.assertEqual(len(df), 3)
        self.assertEqual(list(df['Class']), ["正常周期", "异常周期", "异常周期"])

    def test_midnight_rollover(self):
        rows = [
            row("23:59:58.000   动作名称:放生料完成;;;"),
            row("00:00:02.000   动作名称:放生料完成;;;"),
        ]
        df = build_cycles_df(rows, "放生料完成")
        self.assertEqual(df.iloc[0]['CycleSeconds'], 4.0)

    def test_uph_summary(self):
        df = build_cycles_df(CYCLE_ROWS, "放生料完成,放熟料完成")
        summary = summarize_uph(df, units_per_cycle=1)
        row0 = summary.iloc[0]
        self.assertEqual(row0['周期总数'], 3)
        expected = round(3 / (df['CycleSeconds'].sum() / 3600.0), 2)
        self.assertEqual(row0['UPH(个/小时)'], expected)
        # Pure UPH 基于正常周期：3600/10 = 360
        self.assertEqual(row0['Pure UPH(个/小时)'], 360.0)
        # 无理想/最大CT时，Derated M2 = 全部周期平均
        self.assertEqual(row0['Derated UPH M2(个/小时)'], expected)

    def test_uph_derated_m2_filters(self):
        df = build_cycles_df(CYCLE_ROWS, "放生料完成,放熟料完成")
        summary = summarize_uph(df, 1, ideal_ct=10.0, max_ct=20.0)
        row0 = summary.iloc[0]
        self.assertEqual(row0['Pure UPH(个/小时)'], 360.0)        # 3600 / 10
        self.assertEqual(row0['Derated UPH M2(个/小时)'], 240.0)   # 剔除 241 后 avg=15 → 3600/15

    def test_eff_coretech(self):
        rows = [
            row("2026-07-08 00:00:00.000 [PS][status:RUN,Datetime:...,ReasonID:None]"),
            row("2026-07-08 00:00:10.000 [PS][status:IDLE,Datetime:...,ReasonID:0000010000]"),
            row("2026-07-08 00:00:30.000 [PS][status:DOWN,Datetime:...,ReasonID:0000000411]"),
            row("2026-07-08 00:00:40.000 [PS][status:RUN,Datetime:...,ReasonID:None]"),
            row("2026-07-08 00:01:00.000 [PS][status:IDLE,Datetime:...,ReasonID:0000010000]"),
        ]
        status_summary, _, detail = analyze_status(rows)
        eff = summarize_eff_coretech(status_summary, detail, planned_hours=None, pdt_reason_ids="0000000411")
        r0 = eff.iloc[0]
        self.assertEqual(r0['运行时间RUN(秒)'], 30.0)     # 10 + 20
        self.assertEqual(r0['待机时间IDLE(秒)'], 20.0)
        self.assertEqual(r0['停机时间DOWN(秒)'], 10.0)
        self.assertEqual(r0['计划停机pDT(秒)'], 10.0)     # ReasonID 0000000411 归为计划停机
        self.assertEqual(r0['非计划停机uDT(秒)'], 0.0)
        self.assertEqual(r0['EFF(%)'], 83.33)             # (30+20)/60
        p = down_pareto(detail)
        self.assertEqual(len(p), 1)
        self.assertEqual(p.iloc[0]['ReasonID'], '0000000411')
        self.assertEqual(p.iloc[0]['总时长(秒)'], 10.0)

    def test_end_to_end_eff(self):
        src = tempfile.mkdtemp()
        out = tempfile.mkdtemp()
        with open(os.path.join(src, "a.log"), "w", encoding="utf-8") as f:
            f.write("2026-07-08 00:00:00.000 [PS][status:RUN,ReasonID:None]\n")
            f.write("2026-07-08 00:00:20.000 [PS][status:IDLE,ReasonID:0000010000]\n")
            f.write("2026-07-08 00:00:40.000 [PS][status:DOWN,ReasonID:0000000411]\n")
            f.write("2026-07-08 00:00:50.000 [PS][status:RUN,ReasonID:None]\n")
        path = LogModel().analyze_eff(src, out, pdt_reason_ids="0000000411")
        xl = pd.ExcelFile(path)
        self.assertIn("Summary", xl.sheet_names)
        self.assertIn("DOWN_Pareto", xl.sheet_names)
        self.assertEqual(xl.parse("Summary").iloc[0]['EFF(%)'], 80.0)  # (20+20)/50

    def test_alarm_boundary(self):
        rows = [
            row("2026-07-08 03:00:00.000   ALARM 123"),
            row("2026-07-08 03:00:05.000   报警:过温"),
            row("2026-07-08 03:00:06.000   ALARM 123"),
            row("2026-07-08 03:00:07.000   无料NG1"),
            row("2026-07-08 03:00:08.000   DNMHVG04XP80000Y2N+1053+B"),
        ]
        summary, by_kw, detail = summarize_alarms(rows, "报警,ALARM,NG")
        self.assertEqual(len(detail), 4)  # 编码中的 ng 不命中
        self.assertEqual(len(by_kw), 3)   # ALARM x2, 报警 x1, NG x1

    def test_status_analysis(self):
        rows = [
            row("2026-07-08 00:00:00.000 Net(2) Send [PS][status:RUN,Datetime:...,ReasonID:None]"),
            row("2026-07-08 00:00:10.000 Net(2) Send [PS][status:IDLE,Datetime:...,ReasonID:0000010000]"),
            row("2026-07-08 00:00:30.000 Net(2) Send [PS][status:RUN,Datetime:...,ReasonID:None]"),
            row("2026-07-08 00:00:50.000 Net(2) Send [PS][status:DOWN,Datetime:...,ReasonID:0000000411]"),
            row("2026-07-08 00:00:56.000 Net(2) Send [PS][status:RUN,Datetime:...,ReasonID:None]"),
        ]
        summary, hourly, detail = analyze_status(rows)
        self.assertEqual(len(detail), 4)
        s = summary.set_index('状态')
        self.assertEqual(s.loc['RUN', '总时长(秒)'], 10.0 + 20.0)  # 最后一条 RUN 无后续事件，不计时长
        self.assertEqual(s.loc['IDLE', '总时长(秒)'], 20.0)
        self.assertEqual(s.loc['DOWN', '总时长(秒)'], 6.0)
        self.assertEqual(len(hourly), 1)

    def test_status_warn_and_rufff(self):
        rows = [
            row("2026-07-08 00:00:00.000 [PS][status:RUFFF,Datetime:...,ReasonID:None]"),
            row("2026-07-08 00:00:10.000 [PS][status:RU100,Datetime:...,ReasonID:None]"),
            row("2026-07-08 00:00:20.000 [PS][status:IDLE,Datetime:...,ReasonID:0000010000]"),
            row("2026-07-08 00:00:30.000 [PS][status:WARN,Datetime:...,ReasonID:0000000411]"),
            row("2026-07-08 00:00:40.000 [PS][status:RUN,Datetime:...,ReasonID:None]"),
        ]
        summary, hourly, detail = analyze_status(rows)
        statuses = set(summary['状态'])
        self.assertIn('RUN', statuses)   # RUFFF 归一化为 RUN
        self.assertIn('WARN', statuses)  # 协议中的警告状态
        self.assertEqual(len(detail), 4)

    def test_em_production(self):
        rows = [
            row("2026-07-28 00:27:39.715 Net(2) Send [startdata][0011901001][000000H6MT][EM]"
                "[lotno:K63030373-24,inputqty:507,goodqty:507,ngqty:0,head:001,"
                "startdatetime:20260728000000491,enddatetime:20260728002739713,datetime:20260728002739715][enddata]"),
        ]
        df = parse_em_production(rows)
        self.assertEqual(len(df), 1)
        r0 = df.iloc[0]
        self.assertEqual(r0['LotNo'], 'K63030373-24')
        self.assertEqual(r0['GoodQty'], 507)
        self.assertEqual(r0['NgQty'], 0)
        duration_h = r0['DurationHours']
        self.assertAlmostEqual(duration_h, (1659.222) / 3600, places=3)
        self.assertAlmostEqual(r0['UPH(个/小时)'], round(507 / (1659.222 / 3600), 2))

    def test_end_to_end_status(self):
        src = tempfile.mkdtemp()
        out = tempfile.mkdtemp()
        with open(os.path.join(src, "a.log"), "w", encoding="utf-8") as f:
            f.write("2026-07-08 00:00:00.000 [status:RUN]\n")
            f.write("2026-07-08 00:01:00.000 [status:IDLE]\n")
        path = LogModel().analyze_status(src, out)
        xl = pd.ExcelFile(path)
        self.assertIn("Summary", xl.sheet_names)
        self.assertIn("Hourly", xl.sheet_names)

    def test_end_to_end_uph(self):
        src = tempfile.mkdtemp()
        out = tempfile.mkdtemp()
        with open(os.path.join(src, "a.log"), "w", encoding="utf-8") as f:
            for c in CYCLE_ROWS:
                f.write(c["Content"] + "\n")
            f.write("2026-07-28 00:27:39.715 [EM][lotno:LOT1,inputqty:100,goodqty:98,ngqty:2,head:001,"
                    "startdatetime:20260728000000491,enddatetime:20260728002739713,datetime:20260728002739715]\n")
        path = LogModel().analyze_uph(src, out, trigger_keywords="放生料完成")
        xl = pd.ExcelFile(path)
        self.assertIn("Summary", xl.sheet_names)
        self.assertIn("AMESummary", xl.sheet_names)
        self.assertIn("CycleDetail", xl.sheet_names)
        self.assertIn("EMProduction", xl.sheet_names)
        self.assertEqual(xl.parse("Summary").iloc[0]['周期总数'], 3)

    def test_analyze_uph_with_file_filters(self):
        src = tempfile.mkdtemp()
        out = tempfile.mkdtemp()
        with open(os.path.join(src, "记录PLC2当前工位当前步数记录.log"), "w", encoding="utf-8") as f:
            for c in CYCLE_ROWS:
                f.write(c["Content"] + "\n")
        with open(os.path.join(src, "RAYPRUS交互记录.log"), "w", encoding="utf-8") as f:
            f.write("2026-07-28 00:27:39.715 [EM][lotno:LOT1,inputqty:100,goodqty:98,ngqty:2,head:001,"
                    "startdatetime:20260728000000491,enddatetime:20260728002739713]\n")
        with open(os.path.join(src, "Debug记录.log"), "w", encoding="utf-8") as f:
            f.write("2026-07-28 00:00:00.000 无料NG\n")
        path = LogModel().analyze_uph(
            src, out, trigger_keywords="放生料完成",
            file_filters=["记录PLC2当前工位当前步数记录", "RAYPRUS交互记录"],
        )
        xl = pd.ExcelFile(path)
        self.assertEqual(xl.parse("Summary").iloc[0]['周期总数'], 3)  # 只读 PLC2 文件
        self.assertEqual(len(xl.parse("EMProduction")), 1)            # EM 来自 RAYPRUS 文件

    def test_custom_template_roundtrip(self):
        from models.process_templates import get_template, load_custom_template, save_custom_template
        tpl = {
            "description": "用户自定义模板",
            "file_filters": ["记录PLC2", "RAYPRUS"],
            "UPH分析": {"trigger_keywords": "放生料完成", "units_per_cycle": 1},
            "EFF分析": {"planned_hours": 22.0, "pdt_reason_ids": "411"},
            "报警分析": {"alarm_keywords": "NG,异常"},
            "机台状态分析": {},
        }
        path = os.path.join(tempfile.mkdtemp(), "custom_template.json")
        save_custom_template(tpl, path)
        loaded = load_custom_template(path)
        self.assertEqual(loaded["UPH分析"]["trigger_keywords"], "放生料完成")
        self.assertEqual(loaded["EFF分析"]["pdt_reason_ids"], "411")
        got = get_template("自定义", path)
        self.assertEqual(got["file_filters"], ["记录PLC2", "RAYPRUS"])

    def test_builtin_templates(self):
        from models.process_templates import PROCESS_TEMPLATES
        self.assertEqual(
            PROCESS_TEMPLATES["LM 激光打标"]["UPH分析"]["trigger_keywords"], "MarkEnd1"
        )
        caw = PROCESS_TEMPLATES["CAW 组装"]
        self.assertEqual(caw["UPH分析"]["trigger_keywords"], "放熟料完成,放生料完成")
        self.assertEqual(caw["EFF分析"]["file_filters"], ["RAYPRUS交互记录"])


if __name__ == "__main__":
    unittest.main()
