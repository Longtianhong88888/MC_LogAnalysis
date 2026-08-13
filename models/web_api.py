"""戰情中心（CMS）联网数据接口。

数据源：http://10.147.214.130:8093/#/main/cma/deviceeff 页面背后的 FS 后端。
前端请求带 isFs 标记后切换到 VUE_APP_FS_API（http://10.151.128.35:8098），
默认基址 10.151.129.104:8080 对这批接口返回 404，不要混用。

接口（均无需登录即可调用）：
- api/MESBaseSFC/Load_Machine              机台清单
- api/EquipmentEfficiency/GetMachineEff    逐机台 EFF/UPH 汇总
- api/Mahcine/LoadRunLog                   机台状态日志（RUN/IDLE/DOWN 状态段）

返回统一包裹 {"status":..., "resultvalue":[...]}。
"""

import json
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "http://10.151.128.35:8098"
DEFAULT_PLANT_ID = "8S01"
REQUEST_TIMEOUT = 30


class WebApiError(Exception):
    """联网接口调用失败。"""


class WebNoDataError(WebApiError):
    """所选机台在时间范围内没有数据（未上传/无产出）。"""


def _request(base_url, path, params=None, method="POST", timeout=REQUEST_TIMEOUT):
    url = base_url.rstrip("/") + "/" + path.lstrip("/")
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method, data=b"{}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept-Language", "zh-TW")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # 网络/超时/HTTP 错误统一转业务异常
        raise WebApiError(f"接口请求失败：{url}（{exc}）") from exc
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise WebApiError(f"接口返回非 JSON：{url}") from exc
    if data.get("status") is False or data.get("Status") is False:
        raise WebApiError(
            f"接口返回错误：{data.get('message') or data.get('Message') or url}"
        )
    value = data.get("resultvalue")
    if value is None:
        value = data.get("OtherValue")
    return value if value is not None else []


def fetch_machines(base_url=DEFAULT_BASE_URL, plant_id=DEFAULT_PLANT_ID,
                   timeout=REQUEST_TIMEOUT):
    """机台清单。"""
    return _request(base_url, "api/MESBaseSFC/Load_Machine",
                    params={"PlantID": plant_id}, method="GET", timeout=timeout)


def fetch_machine_eff(base_url, plant_id, machine_type="", machine_no="", device_no="",
                      floor="", begin_time="", end_time="", order_by=1, timeout=60):
    """逐机台 EFF/UPH 汇总（机台类型与机台号至少填一项，否则接口返回空）。"""
    params = {
        "DeviceNO": device_no,
        "MachineType": machine_type,
        "MachineNO": machine_no,
        "Floor": floor,
        "EndTime": end_time,
        "BeginTime": begin_time,
        "IsInLine": "0",
        "InLineType": "",
        "InLineName": "",
        "PlantID": plant_id,
        "OrderBy": str(order_by),
    }
    return _request(base_url, "api/EquipmentEfficiency/GetMachineEff",
                    params=params, timeout=timeout)


def fetch_run_log(base_url, plant_id, machine_no, machine_type="", st="", et="",
                  head="", status_merge_flg=1, timeout=90):
    """机台状态日志。status_merge_flg=1 返回状态段（真实+补录），=0 返回小时粒度。"""
    params = {
        "MachineNO": machine_no,
        "St": st,
        "Et": et,
        "PlantID": plant_id,
        "MachineType": machine_type,
        "Head": head,
        "status_merge_flg": str(status_merge_flg),
    }
    return _request(base_url, "api/Mahcine/LoadRunLog",
                    params=params, timeout=timeout)


def fetch_machine_output_board(base_url, plant_id, machine_type, st, et, timeout=90):
    """机台产出看板：逐机台窗口 投入/产出/目标/达成率/直通率/状态。"""
    params = {
        "plant_id": plant_id,
        "machine_type": machine_type,
        "St": st,
        "Et": et,
    }
    return _request(base_url, "api/Mahcine/GetMachineOutputBoard",
                    params=params, timeout=timeout)
