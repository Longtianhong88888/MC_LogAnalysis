import re
import os
import statistics
from datetime import datetime

import pandas as pd

from models.exceptions import OperationCancelled
from models.reason_codes import reason_info

_TIME_RE = re.compile(
    r'^(?:\[(?P<brackettime>\d{2}:\d{2}:\d{2}(?:\.\d+)?)\]|'
    r'(?:(?P<date>\d{4}-\d{2}-\d{2})[ T])?(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d+)?))'
)

_UNKNOWN_MODULE = '(未识别模块)'


def _module_label(module):
    return module.strip() if module and module.strip() else _UNKNOWN_MODULE


def parse_ts(content):
    """解析日志行开头的时间，支持 'YYYY-MM-DD HH:MM:SS(.mmm)'、'HH:MM:SS(.mmm)' 与 '[HH:MM:SS(.mmm)]'。"""
    m = _TIME_RE.match(content)
    if m:
        time_str = m.group('brackettime') or m.group('time')
        if time_str:
            base = (m.group('date') + ' ' + time_str) if m.group('date') else time_str
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%H:%M:%S.%f', '%H:%M:%S'):
                try:
                    return datetime.strptime(base, fmt)
                except ValueError:
                    continue
    # SA 日志：行中字段 yyyyMMdd-HH-mm-ss-fff
    m2 = re.search(r'(\d{4})(\d{2})(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{3})', content)
    if m2:
        try:
            return datetime(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)),
                            int(m2.group(4)), int(m2.group(5)), int(m2.group(6)),
                            int(m2.group(7)) * 1000)
        except ValueError:
            return None
    return None


def format_ts(ts):
    """时间戳转展示字符串；无日期的纯时间省略日期部分。"""
    if ts is None:
        return ''
    if ts.year == 1900 and ts.month == 1 and ts.day == 1:
        return ts.strftime('%H:%M:%S.%f')[:-3]
    return ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def parse_fields(content):
    """从分号分隔的日志行中提取 模块名称 / 动作名称。"""
    module = ''
    action = ''
    for seg in content.split(';'):
        seg = seg.strip()
        if seg.startswith('模块名称:'):
            module = seg.split(':', 1)[1].strip()
        elif seg.startswith('动作名称:'):
            action = seg.split(':', 1)[1].strip()
    return module, action


def split_keywords(text):
    """按逗号、顿号、分号、空白拆分关键词。"""
    if not text:
        return []
    return [k for k in re.split(r'[,，、;；\s]+', str(text).strip()) if k]


def split_phrases(text):
    """按逗号、顿号、分号拆分短语（保留空格，用于含空格的完成动作如 'UDP Module - Good'）。"""
    if not text:
        return []
    return [p.strip() for p in re.split(r'[,，、;；]+', str(text).strip()) if p.strip()]


def keyword_pattern(kws, allow_trailing_digit=True):
    """
    生成关键词匹配正则。
    纯英文字母数字的关键词按词边界匹配（避免 'NG' 误命中编码中的 'ng'），
    含中文的关键词按普通子串匹配。
    allow_trailing_digit=False 时同时排除后续紧跟数字/下划线的情况（用于周期触发词，避免 'MarkEnd1' 命中 'MarkEnd1_0'）。
    """
    parts = []
    for kw in kws:
        if re.fullmatch(r'[A-Za-z0-9]+', kw):
            if allow_trailing_digit:
                parts.append(r'(?<![A-Za-z0-9])' + re.escape(kw) + r'(?![A-Za-z])')
            else:
                parts.append(r'(?<![A-Za-z0-9_])' + re.escape(kw) + r'(?![A-Za-z0-9_])')
        else:
            parts.append(re.escape(kw))
    return '|'.join(parts)


def _prefilter(rows, pattern, regex=True):
    """向量化预筛选：返回 (contents, file_names, 匹配位置列表)，避免逐行正则扫描全部日志。"""
    contents = [str(row.get('Content', '')) for row in rows]
    file_names = [row.get('FileName', '') for row in rows]
    if pattern:
        mask = pd.Series(contents).str.contains(pattern, case=False, na=False, regex=regex)
    else:
        mask = pd.Series([False] * len(contents))
    return contents, file_names, mask.index[mask]


