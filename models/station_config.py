"""设备效能站位配置：用户可维护站位列表（本地 JSON 持久化）。"""

import json
import os

DEFAULT_STATIONS = ["LM", "SA", "ACF", "FR", "CAW"]

_STATION_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "station_list.json"
)

_MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "web_report_memory.json"
)


def load_stations(path=None):
    """读取站位列表；文件缺失/损坏时返回默认站位。"""
    path = path or _STATION_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            stations = [str(s).strip() for s in data if str(s).strip()]
            return stations or list(DEFAULT_STATIONS)
    except (OSError, ValueError):
        pass
    return list(DEFAULT_STATIONS)


def save_stations(stations, path=None):
    """保存站位列表到本地 JSON。"""
    path = path or _STATION_PATH
    clean = [str(s).strip() for s in stations if str(s).strip()]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    return path


def filter_machines_by_station(machines, station):
    """从 CMS 机台清单中按站位（machine 字段，不区分大小写）过滤机台号并排序。"""
    if not station:
        return []
    kw = station.strip().upper()
    return sorted({
        (m.get("machineNo") or "").strip()
        for m in machines or []
        if (m.get("machine") or m.get("machineType") or "").strip().upper() == kw
        and (m.get("machineNo") or "").strip()
    })


def load_web_report_memory(path=None):
    """读取上一次关闭软件时的设备效能选择方案；无记录/损坏时返回空 dict。"""
    path = path or _MEMORY_PATH
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_web_report_memory(data, path=None):
    """保存设备效能选择方案（站位/机台号/时间等），供下次启动恢复。"""
    path = path or _MEMORY_PATH
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path
