import queue
import re
import threading
import time
import traceback

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from models.exceptions import OperationCancelled
from models.log_model import LogModel
from models.process_templates import get_template, save_custom_template
from views.main_window import ONE_CLICK_FEATURE

# 一键分析（自动报告）只跑 4 项分析；文档合并与内容拆分保留为独立功能，
# 避免大日志（FR/ACF 400万+行）在合并步骤耗时拖慢整体运行
ONE_CLICK_FEATURES = ["UPH分析", "EFF分析", "报警分析", "机台状态分析"]

FEATURE_METHODS = {
    "文档合并与内容拆分": "process",
    "UPH分析": "analyze_uph",
    "EFF分析": "analyze_eff",
    "报警分析": "analyze_alarms",
    "机台状态分析": "analyze_status",
}


class LogController:
    def __init__(self, view):
        self.view = view
        self.source_dir = ""
        self.output_dir = ""
        self.worker = None
        self._progress_queue = queue.Queue()
        self._current_step = None
        self._step_started = 0.0
        self._last_notify = 0.0
        self._skip_event = threading.Event()

    def select_source_folder(self):
        dir_ = QFileDialog.getExistingDirectory(self.view, "选择源文件夹")
        if dir_:
            self.source_dir = dir_
            if hasattr(self.view, 'src_path_edit'):
                self.view.src_path_edit.setText(dir_)

    def select_output_folder(self):
        dir_ = QFileDialog.getExistingDirectory(self.view, "选择输出文件夹")
        if dir_:
            self.output_dir = dir_
            if hasattr(self.view, 'out_path_edit'):
                self.view.out_path_edit.setText(dir_)

    def browse_source(self):
        self.select_source_folder()

    def browse_output(self):
        self.select_output_folder()

    def run_parse(self):
        if not self.source_dir or not self.output_dir:
            QMessageBox.warning(self.view, "错误", "请先选择源文件夹和输出文件夹")
            return
        if self.worker is not None and self.worker.is_alive():
            QMessageBox.information(self.view, "提示", "正在解析中，请稍候")
            return

        if hasattr(self.view, 'show_progress'):
            self.view.show_progress(0)

        feature = self.view.feature_combo.currentText() if hasattr(self.view, 'feature_combo') else "文档合并与内容拆分"
        template = get_template(
            self.view.template_combo.currentText() if hasattr(self.view, 'template_combo') else "通用（手动配置）"
        )

        self._progress_queue = queue.Queue()
        self._skip_event = threading.Event()

        def worker():
            try:
                model = LogModel()
                if feature == ONE_CLICK_FEATURE:
                    results = []
                    succeeded_any = False
                    model = LogModel()
                    # 一次读取日志，供所有分析共享，避免重复加载大文件
                    self._progress_queue.put(('step', '读取日志文件'))
                    self._progress_queue.put(('partial', "正在读取日志文件 ..."))
                    first_params = self._collect_params(ONE_CLICK_FEATURES[0])
                    first_params.update(self._template_settings(template, ONE_CLICK_FEATURES[0]))
                    try:
                        rows = model.load_rows(
                            self.source_dir,
                            file_filters=first_params.get('file_filters'),
                            progress_callback=lambda value: self._progress_queue.put(('progress', value)),
                            cancel_event=self._skip_event,
                        )
                    except OperationCancelled:
                        self._progress_queue.put(('done', None, None))
                        return
                    for sub_feature in ONE_CLICK_FEATURES:
                        if self._skip_event.is_set():
                            self._skip_event.clear()
                            results.append(f"{sub_feature}：已跳过（用户操作）")
                            self._progress_queue.put(('partial', f"{sub_feature}已跳过（用户操作）"))
                            continue
                        self._progress_queue.put(('step', sub_feature))
                        self._progress_queue.put(('partial', f"正在处理：{sub_feature} ..."))
                        try:
                            method_name = FEATURE_METHODS[sub_feature]
                            params = self._collect_params(sub_feature)
                            params.update(self._template_settings(template, sub_feature))
                            params['rows'] = rows
                            params['cancel_event'] = self._skip_event
                            params.pop('file_filters', None)
                            result = getattr(model, method_name)(
                                source_dir=self.source_dir,
                                output_dir=self.output_dir,
                                progress_callback=lambda value: self._progress_queue.put(('progress', value)),
                                **params,
                            )
                            succeeded_any = True
                            results.append(f"{sub_feature}：{result}")
                            self._progress_queue.put(('partial', f"{sub_feature}：{result}"))
                        except OperationCancelled:
                            self._skip_event.clear()
                            results.append(f"{sub_feature}：已跳过（用户操作）")
                            self._progress_queue.put(('partial', f"{sub_feature}已跳过（用户操作）"))
                        except Exception as exc:
                            traceback.print_exc()
                            results.append(f"{sub_feature}失败：{exc}")
                            self._progress_queue.put(('partial', f"{sub_feature}失败：{exc}"))
                    del rows
                    if succeeded_any:
                        try:
                            self._progress_queue.put(('step', 'PPT 报告'))
                            self._progress_queue.put(('partial', "正在生成 PPT 报告 ..."))
                            from models.report import build_ppt_report
                            process_name = (
                                self.view.template_combo.currentText()
                                if hasattr(self.view, 'template_combo') else None
                            )
                            ppt_path = build_ppt_report(self.output_dir, process_name=process_name)
                            results.append(f"PPT报告：{ppt_path}")
                            self._progress_queue.put(('partial', f"PPT报告：{ppt_path}"))
                        except Exception as exc:
                            traceback.print_exc()
                            results.append(f"PPT报告生成失败：{exc}")
                            self._progress_queue.put(('partial', f"PPT报告生成失败：{exc}"))
                    else:
                        results.append("PPT报告：已跳过（无分析结果）")
                        self._progress_queue.put(('partial', "PPT报告已跳过（无分析结果）"))
                    result = results
                else:
                    method_name = FEATURE_METHODS.get(feature, "process")
                    params = self._collect_params(feature)
                    params.update(self._template_settings(template, feature))
                    self._progress_queue.put(('step', feature))
                    result = getattr(model, method_name)(
                        source_dir=self.source_dir,
                        output_dir=self.output_dir,
                        progress_callback=lambda value: self._progress_queue.put(('progress', value)),
                        **params,
                    )
                self._progress_queue.put(('done', result, None))
            except OperationCancelled:
                self._progress_queue.put(('done', None, None))
            except Exception as exc:
                traceback.print_exc()
                self._progress_queue.put(('done', None, exc))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()
        self._current_step = None
        self._step_started = time.monotonic()
        self._last_notify = 0.0
        if hasattr(self.view, 'after'):
            self.view.after(3000, self._watchdog)
        self._poll_worker()

    def _collect_params(self, feature):
        view = self.view
        if feature == "UPH分析":
            return {
                "trigger_keywords": view.uph_trigger_edit.text().strip() or "MarkEnd1",
                "units_per_cycle": int(view.uph_units_spin.value()),
                "normal_threshold": float(view.uph_normal_spin.value()),
                "planned_threshold": float(view.uph_planned_spin.value()),
                "ideal_ct": self._to_float(view.uph_ideal_ct_edit.text()),
                "max_ct": self._to_float(view.uph_max_ct_edit.text()),
                "step_coefficient": float(getattr(view, 'uph_step_coef_spin', None).value())
                if hasattr(view, 'uph_step_coef_spin') else 1.5,
            }
        if feature == "EFF分析":
            return {
                "planned_hours": self._to_float(view.eff_planned_hours_edit.text()),
                "pdt_reason_ids": view.eff_pdt_reason_edit.text().strip() or None,
            }
        if feature == "报警分析":
            return {
                "alarm_keywords": view.alarm_keywords_edit.text().strip()
                or "报警,ALARM,ERROR,NG,失败,异常,停止信号",
            }
        if feature == "机台状态分析":
            return {}
        keywords = view.keyword_edit.text().strip() if hasattr(view, 'keyword_edit') else None
        separator = view.separator_edit.text().strip() if hasattr(view, 'separator_edit') else None
        return {"keywords": keywords or None, "separator": separator or None}

    def _template_settings(self, template, feature):
        """取当前模板下某功能的非界面参数（文件筛选、模组提取等）；日志文件筛选框对所有制程生效且可手动修改。"""
        text = self.view.custom_filter_edit.text().strip()
        filters = [k for k in re.split(r'[,，、;；\s]+', text) if k] if text else None
        settings = {}
        if filters:
            settings["file_filters"] = filters
        feature_tpl = template.get(feature) or {}
        if feature_tpl.get("module_pattern"):
            settings["module_pattern"] = feature_tpl["module_pattern"]
        if feature_tpl.get("pure_uph_factor") is not None:
            settings["pure_uph_factor"] = float(feature_tpl["pure_uph_factor"])
        if feature == "文档合并与内容拆分" and template.get("merge_groups"):
            settings["merge_groups"] = template["merge_groups"]
        if feature == "文档合并与内容拆分":
            alarm = template.get("报警分析") or {}
            base = alarm.get("alarm_keywords") or "报警,ALARM,ERROR,NG,失败,异常,停止信号"
            down_markers = "AutoRun Stop,ErrOn,Err=,生产流程出现异常,当前设备状态Maunal,status:DOWN,MachineState:[Down],机械手不安全,换盘提示,超时"
            # 剔除 "NG"：机台产品码/序列号常含 NG（如 RDA620700NG55423C），会误标正常行
            kws = [k for k in re.split(r'[,，、;；\s]+', base + "," + down_markers) if k and k != 'NG']
            settings["abnormal_keywords"] = ",".join(kws)
            # UPH 步骤超时异常行标红：复用模板的步骤分析配置
            uph = template.get("UPH分析") or {}
            sa = uph.get("step_analysis") or {}
            if sa.get("units"):
                settings["step_units"] = sa["units"]
            if sa.get("mode"):
                settings["step_mode"] = sa["mode"]
            if sa.get("coefficient") is not None:
                settings["step_coefficient"] = float(sa["coefficient"])
            if sa.get("max_step_seconds") is not None:
                settings["step_max_seconds"] = float(sa["max_step_seconds"])
        if feature == "UPH分析":
            if feature_tpl.get("bottleneck_stations"):
                settings["bottleneck_stations"] = feature_tpl["bottleneck_stations"]
            if feature_tpl.get("bottleneck_machines"):
                settings["bottleneck_machines"] = feature_tpl["bottleneck_machines"]
            if feature_tpl.get("bottleneck_units_per_row") is not None:
                settings["bottleneck_units_per_row"] = int(feature_tpl["bottleneck_units_per_row"])
            if feature_tpl.get("tray_change"):
                settings["tray_change"] = feature_tpl["tray_change"]
            if feature_tpl.get("parts"):
                settings["parts"] = feature_tpl["parts"]
            if feature_tpl.get("step_analysis"):
                settings["step_units"] = feature_tpl["step_analysis"].get("units")
                if feature_tpl["step_analysis"].get("mode"):
                    settings["step_mode"] = feature_tpl["step_analysis"]["mode"]
                if feature_tpl["step_analysis"].get("coefficient") is not None:
                    settings["step_coefficient"] = float(feature_tpl["step_analysis"]["coefficient"])
                if feature_tpl["step_analysis"].get("max_step_seconds") is not None:
                    settings["step_max_seconds"] = float(feature_tpl["step_analysis"]["max_step_seconds"])
            if feature_tpl.get("module_from_path"):
                settings["module_from_path"] = True
        if feature == "报警分析" and feature_tpl.get("module_from_path"):
            settings["module_from_path"] = True
        if feature in ("EFF分析", "报警分析", "机台状态分析"):
            combo = getattr(self.view, 'reason_combo', None)
            if combo is not None:
                if combo.currentText() != '（无）':
                    settings["reason_device"] = combo.currentText()
            elif template.get("reason_list"):
                settings["reason_device"] = template["reason_list"]
        if feature in ("EFF分析", "机台状态分析"):
            if feature_tpl.get("activity_keywords"):
                settings["activity_keywords"] = feature_tpl["activity_keywords"]
            if feature_tpl.get("stop_reason_keywords"):
                settings["stop_reason_keywords"] = feature_tpl["stop_reason_keywords"]
        return settings

    def save_custom_template(self):
        text = self.view.custom_filter_edit.text().strip()
        filters = [k for k in re.split(r'[,，、;；\s]+', text) if k] if text else None
        tpl = {
            "description": "用户自定义模板",
            "file_filters": filters,
            "UPH分析": self._collect_params("UPH分析"),
            "EFF分析": self._collect_params("EFF分析"),
            "报警分析": self._collect_params("报警分析"),
            "机台状态分析": {},
        }
        path = save_custom_template(tpl)
        QMessageBox.information(self.view, "已保存", f"自定义模板已保存：\n{path}")

    @staticmethod
    def _to_float(text):
        try:
            return float(str(text).strip())
        except (TypeError, ValueError):
            return None

    def _poll_worker(self):
        after = getattr(self.view, 'after', None)
        try:
            while True:
                kind, *payload = self._progress_queue.get_nowait()
                if kind == 'progress':
                    if hasattr(self.view, 'update_progress'):
                        self.view.update_progress(payload[0])
                elif kind == 'step':
                    self._current_step = payload[0]
                    self._step_started = time.monotonic()
                    self._last_notify = 0.0
                    if hasattr(self.view, 'update_status'):
                        self.view.update_status(f"正在处理：{payload[0]} ...")
                elif kind == 'partial':
                    if hasattr(self.view, 'update_result'):
                        self.view.update_result(payload[0])
                elif kind == 'done':
                    result, error = payload
                    self.worker = None
                    if hasattr(self.view, 'hide_progress'):
                        self.view.hide_progress()
                    if error is not None:
                        if hasattr(self.view, 'update_result'):
                            self.view.update_result(f"处理失败：{error}")
                    elif result is None:
                        if hasattr(self.view, 'update_result'):
                            self.view.update_result("已取消：日志读取被跳过")
                    else:
                        if isinstance(result, list):
                            detail = "\n".join(result)
                            if hasattr(self.view, 'update_result'):
                                self.view.update_result(f"成功导出：\n{detail}")
                        else:
                            if hasattr(self.view, 'update_result'):
                                self.view.update_result(f"成功导出：{result}")
                    if hasattr(self.view, 'update_status'):
                        self.view.update_status("就绪")
                    return
        except queue.Empty:
            pass
        if after is not None:
            after(100, self._poll_worker)

    def _watchdog(self):
        """卡顿检测：步骤运行超过 15 秒后，每 10 秒在状态栏提示已运行时长。"""
        if self.worker is None or not self.worker.is_alive():
            return
        if self._current_step:
            elapsed = time.monotonic() - self._step_started
            if elapsed >= 15 and elapsed - self._last_notify >= 10:
                self._last_notify = elapsed
                if hasattr(self.view, 'update_status'):
                    self.view.update_status(
                        f"正在处理：{self._current_step}（已运行 {int(elapsed)} 秒）..."
                    )
        if hasattr(self.view, 'after'):
            self.view.after(3000, self._watchdog)

    def request_skip(self):
        """用户点击“跳转至下一步”：中断当前步骤，继续后续分析。"""
        if self.worker is None or not self.worker.is_alive():
            if hasattr(self.view, 'update_status'):
                self.view.update_status("当前没有运行中的分析")
            return
        self._skip_event.set()
        if hasattr(self.view, 'update_status'):
            self.view.update_status("已请求跳过当前步骤，正在中断...")
        if hasattr(self.view, 'update_result'):
            self.view.update_result("已请求跳过当前步骤 ...")

    def clear_results(self):
        if hasattr(self.view, 'result_text'):
            self.view.result_text.clear()