def build_cycles_df(rows, trigger_keywords, normal_threshold=10.0, planned_threshold=900.0,
                    module_pattern=None, cancel_event=None):
    """
    按“完成动作”为周期起点构建周期明细。
    rows: [{'FileName', 'Content'}]；返回 DataFrame: FileName/Module/TriggerTime/CycleSeconds/Class/TriggerContent
    module_pattern: 可选正则，从日志行中提取模组名（如 FR 的左轴/右轴），未提供时用 模块名称: 字段
    """
    kws = split_phrases(trigger_keywords)
    pattern = keyword_pattern(kws, allow_trailing_digit=False) if kws else None
    contents, file_names, matched = _prefilter(rows, pattern)
    per_module = {}
    for idx in matched:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = contents[idx]
        ts = parse_ts(content)
        if ts is None:
            continue
        if module_pattern:
            m = re.search(module_pattern, content)
            module = _module_label(m.group(1) if m else '')
        else:
            module, _ = parse_fields(content)
            module = _module_label(module)
        per_module.setdefault(module, []).append({
            'ts': ts,
            'file': file_names[idx],
            'content': content,
        })

    records = []
    for module, events in per_module.items():
        if events and events[0]['ts'].year != 1900:
            events.sort(key=lambda e: e['ts'])
        # 纯时间日志保持读取顺序（文件按名排序、行按写入顺序），可正确处理跨零点/跨日
        prev = None
        for ev in events:
            if prev is not None:
                delta = (ev['ts'] - prev['ts']).total_seconds()
                if delta < 0:
                    delta += 86400.0  # 跨零点
                if delta >= 0:
                    if delta > planned_threshold:
                        cls = '计划性停机'
                    elif delta > normal_threshold:
                        cls = '异常周期'
                    else:
                        cls = '正常周期'
                    records.append({
                        'FileName': prev['file'],
                        'Module': module,
                        'TriggerTime': format_ts(prev['ts']),
                        'CycleSeconds': round(delta, 3),
                        'Class': cls,
                        'TriggerContent': prev['content'],
                    })
            prev = ev
    return pd.DataFrame(
        records,
        columns=['FileName', 'Module', 'TriggerTime', 'CycleSeconds', 'Class', 'TriggerContent'],
    )


def summarize_uph(cycles_df, units_per_cycle=1, ideal_ct=None, max_ct=None, pure_uph_factor=1.0):
    """
    按模块汇总 UPH（CoreTech AME 定义）：
    - UPH(个/小时)：产出数 / 统计时长（实际平均）
    - Pure UPH：3600 × 每周期产出 / 理想周期CT × pure_uph_factor（未提供时取正常周期平均；并行工位可设 0.5）
    - Derated UPH M2：3600 × 每周期产出 / 平均I/O周期（剔除 <0.9×理想CT 和 >1.1×最大理论CT 的离群点）
    """
    rows = []
    for module, g in cycles_df.groupby('Module', sort=False):
        normal = g.loc[g['Class'] == '正常周期', 'CycleSeconds']
        abnormal = g.loc[g['Class'] == '异常周期', 'CycleSeconds']
        planned = g.loc[g['Class'] == '计划性停机', 'CycleSeconds']
        avg_normal = normal.mean() if len(normal) else None
        total_sec = g['CycleSeconds'].sum()
        output_count = len(g) * units_per_cycle
        uph = round(output_count / (total_sec / 3600.0), 2) if total_sec > 0 else ''
        pure = round(3600.0 * units_per_cycle / ideal_ct * pure_uph_factor, 2) if ideal_ct else (
            round(3600.0 * units_per_cycle / avg_normal * pure_uph_factor, 2) if avg_normal else ''
        )
        valid = g['CycleSeconds']
        if ideal_ct:
            valid = valid[valid >= 0.9 * ideal_ct]
        if max_ct:
            valid = valid[valid <= 1.1 * max_ct]
        avg_valid = valid.mean() if len(valid) else None
        derated_m2 = round(3600.0 * units_per_cycle / avg_valid, 2) if avg_valid else ''
        rows.append({
            '模块': module,
            '周期总数': len(g),
            '产出数(个)': output_count,
            '统计时长(秒)': round(total_sec, 3),
            '正常周期数': len(normal),
            '异常周期数': len(abnormal),
            '计划性停机数': len(planned),
            '平均正常周期(秒)': round(avg_normal, 3) if avg_normal else '',
            'UPH(个/小时)': uph,
            'Pure UPH(个/小时)': pure,
            'Derated UPH M2(个/小时)': derated_m2,
            '涉及文件数': g['FileName'].nunique(),
        })
    return pd.DataFrame(rows)


