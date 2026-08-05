import os
import re

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

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
from utils.file_utils import read_files, clean_for_excel


class LogModel:
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
        with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
            for sheet_name, df in sheets.items():
                if cancel_event is not None and cancel_event.is_set():
                    from models.exceptions import OperationCancelled
                    raise OperationCancelled()
                if len(df) <= max_rows:
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                else:
                    # 超限自动拆分：AllLogs → AllLogs_1, AllLogs_2 ...
                    n = (len(df) + max_rows - 1) // max_rows
                    for i in range(n):
                        if cancel_event is not None and cancel_event.is_set():
                            from models.exceptions import OperationCancelled
                            raise OperationCancelled()
                        chunk = df.iloc[i * max_rows:(i + 1) * max_rows]
                        name = f"{sheet_name}_{i + 1}"[:31]
                        chunk.to_excel(writer, sheet_name=name, index=False)
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

        if progress_callback:
            progress_callback(50)

        has_filtered_rows = not filtered_df.empty
        has_separator = separator is not None and separator != ''
        generate_filtered = has_filtered_rows or has_separator

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

        if progress_callback:
            progress_callback(70)

        sheets = {'AllLogs': df_all}
        if generate_filtered and filtered_df is not None and not filtered_df.empty:
            sheets['Filtered'] = filtered_df
        out_path = os.path.join(output_dir, 'LogAnalysis.xlsx')
        self._write_sheets(out_path, sheets, cancel_event=cancel_event)

        if progress_callback:
            progress_callback(100)
        return out_path

    # ---------- 功能二：UPH 分析 ----------
    def analyze_uph(self, source_dir, output_dir, trigger_keywords="MarkEnd1", units_per_cycle=1,
                    normal_threshold=10.0, planned_threshold=900.0,
                    ideal_ct=None, max_ct=None, file_filters=None, module_pattern=None,
                    pure_uph_factor=1.0, rows=None, cancel_event=None, progress_callback=None):
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(40)
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
                    pdt_reason_ids=None, file_filters=None, rows=None, cancel_event=None,
                    progress_callback=None):
        """CoreTech AME 效率：EFF = 操作时间(运行+待机) / 计划生产时间，基于 RUN/IDLE/DOWN 状态。"""
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(50)
        status_summary, hourly, detail = analyze_status(rows, cancel_event=cancel_event)
        summary = summarize_eff_coretech(
            status_summary, detail, planned_hours=planned_hours, pdt_reason_ids=pdt_reason_ids,
        )
        pareto = down_pareto(detail)
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
                       file_filters=None, rows=None, cancel_event=None, progress_callback=None):
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(50)
        summary, by_keyword, detail = summarize_alarms(rows, alarm_keywords, cancel_event=cancel_event)
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
                       progress_callback=None):
        if progress_callback:
            progress_callback(5)
        rows = rows if rows is not None else self._read_all(
            source_dir, progress_callback, file_filters=file_filters, cancel_event=cancel_event)
        if progress_callback:
            progress_callback(50)
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
