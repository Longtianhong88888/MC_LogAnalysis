from models.log_model import LogModel
from utils.file_utils import clean_for_excel
import os
from tkinter import filedialog, messagebox   # 添加这行
import tkinter as tk

class LogController:
    def __init__(self, view):
        self.view = view
        self.source_dir = ""
        self.output_dir = ""

    # 选择源文件夹（供菜单和按钮使用）
    def select_source_folder(self):
        dir_ = filedialog.askdirectory(title="选择源文件夹")
        if dir_:
            self.source_dir = dir_
            if hasattr(self.view, 'src_path_var'):
                self.view.src_path_var.set(dir_)

    # 选择输出文件夹
    def select_output_folder(self):
        dir_ = filedialog.askdirectory(title="选择输出文件夹")
        if dir_:
            self.output_dir = dir_
            if hasattr(self.view, 'out_path_var'):
                self.view.out_path_var.set(dir_)

    # 以下两个方法是旧版本中可能被调用的，与上述功能重复，建议统一使用上面的方法
    # 如果你在 `main_window.py` 中使用了 `browse_source`，请改为 `select_source_folder`
    def browse_source(self):
        self.select_source_folder()   # 直接复用

    def browse_output(self):
        self.select_output_folder()   # 直接复用

    # 执行解析
    def run_parse(self):
        if not self.source_dir or not self.output_dir:
            messagebox.showerror("错误", "请先选择源文件夹和输出文件夹")
            return

        # 从视图获取参数
        keywords = self.view.keyword_var.get().strip() if hasattr(self.view, 'keyword_var') else None
        separator = self.view.separator_var.get().strip() if hasattr(self.view, 'separator_var') else None
        if separator == "":
            separator = None

        try:
            model = LogModel()
            result = model.process(
                source_dir=self.source_dir,
                output_dir=self.output_dir,
                keywords=keywords,
                separator=separator
            )
            messagebox.showinfo("完成", f"解析完成！\n结果保存在：{result}")
            if hasattr(self.view, 'update_result'):
                self.view.update_result(f"成功导出：{result}")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败：{e}")

    def clear_results(self):
        if hasattr(self.view, 'result_text'):
            self.view.result_text.delete(1.0, tk.END)