def summarize_uph_ame(cycles_df, units_per_cycle=1, ideal_ct=None, max_ct=None,
                      em_df=None, run_seconds=None):
    """CoreTech AME 整机 UPH 指标：Pure UPH（左右轴合并总产能，不乘单轴系数）、M1、M2。"""
    total_cycles = len(cycles_df)
    total_sec = cycles_df['CycleSeconds'].sum() if total_cycles else 0.0
    module_count = cycles_df['Module'].nunique() if total_cycles else 0
    normal = cycles_df.loc[cycles_df['Class'] == '正常周期', 'CycleSeconds'] if total_cycles else pd.Series(dtype=float)
    avg_normal = normal.mean() if len(normal) else None
    pure = round(3600.0 * units_per_cycle / ideal_ct, 2) if ideal_ct else (
        round(3600.0 * units_per_cycle / avg_normal, 2) if avg_normal else ''
    )
    # Derated UPH M2：整机 = 各模组 M2 之和（FR 为左轴+右轴，并行工位不按合并周期平均）
    m2_total = 0.0
    if total_cycles:
        for _, g in cycles_df.groupby('Module', sort=False):
            valid = g['CycleSeconds']
            if ideal_ct:
                valid = valid[valid >= 0.9 * ideal_ct]
            if max_ct:
                valid = valid[valid <= 1.1 * max_ct]
            if len(valid):
                m2_total += 3600.0 * units_per_cycle / valid.mean()
    derated_m2 = round(m2_total, 2) if m2_total else ''
    em_input = int(em_df['InputQty'].sum()) if em_df is not None and not em_df.empty else None
    em_good = int(em_df['GoodQty'].sum()) if em_df is not None and not em_df.empty else None
    if module_count > 1:
        # 并行多模组机台（如 FR 左轴+右轴）：整机 M1 = 各模组 M1 之和
        m1_total = 0.0
        for _, g in cycles_df.groupby('Module', sort=False):
            secs = g['CycleSeconds'].sum()
            if secs > 0:
                m1_total += len(g) * units_per_cycle / (secs / 3600.0)
        derated_m1 = round(m1_total, 2) if m1_total else ''
    else:
        # 单模组机台：CoreTech Method 1 = EM 投入 / RUN 时长
        derated_m1 = round(em_input / (run_seconds / 3600.0), 2) if em_input and run_seconds else ''
    return pd.DataFrame([{
        'Pure UPH(个/小时)': pure,
        'Derated UPH M1(个/小时)': derated_m1,
        'Derated UPH M2(个/小时)': derated_m2,
        'EM投入数(个)': em_input if em_input is not None else '',
        'EM良品数(个)': em_good if em_good is not None else '',
        '运行时间RUN(秒)': round(run_seconds, 3) if run_seconds else '',
        '周期总数': total_cycles,
        '统计时长(秒)': round(total_sec, 3) if total_sec else '',
        '平均正常周期(秒)': round(avg_normal, 3) if avg_normal else '',
        '理想周期CT(秒)': ideal_ct if ideal_ct else '',
        '最大理论周期CT(秒)': max_ct if max_ct else '',
    }])


