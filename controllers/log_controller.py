import queue
import threading
import traceback

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from models.log_model import LogModel

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
        method_name = FEATURE_METHODS.get(feature, "process")
        params = self._collect_params(feature)

        self._progress_queue = queue.Queue()

        def worker():
            try:
                model = LogModel()
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
