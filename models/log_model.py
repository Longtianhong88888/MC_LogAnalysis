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
                file_filters=None, rows=None, cancel_event=None, progress_callback=None):
        if progress_callback:
            progress_callback(5)
        all_data = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        df_all = pd.DataFrame(all_data)

        if progress_callback:
            progress_callback(30)

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
                    tray_change=None, rows=None, cancel_event=None, progress_callback=None):
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(40)

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
                '单次换盘净时间(秒)': bn.get('单次换盘净时间(秒)') or '',
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
        summary, by_keyword, detail = summarize_alarms(
            rows, alarm_keywords, cancel_event=cancel_event, reason_map=reason_map,
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