def summarize_eff_coretech(status_summary, status_detail, planned_hours=None, pdt_reason_ids=None,
                           reason_map=None):
    """
    CoreTech AME EFF（基于机器状态）：
    EFF = 操作时间(运行RUN+待机IDLE) / 计划生产时间
    可用性损失 = 停机时间(DOWN)，可依据 ReasonID 拆分为 计划停机pDT / 非计划停机uDT。
    """
    secs = {r['状态']: r['总时长(秒)'] for _, r in status_summary.iterrows()}
    run = float(secs.get('RUN', 0.0))
    idle = float(secs.get('IDLE', 0.0))
    down = float(secs.get('DOWN', 0.0))
    total = run + idle + down
    planned = planned_hours * 3600.0 if planned_hours else total

    down_rows = status_detail.loc[status_detail['Status'] == 'DOWN'] if not status_detail.empty else status_detail
    # pDT 判定：EReason 清单匹配优先（Planned/Routine Downtime），手动计划停机码补充
    planned_mask = pd.Series(False, index=down_rows.index)
    if reason_map:
        from models.reason_codes import is_planned
        planned_mask |= down_rows['ReasonID'].apply(lambda rid: is_planned(reason_map, rid))
    if pdt_reason_ids:
        manual_set = set(split_keywords(pdt_reason_ids))
        planned_mask |= down_rows['ReasonID'].isin(manual_set)
    pdt = float(down_rows.loc[planned_mask, 'DurationSeconds'].sum())
    udt = down - pdt
    operating = run + idle
    eff = round(operating / planned * 100, 2) if planned > 0 else ''
    return pd.DataFrame([{
        '总时间(秒)': round(total, 3),
        '计划生产时间(秒)': round(planned, 3),
        '运行时间RUN(秒)': round(run, 3),
        '待机时间IDLE(秒)': round(idle, 3),
        '停机时间DOWN(秒)': round(down, 3),
        '计划停机pDT(秒)': round(pdt, 3),
        '非计划停机uDT(秒)': round(udt, 3),
        '可用性损失(秒)': round(down, 3),
        '操作时间(秒)': round(operating, 3),
        'EFF(%)': eff,
    }])


def down_pareto(status_detail, reason_map=None):
    """停机 DOWN 的 ReasonID Pareto（次数、总时长、占比）；提供原因清单时附加原因名称与停机类型。"""
    down_rows = status_detail.loc[status_detail['Status'] == 'DOWN']
    if down_rows.empty:
        cols = ['ReasonID', '次数', '总时长(秒)', '占比(%)']
        if reason_map:
            cols += ['原因名称', '停机类型']
        return pd.DataFrame(columns=cols)
    g = (
        down_rows.groupby('ReasonID', sort=False)['DurationSeconds']
        .agg(['count', 'sum'])
        .reset_index()
    )
    g.columns = ['ReasonID', '次数', '总时长(秒)']
    g = g.sort_values('总时长(秒)', ascending=False).reset_index(drop=True)
    g['占比(%)'] = (g['总时长(秒)'] / g['总时长(秒)'].sum() * 100).round(2)
    if reason_map:
        from models.reason_codes import is_planned, reason_info
        g['原因名称'] = g['ReasonID'].apply(
            lambda rid: (reason_info(reason_map, rid) or {}).get('name', '')
        )
        g['停机类型'] = g['ReasonID'].apply(
            lambda rid: 'pDT' if is_planned(reason_map, rid) else 'uDT'
        )
    return g


