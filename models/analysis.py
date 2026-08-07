import re
import os
import bisect
import statistics
from datetime import datetime
from collections import Counter

import pandas as pd

from models.exceptions import OperationCancelled
from models.reason_codes import reason_info

_TIME_RE = re.compile(
    r'^(?:\[(?P<brackettime>\d{2}:\d{2}:\d{2}(?:[.]\d{1,3}|\s\d{3})?)\]|'
    r'(?:(?P<date>\d{4}[-/]\d{2}[-/]\d{2})[ T])?(?P<time>\d{2}:\d{2}:\d{2}(?:[.]\d{1,3}|\s\d{3})?))'
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
            if ' ' in time_str:
                # ACF 格式：HH:MM:SS 毫秒
                hms, ms = time_str.split(' ', 1)
                h, mi, s = map(int, hms.split(':'))
                t = datetime(1900, 1, 1, h, mi, s, int(ms) * 1000)
                if m.group('date'):
                    d = datetime.strptime(m.group('date'), '%Y-%m-%d')
                    t = t.replace(year=d.year, month=d.month, day=d.day)
                return t
            base = (m.group('date') + ' ' + time_str) if m.group('date') else time_str
            for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S',
                        '%Y/%m/%d %H:%M:%S.%f', '%Y/%m/%d %H:%M:%S',
                        '%H:%M:%S.%f', '%H:%M:%S'):
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
                    module_pattern=None, module_from_path=False, cancel_event=None):
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
        if module_from_path:
            module = _module_label(file_names[idx].split('/')[0])
        elif module_pattern:
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


