# views/main_window.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class MainWindow(tk.Tk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller   # 保存控制器
        self.title("MC Log Analysis Tool")
        self.geometry("800x600")
        self._create_menu()
        self._create_widgets()
        self.keyword_var = tk.StringVar()
        self.separator_var = tk.StringVar()
        # ... 其他初始化

    def _create_menu(self):
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="选择源文件夹", command=self.controller.select_source_folder)
        file_menu.add_command(label="选择输出文件夹", command=self.controller.select_output_folder)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)
        menubar.add_cascade(label="文件", menu=file_menu)

        func_menu = tk.Menu(menubar, tearoff=0)
        func_menu.add_command(label="执行解析", command=self.controller.run_parse)
        menubar.add_cascade(label="功能", menu=func_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.config(menu=menubar)

    def _create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 选择路径区域
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=5)
        ttk.Label(path_frame, text="源文件夹：").grid(row=0, column=0, sticky=tk.W)
        self.src_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.src_path_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="浏览", command=self.controller.browse_source).grid(row=0, column=2)

        ttk.Label(path_frame, text="输出文件夹：").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.out_path_var = tk.StringVar()
        ttk.Entry(path_frame, textvariable=self.out_path_var, width=60).grid(row=1, column=1, padx=5)
        ttk.Button(path_frame, text="浏览", command=self.controller.browse_output).grid(row=1, column=2)

        # 参数设置区域
        param_frame = ttk.LabelFrame(main_frame, text="解析参数")
        param_frame.pack(fill=tk.X, pady=10)
        ttk.Label(param_frame, text="关键词（空格/分号分隔）：").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.keyword_var = tk.StringVar()
        ttk.Entry(param_frame, textvariable=self.keyword_var, width=50).grid(row=0, column=1, padx=5)

        ttk.Label(param_frame, text="分隔符（留空则不拆分）：").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.separator_var = tk.StringVar()
        ttk.Entry(param_frame, textvariable=self.separator_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5)

        # 操作按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="开始解析", command=self.controller.run_parse).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空结果", command=self.controller.clear_results).pack(side=tk.LEFT, padx=5)
        # 进度条（初始隐藏）
        self.progress = ttk.Progressbar(main_frame, orient='horizontal', length=400, mode='determinate')
        self.progress.pack(pady=10)
        self.progress.pack_forget()  # 隐藏
        # 结果显示区域（例如使用 Treeview 或 Text）
        result_frame = ttk.LabelFrame(main_frame, text="解析结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        self.result_text = tk.Text(result_frame, wrap=tk.NONE)
        scroll_y = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        scroll_x = ttk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=self.result_text.xview)
        self.result_text.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.result_text.grid(row=0, column=0, sticky=tk.NSEW)
        scroll_y.grid(row=0, column=1, sticky=tk.NS)
        scroll_x.grid(row=1, column=0, sticky=tk.EW)
        result_frame.grid_rowconfigure(0, weight=1)
        result_frame.grid_columnconfigure(0, weight=1)


    def _show_about(self):
        messagebox.showinfo("关于", "MC Log Analysis Tool v1.0\n\n适用于多日志文件解析、筛选与拆分。")

    def update_result(self, text):
        self.result_text.insert(tk.END, text + "\n")
        self.result_text.see(tk.END)

    def show_progress(self, value=0):
            """显示进度条并设置当前值（0~100）"""
            self.progress.pack(pady=10)
            self.progress['value'] = value
            self.update_idletasks()
        
    def update_progress(self, value):
            """更新进度条数值"""
            self.progress['value'] = value
            self.update_idletasks()
        
    def hide_progress(self):
            """完成后隐藏进度条"""
            self.progress.pack_forget()
   