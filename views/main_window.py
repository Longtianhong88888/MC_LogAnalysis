from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.process_templates import CUSTOM_TEMPLATE_NAME, PROCESS_TEMPLATES, get_template
from utils.resource_utils import resource_path

ONE_CLICK_FEATURE = "一键分析（全部）"
FEATURES = ["文档合并与内容拆分", "UPH分析", "EFF分析", "报警分析", "机台状态分析", ONE_CLICK_FEATURE]

DEFAULT_TRIGGER_KEYWORDS = "MarkEnd1"
DEFAULT_ALARM_KEYWORDS = "报警,ALARM,ERROR,NG,失败,异常,停止信号"


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("MC Log Analysis Tool")
        self.resize(800, 680)
        icon = QIcon(resource_path("log.ico"))
        if not icon.isNull():
            self.setWindowIcon(icon)
        self._create_menu()
        self._create_widgets()

    def _create_menu(self):
        file_menu = self.menuBar().addMenu("文件")
        file_menu.addAction("选择源文件夹", self.controller.select_source_folder)
        file_menu.addAction("选择输出文件夹", self.controller.select_output_folder)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.close)

        func_menu = self.menuBar().addMenu("功能")
        func_menu.addAction("执行解析", self.controller.run_parse)
        func_menu.addSeparator()
        self._feature_actions = []
        for index, name in enumerate(FEATURES):
            action = func_menu.addAction(
                name, lambda checked=False, i=index: self.feature_combo.setCurrentIndex(i)
            )
            action.setCheckable(True)
            self._feature_actions.append(action)

        help_menu = self.menuBar().addMenu("帮助")
        help_menu.addAction("关于", self._show_about)

    def _create_widgets(self):
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # 制程模板
        template_row = QHBoxLayout()
        template_row.addWidget(QLabel("制程模板："))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(PROCESS_TEMPLATES.keys()))
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        template_row.addWidget(self.template_combo)
        self.save_template_btn = QPushButton("保存为自定义模板")
        self.save_template_btn.clicked.connect(self.controller.save_custom_template)
        template_row.addWidget(self.save_template_btn)
        template_row.addStretch(1)
        root.addLayout(template_row)

        # 自定义模板的日志文件筛选
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("日志文件筛选："))
        self.custom_filter_edit = QLineEdit()
        self.custom_filter_edit.setPlaceholderText("逗号分隔文件名关键词，留空=全部（仅自定义模板生效）")
        filter_row.addWidget(self.custom_filter_edit, 1)
        root.addLayout(filter_row)

        # 功能选择
        feature_row = QHBoxLayout()
        feature_row.addWidget(QLabel("功能选择："))
        self.feature_combo = QComboBox()
        self.feature_combo.addItems(FEATURES)
        self.feature_combo.currentIndexChanged.connect(self._on_feature_changed)
        feature_row.addWidget(self.feature_combo)
        feature_row.addStretch(1)
        root.addLayout(feature_row)

        # 解析参数（按功能切换）
        self.param_stack = QStackedWidget()
        self._build_merge_page()
        self._build_uph_page()
        self._build_eff_page()
        self._build_alarm_page()
        self._build_status_page()
        self._build_all_page()
        root.addWidget(self.param_stack)
        self._on_feature_changed(0)
        self._apply_template()

        # 路径
        path_box = QGroupBox("路径")
        path_grid = QGridLayout(path_box)
        self.src_path_edit = QLineEdit()
        self.src_path_edit.setReadOnly(True)
        self.src_path_edit.setPlaceholderText("未选择")
        src_btn = QPushButton("浏览")
        src_btn.clicked.connect(self.controller.browse_source)
        path_grid.addWidget(QLabel("源文件夹："), 0, 0)
        path_grid.addWidget(self.src_path_edit, 0, 1)
        path_grid.addWidget(src_btn, 0, 2)

        self.out_path_edit = QLineEdit()
        self.out_path_edit.setReadOnly(True)
        self.out_path_edit.setPlaceholderText("未选择")
        out_btn = QPushButton("浏览")
        out_btn.clicked.connect(self.controller.browse_output)
        path_grid.addWidget(QLabel("输出文件夹："), 1, 0)
        path_grid.addWidget(self.out_path_edit, 1, 1)
        path_grid.addWidget(out_btn, 1, 2)
        path_grid.setColumnStretch(1, 1)
        root.addWidget(path_box)

        # 按钮
        btn_row = QHBoxLayout()
        start_btn = QPushButton("开始解析")
        start_btn.clicked.connect(self.controller.run_parse)
        clear_btn = QPushButton("清空结果")
        clear_btn.clicked.connect(self.controller.clear_results)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # 进度条
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.hide()
        root.addWidget(self.progress)

        # 结果
        result_box = QGroupBox("解析结果")
        result_layout = QVBoxLayout(result_box)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        root.addWidget(result_box, 1)

    # ---------- 参数页 ----------
    def _new_param_page(self):
        box = QGroupBox("解析参数")
        form = QFormLayout(box)
        self.param_stack.addWidget(box)
        return form

    def _build_merge_page(self):
        form = self._new_param_page()
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText("多个关键词用空格、分号、顿号或中文逗号分隔")
        self.separator_edit = QLineEdit()
        self.separator_edit.setPlaceholderText("留空则不拆分，例如 , 或 \\t")
        form.addRow("关键词：", self.keyword_edit)
        form.addRow("分隔符：", self.separator_edit)

    def _threshold_spin(self, value):
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 86400.0)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setSuffix(" 秒")
        return spin

    def _build_uph_page(self):
        form = self._new_param_page()
        self.uph_trigger_edit = QLineEdit(DEFAULT_TRIGGER_KEYWORDS)
        self.uph_trigger_edit.setPlaceholderText("行内容包含任一关键词即记为一个产出周期，多个用逗号分隔")
        self.uph_units_spin = QSpinBox()
        self.uph_units_spin.setRange(1, 9999)
        self.uph_units_spin.setValue(1)
        self.uph_units_spin.setSuffix(" 个/周期")
        self.uph_normal_spin = self._threshold_spin(10.0)
        self.uph_planned_spin = self._threshold_spin(900.0)
        self.uph_ideal_ct_edit = QLineEdit()
        self.uph_ideal_ct_edit.setPlaceholderText("留空自动取正常周期平均")
        self.uph_max_ct_edit = QLineEdit()
        self.uph_max_ct_edit.setPlaceholderText("留空则不按上限过滤")
        form.addRow("完成动作关键词：", self.uph_trigger_edit)
        form.addRow("每周期产出数：", self.uph_units_spin)
        form.addRow("正常周期阈值：", self.uph_normal_spin)
        form.addRow("计划性停机阈值：", self.uph_planned_spin)
        form.addRow("理想周期CT(秒)：", self.uph_ideal_ct_edit)
        form.addRow("最大理论周期CT(秒)：", self.uph_max_ct_edit)

    def _build_eff_page(self):
        form = self._new_param_page()
        self.eff_planned_hours_edit = QLineEdit()
        self.eff_planned_hours_edit.setPlaceholderText("留空则取日志总时长")
        self.eff_pdt_reason_edit = QLineEdit()
        self.eff_pdt_reason_edit.setPlaceholderText("如 0000000411,0000000412，留空则全部计入可用性损失")
        note = QLabel("按 CoreTech AME 定义：EFF(效率) = 操作时间(运行+待机) / 计划生产时间，\n"
                      "基于日志中的 RUN / IDLE / DOWN 状态统计，停机可依 ReasonID 拆分为计划停机 pDT 与非计划停机 uDT。")
        note.setWordWrap(True)
        form.addRow(note)
        form.addRow("计划生产时间(小时)：", self.eff_planned_hours_edit)
        form.addRow("计划停机ReasonID：", self.eff_pdt_reason_edit)

    def _build_alarm_page(self):
        form = self._new_param_page()
        self.alarm_keywords_edit = QLineEdit(DEFAULT_ALARM_KEYWORDS)
        self.alarm_keywords_edit.setPlaceholderText("多个关键词用逗号、空格或分号分隔，忽略大小写")
        form.addRow("报警关键词：", self.alarm_keywords_edit)

    def _build_status_page(self):
        form = self._new_param_page()
        note = QLabel("自动识别日志中的 status:RUN / IDLE / DOWN 状态行，\n"
                      "统计各状态时长与占比，并按小时输出分布。")
        note.setWordWrap(True)
        form.addRow(note)

    def _build_all_page(self):
        form = self._new_param_page()
        note = QLabel("按当前制程模板依次运行 UPH / EFF / 报警 / 机台状态四项分析，\n"
                      "分别输出 UPH_Analysis.xlsx、EFF_Analysis.xlsx、Alarm_Analysis.xlsx、Status_Analysis.xlsx。")
        note.setWordWrap(True)
        form.addRow(note)

    def _on_template_changed(self, index):
        self._apply_template()

    def _apply_template(self):
        """按当前制程模板预填各功能参数；自定义模板同时回填保存的配置。"""
        tpl = get_template(self.template_combo.currentText())
        uph = tpl.get("UPH分析") or {}
        eff = tpl.get("EFF分析") or {}
        alarm = tpl.get("报警分析") or {}
        if hasattr(self, 'uph_trigger_edit'):
            self.uph_trigger_edit.setText(str(uph.get("trigger_keywords") or DEFAULT_TRIGGER_KEYWORDS))
            self.uph_units_spin.setValue(int(uph.get("units_per_cycle") or 1))
            self.uph_normal_spin.setValue(float(uph.get("normal_threshold") or 10.0))
            self.uph_planned_spin.setValue(float(uph.get("planned_threshold") or 900.0))
            self.uph_ideal_ct_edit.setText("" if not uph.get("ideal_ct") else str(uph["ideal_ct"]))
            self.uph_max_ct_edit.setText("" if not uph.get("max_ct") else str(uph["max_ct"]))
            self.eff_planned_hours_edit.setText("" if not eff.get("planned_hours") else str(eff["planned_hours"]))
            self.eff_pdt_reason_edit.setText(str(eff.get("pdt_reason_ids") or ""))
            self.alarm_keywords_edit.setText(str(alarm.get("alarm_keywords") or DEFAULT_ALARM_KEYWORDS))
            if self.template_combo.currentText() == CUSTOM_TEMPLATE_NAME:
                filters = tpl.get("file_filters")
                self.custom_filter_edit.setText(", ".join(filters) if filters else "")

    def _on_feature_changed(self, index):
        self.param_stack.setCurrentIndex(index)
        for i, action in enumerate(self._feature_actions):
            action.setChecked(i == index)

    # ---------- 控制器回调 ----------
    def _show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "MC Log Analysis Tool v1.0\n\n"
            "文档合并与内容拆分 / UPH分析 / EFF分析 / 报警分析 / 机台状态分析",
        )

    def update_result(self, text):
        self.result_text.append(text)

    def show_progress(self, value=0):
        self.progress.setValue(value)
        self.progress.show()

    def update_progress(self, value):
        self.progress.setValue(value)

    def hide_progress(self):
        self.progress.hide()

    def after(self, ms, callback):
        """供控制器调度主线程回调。"""
        QTimer.singleShot(ms, callback)