def summarize_alarms(rows, alarm_keywords, cancel_event=None, reason_map=None):
    """报警统计：汇总（按模块）、按关键词计数、明细。"""
    kws = split_keywords(alarm_keywords)
    pattern = keyword_pattern(kws) if kws else None
    contents, file_names, matched = _prefilter(rows, pattern)
    detail = []
    for idx in matched:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = contents[idx]
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            module, _ = parse_fields(content)
            reason_name = ''
            if reason_map:
                em = re.search(r'\[Error (\d+)\]', content)
                if em:
                    info = reason_info(reason_map, em.group(1))
                    reason_name = info['name'] if info else ''
            detail.append({
                'FileName': file_names[idx],
                'Timestamp': format_ts(parse_ts(content)),
                'Module': _module_label(module),
                '命中关键词': m.group(0),
                'Message': content.split(' ', 2)[-1] if ' ' in content else content,
                'Content': content,
                '原因名称': reason_name,
            })
    if not detail:
        return (
            pd.DataFrame(columns=['模块', '报警次数', '不同报警消息数']),
            pd.DataFrame(columns=['关键词', '报警次数']),
            pd.DataFrame(columns=['FileName', 'Timestamp', 'Module', '命中关键词', 'Message', 'Content', '原因名称']),
        )
    detail_df = pd.DataFrame(detail)
    summary = (
        detail_df.groupby('Module', sort=False)
        .agg(报警次数=('Content', 'count'), 不同报警消息数=('Message', 'nunique'))
        .reset_index()
    )
    by_keyword = (
        detail_df.groupby('命中关键词', sort=False)
        .agg(报警次数=('Content', 'count'))
        .reset_index()
    )
    return summary, by_keyword, detail_df


_STATUS_RE = re.compile(r'status:(RU[A-F0-9]{3}|RUN|IDLE|DOWN|WARN)', re.IGNORECASE)
_REASON_RE = re.compile(r'ReasonID:([0-9A-Fa-f]+)')


def _normalize_status(raw):
    """RUFFF（含各 Socket/Tester 状态码）归一化为 RUN。"""
    s = raw.upper()
    return 'RUN' if s.startswith('RU') else s


def _finalize_status(records):
    """由状态记录（StartTime/Status/ReasonID/DurationSeconds/NextStatus/_ts）生成汇总/按小时/明细。"""
    detail_cols = ['FileName', 'StartTime', 'Status', 'ReasonID', 'DurationSeconds', 'NextStatus']
    detail_df = pd.DataFrame([{k: r[k] for k in detail_cols} for r in records], columns=detail_cols)
    if detail_df.empty:
        return (
            pd.DataFrame(columns=['状态', '次数', '总时长(秒)', '占比(%)']),
            pd.DataFrame(columns=['小时', 'RUN(秒)', 'IDLE(秒)', 'DOWN(秒)', '合计(秒)',
                                  'RUN占比(%)', 'IDLE占比(%)', 'DOWN占比(%)', 'EFF(%)']),
            detail_df,
        )

    total = detail_df['DurationSeconds'].sum()
    summary = (
        detail_df.groupby('Status', sort=False)['DurationSeconds']
        .agg(['count', 'sum'])
        .reset_index()
    )
    summary.columns = ['状态', '次数', '总时长(秒)']
    summary['占比(%)'] = (summary['总时长(秒)'] / total * 100).round(2)
    summary = summary.sort_values('总时长(秒)', ascending=False).reset_index(drop=True)

    hour_sums = {}
    for r in records:
        ts = r['_ts']
        if ts.year == 1900:
            stem = os.path.splitext(r['FileName'])[0]
            hour = f"{stem} {ts.strftime('%H:00')}"
        else:
            hour = ts.strftime('%Y-%m-%d %H:00')
        hour_sums[(hour, r['Status'])] = hour_sums.get((hour, r['Status']), 0.0) + r['DurationSeconds']
    hours = sorted({h for h, _ in hour_sums})
    hourly_rows = []
    for h in hours:
        run = hour_sums.get((h, 'RUN'), 0.0)
        idle = hour_sums.get((h, 'IDLE'), 0.0)
        down = hour_sums.get((h, 'DOWN'), 0.0)
        total_h = run + idle + down
        hourly_rows.append({
            '小时': h,
            'RUN(秒)': round(run, 3),
            'IDLE(秒)': round(idle, 3),
            'DOWN(秒)': round(down, 3),
            '合计(秒)': round(total_h, 3),
            'RUN占比(%)': round(run / total_h * 100, 2) if total_h else '',
            'IDLE占比(%)': round(idle / total_h * 100, 2) if total_h else '',
            'DOWN占比(%)': round(down / total_h * 100, 2) if total_h else '',
            'EFF(%)': round((run + idle) / total_h * 100, 2) if total_h else '',
        })
    return summary, pd.DataFrame(hourly_rows), detail_df


