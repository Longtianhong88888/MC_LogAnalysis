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
            # 换盘时间（整盘打标结束 下料->新盘上料）平摊到整盘产品：
            # 每盘颗数 = CCD 批次间 MarkEnd1 数（每批6颗） × 换盘间 CCD 批次数（每盘4批）
            "tray_change": {
                "unload": "Move to unload",
                "load": "收到上料完成信号",
                "batch": "Start parsing CCD data",
                "unit": "MarkEnd1",
                "tray": "Move to unload",
            },
            "step_analysis": {
                "coefficient": 1.5,
                "units": [{
                    "name": "整机",
                    "cycle": "MarkEnd1",
                    "steps": [
                        # 单颗循环（MarkEnd1→MarkEnd1），按轴/平台运动节拍拆分，段和=CT：
                        #  打标前间隔（B 模式顺序切分）= 上一颗完成到下一颗开始；
                        #  Z轴焦距定位（A 模式）= MarkStart1 → MarkStart1_0；
                        #  激光打标（A 模式）= MarkStart1_0 → MarkEnd1_0（振镜扫描）。
                        {"name": "打标前间隔", "end": "MarkStart1"},
                        {"name": "Z轴焦距定位", "start": "MarkStart1", "end": "MarkStart1_0",
                         "timeout_seconds": 0.1},
                        {"name": "激光打标(振镜扫描)", "start": "MarkStart1_0", "end": "MarkEnd1_0",
                         "timeout_seconds": 1.0},
                        # 批次级动作（每批约 6 颗、每盘 4 批），standalone 独立计时，
                        # 不参与单颗循环链式切分（避免此前 CCD 被算成 1.8s 伪段）。
                        {"name": "读码GetSN(每批)", "start": "GetSN_Start", "end": "GetSN_End",
                         "standalone": True, "timeout_seconds": 0.5},
                        {"name": "CCD轴移动定位(每批)", "start": "Move CcdPos finish",
                         "end": "CCD定位完成", "standalone": True, "timeout_seconds": 1.0},
                        # 平台级动作（每盘约 24 颗），standalone 独立计时。
                        {"name": "平台下料(每盘)", "start": "发送下料请求信号",
                         "end": "收到下料完成信号", "standalone": True, "timeout_seconds": 5.0},
                        {"name": "平台上料(每盘)", "start": "发送上料请求信号",
                         "end": "收到上料完成信号", "standalone": True, "timeout_seconds": 5.0},
                    ],
                }],
            },
        },
        "EFF分析": {},
        "报警分析": {"alarm_keywords": DEFAULT_ALARM_KEYWORDS},
        "机台状态分析": {},
    },
    "CAW 组装": {
        "description": "CAW 组装机：PLC2 上料机 + PLC1 焊接机（左右工作区并行）；UPH 按双机台瓶颈判定（焊接机为瓶颈，整机≈1250/hr）；合并分析按 PLC1/PLC2 分组导出",
        "file_filters": ["记录PLC", "RAYPRUS", "Debug", "设备状态"],
        "merge_groups": [
            {"name": "PLC1焊接机", "file": "记录PLC1"},
            {"name": "PLC2上料机", "file": "记录PLC2"},
        ],
        "UPH分析": {
            "bottleneck_machines": [
                # 上料机：每次给 1 个滑台换料 = 2 颗（与焊接机每滑台周期需求对齐，不是 4 颗）
                {"name": "上料机", "module": {"file": "记录PLC2"},
                 "trigger": "放熟料完成", "units_per_cycle": 2,
                 "parallel_units": 2,
                 "normal_threshold": 15.0,
                 "unit_pattern": "取料[12]"},
                {"name": "焊接机", "module": {"file": "记录PLC1"},
                 "trigger": "去交换位", "units_per_cycle": 2,
                 "parallel_units": 4,  # 左右2侧 × 每侧2滑台 = 4 条并行链；每滑台左右2工位各1颗=2颗/周期
                 "normal_threshold": 30.0,
                 "unit_pattern": "滑台([1-4](?:左|右))"},
            ],
            "step_analysis": {
                "coefficient": 1.5,
                "units": [
                    # 上料机（PLC2）：左右取料轴；每轴 2 生料吸嘴 + 2 熟料吸嘴
                    {"name": "上料机-取料1", "module": {"pattern": "取料1"}, "cycle": "放熟料完成",
                     "steps": [
                         {"name": "取生料", "end": "双取生料完成"},
                         {"name": "扫码", "end": "扫码完成"},
                         {"name": "取熟料", "end": "取熟料完成"},
                         {"name": "放生料", "end": "放生料完成"},
                         {"name": "放熟料", "end": "放熟料完成"},
                     ]},
                    {"name": "上料机-取料2", "module": {"pattern": "取料2"}, "cycle": "放熟料完成",
                     "steps": [
                         {"name": "取生料", "end": "双取生料完成"},
                         {"name": "扫码", "end": "扫码完成"},
                         {"name": "取熟料", "end": "取熟料完成"},
                         {"name": "放生料", "end": "放生料完成"},
                         {"name": "放熟料", "end": "放熟料完成"},
                     ]},
                ] + [
                    # 焊接机（PLC1）：支架流程 = chassis（每滑台一个，不带左/右）
                    {"name": "焊接机-滑台%d支架" % s,
                     "module": {"pattern": "滑台%dclassis" % s},
                     "cycle": "classis中轉軸去焊接位",
                     "steps": [
                         {"name": "支架请求上生料", "end": "classis平台请求上生料"},
                         {"name": "支架中转去上料位", "end": "classis中轉軸去上料位"},
                         {"name": "支架装载完成", "end": "classis平台上生料完成"},
                         {"name": "支架中转去焊接位", "end": "classis中轉軸去焊接位"},
                     ]}
                    for s in range(1, 5)
                ] + [
                    # 焊接机（PLC1）：焊接流程 = 2 焊接头 4 工站 8 工位（滑台1-4 × 左/右）
                    {"name": "焊接机-滑台%d%s" % (s, side),
                     "module": {"pattern": "滑台%d%s" % (s, side)},
                     "cycle": "去交换位",
                     "steps": [
                         {"name": "下熟料", "end": "纠偏平台下熟料完成"},
                         {"name": "上生料", "end": "纠偏平台上生料完成"},
                         {"name": "PR1纠偏", "end": "平台PR1"},
                         {"name": "纠偏", "end": "平台糾偏", "timeout_seconds": 0.5},
                         {"name": "贴合", "end": "平台贴合", "timeout_seconds": 0.5},
                         {"name": "判定PR3", "end": "平台PR3"},
                         {"name": "焊接", "end": "平台焊接", "timeout_seconds": 1.0},
                         {"name": "检查PR6", "end": "平台PR6"},
                         {"name": "压合回零", "end": "压合回零", "timeout_seconds": 1.0},
                         {"name": "交换", "end": "去交换位", "timeout_seconds": 0.5},
                     ]}
                    for s in range(1, 5) for side in ("左", "右")
                ],
            },
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
            "step_analysis": {
                "coefficient": 1.5,
                "units": [
                    {"name": "左轴", "module": {"pattern": "左轴"}, "cycle": "轴点胶完成",
                     "steps": [{"name": "点胶", "start": "左轴开始点胶", "end": "左轴点胶完成"}]},
                    {"name": "右轴", "module": {"pattern": "右轴"}, "cycle": "轴点胶完成",
                     "steps": [{"name": "点胶", "start": "右轴开始点胶", "end": "右轴点胶完成"}]},
                ],
            },
        },
        "EFF分析": {},
        "报警分析": {
            "alarm_keywords": "报警,ALARM,ERROR,NG,失败,异常,不达标,有漏点产品",
        },
        "机台状态分析": {},
    },
    "SA 机台": {
        "description": "SA 四工位机（点胶/贴附/热压/检测）：自动判定各工位每排周期，取最长工位为瓶颈计算 UPH；每排产品数可调（当前 2）",
        "reason_list": "SA",
        "file_filters": [".txt"],
        "EFF分析": {
            "activity_keywords": "UDP Module - Good",
            "stop_reason_keywords": "AutoRun Stop - ErrorName",
        },
        "UPH分析": {
            "trigger_keywords": "Heater 0 :Heating Complete",
            "units_per_cycle": 2,
            "normal_threshold": 15.0,
            "planned_threshold": 900.0,
            "bottleneck_stations": [
                {"name": "点胶", "function": "sa_dispense"},
                {"name": "贴附", "function": "sa_attach"},
                {"name": "热压", "function": "sa_heatpress"},
                {"name": "检测", "function": "sa_inspect"},
            ],
            "bottleneck_units_per_row": 2,
            "step_analysis": {
                "mode": "sa",
                "coefficient": 1.5,
            },
            "tray_change": {
                "pattern": "JigLoadingCycle",
                "unload_pattern": "JigUnloadingCycle",
                "reference_station": "点胶",
            },
        },
        "报警分析": {
            "alarm_keywords": "Error,NG,Fail,报警,失败,异常,Warning",
        },
        "机台状态分析": {
            "activity_keywords": "UDP Module - Good",
            "stop_reason_keywords": "AutoRun Stop - ErrorName",
        },
    },
    "ACF 三機": {
        "description": "ACF 由上料機/主機/下料機三部分（分文件夹）构成，按部分分开统计；每盘颗数按 Tray ID 动态统计（上料机 carrierId=8颗/盘、下料机 CubeTrayId=24颗/盘），换盘时间按 SA 式卸载→装载间隔（上料机 请求出托盘→等待Carrier Ready，下料机 清除2号托盘→轨道2进板成功）；主机一批=一个 carrier=8颗（Cavity cnt:1）",
        "reason_list": "ACF",
        "file_filters": [".txt"],
        "UPH分析": {
            "parts": [
                {"name": "上料機", "trigger": "更新Carrier盘", "units_per_cycle": 8,
                 "normal_threshold": 35.0,
                 "tray_detect": {
                     "segments": "line",
                     "tray_id": r"更新Carrier盘:.*?carrierId:([A-Z0-9\-]+)",
                     "unit": r"SiteId",
                 },
                 "tray_change": {"unload": "请求出托盘", "load": "等待Carrier Ready"}},
                {"name": "主機", "trigger": "Cavity cnt:1", "units_per_cycle": 8,
                 "normal_threshold": 35.0},
                {"name": "下料機", "trigger": "UnloadDuts Finish",
                 "units_per_cycle": 3, "normal_threshold": 15.0,
                 "tray_detect": {
                     "tray_id": r"CubeTrayId:([A-Z0-9\-]+)",
                 },
                 "tray_change": {"unload": "清除2号托盘所有格子状态", "load": "轨道2进板成功"}},
            ],
            "module_from_path": True,
            "units_per_cycle": 1,
            "normal_threshold": 10.0,
            "planned_threshold": 900.0,
            "step_analysis": {
                "coefficient": 1.5,
                "units": [
                    {"name": "上料機", "module": {"from_path": "上料機"}, "cycle": "更新Carrier盘",
                     "steps": [
                         {"name": "取料", "end": "托盘取料后二维码"},
                         {"name": "放料装盘", "end": "放料成功"},
                     ]},
                    {"name": "主機", "module": {"from_path": "主機"}, "cycle": "Cavity cnt:1",
                     "steps": [
                         {"name": "压合出料", "end": "ProdCountCarrier"},
                     ]},
                    {"name": "下料機", "module": {"from_path": "下料機"}, "cycle": "UnloadDuts Finish",
                     "steps": [
                         {"name": "上料取件", "end": "托盘取料后二维码"},
                         {"name": "测试完成", "end": "Test1Cycle Finish"},
                         {"name": "下料取件", "end": "SetStateAfterPickFromSocket"},
                     ]},
                ],
            },
        },
        "EFF分析": {
            "activity_keywords": "更新Carrier盘,Cavity cnt:1,UnloadDuts Finish",
            "stop_reason_keywords": "ErrOn,生产流程出现异常,当前设备状态Maunal",
        },
        "报警分析": {
            "alarm_keywords": "ErrOn,Err=,机械手不安全,生产流程出现异常,已添加了具有相同键的项,索引超出了数组界限,换盘提示,报警操作",
            "module_from_path": True,
        },
        "机台状态分析": {
            "activity_keywords": "更新Carrier盘,Cavity cnt:1,UnloadDuts Finish",
            "stop_reason_keywords": "ErrOn,生产流程出现异常,当前设备状态Maunal",
        },
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
