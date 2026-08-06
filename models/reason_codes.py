"""状态变更原因清单：ERRORNO → 中文名/停机类型映射。

清单文件位于外部目录（打包后为 exe 同目录的 EReasonList/，开发时为项目根目录），
含内部数据，不随包/仓库分发。
"""

import os

import pandas as pd

from utils.resource_utils import find_external_resource

_CACHE = {}


def load_reason_codes(device):
    """
    读取 {device}_EReasonList.xlsx，返回 {去零原因码: {'name','category','state'}}。
    文件缺失或解析失败时返回空 dict。
    """
    if device in _CACHE:
        return _CACHE[device]
    mapping = {}
    path = find_external_resource(os.path.join('EReasonList', f'{device}_EReasonList.xlsx'))
    if path:
        try:
            df = pd.read_excel(path)
            for _, r in df.iterrows():
                code = str(r.get('ERRORNO', '')).strip()
                key = code.lstrip('0') or '0'
                mapping[key] = {
                    'name': str(r.get('ATT1', '') or r.get('ERRORNAME', '')),
                    'category': str(r.get('ATT3', '')),
                    'state': str(r.get('ATT4', '')),
                }
        except Exception:
            mapping = {}
    _CACHE[device] = mapping
    return mapping


def reason_info(mapping, reason_id):
    key = str(reason_id).lstrip('0') or '0'
    return mapping.get(key)


def is_planned(mapping, reason_id):
    """Planned/Routine Downtime 归为计划停机 pDT。"""
    info = reason_info(mapping, reason_id)
    if not info:
        return False
    category = info['category']
    return 'Planned' in category or 'Routine' in category