def analyze_status(rows, cancel_event=None):
    """
    机台状态分析：识别 status:RUN/IDLE/DOWN 状态行，计算各状态时长与占比、按小时分布。
    返回 (汇总, 按小时, 明细)。
    """
    contents, file_names, matched = _prefilter(rows, 'status:')
    events = []
    for idx in matched:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = contents[idx]
        m = _STATUS_RE.search(content)
        if not m:
            continue
        ts = parse_ts(content)
        if ts is None:
            continue
        reason_m = _REASON_RE.search(content)
        events.append({
            'ts': ts,
            'file': file_names[idx],
            'status': _normalize_status(m.group(1)),
            'reason': reason_m.group(1) if reason_m else '',
            'content': content,
        })
    if events and events[0]['ts'].year != 1900:
        events.sort(key=lambda e: e['ts'])
    # 纯时间日志保持读取顺序（文件按名排序、行按写入顺序），跨零点/跨日时长按 +86400 处理

    records = []
    for i in range(len(events) - 1):
        delta = (events[i + 1]['ts'] - events[i]['ts']).total_seconds()
        if delta < 0:
            delta += 86400.0  # 跨零点
        if delta >= 0:
            records.append({
                'FileName': events[i]['file'],
                'StartTime': format_ts(events[i]['ts']),
                'Status': events[i]['status'],
                'ReasonID': events[i]['reason'],
                'DurationSeconds': round(delta, 3),
                'NextStatus': events[i + 1]['status'],
                '_ts': events[i]['ts'],
            })

    return _finalize_status(records)


_STOP_REASON_RE = re.compile(r'ErrorName = \[(.*?)\]')


def _classify_stop(reason, reason_map):
    """按 EReason 清单匹配 AutoRun Stop 原因 → 状态（Error 码→DOWN/IDLE/RUN，操作员停止→IDLE）。"""
    m = re.search(r'Error (\d+)', reason)
    if m:
        info = reason_info(reason_map, m.group(1)) if reason_map else None
        if info and info.get('state'):
            return info['state']
        return 'DOWN'
    if '정지' in reason or 'stop' in reason.lower() or 'Stop' in reason:
        return 'IDLE'
    return 'IDLE'


def analyze_status_derived(rows, activity_keywords, stop_reason_keywords, reason_map=None,
                           cancel_event=None):
    """
    推导式机台状态：以活动事件（如 UDP Module - Good）表示运行，AutoRun Stop 事件按 EReason 清单
    分类为 DOWN/IDLE，构建 RUN/IDLE/DOWN 时间线并计算时长与占比。
    """
    activity_kws = split_phrases(activity_keywords)
    stop_kws = split_phrases(stop_reason_keywords)
    events = []
    for row in rows:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = str(row.get('Content', ''))
        is_activity = activity_kws and any(kw in content for kw in activity_kws)
        is_stop = any(kw in content for kw in stop_kws)
        if not is_activity and not is_stop:
            continue
        ts = parse_ts(content)
        if ts is None:
            continue
        if is_stop:
            m = _STOP_REASON_RE.search(content)
            reason = m.group(1) if m else ''
            code_m = re.search(r'Error (\d+)', reason)
            reason_id = code_m.group(1) if code_m else reason
            events.append({
                'ts': ts, 'file': row.get('FileName', ''), 'kind': 'stop',
                'state': _classify_stop(reason, reason_map),
                'reason_id': reason_id, 'content': content,
            })
        else:
            events.append({
                'ts': ts, 'file': row.get('FileName', ''), 'kind': 'activity',
                'state': 'RUN', 'reason_id': '', 'content': content,
            })
    if not events:
        return _finalize_status([])
    if events[0]['ts'].year != 1900:
        events.sort(key=lambda e: e['ts'])

    records = []
    cur_state = None
    last_change = None
    for ev in events:
        new_state = 'RUN' if ev['kind'] == 'activity' else ev['state']
        if cur_state is None:
            cur_state = new_state
            last_change = ev['ts']
            last_file = ev['file']
            last_reason = ev['reason_id']
            continue
        if new_state != cur_state:
            delta = (ev['ts'] - last_change).total_seconds()
            if delta < 0:
                delta += 86400.0
            if delta >= 0:
                records.append({
                    'FileName': last_file,
                    'StartTime': format_ts(last_change),
                    'Status': cur_state,
                    'ReasonID': last_reason,
                    'DurationSeconds': round(delta, 3),
                    'NextStatus': new_state,
                    '_ts': last_change,
                })
            cur_state = new_state
            last_change = ev['ts']
            last_file = ev['file']
            last_reason = ev['reason_id']
    return _finalize_status(records)


