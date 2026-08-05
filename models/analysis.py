import re
import os
from datetime import datetime

import pandas as pd

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
    if not m:
        return None
    time_str = m.group('brackettime') or m.group('time')
    if not time_str:
        return None
    base = (m.group('date') + ' ' + time_str) if m.group('date') else time_str
    for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%H:%M:%S.%f', '%H:%M:%S'):
        try:
            return datetime.strptime(base, fmt)
        except ValueError:
            continue
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


def build_cycles_df(rows, trigger_keywords, normal_threshold=10.0, planned_threshold=900.0):
    """
    按“完成动作”为周期起点构建周期明细。
    rows: [{'FileName', 'Content'}]；返回 DataFrame: FileName/Module/TriggerTime/CycleSeconds/Class/TriggerContent
    """
    kws = split_keywords(trigger_keywords)
    per_module = {}
    for row in rows:
        content = str(row.get('Content', ''))
        ts = parse_ts(content)
        if ts is None:
            continue
        # 关键词匹配整行内容（兼容“动作名称:xxx”和普通消息两种日志格式）
        if not kws or not re.search(keyword_pattern(kws, allow_trailing_digit=False), content, re.IGNORECASE):
            continue
        module, _ = parse_fields(content)
        module = _module_label(module)
        per_module.setdefault(module, []).append({
            'ts': ts,
            'file': row.get('FileName', ''),
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


def summarize_uph(cycles_df, units_per_cycle=1, ideal_ct=None, max_ct=None):
    """
    按模块汇总 UPH（CoreTech AME 定义）：
    - UPH(个/小时)：产出数 / 统计时长（实际平均）
    - Pure UPH：3600 × 每周期产出 / 理想周期CT（未提供时取正常周期平均）
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
        pure = round(3600.0 * units_per_cycle / ideal_ct, 2) if ideal_ct else (
            round(3600.0 * units_per_cycle / avg_normal, 2) if avg_normal else ''
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
    """CoreTech AME 整机 UPH 指标：Pure UPH、Derated UPH M1（投入/运行时间）、Derated UPH M2。"""
    total_cycles = len(cycles_df)
    total_sec = cycles_df['CycleSeconds'].sum() if total_cycles else 0.0
    normal = cycles_df.loc[cycles_df['Class'] == '正常周期', 'CycleSeconds'] if total_cycles else pd.Series(dtype=float)
    avg_normal = normal.mean() if len(normal) else None
    pure = round(3600.0 * units_per_cycle / ideal_ct, 2) if ideal_ct else (
        round(3600.0 * units_per_cycle / avg_normal, 2) if avg_normal else ''
    )
    valid = cycles_df['CycleSeconds'] if total_cycles else pd.Series(dtype=float)
    if ideal_ct:
        valid = valid[valid >= 0.9 * ideal_ct]
    if max_ct:
        valid = valid[valid <= 1.1 * max_ct]
    avg_valid = valid.mean() if len(valid) else None
    derated_m2 = round(3600.0 * units_per_cycle / avg_valid, 2) if avg_valid else ''
    em_input = int(em_df['InputQty'].sum()) if em_df is not None and not em_df.empty else None
    em_good = int(em_df['GoodQty'].sum()) if em_df is not None and not em_df.empty else None
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


def summarize_eff_coretech(status_summary, status_detail, planned_hours=None, pdt_reason_ids=None):
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

    pdt_set = set(split_keywords(pdt_reason_ids)) if pdt_reason_ids else set()
    if pdt_set and not status_detail.empty:
        down_rows = status_detail.loc[status_detail['Status'] == 'DOWN']
        pdt = float(down_rows.loc[down_rows['ReasonID'].isin(pdt_set), 'DurationSeconds'].sum())
    else:
        pdt = 0.0
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


def down_pareto(status_detail):
    """停机 DOWN 的 ReasonID Pareto（次数、总时长、占比）。"""
    down_rows = status_detail.loc[status_detail['Status'] == 'DOWN']
    if down_rows.empty:
        return pd.DataFrame(columns=['ReasonID', '次数', '总时长(秒)', '占比(%)'])
    g = (
        down_rows.groupby('ReasonID', sort=False)['DurationSeconds']
        .agg(['count', 'sum'])
        .reset_index()
    )
    g.columns = ['ReasonID', '次数', '总时长(秒)']
    g = g.sort_values('总时长(秒)', ascending=False).reset_index(drop=True)
    g['占比(%)'] = (g['总时长(秒)'] / g['总时长(秒)'].sum() * 100).round(2)
    return g


def summarize_alarms(rows, alarm_keywords):
    """报警统计：汇总（按模块）、按关键词计数、明细。"""
    kws = split_keywords(alarm_keywords)
    pattern = keyword_pattern(kws) if kws else ''
    detail = []
    for row in rows:
        content = str(row.get('Content', ''))
        if not pattern:
            continue
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            module, _ = parse_fields(content)
            detail.append({
                'FileName': row.get('FileName', ''),
                'Timestamp': format_ts(parse_ts(content)),
                'Module': _module_label(module),
                '命中关键词': m.group(0),
                'Message': content.split(' ', 2)[-1] if ' ' in content else content,
                'Content': content,
            })
    if not detail:
        return (
            pd.DataFrame(columns=['模块', '报警次数', '不同报警消息数']),
            pd.DataFrame(columns=['关键词', '报警次数']),
            pd.DataFrame(columns=['FileName', 'Timestamp', 'Module', '命中关键词', 'Message', 'Content']),
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


def analyze_status(rows):
    """
    机台状态分析：识别 status:RUN/IDLE/DOWN 状态行，计算各状态时长与占比、按小时分布。
    返回 (汇总, 按小时, 明细)。
    """
    events = []
    for row in rows:
        content = str(row.get('Content', ''))
        m = _STATUS_RE.search(content)
        if not m:
            continue
        ts = parse_ts(content)
        if ts is None:
            continue
        reason_m = _REASON_RE.search(content)
        events.append({
            'ts': ts,
            'file': row.get('FileName', ''),
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
            # 纯时间日志按日分文件：小时带文件名前缀，避免多日数据合并到同一小时
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


def parse_em_production(rows):
    """
    解析协议 EM（設備產量數據上傳）消息：
    [EM][lotno:...,inputqty:...,goodqty:...,ngqty:...,head:...,startdatetime:...,enddatetime:...,datetime:...]
    """
    records = []
    for row in rows:
        content = str(row.get('Content', ''))
        if '[EM]' not in content:
            continue
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
            'FileName': row.get('FileName', ''),
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
