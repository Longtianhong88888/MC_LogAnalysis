import os
import re

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

try:
    import xlsxwriter  # noqa: F401  提速 Excel 写入
    _HAS_XLSXWRITER = True
except ImportError:
    _HAS_XLSXWRITER = False

from models.analysis import (
    analyze_bottleneck_machines,
    analyze_status,
    analyze_status_derived,
    analyze_steps,
    analyze_steps_sa,
    build_cycles_df,
    detect_tray_stats,
    down_pareto,
    measure_tray_change,
    parse_em_production,
    summarize_alarms,
    summarize_eff_coretech,
    summarize_uph,
    summarize_uph_ame,
)
from utils.file_utils import read_files, clean_for_excel


class LogModel:
    # 文档合并的行数上限：超过后放弃合并，改为按日志文件逐个导出 Excel
    MERGE_MAX_TOTAL_ROWS = 1_000_000

    # ---------- 通用：读取 / 导出 ----------
    def _read_all(self, source_dir, progress_callback=None, file_filters=None, cancel_event=None):
        def on_read_progress(frac):
            if progress_callback:
                progress_callback(10 + int(19 * frac))

        all_data = read_files(source_dir, progress_callback=on_read_progress, file_filters=file_filters,
                              cancel_event=cancel_event)
        if not all_data:
            raise ValueError("日志文件内容均为空，无法解析")
        return all_data

    def load_rows(self, source_dir, file_filters=None, progress_callback=None, cancel_event=None):
        """读取日志行（供一键分析共享，避免每项重复读取大文件）。"""
        return self._read_all(source_dir, progress_callback, file_filters=file_filters,
                              cancel_event=cancel_event)

    @staticmethod
    def _write_sheets(out_path, sheets, cancel_event=None):
        max_rows = 1048575  # Excel 单表最大行数（含表头行）
        heavy = False  # 是否包含超大表（>20万行）：跳过整体格式化，避免重新加载保存拖慢导出
        writer_kwargs = {}
        if _HAS_XLSXWRITER:
            writer_kwargs = {
                'engine': 'xlsxwriter',
                'engine_kwargs': {'options': {'nan_inf_to_errors': True}},
            }
        with pd.ExcelWriter(out_path, **writer_kwargs) as writer:
            for sheet_name, df in sheets.items():
                if cancel_event is not None and cancel_event.is_set():
                    from models.exceptions import OperationCancelled
                    raise OperationCancelled()
                if len(df) <= max_rows:
                    if len(df) > LogModel.MAX_FORMAT_ROWS:
                        heavy = True
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    # 超限自动拆分：AllLogs → AllLogs_1, AllLogs_2 ...
                    heavy = True
                    n = (len(df) + max_rows - 1) // max_rows
                    for i in range(n):
                        if cancel_event is not None and cancel_event.is_set():
                            from models.exceptions import OperationCancelled
                            raise OperationCancelled()
                        chunk = df.iloc[i * max_rows:(i + 1) * max_rows]
                        name = f"{sheet_name}_{i + 1}"[:31]
                        chunk.to_excel(writer, sheet_name=name, index=False)
        if not heavy:
            LogModel._format_workbook(out_path)

    # 超大表逐格样式上限（超过则只做表头/列宽，避免卡死）
    MAX_FORMAT_ROWS = 200000

    @staticmethod
    def _format_workbook(path):
        """统一 Excel 样式：列宽自适应、内容居中、有内容加框线、表头浅蓝加粗。"""
        thin = Side(style='thin')
        border = Border(left=thin, right=thin, top=thin, bottom=thin)
        center = Alignment(horizontal='center', vertical='center')
        header_fill = PatternFill('solid', fgColor='DDEBF7')  # 浅蓝色
        header_font = Font(bold=True)

        wb = load_workbook(path)
        for ws in wb.worksheets:
            # 表头：浅蓝填充 + 加粗 + 居中
            for cell in ws[1]:
                cell.fill = header_fill
                cell.font = header_font
                cell.alignment = center

            # 列宽自适应（中文按 2 字符宽计）
            for col_cells in ws.columns:
                letter = get_column_letter(col_cells[0].column)
                max_len = 0
                for cell in col_cells:
                    if cell.value is None:
                        continue
                    length = sum(2 if ord(ch) > 127 else 1 for ch in str(cell.value))
                    if length > max_len:
                        max_len = length
                ws.column_dimensions[letter].width = min(max(max_len + 2, 8), 60)

            # 超大表跳过逐格样式，避免导出卡死
            if ws.max_row > LogModel.MAX_FORMAT_ROWS:
                continue

            # 内容单元格：居中 + 有内容加框线（空单元格保持无格线）
            for row in ws.iter_rows(min_row=2):
                for cell in row:
                    if cell.value is None or str(cell.value) == '':
                        continue
                    cell.alignment = center
                    cell.border = border
        wb.save(path)

    # ---------- 功能一：文档合并与内容拆分 ----------
    def process(self, source_dir, output_dir, keywords=None, separator=None,
                file_filters=None, rows=None, cancel_event=None, progress_callback=None,
                merge_groups=None):
        if progress_callback:
            progress_callback(5)
        all_data = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        df_all = pd.DataFrame(all_data)

        if progress_callback:
            progress_callback(30)

        if merge_groups:
            # 按文件分组（如 PLC1/PLC2）分别导出 Excel
            return self._process_by_groups(
                all_data, output_dir, keywords, separator, merge_groups,
                cancel_event, progress_callback,
            )

        if len(all_data) > self.MERGE_MAX_TOTAL_ROWS:
            # 原始日志过大：放弃合并，按日志文件逐个导出 Excel
            return self._process_per_file(
                all_data, output_dir, keywords, separator, cancel_event, progress_callback,
            )

        df_all = pd.DataFrame(all_data)
        sheets = self._build_merge_sheets(df_all, keywords, separator, cancel_event)

        if progress_callback:
            progress_callback(70)

        out_path = os.path.join(output_dir, 'LogAnalysis.xlsx')
        self._write_sheets(out_path, sheets, cancel_event=cancel_event)

        if progress_callback:
            progress_callback(100)
        return out_path

    def _process_by_groups(self, all_data, output_dir, keywords, separator, merge_groups,
                           cancel_event=None, progress_callback=None):
        """按文件关键词分组分别导出 LogAnalysis_<组名>.xlsx，未匹配行归入“其他”。"""
        import os as _os
        _os.makedirs(output_dir, exist_ok=True)
        rows_list = list(all_data)
        written = []
        matched_ids = set()
        total = len(merge_groups)
        for gi, group in enumerate(merge_groups):
            if cancel_event is not None and cancel_event.is_set():
                from models.exceptions import OperationCancelled
                raise OperationCancelled()
            name = group.get('name', '组%d' % (gi + 1))
            file_kw = group.get('file', '')
            sub = [r for r in rows_list if file_kw in str(r.get('FileName', ''))] if file_kw else rows_list
            if not sub:
                continue
            sheets = self._build_merge_sheets(pd.DataFrame(sub), keywords, separator, cancel_event)
            out_path = _os.path.join(output_dir, 'LogAnalysis_%s.xlsx' % name)
            self._write_sheets(out_path, sheets, cancel_event=cancel_event)
            written.append(out_path)
            matched_ids.update(id(r) for r in sub)
            if progress_callback:
                progress_callback(20 + int(60 * (gi + 1) / total))
        others = [r for r in rows_list if id(r) not in matched_ids]
        if others:
            sheets = self._build_merge_sheets(pd.DataFrame(others), keywords, separator, cancel_event)
            out_path = _os.path.join(output_dir, 'LogAnalysis_其他.xlsx')
            self._write_sheets(out_path, sheets, cancel_event=cancel_event)
            written.append(out_path)
        if progress_callback:
            progress_callback(100)
        if written:
            return "; ".join(written) + "（已按分组分别导出）"
        return "无匹配日志"

    def _build_merge_sheets(self, df_all, keywords, separator, cancel_event=None):
        """关键词筛选 + 分隔符拆分，返回 {'AllLogs':..., 'Filtered':...}。"""
        if keywords:
            kw_list = re.split(r'[ ;、，]+', keywords)
            kw_list = [k for k in kw_list if k]
            if kw_list:
                pattern = '|'.join(re.escape(k) for k in kw_list)
                mask = df_all['Content'].str.contains(pattern, case=False, na=False)
                filtered_df = df_all[mask].copy()
            else:
                filtered_df = df_all.copy()
        else:
            filtered_df = df_all.copy()

        has_filtered_rows = not filtered_df.empty
        has_separator = separator is not None and separator != ''
        has_keywords = bool(keywords and str(keywords).strip())
        # 无关键词且无分隔符时 Filtered 与 AllLogs 完全相同，跳过以加速大文件导出
        generate_filtered = (has_filtered_rows or has_separator) and (has_keywords or has_separator)

        if generate_filtered:
            if not has_filtered_rows and has_separator:
                filtered_df = df_all.copy()
                has_filtered_rows = True
            if has_separator:
                sep = separator
                if sep == '\\t':
                    sep = '\t'
                split_rows = []
                max_parts = 0
                for _, row in filtered_df.iterrows():
                    if cancel_event is not None and cancel_event.is_set():
                        from models.exceptions import OperationCancelled
                        raise OperationCancelled()
                    parts = row['Content'].split(sep)
                    parts = [clean_for_excel(p) for p in parts]
                    max_parts = max(max_parts, len(parts))
                    split_rows.append(parts)
                col_names = [f'Part_{i+1}' for i in range(max_parts)]
                split_data = []
                for parts in split_rows:
                    parts += [''] * (max_parts - len(parts))
                    split_data.append(parts)
                split_df = pd.DataFrame(split_data, columns=col_names)
                filtered_df = filtered_df.reset_index(drop=True)
                filtered_df = pd.concat([
                    filtered_df[['FileName']],
                    pd.DataFrame({'OriginalContent': filtered_df['Content']}),
                    split_df
                ], axis=1)
                # Content 已由 OriginalContent 取代，无需（也无法）再删除

        sheets = {'AllLogs': df_all}
        if generate_filtered and filtered_df is not None and not filtered_df.empty:
            sheets['Filtered'] = filtered_df
        return sheets

    def _process_per_file(self, all_data, output_dir, keywords, separator, cancel_event=None,
                          progress_callback=None):
        """日志过大：新建子文件夹，按日志文件逐个导出 Excel（文件名 = 日志文件名去掉扩展名）。"""
        sub_dir = os.path.join(output_dir, 'LogAnalysis_Files')
        os.makedirs(sub_dir, exist_ok=True)
        has_keywords = bool(keywords and str(keywords).strip())
        has_separator = separator is not None and separator != ''
        if not has_keywords and not has_separator:
            # 无筛选：直接流式写入，避免构建大 DataFrame（最快、内存最低）
            n = self._stream_per_file(sub_dir, all_data, cancel_event)
            if progress_callback:
                progress_callback(100)
            return f"{sub_dir}（日志过大，已按文件分别导出 {n} 个 Excel）"

        file_names = sorted({r.get('FileName', '') for r in all_data})
        n = len(file_names)
        for idx, fname in enumerate(file_names):
            if cancel_event is not None and cancel_event.is_set():
                from models.exceptions import OperationCancelled
                raise OperationCancelled()
            sub = pd.DataFrame([r for r in all_data if r.get('FileName') == fname])
            sheets = self._build_merge_sheets(sub, keywords, separator, cancel_event)
            stem = os.path.splitext(fname)[0].replace('/', '_').replace('\\', '_')
            out_path = os.path.join(sub_dir, f'{stem}.xlsx')
            self._write_sheets(out_path, sheets, cancel_event=cancel_event)
            if progress_callback:
                progress_callback(30 + int(60 * (idx + 1) / n))
        if progress_callback:
            progress_callback(100)
        return f"{sub_dir}（日志过大，已按文件分别导出 {n} 个 Excel）"

    @staticmethod
    def _stream_per_file(sub_dir, all_data, cancel_event=None):
        """无筛选时按日志文件流式写入 Excel（xlsxwriter 常量内存模式）。返回文件数。"""
        import xlsxwriter
        max_rows = 1048575
        file_names = sorted({r.get('FileName', '') for r in all_data})
        wbs = {}
        sheets = {}
        rows_written = {}
        sheet_no = {}
        try:
            for fname in file_names:
                stem = os.path.splitext(fname)[0].replace('/', '_').replace('\\', '_')
                wb = xlsxwriter.Workbook(
                    os.path.join(sub_dir, f'{stem}.xlsx'),
                    {'nan_inf_to_errors': True, 'constant_memory': True},
                )
                ws = wb.add_worksheet('AllLogs')
                ws.write_string(0, 0, 'FileName')
                ws.write_string(0, 1, 'Content')
                wbs[fname] = wb
                sheets[fname] = ws
                rows_written[fname] = 1
                sheet_no[fname] = 1
            for row in all_data:
                if cancel_event is not None and cancel_event.is_set():
                    raise OperationCancelled()
                fname = row.get('FileName', '')
                ws = sheets[fname]
                r = rows_written[fname]
                if r > max_rows:
                    sheet_no[fname] += 1
                    ws = wbs[fname].add_worksheet(f'AllLogs_{sheet_no[fname]}'[:31])
                    ws.write_string(0, 0, 'FileName')
                    ws.write_string(0, 1, 'Content')
                    sheets[fname] = ws
                    r = 1
                ws.write_string(r, 0, str(fname))
                ws.write_string(r, 1, str(row.get('Content', '')))
                rows_written[fname] = r + 1
        finally:
            for wb in wbs.values():
                wb.close()
        return len(file_names)

    # ---------- 功能二：UPH 分析 ----------
    def analyze_uph(self, source_dir, output_dir, trigger_keywords="MarkEnd1", units_per_cycle=1,
                    normal_threshold=10.0, planned_threshold=900.0,
                    ideal_ct=None, max_ct=None, file_filters=None, module_pattern=None,
                    pure_uph_factor=1.0, bottleneck_stations=None, bottleneck_units_per_row=None,
                    bottleneck_machines=None, tray_change=None, parts=None, module_from_path=False,
                    step_units=None, step_coefficient=1.5, step_max_seconds=None, step_mode=None,
                    rows=None, cancel_event=None, progress_callback=None):
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(40)

        steps_df = None
        if step_units or step_mode == 'sa':
            cutoff = step_max_seconds if step_max_seconds is not None else planned_threshold
            if step_mode == 'sa':
                steps_df = analyze_steps_sa(
                    rows, step_coefficient,
                    max_step_seconds=cutoff, cancel_event=cancel_event,
                )
            elif step_units:
                steps_df = analyze_steps(
                    rows, step_units, step_coefficient,
                    max_step_seconds=cutoff, cancel_event=cancel_event,
                )

        if bottleneck_machines:
            # CAW 双机台：上料机/焊接机 各自单颗 CT，取 CT 长者计算 UPH
            machine_df, bn = analyze_bottleneck_machines(
                rows, bottleneck_machines, cancel_event=cancel_event,
            )
            ame = pd.DataFrame([{
                '瓶颈机台': bn.get('瓶颈机台', ''),
                '瓶颈CT(秒)': bn.get('瓶颈CT(秒)', ''),
                'UPH(个/小时)': bn.get('UPH(个/小时)', ''),
            }])
            sheets = {'Summary': machine_df, 'AMESummary': ame}
            if steps_df is not None and not steps_df.empty:
                sheets['步骤分析'] = steps_df
            if progress_callback:
                progress_callback(70)
            out_path = os.path.join(output_dir, 'UPH_Analysis.xlsx')
            self._write_sheets(out_path, sheets, cancel_event=cancel_event)
            if progress_callback:
                progress_callback(100)
            return out_path

        if parts:
            # 多部分机台（如上料机/主机/下料机）：各部分独立 UPH，换盘时间可平摊
            part_summaries = []
            ame_rows = []
            for part in parts:
                name = part.get('name', '')
                trigger = part.get('trigger', '')
                units = int(part.get('units_per_cycle', units_per_cycle or 1))
                part_normal = float(part.get('normal_threshold', normal_threshold))
                part_planned = float(part.get('planned_threshold', planned_threshold))
                p_rows = [r for r in rows if str(r.get('FileName', '')).split('/')[0] == name]
                cycles = build_cycles_df(p_rows, trigger, part_normal, part_planned,
                                         module_from_path=module_from_path, cancel_event=cancel_event)
                if cycles.empty:
                    row = {'模块': name, '周期总数': 0, '产出数(个)': 0, '统计时长(秒)': 0,
                           'UPH(个/小时)': '', 'Pure UPH(个/小时)': '', 'Derated UPH M2(个/小时)': ''}
                    if part.get('tray_seconds') or part.get('tray_detect'):
                        row.update({'每盘颗数(统计)': '', '换盘次数': '',
                                    '单次换盘时间(秒)': '', '每颗换盘开销(秒)': '',
                                    '有效周期(秒)': '', '有效UPH(个/小时)': ''})
                    part_summaries.append(pd.DataFrame([row]))
                    ame_rows.append({'模块': name, 'Pure UPH(个/小时)': '', 'UPH(个/小时)': '', '产出数(个)': 0})
                    continue
                s = summarize_uph(cycles, units, ideal_ct=ideal_ct, max_ct=max_ct,
                                  pure_uph_factor=pure_uph_factor)
                tray_s = part.get('tray_seconds')
                units_per_tray = part.get('units_per_tray') or part.get('rows_per_tray')
                tray_stats = None
                if part.get('tray_detect'):
                    try:
                        tray_stats = detect_tray_stats(
                            p_rows,
                            part['tray_detect']['tray_id'],
                            part['tray_detect'].get('unit'),
                            segments=part['tray_detect'].get('segments', 'id'),
                            run_gap=float(part['tray_detect'].get('run_gap', 300.0)),
                            cancel_event=cancel_event,
                        )
                    except Exception:
                        tray_stats = None
                if tray_stats:
                    units_per_tray = tray_stats['units_per_tray']
                    s['每盘颗数(统计)'] = tray_stats['units_per_tray']
                    s['换盘次数'] = tray_stats['tray_count']
                    s['单次换盘时间(秒)'] = tray_stats['tray_seconds']
                if part.get('tray_change'):
                    # SA 式：换盘时间 = 同工位 卸载 -> 下一次装载 的间隔
                    tc = measure_tray_change(
                        p_rows,
                        part['tray_change'].get('unload', ''),
                        part['tray_change'].get('load', ''),
                        cancel_event=cancel_event,
                    )
                    if tc:
                        tray_s = tc['tray_seconds']
                        s['换盘次数'] = tc['tray_count']
                        s['单次换盘时间(秒)'] = tc['tray_seconds']
                if tray_s and units_per_tray:
                    try:
                        pure_f = float(s.iloc[0].get('Pure UPH(个/小时)'))
                        base_cycle = 3600.0 * units / pure_f
                        overhead = float(tray_s) / float(units_per_tray)
                        eff_cycle = base_cycle + overhead
                        s['每颗换盘开销(秒)'] = round(overhead, 3)
                        s['有效周期(秒)'] = round(eff_cycle, 3)
                        s['有效UPH(个/小时)'] = round(3600.0 * units / eff_cycle, 2)
                    except (TypeError, ValueError, ZeroDivisionError):
                        pass
                part_summaries.append(s)
                r0 = s.iloc[0]
                p_em = parse_em_production(p_rows, cancel_event=cancel_event)
                em_input = int(p_em['InputQty'].sum()) if not p_em.empty else ''
                em_good = int(p_em['GoodQty'].sum()) if not p_em.empty else ''
                ame_rows.append({
                    '模块': name,
                    'Pure UPH(个/小时)': r0.get('Pure UPH(个/小时)'),
                    'Derated UPH M1(个/小时)': '',
                    'Derated UPH M2(个/小时)': r0.get('Derated UPH M2(个/小时)'),
                    'UPH(个/小时)': r0.get('UPH(个/小时)'),
                    '产出数(个)': r0.get('产出数(个)'),
                    'EM投入数(个)': em_input,
                    'EM良品数(个)': em_good,
                    '运行时间RUN(秒)': '',
                    '周期总数': r0.get('周期总数'),
                    '统计时长(秒)': r0.get('统计时长(秒)'),
                    '平均正常周期(秒)': r0.get('平均正常周期(秒)'),
                })
            summary = pd.concat(part_summaries, ignore_index=True)
            ame_summary = pd.DataFrame(ame_rows)
            em_all = parse_em_production(rows, cancel_event=cancel_event)
            if progress_callback:
                progress_callback(70)
            sheets = {'Summary': summary, 'AMESummary': ame_summary}
            if not em_all.empty:
                sheets['EMProduction'] = em_all
            if steps_df is not None and not steps_df.empty:
                sheets['步骤分析'] = steps_df
            out_path = os.path.join(output_dir, 'UPH_Analysis.xlsx')
            self._write_sheets(out_path, sheets, cancel_event=cancel_event)
            if progress_callback:
                progress_callback(100)
            return out_path

        if bottleneck_stations:
            # 多工位机：自动判定瓶颈工位，UPH = 每排产品数 × 3600 / 瓶颈工位每排周期
            from models.analysis import analyze_bottleneck
            units = bottleneck_units_per_row or units_per_cycle
            stations_df, bn = analyze_bottleneck(
                rows, bottleneck_stations, units, tray_change=tray_change,
                cancel_event=cancel_event,
            )
            b_name = bn.get('瓶颈工位') or ''
            eff_cycle = bn.get('有效周期(秒)')
            pure = round(units * 3600.0 / eff_cycle, 2) if eff_cycle else ''
            em = parse_em_production(rows, cancel_event=cancel_event)
            ame = pd.DataFrame([{
                '瓶颈工位': b_name,
                '瓶颈周期(秒)': bn.get('瓶颈周期(秒)') or '',
                '换盘次数': bn.get('换盘次数') or '',
                '单次换盘时间(秒)': bn.get('单次换盘时间(秒)') or '',
                '每盘排数': bn.get('每盘排数') or '',
                '每排换盘开销(秒)': bn.get('每排换盘开销(秒)') or '',
                '有效周期(秒)': eff_cycle if eff_cycle else '',
                '单颗CT(秒)': round(eff_cycle / units, 3) if eff_cycle else '',
                '每排产品数(个)': units,
                'Pure UPH(个/小时)': pure,
                'Derated UPH M1(个/小时)': '',
                'Derated UPH M2(个/小时)': pure if pure != '' else '',
                'EM投入数(个)': int(em['InputQty'].sum()) if not em.empty else '',
            }])
            if progress_callback:
                progress_callback(70)
            sheets = {'Summary': stations_df, 'AMESummary': ame}
            if not em.empty:
                sheets['EMProduction'] = em
            if steps_df is not None and not steps_df.empty:
                sheets['步骤分析'] = steps_df
            out_path = os.path.join(output_dir, 'UPH_Analysis.xlsx')
            self._write_sheets(out_path, sheets, cancel_event=cancel_event)
            if progress_callback:
                progress_callback(100)
            return out_path

        cycles = build_cycles_df(rows, trigger_keywords, normal_threshold, planned_threshold,
                                 module_pattern=module_pattern, cancel_event=cancel_event)
        summary = summarize_uph(cycles, units_per_cycle, ideal_ct=ideal_ct, max_ct=max_ct,
                                pure_uph_factor=pure_uph_factor)
        em = parse_em_production(rows, cancel_event=cancel_event)
        status_summary, _, _ = analyze_status(rows, cancel_event=cancel_event)
        run_seconds = None
        if not status_summary.empty:
            run_rows = status_summary.loc[status_summary['状态'] == 'RUN', '总时长(秒)']
            run_seconds = float(run_rows.sum()) if len(run_rows) else None
        ame_summary = summarize_uph_ame(
            cycles, units_per_cycle, ideal_ct=ideal_ct, max_ct=max_ct,
            em_df=em, run_seconds=run_seconds,
        )
        if progress_callback:
            progress_callback(70)
        sheets = {'Summary': summary, 'AMESummary': ame_summary}
        if not cycles.empty:
            sheets['CycleDetail'] = cycles
        if not em.empty:
            sheets['EMProduction'] = em
        if steps_df is not None and not steps_df.empty:
            sheets['步骤分析'] = steps_df
        out_path = os.path.join(output_dir, 'UPH_Analysis.xlsx')
        self._write_sheets(out_path, sheets, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(100)
        return out_path

    # ---------- 功能三：EFF 分析 ----------
    def analyze_eff(self, source_dir, output_dir, planned_hours=None,
                    pdt_reason_ids=None, reason_device=None, file_filters=None, rows=None,
                    cancel_event=None, activity_keywords=None, stop_reason_keywords=None,
                    progress_callback=None):
        """CoreTech AME 效率：EFF = 操作时间(运行+待机) / 计划生产时间，基于 RUN/IDLE/DOWN 状态。"""
        reason_map = None
        if reason_device:
            from models.reason_codes import load_reason_codes
            reason_map = load_reason_codes(reason_device)
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(50)
        if activity_keywords:
            status_summary, hourly, detail = analyze_status_derived(
                rows, activity_keywords, stop_reason_keywords,
                reason_map=reason_map, cancel_event=cancel_event,
            )
        else:
            status_summary, hourly, detail = analyze_status(rows, cancel_event=cancel_event)
        summary = summarize_eff_coretech(
            status_summary, detail, planned_hours=planned_hours, pdt_reason_ids=pdt_reason_ids,
            reason_map=reason_map,
        )
        pareto = down_pareto(detail, reason_map=reason_map)
        if progress_callback:
            progress_callback(70)
        sheets = {'Summary': summary}
        if not hourly.empty:
            sheets['Hourly'] = hourly
        if not pareto.empty:
            sheets['DOWN_Pareto'] = pareto
        if not detail.empty:
            sheets['Detail'] = detail
        out_path = os.path.join(output_dir, 'EFF_Analysis.xlsx')
        self._write_sheets(out_path, sheets, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(100)
        return out_path

    # ---------- 功能四：报警分析 ----------
    def analyze_alarms(self, source_dir, output_dir, alarm_keywords="报警,ALARM,ERROR,NG,失败,异常,停止信号",
                       file_filters=None, rows=None, cancel_event=None, reason_device=None,
                       module_from_path=False, progress_callback=None):
        reason_map = None
        if reason_device:
            from models.reason_codes import load_reason_codes
            reason_map = load_reason_codes(reason_device)
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(50)
        summary, by_keyword, detail = summarize_alarms(
            rows, alarm_keywords, cancel_event=cancel_event, reason_map=reason_map,
            module_from_path=module_from_path,
        )
        if progress_callback:
            progress_callback(70)
        sheets = {'Summary': summary}
        if not by_keyword.empty:
            sheets['ByKeyword'] = by_keyword
        if not detail.empty:
            sheets['Detail'] = detail
        out_path = os.path.join(output_dir, 'Alarm_Analysis.xlsx')
        self._write_sheets(out_path, sheets, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(100)
        return out_path

    # ---------- 功能五：机台状态分析 ----------
    def analyze_status(self, source_dir, output_dir, file_filters=None, rows=None, cancel_event=None,
                       activity_keywords=None, stop_reason_keywords=None, reason_device=None,
                       progress_callback=None):
        reason_map = None
        if reason_device:
            from models.reason_codes import load_reason_codes
            reason_map = load_reason_codes(reason_device)
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(50)
        if activity_keywords:
            summary, hourly, detail = analyze_status_derived(
                rows, activity_keywords, stop_reason_keywords,
                reason_map=reason_map, cancel_event=cancel_event,
            )
        else:
            summary, hourly, detail = analyze_status(rows, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(70)
        sheets = {'Summary': summary}
        if not hourly.empty:
            sheets['Hourly'] = hourly
        if not detail.empty:
            sheets['Detail'] = detail
        out_path = os.path.join(output_dir, 'Status_Analysis.xlsx')
        self._write_sheets(out_path, sheets, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(100)
        return out_path
