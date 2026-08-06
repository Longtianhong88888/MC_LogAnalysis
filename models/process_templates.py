"""制程模板：按机台/制程预配置分析参数与日志文件筛选规则。

每个模板按功能（UPH分析/EFF分析/报警分析/机台状态分析）给出参数；
`file_filters` 指定该功能读取哪些日志文件（按相对路径模糊匹配，None 表示读取全部）。
"""

import json
import os

CUSTOM_TEMPLATE_NAME = "自定义"

_CUSTOM_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "custom_template.json"
)

DEFAULT_ALARM_KEYWORDS = "报警,ALARM,ERROR,NG,失败,异常,停止信号"

PROCESS_TEMPLATES = {
    "通用（手动配置）": {
        "description": "不套用模板，按界面当前参数分析全部日志文件",
        "file_filters": None,
        "UPH分析": {},
        "EFF分析": {},
        "报警分析": {},
        "机台状态分析": {},
    },
    CUSTOM_TEMPLATE_NAME: {
        "description": "用户自定义模板：可配置参数与日志文件筛选，点击“保存为自定义模板”持久化",
        "file_filters": None,
        "UPH分析": {},
        "EFF分析": {},
        "报警分析": {},
        "机台状态分析": {},
    },
    "LM 激光打标": {
        "description": "LM4405 激光打标机：MarkEnd1 完成动作，PS/EM 消息在同批当日日志中",
        "reason_list": "LM",
        "file_filters": None,
        "UPH分析": {
            "trigger_keywords": "MarkEnd1",
            "units_per_cycle": 1,
            "normal_threshold": 10.0,
            "planned_threshold": 900.0,
        },
        "EFF分析": {},
        "报警分析": {"alarm_keywords": DEFAULT_ALARM_KEYWORDS},
        "机台状态分析": {},
    },
    "CAW 组装": {
        "description": "CAW 组装机：PLC2 步数记录算周期，RAYPRUS 交互记录取状态与 EM 产量",
        "file_filters": ["记录PLC", "RAYPRUS", "Debug", "设备状态"],
        "UPH分析": {
            "trigger_keywords": "放熟料完成,放生料完成",
            "units_per_cycle": 1,
            "normal_threshold": 10.0,
            "planned_threshold": 900.0,
        },
        "EFF分析": {},
        "报警分析": {
            "alarm_keywords": DEFAULT_ALARM_KEYWORDS,
        },
        "机台状态分析": {},
    },
    "FR 机台": {
        "description": "FR 点胶机：轴点胶完成/有漏点产品为单件完成标记（漏点件以有漏点产品代替点胶完成），左轴/右轴分模组",
        "reason_list": "FR",
        "file_filters": None,
        "UPH分析": {
            "trigger_keywords": "轴点胶完成,有漏点产品",
            "module_pattern": "(左轴|右轴)",
            "pure_uph_factor": 0.5,
            "units_per_cycle": 1,
            "normal_threshold": 10.0,
            "planned_threshold": 900.0,
        },
        "EFF分析": {},
        "报警分析": {
            "alarm_keywords": "报警,ALARM,ERROR,NG,失败,异常,不达标,有漏点产品",
        },
        "机台状态分析": {},
    },
    "SA 机台": {
        "description": "SA 点胶组装机：LogData_*.txt 序列日志，UDP Module - Good 为单件完成标记（.log 为序列化转储，仅取 .txt）",
        "file_filters": [".txt"],
        "UPH分析": {
            "trigger_keywords": "UDP Module - Good",
            "units_per_cycle": 1,
            "normal_threshold": 10.0,
            "planned_threshold": 900.0,
        },
        "EFF分析": {},
        "报警分析": {
            "alarm_keywords": "Error,NG,Fail,报警,失败,异常,Warning",
        },
        "机台状态分析": {},
    },
}


def _custom_path(path=None):
    return path or _CUSTOM_PATH


def load_custom_template(path=None):
    """读取已保存的自定义模板；不存在或损坏时返回 None。"""
    p = _custom_path(path)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def save_custom_template(tpl, path=None):
    """保存自定义模板到本地 JSON，返回保存路径。"""
    p = _custom_path(path)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(tpl, f, ensure_ascii=False, indent=2)
    return p


def get_template(name, path=None):
    """按名称取模板；自定义模板优先读取已保存配置，未保存时返回空模板。"""
    if name == CUSTOM_TEMPLATE_NAME:
        custom = load_custom_template(path)
        if custom is not None:
            return custom
        return PROCESS_TEMPLATES[CUSTOM_TEMPLATE_NAME]
    return PROCESS_TEMPLATES.get(name) or PROCESS_TEMPLATES["通用（手动配置）"]


def template_file_filters(template, feature):
    """取某功能在模板下的日志文件筛选规则（功能级优先，其次模板级）。"""
    if not template:
        return None
    feature_tpl = template.get(feature) or {}
    if 'file_filters' in feature_tpl:
        return feature_tpl['file_filters']
    return template.get('file_filters')