def detect_tray_stats(rows, tray_id_pattern, unit_pattern=None, segments='id',
                      run_gap=300.0, cancel_event=None):
    """
    按 Tray ID 把日志行分段，统计：
    - units_per_tray：每盘颗数 = 完整段单位数的众数（去掉首尾可能不完整的段）
    - tray_seconds：单次换盘时间 = 旧盘最后一条 -> 新盘第一条 的间隔中位数
    - tray_count：换盘次数（段数-1）

    tray_id_pattern：从日志行中提取 Tray ID 的正则（须含一个捕获组）。
    unit_pattern：可选；提供时每条日志的单位数 = 该行匹配次数（如 carrier 消息里的 SiteId 数量），
                  否则每条日志按 1 颗计。
    segments：分段方式
      - 'id'（默认）：每个不同的 Tray ID 视为一盘（适合下料机 CubeTrayId，交叉出现也算同一盘），
        同一 Tray ID 两次出现间隔超过 run_gap 秒视为换了一盘（防止跨小时复用同号托盘被合并）；
        每盘颗数 = 每段出现条数之和的众数；
      - 'line'：每条匹配日志视为一盘（适合上料机 carrier 消息，一条消息=一次装盘），
        每盘颗数 = 每条日志单位数的众数。
    run_gap：仅 'id' 模式有效；同一 Tray ID 相邻两次出现超过该秒数时切为新的一段。
    无法识别时返回 None。
    """
    tray_re = re.compile(tray_id_pattern)
    unit_re = re.compile(unit_pattern) if unit_pattern else None
    segs = []  # (tray_id, first_ts, last_ts, units)
    if segments == 'line':
        # 每条匹配日志 = 一盘；同毫秒重复消息去重
        seen_keys = set()
        for mono, content in _iter_monotonic(rows, cancel_event):
            m = tray_re.search(content)
            if not m:
                continue
            units = len(unit_re.findall(content)) if unit_re else 1
            if unit_re and units == 0:
                continue  # 非装盘消息（如 DataReceived 重复行），不参与分段
            key = (round(mono, 1), m.group(1))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            segs.append((m.group(1), mono, mono, units))
    else:
        # 按 Tray ID 聚合：同一 ID 的所有日志行合并为一盘
        # 同一 Tray ID 相邻出现间隔超过 run_gap 视为新的一段（防止跨小时复用同号托盘合并）
        last_seen = {}
        run_idx = {}
        runs = {}
        order = []
        for mono, content in _iter_monotonic(rows, cancel_event):
            m = tray_re.search(content)
            if not m:
                continue
            tid = m.group(1)
            if tid in last_seen and mono - last_seen[tid] > run_gap:
                run_idx[tid] += 1
            elif tid not in run_idx:
                run_idx[tid] = 0
            key = (tid, run_idx[tid])
            if key not in runs:
                runs[key] = [mono, mono, 0]
                order.append(key)
            last_seen[tid] = mono
            rec = runs[key]
            rec[1] = mono
            rec[2] += len(unit_re.findall(content)) if unit_re else 1
        for key in order:
            first, last, units = runs[key]
            segs.append((key[0], first, last, units))

    if len(segs) < 2:
        return None
    counts = [s[3] for s in segs[1:-1]] or [s[3] for s in segs]
    if not counts:
        return None
    units_per_tray = Counter(counts).most_common(1)[0][0]
    gaps = sorted(b[1] - a[2] for a, b in zip(segs, segs[1:]) if b[1] - a[2] >= 0)
    if not gaps:
        return None
    tray_seconds = round(gaps[len(gaps) // 2], 3)
    return {
        'units_per_tray': int(units_per_tray),
        'tray_seconds': tray_seconds,
        'tray_count': len(segs) - 1,
        'segments': len(segs),
    }


def _iter_monotonic(rows, cancel_event=None):
    """按行序生成 (单调秒, 行内容)：纯时间日志（无日期）跨零点时自动累加一天，
    保证跨文件/跨日的时间比较与间隔计算正确；带日期的日志直接用真实时间戳。"""
    prev_sec = None
    offset = 0.0
    for row in rows:
        if cancel_event is not None and cancel_event.is_set():
            raise OperationCancelled()
        content = str(row.get('Content', ''))
        t = parse_ts(content)
        if t is None:
            continue
        if t.year == 1900:
            sec = t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6
            if prev_sec is not None and sec < prev_sec:
                offset += 86400.0
            prev_sec = sec
            mono = sec + offset
        else:
            mono = t.timestamp()
        yield mono, content


def measure_tray_change(rows, unload_keywords, load_keywords, max_gap=600.0, cancel_event=None):
    """
    SA 式换盘时间：同工位「卸载 -> 下一次装载」的间隔中位数。
    unload_keywords：卸载动作关键词（如“请求出托盘”“清除N号托盘所有格子状态”）；
    load_keywords：装载动作关键词（如“等待Carrier Ready”“轨道N进板成功”）。
    返回 {'tray_seconds': 中位间隔, 'tray_count': 配对数}；无法匹配时返回 None。
    """
    unload_kws = split_phrases(unload_keywords)
    load_kws = split_phrases(load_keywords)
    unloads = []
    loads = []
    for mono, content in _iter_monotonic(rows, cancel_event):
        if unload_kws and any(kw in content for kw in unload_kws):
            unloads.append(mono)
        if load_kws and any(kw in content for kw in load_kws):
            loads.append(mono)
    unloads.sort()
    loads.sort()
    if not unloads or not loads:
        return None
    # 每个卸载找其后最近的装载：二分查找，O(n log n)，避免双重循环
    durations = []
    for ut in unloads:
        i = bisect.bisect_right(loads, ut)
        if i < len(loads):
            d = loads[i] - ut
            if 0 < d < max_gap:
                durations.append(d)
    if not durations:
        return None
    durations.sort()
    return {
        'tray_seconds': round(durations[len(durations) // 2], 3),
        'tray_count': len(durations),
    }


def fmt_hms(seconds):
    """秒 → h:mm:ss(.mmm)，几百秒几千秒更直观。"""
    try:
        seconds = float(seconds)
    except (TypeError, ValueError):
        return ''
    if seconds < 0:
        return ''
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    ms = int(round((s - int(s)) * 1000))
    if ms >= 1000:
        ms = 0
        s += 1
    sec = int(s)
    if ms:
        return "%d:%02d:%02d.%03d" % (h, m, sec, ms)
    return "%d:%02d:%02d" % (h, m, sec)


def analyze_steps(rows, units, coefficient=1.5, min_step_median=0.01,
                  max_step_seconds=None, cancel_event=None):
    """
    单颗循环步骤深度分析：
    - units：每个单元配置 {name, module?, cycle, steps:[{name, start?, end?, timeout_seconds?}]}
      * start+end：步骤时长 = End − Start（事件对模式）
      * 仅 end：步骤时长 = 本步完成 − 上一步完成（顺序切分模式，首步用循环起点）
      * module：可选 {"from_path": 文件夹} 或 {"pattern": 正则}，过滤单元行
    - 每步统计时长分布，以中位数为基准；异常 = 时长 > 中位数×coefficient
      或（配置了 timeout_seconds 时）时长 > 中位数 + timeout_seconds。
    - 中位时长低于 min_step_median（默认 0.01 秒）的动作视为信号抖动，直接忽略。
    - 时长超过 max_step_seconds（默认 None=不剔除）视为超长停机，从步骤统计与异常中剔除。
    - 输出指标：循环数、中位时长、异常次数、异常影响时长（超额时长）、
      异常时间占比、异常频率（次/小时）。时间为 h:mm:ss 格式。
    """
    import statistics
    from collections import Counter
    rows_by_unit = {}
    for unit in units:
        module = unit.get('module') or {}
        if module.get('from_path'):
            prefix = module['from_path'].rstrip('/') + '/'
            u_rows = [r for r in rows if str(r.get('FileName', '')).startswith(prefix)]
        elif module.get('pattern'):
            pat = re.compile(module['pattern'])
            u_rows = [r for r in rows if pat.search(str(r.get('Content', '')))]
        else:
            u_rows = rows
        rows_by_unit[unit.get('name', '单元')] = (unit, u_rows)

    all_rows = []
    for unit_name, (unit, u_rows) in rows_by_unit.items():
        cycle_kws = split_phrases(unit.get('cycle', ''))
        if not cycle_kws:
            continue
        steps = unit.get('steps') or []
        if not steps:
            continue
        # 收集循环边界与各步骤事件（单调时间）
        cycle_ts = []
        step_events = {i: [] for i in range(len(steps))}
        step_end_events = {i: [] for i in range(len(steps))}
        for mono, content in _iter_monotonic(u_rows, cancel_event):
            if any(kw in content for kw in cycle_kws):
                cycle_ts.append(mono)
            for i, st in enumerate(steps):
                if st.get('start'):
                    if any(kw in content for kw in split_phrases(st['start'])):
                        step_events[i].append(mono)
                    if st.get('end') and any(kw in content for kw in split_phrases(st['end'])):
                        step_end_events[i].append(mono)
                elif st.get('end') and any(kw in content for kw in split_phrases(st['end'])):
                    step_events[i].append(mono)
        if not cycle_ts:
            continue
        cycle_ts.sort()
        # 每个循环内组装各步骤时长
        per_step = {i: [] for i in range(len(steps))}
        for ci in range(len(cycle_ts)):
            c_start = cycle_ts[ci]
            c_end = cycle_ts[ci + 1] if ci + 1 < len(cycle_ts) else float('inf')
            prev_ts = c_start
            for i, st in enumerate(steps):
                evs = [t for t in step_events[i] if c_start < t <= c_end]
                if not evs:
                    continue
                if st.get('start'):
                    # 事件对：取本循环内第一个 start 与其后第一个 end
                    start_ts = evs[0]
                    end_evs = [t for t in step_end_events[i] if t >= start_ts and t <= c_end]
                    end_ts = end_evs[0] if end_evs else None
                    if end_ts is None:
                        continue
                    dur = end_ts - start_ts
                    prev_ts = end_ts
                else:
                    dur = evs[0] - prev_ts
                    prev_ts = evs[0]
                if dur >= 0:
                    per_step[i].append(dur)
        # 统计
        total_sec = (cycle_ts[-1] - cycle_ts[0]) if len(cycle_ts) > 1 else 0.0
        for i, st in enumerate(steps):
            durs = per_step[i]
            if max_step_seconds is not None:
                durs = [d for d in durs if d <= max_step_seconds]
            if not durs:
                continue
            median = statistics.median(durs)
            if median < min_step_median:
                continue  # 低于 0.01 秒的动作忽略
            timeout = st.get('timeout_seconds')
            anomalies = [d for d in durs if d > median * coefficient or
                         (timeout is not None and d > median + float(timeout))]
            excess = sum(d - median for d in anomalies)
            total_dur = sum(durs)
            n = len(durs)
            freq = (len(anomalies) / total_sec * 3600.0) if total_sec > 0 else 0.0
            all_rows.append({
                '单元': unit_name,
                '步骤': st.get('name', '步骤%d' % (i + 1)),
                '循环数': n,
                '中位时长': fmt_hms(median),
                '平均时长': fmt_hms(statistics.mean(durs)),
                'P90时长': fmt_hms(sorted(durs)[int(n * 0.9) - 1] if n else ''),
                '最长时长': fmt_hms(max(durs)),
                '异常次数': len(anomalies),
                '异常影响时长': fmt_hms(excess),
                '异常时间占比(%)': round(excess / total_dur * 100, 2) if total_dur > 0 else '',
                '异常频率(次/小时)': round(freq, 2),
            })
    return pd.DataFrame(all_rows)


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


def summarize_alarms(rows, alarm_keywords, cancel_event=None, reason_map=None, module_from_path=False):
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
            if module_from_path:
                module = _module_label(file_names[idx].split('/')[0])
            else:
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
    summary = summary.rename(columns={'Module': '模块'})
    by_keyword = (
        detail_df.groupby('命中关键词', sort=False)
        .agg(报警次数=('Content', 'count'))
        .reset_index()
    )
    return summary, by_keyword, detail_df


_STATUS_RE = re.compile(r'status:(RU[A-F0-9]{3}|RUN|IDLE|DOWN|WARN)', re.IGNORECASE)
_REASON_RE = re.compile(r'ReasonID:([0-9A-Fa-f]+)')
_FNAME_DATE_RE = re.compile(r'(20\d{2})[-_]?(\d{2})[-_]?(\d{2})')


def _row_date(file_name):
    """从文件名提取日期（如 Logger 2026_08_05_00.txt / OHLog20260805000001.txt），
    用于给纯时间日志补日期，避免与带日期日志混排时时长失真。"""
    m = _FNAME_DATE_RE.search(str(file_name))
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
        except ValueError:
            return None
    return None


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
        fdate = _row_date(file_names[idx])
        if ts.year == 1900 and fdate is not None:
            ts = ts.replace(year=fdate.year, month=fdate.month, day=fdate.day)
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


_STOP_REASON_RE = re.compile(r'ErrorName = \[(.*?)\]|Err=(\d+):?([^,\n]*)')


def _classify_stop(reason, reason_map, reason_id=None):
    """按 EReason 清单匹配停机原因 → 状态（Error/Err 码→清单或 DOWN，异常中止→DOWN，操作员停止→IDLE）。"""
    code = None
    m = re.search(r'Error (\d+)', reason)
    if m:
        code = m.group(1)
    elif reason_id and str(reason_id).isdigit():
        code = str(reason_id)
    if code:
        info = reason_info(reason_map, code) if reason_map else None
        if info and info.get('state'):
            return info['state']
        return 'DOWN'
    if '异常' in reason or '中止' in reason:
        return 'DOWN'
    if '정지' in reason or 'stop' in reason.lower():
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
        fdate = _row_date(row.get('FileName', ''))
        if ts.year == 1900 and fdate is not None:
            ts = ts.replace(year=fdate.year, month=fdate.month, day=fdate.day)
        if is_stop:
            m = _STOP_REASON_RE.search(content)
            reason = ''
            reason_id = ''
            if m:
                if m.group(1):  # ErrorName = [Error NNN] ... 格式
                    reason = m.group(1)
                    code_m = re.search(r'Error (\d+)', reason)
                    reason_id = code_m.group(1) if code_m else reason
                elif m.group(2):  # Err=NNNN:Text 格式（ACF 主機）
                    reason_id = m.group(2)
                    reason = m.group(3) or reason_id
            events.append({
                'ts': ts, 'file': row.get('FileName', ''), 'kind': 'stop',
                'state': _classify_stop(reason or content, reason_map, reason_id),
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
    返回 (事件数, 每排事件数, 每排周期中位秒, 事件时间戳列表)。"""
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
        return 0, k, None, tlist
    if k == 'auto':
        return len(tlist), k, None, tlist
    intervals = [
        (tlist[i + k] - tlist[i]).total_seconds()
        for i in range(len(tlist) - k)
        if 0 < (tlist[i + k] - tlist[i]).total_seconds() < 3600
    ]
    return len(tlist), k, (statistics.median(intervals) if intervals else None), tlist


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
    count, _, _, tlist = _station_cycle(rows, "UDP Module - Good", 1, cancel_event)
    k = max(1, round(count / ref_rows)) if ref_rows else 1
    _, _, med, _ = _station_cycle(rows, "UDP Module - Good", k, cancel_event)
    return count, k, med, tlist


def analyze_bottleneck(rows, stations, units_per_row, tray_change=None, cancel_event=None):
    """
    自动判定瓶颈工位：每个工位按各自逻辑计算每排周期，取最长工位为瓶颈。
    tray_change: 可选 {'pattern': '...'}，将换 Tray 时间平摊到每排周期（进而平摊到单颗 CT）。
    返回 (工位明细DataFrame, 瓶颈信息dict)。
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
            ref_rows = max(
                (c // k for c, k, _, _ in collected.values() if isinstance(k, int) and k >= 1),
                default=0,
            )
            collected[name] = _station_inspect(rows, ref_rows, cancel_event)
        else:
            collected[name] = _station_cycle(rows, st.get('pattern', ''), st.get('events_per_row', 1),
                                             cancel_event)

    ref_rows = max(
        (c // k for c, k, _, _ in collected.values() if isinstance(k, int) and k >= 1),
        default=0,
    )
    # 换 Tray 开销：换盘时间 = 同工位 unloading → loading 之间的时长，再平摊到整盘排数
    tray_info = {'次数': 0, '单次换盘时间(秒)': 0.0, '每盘排数': '', '每排开销(秒)': 0.0}
    if tray_change and collected:
        bottleneck_name_ = max(collected, key=lambda n: collected[n][2] or 0)
        # 换盘测量参考工位：优先取配置（如装盘/点胶工位），否则用瓶颈工位流
        ref_name = tray_change.get('reference_station') or bottleneck_name_
        ref_ts = collected.get(ref_name, (0, 0, None, []))[3]
        if ref_ts:
            load_events = []    # (ts, 工位)
            unload_events = []  # (ts, 工位)
            load_kws = split_phrases(tray_change.get('pattern', ''))
            unload_kws = split_phrases(tray_change.get('unload_pattern', ''))
            for row in rows:
                if cancel_event is not None and cancel_event.is_set():
                    raise OperationCancelled()
                content = str(row.get('Content', ''))
                t = parse_ts(content)
                if t is None:
                    continue
                pos_m = re.search(r'SeqCycle(\d+)_', content)
                pos = pos_m.group(1) if pos_m else ''
                if load_kws and any(kw in content for kw in load_kws):
                    load_events.append((t, pos))
                if unload_kws and any(kw in content for kw in unload_kws):
                    unload_events.append((t, pos))
            load_events.sort()
            unload_events.sort()

            # 每盘排数：同工位相邻装盘之间的排数众数（一盘有几排，自动抓取）
            rows_per_tray = None
            if load_events:
                by_pos = {}
                for t, pos in load_events:
                    by_pos.setdefault(pos, []).append(t)
                row_counts = []
                for ts_list in by_pos.values():
                    for a, b in zip(ts_list, ts_list[1:]):
                        row_counts.append(sum(1 for x in ref_ts if a <= x < b))
                # 检测工位按排装盘会产生大量 0 排间隔，取非零间隔的众数作为每盘排数
                positive = [c for c in row_counts if c > 0]
                if positive:
                    rows_per_tray = Counter(positive).most_common(1)[0][0]

            # 换盘时间：同工位 unloading → 下一个 loading 的时长
            durations = []
            if unload_events and load_events:
                for ut, upos in unload_events:
                    for lt, lpos in load_events:
                        if lt > ut and lpos == upos:
                            d = (lt - ut).total_seconds()
                            if 0 < d < 600:
                                durations.append(d)
                            break
            if durations:
                net = statistics.median(durations)
                single = tray_change.get('single_tray_seconds')
                if single:
                    net = float(single)
                rows_per_tray = tray_change.get('rows_per_tray') or rows_per_tray
                if not rows_per_tray:
                    rows_per_tray = 16
                rows_per_tray = int(rows_per_tray)
                tray_info = {
                    '次数': len(durations),
                    '单次换盘时间(秒)': round(net, 3),
                    '每盘排数': rows_per_tray,
                    '每排开销(秒)': round(net / rows_per_tray, 4),
                }

    rows_list = []
    bottleneck_time = 0.0
    bottleneck_name = ''
    for name, (count, k, med, _tlist) in collected.items():
        if not count:
            rows_list.append({
                '工位': name, '事件数': 0, '每排事件数': k, '每排周期(秒)': '',
                '每排换盘开销(秒)': tray_info['每排开销(秒)'] or '', '有效周期(秒)': '',
                '极限UPH(个/小时)': '', '有效UPH(个/小时)': '', '瓶颈': '',
            })
            continue
        if k == 'auto':
            k = max(1, round(count / ref_rows)) if ref_rows else 1
        eff_med = (med + tray_info['每排开销(秒)']) if med else None
        uph = round(units_per_row * 3600.0 / eff_med, 2) if eff_med else ''
        if med is not None and med > bottleneck_time:
            bottleneck_time = med
            bottleneck_name = name
        rows_list.append({
            '工位': name,
            '事件数': count,
            '每排事件数': k,
            '每排周期(秒)': round(med, 3) if med else '',
            '每排换盘开销(秒)': round(tray_info['每排开销(秒)'], 3) if tray_info['每排开销(秒)'] else '',
            '有效周期(秒)': round(eff_med, 3) if eff_med else '',
            '极限UPH(个/小时)': uph,
            '有效UPH(个/小时)': uph if tray_info['每排开销(秒)'] else '',
            '瓶颈': '',
        })

    df = pd.DataFrame(rows_list)
    if bottleneck_time:
        df['瓶颈'] = df['每排周期(秒)'].apply(
            lambda v: '★' if isinstance(v, (int, float)) and abs(v - bottleneck_time) < 0.001 else ''
        )
    result = {
        '瓶颈工位': bottleneck_name,
        '瓶颈周期(秒)': round(bottleneck_time, 3) if bottleneck_time else None,
        '换盘次数': tray_info['次数'],
        '单次换盘时间(秒)': tray_info['单次换盘时间(秒)'],
        '每盘排数': tray_info['每盘排数'],
        '每排换盘开销(秒)': tray_info['每排开销(秒)'],
        '有效周期(秒)': round(bottleneck_time + tray_info['每排开销(秒)'], 3) if bottleneck_time else None,
    }
    return df, result
