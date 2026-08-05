import queue
import re
import threading
import traceback

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from models.log_model import LogModel
from models.process_templates import CUSTOM_TEMPLATE_NAME, get_template, save_custom_template, template_file_filters
from views.main_window import ONE_CLICK_FEATURE

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

        def worker():
            try:
                model = LogModel()
                if feature == ONE_CLICK_FEATURE:
                    results = []
                    for sub_feature in ONE_CLICK_FEATURES:
                        method_name = FEATURE_METHODS[sub_feature]
                        params = self._collect_params(sub_feature)
                        params.update(self._template_filters(template, sub_feature))
                        result = getattr(model, method_name)(
                            source_dir=self.source_dir,
                            output_dir=self.output_dir,
                            progress_callback=lambda value: self._progress_queue.put(('progress', value)),
                            **params,
                        )
                        results.append(f"{sub_feature}：{result}")
                    try:
                        from models.report import build_ppt_report
                        ppt_path = build_ppt_report(self.output_dir)
                        results.append(f"PPT报告：{ppt_path}")
                    except Exception as exc:
                        traceback.print_exc()
                        results.append(f"PPT报告生成失败：{exc}")
                    result = results
                else:
                    method_name = FEATURE_METHODS.get(feature, "process")
                    params = self._collect_params(feature)
                    params.update(self._template_filters(template, feature))
                    result = getattr(model, method_name)(
                        source_dir=self.source_dir,
                        output_dir=self.output_dir,
                        progress_callback=lambda value: self._progress_queue.put(('progress', value)),
                        **params,
                    )
                self._progress_queue.put(('done', result, None))
            except Exception as exc:
                traceback.print_exc()
                self._progress_queue.put(('done', None, exc))

        self.worker = threading.Thread(target=worker, daemon=True)
        self.worker.start()
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

    def _template_filters(self, template, feature):
        """取当前模板下某功能的日志文件筛选；自定义模板优先使用界面输入的筛选关键词。"""
        if hasattr(self.view, 'template_combo') and self.view.template_combo.currentText() == CUSTOM_TEMPLATE_NAME:
            text = self.view.custom_filter_edit.text().strip()
            filters = [k for k in re.split(r'[,，、;；\s]+', text) if k] if text else None
        else:
            filters = template_file_filters(template, feature)
        return {"file_filters": filters} if filters else {}

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
                elif kind == 'done':
                    result, error = payload
                    self.worker = None
                    if hasattr(self.view, 'hide_progress'):
                        self.view.hide_progress()
                    if error is not None:
                        QMessageBox.critical(self.view, "错误", f"处理失败：{error}")
                    else:
                        if isinstance(result, list):
                            detail = "\n".join(result)
                            QMessageBox.information(self.view, "完成", f"全部解析完成：\n{detail}")
                            if hasattr(self.view, 'update_result'):
                                self.view.update_result(f"成功导出：\n{detail}")
                        else:
                            QMessageBox.information(self.view, "完成", f"解析完成！\n结果保存在：{result}")
                            if hasattr(self.view, 'update_result'):
                                self.view.update_result(f"成功导出：{result}")
                    return
        except queue.Empty:
            pass
        if after is not None:
            after(100, self._poll_worker)

    def clear_results(self):
        if hasattr(self.view, 'result_text'):
            self.view.result_text.clear()
