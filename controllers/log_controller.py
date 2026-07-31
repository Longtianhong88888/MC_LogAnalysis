from models.log_model import LogModel
from utils.file_utils import clean_for_excel
import os
from tkinter import filedialog, messagebox
import tkinter as tk
import traceback

class LogController:
    def __init__(self, view):
        self.view = view
        self.source_dir = ""
        self.output_dir = ""

    def select_source_folder(self):
        dir_ = filedialog.askdirectory(title="选择源文件夹")
        if dir_:
            self.source_dir = dir_
            if hasattr(self.view, 'src_path_var'):
                self.view.src_path_var.set(dir_)

    def select_output_folder(self):
        dir_ = filedialog.askdirectory(title="选择输出文件夹")
        if dir_:
            self.output_dir = dir_
            if hasattr(self.view, 'out_path_var'):
                self.view.out_path_var.set(dir_)

    def browse_source(self):
        self.select_source_folder()

    def browse_output(self):
        self.select_output_folder()

    def run_parse(self):
        try:
            if not self.source_dir or not self.output_dir:
                messagebox.showerror("错误", "请先选择源文件夹和输出文件夹")
                return

            if hasattr(self.view, 'show_progress'):
                self.view.show_progress(0)

            keywords = self.view.keyword_var.get().strip() if hasattr(self.view, 'keyword_var') else None
            separator = self.view.separator_var.get().strip() if hasattr(self.view, 'separator_var') else None
            if separator == "":
                separator = None

            def update_progress(value):
                if hasattr(self.view, 'update_progress'):
                    self.view.update_progress(value)

            model = LogModel()
            result = model.process(
                source_dir=self.source_dir,
                output_dir=self.output_dir,
                keywords=keywords if keywords else None,
                separator=separator,
                progress_callback=update_progress
            )
            if hasattr(self.view, 'hide_progress'):
                self.view.hide_progress()
            messagebox.showinfo("完成", f"解析完成！\n结果保存在：{result}")
            if hasattr(self.view, 'update_result'):
                self.view.update_result(f"成功导出：{result}")
        except Exception as e:
            if hasattr(self.view, 'hide_progress'):
                self.view.hide_progress()
            messagebox.showerror("错误", f"处理失败：{e}")
            traceback.print_exc()

    def clear_results(self):
        if hasattr(self.view, 'result_text'):
            self.view.result_text.delete(1.0, tk.END)