_EM_FIELD_RE = re.compile(r'(lotno|inputqty|goodqty|ngqty|head|startdatetime|enddatetime|datetime):([^,\]]*)')


def parse_compact_dt(value):
    """解析 yyyyMMddHHmmssfff 紧凑格式时间。"""
    if not value:
        return None
    for fmt in ('%Y%m%d%H%M%S%f', '%Y%m%d%H%M%S'):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_em_production(rows, cancel_event=None):
    """
    解析协议 EM（設備產量數據上傳）消息：
    [EM][lotno:...,inputqty:...,goodqty:...,ngqty:...,head:...,startdatetime:...,enddatetime:...,datetime:...]
    """
    contents, file_names, matched = _prefilter(rows, '[EM]', regex=False)
    records = []
    for idx in matched:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = contents[idx]
        fields = dict(_EM_FIELD_RE.findall(content))
        if not fields:
            continue

        def num(key):
            try:
                return int(fields.get(key, '') or 0)
            except ValueError:
                return 0

        input_qty = num('inputqty')
        good_qty = num('goodqty')
        ng_qty = num('ngqty')
        start = parse_compact_dt(fields.get('startdatetime'))
        end = parse_compact_dt(fields.get('enddatetime'))
        duration_h = ((end - start).total_seconds() / 3600.0) if (start and end and end > start) else None
        records.append({
            'FileName': file_names[idx],
            'Timestamp': format_ts(parse_ts(content)),
            'LotNo': fields.get('lotno', ''),
            'InputQty': input_qty,
            'GoodQty': good_qty,
            'NgQty': ng_qty,
            'Head': fields.get('head', ''),
            'StartTime': format_ts(start),
            'EndTime': format_ts(end),
            'DurationHours': round(duration_h, 3) if duration_h else '',
            'UPH(个/小时)': round(good_qty / duration_h, 2) if duration_h else '',
            'NG率(%)': round(ng_qty / input_qty * 100, 2) if input_qty else '',
        })
    return pd.DataFrame(
        records,
        columns=['FileName', 'Timestamp', 'LotNo', 'InputQty', 'GoodQty', 'NgQty',
                 'Head', 'StartTime', 'EndTime', 'DurationHours', 'UPH(个/小时)', 'NG率(%)'],
    )


def _station_cycle(rows, pattern, events_per_row, cancel_event=None):
    """通用工位周期：收集完成事件时间戳，按每排事件数折算每排周期中位秒。
    返回 (事件数, 每排事件数, 每排周期中位秒)。events_per_row='auto' 时按参考排数自动估算。"""
    tlist = []
    for row in rows:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = str(row.get('Content', ''))
        if not pattern or pattern not in content:
            continue
        t = parse_ts(content)
        if t is not None:
            tlist.append(t)
    tlist.sort()
    k = events_per_row
    if not tlist:
        return 0, k, None
    if k == 'auto':
        return len(tlist), k, None  # auto 由调用方传入参考排数后再算
    intervals = [
        (tlist[i + k] - tlist[i]).total_seconds()
        for i in range(len(tlist) - k)
        if 0 < (tlist[i + k] - tlist[i]).total_seconds() < 3600
    ]
    return len(tlist), k, (statistics.median(intervals) if intervals else None)


