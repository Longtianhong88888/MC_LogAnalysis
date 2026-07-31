import sys
from views.main_window import MainWindow
from controllers.log_controller import LogController

class App:
    def __init__(self):
        # 先创建控制器（还没有视图）
        self.controller = LogController(None)
        # 创建主窗口，将控制器传入
        self.root = MainWindow(self.controller)
        # 双向绑定（如果控制器需要访问视图，可以设置）
        self.controller.view = self.root

    def run(self):
        self.root.mainloop()