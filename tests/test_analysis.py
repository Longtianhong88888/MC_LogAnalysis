import os
import tempfile
import unittest

import pandas as pd

from models.analysis import (
    analyze_status,
    analyze_status_derived,
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
        bracket = parse_ts("[00:00:05] 左 图像数据获取完成")
        self.assertIsNotNone(bracket)
        self.assertEqual((bracket.hour, bracket.minute, bracket.second), (0, 0, 5))
        sa = parse_ts("[001] Sequence, VisionAlign, 20260803-09-55-26-191, DispProbeCheck, 13, Head No = 0")
        self.assertIsNotNone(sa)
        self.assertEqual((sa.year, sa.month, sa.day, sa.hour, sa.minute, sa.second, sa.microsecond),
                         (2026, 8, 3, 9, 55, 26, 191000))

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

    def test_phrase_trigger_with_spaces(self):
        # SA：含空格的完成动作短语整体匹配
        rows = [
            {"FileName": "a.txt", "Content": "[324] Sequence, VisionAlign, 20260803-09-59-09-943, X, 0, UDP Module - Good, 0"},
            {"FileName": "a.txt", "Content": "[325] Sequence, VisionAlign, 20260803-09-59-11-394, X, 0, UDP Module - Good, 0"},
            {"FileName": "a.txt", "Content": "[326] Sequence, X, 20260803-09-59-13-000, X, 0, UDP Recv [Good]"},
        ]
        df = build_cycles_df(rows, "UDP Module - Good")
        self.assertEqual(len(df), 1)  # 只匹配完整短语
        self.assertEqual(df.iloc[0]['CycleSeconds'], 1.451)

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

    def test_pure_uph_factor(self):
        # FR 并行工位：单轴 Pure UPH ×0.5；整机 AME Pure 为左右合并，不乘系数
        df = build_cycles_df(CYCLE_ROWS, "放生料完成,放熟料完成")
        normal = summarize_uph(df, 1, pure_uph_factor=0.5)
        ame = summarize_uph_ame(df, 1)
        self.assertEqual(normal.iloc[0]['Pure UPH(个/小时)'], 180.0)   # 360/2
        self.assertEqual(normal.iloc[0]['Derated UPH M2(个/小时)'], normal.iloc[0]['UPH(个/小时)'])
        self.assertEqual(ame.iloc[0]['Pure UPH(个/小时)'], 360.0)      # 整机不乘系数

    def test_ame_m2_is_sum_of_modules(self):
        # 整机 Derated UPH M2 = 各模组之和（FR 左轴+右轴）
        df = pd.DataFrame({
            "Module": ["左轴", "左轴", "右轴"],
            "Class": ["正常周期"] * 3,
            "CycleSeconds": [3.0, 3.0, 6.0],
            "FileName": ["a.log"] * 3,
        })
        ame = summarize_uph_ame(df, 1)
        self.assertEqual(ame.iloc[0]['Derated UPH M2(个/小时)'], 1200.0 + 600.0)
        self.assertEqual(ame.iloc[0]['Derated UPH M1(个/小时)'], 1200.0 + 600.0)  # 多模组 M1 同样求和

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

    def test_reason_code_mapping(self):
        from models.reason_codes import is_planned, load_reason_codes, reason_info
        lm = load_reason_codes("LM")
        self.assertIn("411", lm)
        self.assertEqual(lm["411"]["name"], "打標位建真空")
        self.assertEqual(lm["411"]["category"], "Unplanned Downtime")
        self.assertFalse(is_planned(lm, "411"))
        fr = load_reason_codes("FR")
        self.assertEqual(reason_info(fr, "1110000000")["name"], "真空報警")
        # 计划停机分类：构造 Routine 类型
        fake = {"999": {"name": "例行保养", "category": "Routine Downtime", "state": "DOWN"}}
        self.assertTrue(is_planned(fake, "999"))

    def test_available_reason_lists(self):
        from models.reason_codes import available_reason_lists
        lists = available_reason_lists()
        self.assertIn("LM", lists)
        self.assertIn("FR", lists)

    def test_eff_coretech_with_reason_map(self):
        reason_map = {
            "1110000000": {"name": "真空報警", "category": "Unplanned Downtime", "state": "DOWN"},
            "2220000000": {"name": "例行保養", "category": "Routine Downtime", "state": "DOWN"},
        }
        rows = [
            row("2026-07-08 00:00:00.000 [PS][status:RUN,ReasonID:None]"),
            row("2026-07-08 00:00:10.000 [PS][status:DOWN,ReasonID:1110000000]"),
            row("2026-07-08 00:00:20.000 [PS][status:DOWN,ReasonID:2220000000]"),
            row("2026-07-08 00:00:30.000 [PS][status:RUN,ReasonID:None]"),
        ]
        status_summary, _, detail = analyze_status(rows)
        eff = summarize_eff_coretech(status_summary, detail, reason_map=reason_map)
        self.assertEqual(eff.iloc[0]['非计划停机uDT(秒)'], 10.0)   # 1110000000 → uDT
        self.assertEqual(eff.iloc[0]['计划停机pDT(秒)'], 10.0)     # 2220000000 → pDT
        p = down_pareto(detail, reason_map=reason_map)
        self.assertIn('原因名称', p.columns)
        self.assertIn('停机类型', p.columns)
        self.assertEqual(set(p['停机类型']), {'pDT', 'uDT'})

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

    def test_alarm_reason_name(self):
        reason_map = {"305": {"name": "吸取钢片真空報警", "category": "Unplanned Downtime", "state": "DOWN"}}
        rows = [
            row("2026-07-08 03:00:00.000 [Error 305] Picker真空报警"),
            row("2026-07-08 03:00:01.000 无料NG"),
        ]
        summary, by_kw, detail = summarize_alarms(rows, "Error,NG", reason_map=reason_map)
        self.assertIn("原因名称", detail.columns)
        self.assertEqual(detail.iloc[0]["原因名称"], "吸取钢片真空報警")
        self.assertEqual(detail.iloc[1]["原因名称"], "")

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
        self.assertEqual(caw["file_filters"], ["记录PLC", "RAYPRUS", "Debug", "设备状态"])
        self.assertIn("FR 机台", PROCESS_TEMPLATES)
        fr = PROCESS_TEMPLATES["FR 机台"]
        self.assertIn("SA 机台", PROCESS_TEMPLATES)
        self.assertEqual(PROCESS_TEMPLATES["SA 机台"]["UPH分析"]["trigger_keywords"], "UDP Module - Good")
        self.assertEqual(PROCESS_TEMPLATES["SA 机台"]["file_filters"], [".txt"])
        self.assertEqual(PROCESS_TEMPLATES["SA 机台"]["机台状态分析"]["activity_keywords"], "UDP Module - Good")
        self.assertIn("不达标", fr["报警分析"]["alarm_keywords"])
        self.assertIn("有漏点产品", fr["报警分析"]["alarm_keywords"])
        self.assertEqual(fr["UPH分析"]["trigger_keywords"], "轴点胶完成,有漏点产品")
        self.assertEqual(fr["UPH分析"]["module_pattern"], "(左轴|右轴)")
        self.assertEqual(fr["UPH分析"]["pure_uph_factor"], 0.5)

    def test_one_click_includes_merge(self):
        from controllers.log_controller import ONE_CLICK_FEATURES
        self.assertIn("文档合并与内容拆分", ONE_CLICK_FEATURES)
        self.assertEqual(ONE_CLICK_FEATURES[-1], "文档合并与内容拆分")  # 合并最后执行，先出分析结果

    def test_analyze_uph_with_shared_rows(self):
        # 共享已读日志：提供 rows 时不读目录，正常出结果
        rows = [{"FileName": c["FileName"], "Content": c["Content"]} for c in CYCLE_ROWS]
        out = tempfile.mkdtemp()
        path = LogModel().analyze_uph("不存在的目录", out, trigger_keywords="放生料完成", rows=rows)
        self.assertEqual(pd.ExcelFile(path).parse("Summary").iloc[0]['周期总数'], 3)

    def test_cancel_event_skips_cycle_build(self):
        import threading
        from models.exceptions import OperationCancelled
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(OperationCancelled):
            build_cycles_df(CYCLE_ROWS, "放生料完成", cancel_event=cancel)

    def test_cancel_event_skips_read_files(self):
        import threading
        from models.exceptions import OperationCancelled
        from utils.file_utils import read_files
        src = tempfile.mkdtemp()
        with open(os.path.join(src, "a.log"), "w", encoding="utf-8") as f:
            f.write("x\n")
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(OperationCancelled):
            read_files(src, cancel_event=cancel)

    def test_module_pattern_with_defect_completion(self):
        # 漏点件以"有漏点产品"代替"点胶完成"，周期序列应连续且分左/右轴
        rows = [
            {"FileName": "a.log", "Content": "[00:00:00] 左轴点胶完成"},
            {"FileName": "a.log", "Content": "[00:00:06] 右轴点胶完成"},
            {"FileName": "a.log", "Content": "[00:00:07] 左轴有漏点产品，请处理！"},
            {"FileName": "a.log", "Content": "[00:00:14] 右轴有漏点产品，请处理！"},
            {"FileName": "a.log", "Content": "[00:00:15] 左轴点胶完成"},
        ]
        df = build_cycles_df(rows, "轴点胶完成,有漏点产品",
                             module_pattern=r"(左轴|右轴)")
        self.assertEqual(set(df["Module"]), {"左轴", "右轴"})
        left = df[df["Module"] == "左轴"]
        right = df[df["Module"] == "右轴"]
        self.assertEqual(list(left["CycleSeconds"]), [7.0, 8.0])   # 漏点件计入周期
        self.assertEqual(list(right["CycleSeconds"]), [8.0])

    def test_ppt_report(self):
        from models.report import build_ppt_report
        from pptx import Presentation
        src = tempfile.mkdtemp()
        out = tempfile.mkdtemp()
        lines = [
            "2026-07-08 00:00:00.000 [PS][status:RUN,ReasonID:None]",
            "2026-07-08 00:00:10.000 [PS][status:IDLE,ReasonID:0000010000]",
            "2026-07-08 00:00:30.000 [PS][status:DOWN,ReasonID:0000000411]",
            "2026-07-08 00:00:40.000 [PS][status:RUN,ReasonID:None]",
            "2026-07-08 00:00:50.000 无料NG",
            "2026-07-08 00:00:55.000 MarkEnd1",
            "2026-07-08 00:00:58.000 MarkEnd1",
            "2026-07-08 00:00:02.000 [EM][lotno:LOT1,inputqty:100,goodqty:98,ngqty:2,head:001,"
            "startdatetime:20260708000000491,enddatetime:20260708000030000]",
        ]
        with open(os.path.join(src, "a.log"), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        m = LogModel()
        m.analyze_uph(src, out, trigger_keywords="MarkEnd1")
        m.analyze_eff(src, out)
        m.analyze_alarms(src, out)
        m.analyze_status(src, out)
        ppt = build_ppt_report(out, process_name="CAW 组装")
        prs = Presentation(ppt)
        self.assertEqual(len(prs.slides), 7)  # 封面 + 6 内容页（模板目录页已删除）
        self.assertFalse(any('agenda' in s.slide_layout.name.lower() for s in prs.slides))
        self.assertTrue(any(shape.has_chart for s in prs.slides for shape in s.shapes))
        cover_text = "\n".join(
            sh.text_frame.text for sh in prs.slides[0].shapes if sh.has_text_frame
        )
        self.assertIn("CAW設備一鍵自動分析報告", cover_text)  # 制程字母已替换
        self.assertIn("——UPH、EFF、Alarm", cover_text)  # 模板副标题保留
        self.assertIn("1 /", cover_text)
        self.assertIn("7", cover_text)  # 封面总页数
        uph_page = "\n".join(
            sh.text_frame.text for sh in prs.slides[1].shapes if sh.has_text_frame
        )
        self.assertIn("2/7", uph_page)  # 内容页页码同步（与模板样式一致）
        # 原因码前导零在 PPT 表格中保留（0000000411）
        table_texts = []
        for s in prs.slides:
            for shape in s.shapes:
                if shape.has_table:
                    for r in range(len(shape.table.rows)):
                        for c in range(len(shape.table.columns)):
                            table_texts.append(shape.table.cell(r, c).text)
        self.assertIn("0000000411", table_texts)

    def test_ppt_report_nan_values(self):
        # 回归：AMESummary 存在 NaN（如 FR 无周期时 Pure/M2 为空）不应导致图表写入报错
        from models.report import build_ppt_report
        from pptx import Presentation
        out = tempfile.mkdtemp()
        LogModel._write_sheets(os.path.join(out, "UPH_Analysis.xlsx"), {
            "AMESummary": pd.DataFrame({
                "Pure UPH(个/小时)": [float("nan")],
                "Derated UPH M1(个/小时)": [2892.32],
                "Derated UPH M2(个/小时)": [float("nan")],
            })
        })
        ppt = build_ppt_report(out, process_name="FR 机台")
        self.assertTrue(os.path.exists(ppt))
        prs = Presentation(ppt)
        self.assertGreaterEqual(len(prs.slides), 2)  # 封面 + UPH 页（其余 Excel 缺失被移除）
        self.assertTrue(any(shape.has_chart for s in prs.slides for shape in s.shapes))

    def test_status_time_only_multi_file(self):
        # FR 风格：纯时间戳 + 按日分文件，跨日 23:59:58 -> 00:00:01 应为 3 秒
        rows = [
            {"FileName": "L06-25.log", "Content": "[23:59:58] Send: [PS][status:RUN,ReasonID:None]"},
            {"FileName": "L06-26.log", "Content": "[00:00:01] Send: [PS][status:IDLE,ReasonID:0020000000]"},
            {"FileName": "L06-26.log", "Content": "[00:00:31] Send: [PS][status:RUN,ReasonID:None]"},
        ]
        summary, hourly, detail = analyze_status(rows)
        self.assertEqual(len(detail), 2)
        s = summary.set_index('状态')
        self.assertEqual(s.loc['RUN', '总时长(秒)'], 3.0)   # 跨日 3 秒；最后一条 RUN 无后续事件不计时长
        self.assertEqual(s.loc['IDLE', '总时长(秒)'], 30.0)

    def test_status_derived(self):
        reason_map = {"305": {"name": "吸取钢片真空報警", "category": "Unplanned Downtime", "state": "DOWN"}}
        rows = [
            {"FileName": "a.txt", "Content": "[0] X, 20260803-09-00-00-000, X, 0, UDP Module - Good"},
            {"FileName": "a.txt", "Content": "[1] X, 20260803-09-00-05-000, X, 0, UDP Module - Good"},
            {"FileName": "a.txt", "Content": "[2] X, 20260803-09-00-08-000, X, 0, AutoRun Stop - ErrorName = [Error 305] Picker"},
            {"FileName": "a.txt", "Content": "[3] X, 20260803-09-00-12-000, X, 0, UDP Module - Good"},
            {"FileName": "a.txt", "Content": "[4] X, 20260803-09-00-15-000, X, 0, AutoRun Stop - ErrorName = [작업자 정지]"},
            {"FileName": "a.txt", "Content": "[5] X, 20260803-09-00-20-000, X, 0, UDP Module - Good"},
        ]
        summary, hourly, detail = analyze_status_derived(
            rows, "UDP Module - Good", "AutoRun Stop - ErrorName", reason_map=reason_map,
        )
        s = summary.set_index('状态')
        self.assertEqual(s.loc['RUN', '总时长(秒)'], 8.0 + 3.0)   # 0→8、12→15
        self.assertEqual(s.loc['DOWN', '总时长(秒)'], 4.0)         # Error 305 → DOWN
        self.assertEqual(s.loc['IDLE', '总时长(秒)'], 5.0)         # 操作员停止 → IDLE
        down = detail[detail['Status'] == 'DOWN'].iloc[0]
        self.assertEqual(down['ReasonID'], '305')


if __name__ == "__main__":
    unittest.main()
