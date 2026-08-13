from controllers.log_controller import LogController
from views.main_window import MainWindow


class App:
    def __init__(self):
        self.controller = LogController(None)
        self.root = MainWindow(self.controller)
        self.controller.view = self.root
        self.root.restore_web_report_memory()
        self.controller.refresh_station_machines()