def _station_dispense(rows, cancel_event=None):
    """SA 点胶工位：DispOneChipProfileWorkCycle 每次点胶一排，每排 1 次。"""
    return _station_cycle(rows, "DispOneChipProfileWorkCycle", 1, cancel_event)


def _station_attach(rows, cancel_event=None):
    """SA 贴附工位：AfterPickUp StopCondition 每排 2 次（两个取料头各一次）。"""
    return _station_cycle(rows, "AfterPickUp StopCondition", 2, cancel_event)


def _station_heatpress(rows, cancel_event=None):
    """SA 热压工位：两个加热头并行加热同一排，Heater 0 完成事件每排 1 次。"""
    return _station_cycle(rows, "Heater 0 :Heating Complete", 1, cancel_event)


def _station_inspect(rows, ref_rows, cancel_event=None):
    """SA 检测工位：UDP Module - Good 每排 k 次（k = round(事件数/参考排数) 自动估算）。"""
    count, _, _ = _station_cycle(rows, "UDP Module - Good", 1, cancel_event)
    k = max(1, round(count / ref_rows)) if ref_rows else 1
    _, _, med = _station_cycle(rows, "UDP Module - Good", k, cancel_event)
    return count, k, med


def analyze_bottleneck(rows, stations, units_per_row, cancel_event=None):
    """
    自动判定瓶颈工位：每个工位按各自逻辑计算每排周期，取最长工位为瓶颈。
    返回 (工位明细DataFrame, 瓶颈周期秒, 瓶颈工位名)。
    stations: [{'name','function'|'pattern','events_per_row'}]，function 走专属工位逻辑。
    """
    collected = {}
    for st in stations:
        fn = st.get('function')
        name = st.get('name')
        if fn == 'sa_dispense':
            collected[name] = _station_dispense(rows, cancel_event)
        elif fn == 'sa_attach':
            collected[name] = _station_attach(rows, cancel_event)
        elif fn == 'sa_heatpress':
            collected[name] = _station_heatpress(rows, cancel_event)
        elif fn == 'sa_inspect':
            # 参考排数：固定工位中折算排数最大值
            ref_rows = max(
                (c // k for c, k, _ in collected.values() if isinstance(k, int) and k >= 1),
                default=0,
            )
            collected[name] = _station_inspect(rows, ref_rows, cancel_event)
        else:
            collected[name] = _station_cycle(rows, st.get('pattern', ''), st.get('events_per_row', 1),
                                             cancel_event)

    ref_rows = max(
        (c // k for c, k, _ in collected.values() if isinstance(k, int) and k >= 1),
        default=0,
    )
    rows_list = []
    bottleneck_time = 0.0
    bottleneck_name = ''
    for name, (count, k, med) in collected.items():
        if not count:
            rows_list.append({'工位': name, '事件数': 0, '每排事件数': k, '每排周期(秒)': '', '极限UPH(个/小时)': '', '瓶颈': ''})
            continue
        if k == 'auto':
            k = max(1, round(count / ref_rows)) if ref_rows else 1
            pattern = next((st.get('pattern') for st in stations if st.get('name') == name), '')
            _, _, med = _station_cycle(rows, pattern, k, cancel_event)
        uph = round(units_per_row * 3600.0 / med, 2) if med else ''
        if med is not None and med > bottleneck_time:
            bottleneck_time = med
            bottleneck_name = name
        rows_list.append({
            '工位': name,
            '事件数': count,
            '每排事件数': k,
            '每排周期(秒)': round(med, 3) if med else '',
            '极限UPH(个/小时)': uph,
            '瓶颈': '',
        })

    df = pd.DataFrame(rows_list)
    if bottleneck_time:
        df['瓶颈'] = df['每排周期(秒)'].apply(
            lambda v: '★' if isinstance(v, (int, float)) and abs(v - bottleneck_time) < 0.001 else ''
        )
    return df, round(bottleneck_time, 3) if bottleneck_time else None, bottleneck_name
