"""主窗口：Apple 风格 UI。"""

from datetime import datetime

from PyQt5.QtCore import QDateTime, QEasingCurve, QPropertyAnimation, QTime, Qt, QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDoubleSpinBox,
    QFrame,
    QFormLayout,
    QLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from models.process_templates import CUSTOM_TEMPLATE_NAME, PROCESS_TEMPLATES, get_template
from models.reason_codes import available_reason_lists
from models import station_config
from models import web_api
from utils.resource_utils import resource_path
from views.user_guide import USER_GUIDE_HTML

ONE_CLICK_FEATURE = "一键分析（自动报告）"
FEATURES = ["文档合并与内容拆分", "UPH分析", "EFF分析", "报警分析", "机台状态分析",
            ONE_CLICK_FEATURE]
WINDOW_DEFAULT_SIZE = (980, 880)
WINDOW_SCREEN_RATIO = 0.8  # 主窗口占屏幕可用区域的百分比


def window_target_size(ratio=WINDOW_SCREEN_RATIO):
    """按当前屏幕可用区域计算主窗口目标尺寸（默认 80%）。"""
    screen = QApplication.primaryScreen()
    if screen is None:
        return WINDOW_DEFAULT_SIZE
    geo = screen.availableGeometry()
    w = max(900, int(geo.width() * ratio))
    h = max(620, int(geo.height() * ratio))
    return w, h

DEFAULT_TRIGGER_KEYWORDS = "MarkEnd1"
DEFAULT_ALARM_KEYWORDS = "报警,ALARM,ERROR,NG,失败,异常,停止信号"

# ── Apple 设计体系 ──────────────────────────────────────────────
# 色彩
C_BG     = "#F5F5F7"   # 窗口背景（Apple 标志性浅灰）
C_CARD   = "#FFFFFF"   # 卡片底色
C_PRIME  = "#007AFF"   # 主色调（Apple Blue）
C_PRIME_H= "#0062CC"   # 主色调 hover
C_TEXT   = "#1D1D1F"   # 主文字
C_SUB    = "#86868B"   # 辅助文字
C_BORDER = "#E5E5EA"   # 边框/分割线
C_INPUT_BG = "#F9F9F9" # 输入框底板
C_GREEN  = "#34C759"
C_RED    = "#FF3B30"

# 字体（macOS → SF Pro / Windows → Segoe UI）
FONT_FAMILY = (
    '"Helvetica Neue", "PingFang SC", "Segoe UI", "Microsoft YaHei", sans-serif'
)
FONT_MONO = '"Menlo", "Consolas", "Cascadia Code", "SF Mono", monospace'

# 间距
GAP_SECTION = 10       # 卡片间距
GAP_ROW     = 6        # 行内控件间距
GAP_INNER   = 6        # 标签-控件间距
CARD_PAD    = 12       # 卡片内边距
RADIUS      = 8        # 圆角

# ── 全局样式表 ──────────────────────────────────────────────────
APPLE_QSS = f"""
/* ─── 全局 ─── */
QMainWindow, QDialog {{
    background-color: {C_BG};
}}
QWidget {{
    font-family: {FONT_FAMILY};
    font-size: 13px;
    color: {C_TEXT};
}}

/* ─── 卡片容器 ─── */
QWidget[card="true"] {{
    background-color: {C_CARD};
    border: 1px solid {C_BORDER};
    border-radius: {RADIUS}px;
}}

/* ─── 标签 ─── */
QLabel[heading="true"] {{
    font-size: 15px;
    font-weight: bold;
    color: {C_TEXT};
    padding: 0;
}}
QLabel[subtitle="true"] {{
    font-size: 12px;
    color: {C_SUB};
}}

/* ─── 主按钮（实心蓝） ─── */
QPushButton[primary="true"] {{
    background-color: {C_PRIME};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 8px 24px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton[primary="true"]:hover {{
    background-color: {C_PRIME_H};
}}
QPushButton[primary="true"]:pressed {{
    background-color: #0055AA;
}}

/* ─── 次按钮（浅灰底） ─── */
QPushButton[secondary="true"] {{
    background-color: #F0F0F2;
    color: {C_TEXT};
    border: none;
    border-radius: 10px;
    padding: 8px 18px;
    font-size: 13px;
}}
QPushButton[secondary="true"]:hover {{
    background-color: #E4E4E8;
}}
QPushButton[secondary="true"]:pressed {{
    background-color: #D8D8DC;
}}

/* ─── 文字按钮（蓝色链接风） ─── */
QPushButton[link="true"] {{
    background: transparent;
    color: {C_PRIME};
    border: none;
    padding: 6px 12px;
    font-size: 13px;
}}
QPushButton[link="true"]:hover {{
    color: {C_PRIME_H};
    text-decoration: underline;
}}

/* ─── 描边按钮（无底色，Apple 次按钮） ─── */
QPushButton[outline="true"] {{
    background: transparent;
    color: {C_TEXT};
    border: 1px solid #D2D2D7;
    border-radius: 10px;
    padding: 7px 18px;
    font-size: 13px;
}}
QPushButton[outline="true"]:hover {{
    border-color: {C_PRIME};
    color: {C_PRIME};
}}
QPushButton[outline="true"]:disabled {{
    color: #AEAEB2;
    border-color: #E5E5EA;
    background: transparent;
}}

/* ─── 成功按钮（查询有数据后启用） ─── */
QPushButton[success="true"] {{
    background-color: {C_GREEN};
    color: #FFFFFF;
    border: none;
    border-radius: 10px;
    padding: 7px 18px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton[success="true"]:hover {{
    background-color: #2DB84F;
}}

/* ─── 文字按钮（蓝色下划线风，用于重置/选路径） ─── */
QPushButton[linkblue="true"] {{
    background: transparent;
    color: {C_PRIME};
    border: none;
    padding: 4px 8px;
    font-size: 12px;
}}
QPushButton[linkblue="true"]:hover {{
    text-decoration: underline;
}}

/* ─── 输入框 ─── */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid #D2D2D7;
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 13px;
    color: {C_TEXT};
}}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1.5px solid {C_PRIME};
    background-color: #F2F8FF;
}}
QLineEdit[readOnly="true"] {{
    background-color: #F5F5F7;
    color: {C_SUB};
}}

/* ─── 下拉框 ─── */
QComboBox {{
    background-color: #FFFFFF;
    border: 1px solid #D2D2D7;
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 13px;
    min-width: 160px;
}}
QComboBox:focus {{
    border: 1.5px solid {C_PRIME};
    background-color: #F2F8FF;
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 28px;
    border: none;
    border-left: 1px solid {C_BORDER};
    border-top-right-radius: 6px;
    border-bottom-right-radius: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: #FFFFFF;
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    selection-background-color: {C_PRIME};
    selection-color: #FFFFFF;
    padding: 4px;
    outline: none;
}}

/* ─── 设备效能页：Apple 轻量样式 ─── */
QLabel#webTitle {{
    font-size: 30px;
    font-weight: 600;
    color: {C_TEXT};
}}
QLabel#webSub {{
    font-size: 13px;
    color: {C_SUB};
}}
QLabel[chip="true"] {{
    background-color: #F5F5F7;
    color: {C_TEXT};
    border-radius: 10px;
    padding: 5px 12px;
    font-size: 12px;
}}
QPlainTextEdit#webLog {{
    background-color: #F5F5F7;
    border: none;
    border-radius: 10px;
    font-family: {FONT_MONO};
    font-size: 11px;
    color: #3A3A3C;
    padding: 8px;
}}
QTableWidget {{
    background-color: #FFFFFF;
    border: 1px solid #E5E5EA;
    border-radius: 10px;
    gridline-color: #E5E5EA;
}}
QTableWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget QHeaderView::section {{
    background-color: #F9F9FB;
    color: {C_TEXT};
    font-weight: bold;
    font-size: 11px;
    border: none;
    border-bottom: 1px solid #E5E5EA;
    padding: 6px 8px;
}}

/* ─── 进度条 ─── */
QProgressBar {{
    background-color: #E8E8ED;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;              /* 隐藏百分比文字 */
}}
QProgressBar::chunk {{
    background-color: {C_PRIME};
    border-radius: 4px;
}}

/* ─── 结果文本框 ─── */
QTextEdit {{
    background-color: #FAFAFA;
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 10px;
    font-family: {FONT_MONO};
    font-size: 12px;
    color: {C_TEXT};
}}

/* ─── 滚动条 ─── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: #D0D0D6;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #B0B0B6;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

/* ─── 菜单栏 ─── */
QMenuBar {{
    background-color: #FFFFFF;
    border-bottom: 1px solid {C_BORDER};
    padding: 2px 0;
}}
QMenuBar::item {{
    padding: 6px 14px;
    border-radius: 5px;
}}
QMenuBar::item:selected {{
    background-color: #F0F0F2;
}}
QMenu {{
    background-color: #FFFFFF;
    border: 1px solid {C_BORDER};
    border-radius: 8px;
    padding: 6px 0;
}}
QMenu::item {{
    padding: 7px 32px 7px 20px;
}}
QMenu::item:selected {{
    background-color: {C_PRIME};
    color: #FFFFFF;
    border-radius: 4px;
}}

/* ─── 状态栏 ─── */
QStatusBar {{
    background-color: #FFFFFF;
    border-top: 1px solid {C_BORDER};
    font-size: 12px;
    color: {C_SUB};
    padding: 2px 12px;
}}

/* ─── 提示框 ─── */
QToolTip {{
    background-color: #FFFFFF;
    border: 1px solid {C_BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
    color: {C_TEXT};
}}
"""

# ── 辅助函数 ────────────────────────────────────────────────────
def _card(title_text, layout_or_widget, parent=None):
    """创建 Apple 风格卡片：白色圆角背景 + 可选标题。"""
    card = QWidget(parent)
    card.setProperty("card", True)
    # 卡片内布局
    inner = QVBoxLayout(card)
    inner.setContentsMargins(CARD_PAD, CARD_PAD, CARD_PAD, CARD_PAD)
    inner.setSpacing(GAP_ROW)
    if title_text:
        heading = QLabel(title_text)
        heading.setProperty("heading", True)
        inner.addWidget(heading)
    if isinstance(layout_or_widget, QLayout):
        inner.addLayout(layout_or_widget, 1)
    else:
        inner.addWidget(layout_or_widget, 1)
    return card


def _hint(text):
    """灰色辅助说明标签。"""
    lbl = QLabel(text)
    lbl.setProperty("subtitle", True)
    lbl.setWordWrap(True)
    return lbl


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.setWindowTitle("设备效能分析工具")
        w, h = window_target_size()
        self.resize(w, h)
        self.setMinimumSize(max(840, int(w * 0.8)), max(600, int(h * 0.85)))

        icon = QIcon(resource_path("log.ico"))
        if not icon.isNull():
            self.setWindowIcon(icon)

        self.setStyleSheet(APPLE_QSS)
        self._create_menu()
        self._create_widgets()

        # 状态栏
        sb = self.statusBar()
        sb.showMessage("就绪")
        sb_label = QLabel("Copyright © 2026 ABU NPD EOL")
        sb_label.setStyleSheet("color: #AEAEB2; font-size: 10px; padding-right: 8px;")
        sb.addPermanentWidget(sb_label)

    # ── 菜单栏 ──────────────────────────────────────────────────
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
        help_menu.addAction("使用说明", self._show_user_guide)
        help_menu.addAction("关于", self._show_about)

    # ── 主布局 ──────────────────────────────────────────────────
    def _create_widgets(self):
        self.tabs = QTabWidget(self)
        self.setCentralWidget(self.tabs)

        # ── 页签 1：日志分析（原有功能） ──
        log_page = QWidget()
        root = QVBoxLayout(log_page)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(GAP_SECTION)

        # ─── 配置卡片 ───
        config_grid = QGridLayout()
        config_grid.setVerticalSpacing(GAP_ROW)
        config_grid.setHorizontalSpacing(16)
        config_grid.setColumnStretch(1, 1)
        config_grid.setColumnStretch(3, 1)

        # 第 1 行：制程模板 + 制程名称
        config_grid.addWidget(QLabel("制程模板"), 0, 0)
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(PROCESS_TEMPLATES.keys()))
        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        tmpl_row = QHBoxLayout()
        tmpl_row.setSpacing(GAP_INNER)
        tmpl_row.addWidget(self.template_combo, 1)
        self.save_template_btn = QPushButton("保存为自定义模板")
        self.save_template_btn.setProperty("link", True)
        self.save_template_btn.clicked.connect(self.controller.save_custom_template)
        tmpl_row.addWidget(self.save_template_btn)
        guide_btn = QPushButton("使用说明")
        guide_btn.setProperty("link", True)
        guide_btn.clicked.connect(self._show_user_guide)
        tmpl_row.addWidget(guide_btn)
        config_grid.addLayout(tmpl_row, 0, 1)

        config_grid.addWidget(QLabel("制程名称"), 0, 2)
        reason_row = QHBoxLayout()
        reason_row.setSpacing(GAP_INNER)
        self.reason_combo = QComboBox()
        self.reason_combo.addItem("（无）")
        for device in available_reason_lists():
            self.reason_combo.addItem(device)
        reason_row.addWidget(self.reason_combo)
        reason_row.addStretch(1)
        config_grid.addLayout(reason_row, 0, 3)

        # 第 2 行：功能选择（左） + 日志文件筛选（右）
        config_grid.addWidget(QLabel("功能选择"), 1, 0)
        self.feature_combo = QComboBox()
        self.feature_combo.addItems(FEATURES)
        self.feature_combo.currentIndexChanged.connect(self._on_feature_changed)
        config_grid.addWidget(self.feature_combo, 1, 1)

        config_grid.addWidget(QLabel("日志文件筛选"), 1, 2)
        self.custom_filter_edit = QLineEdit()
        self.custom_filter_edit.setPlaceholderText("逗号分隔文件名关键词，留空=全部；随制程自动填充，可手动修改")
        config_grid.addWidget(self.custom_filter_edit, 1, 3)

        root.addWidget(_card("配置", config_grid))

        # ─── 参数卡片 ───
        self.param_stack = QStackedWidget()
        self.param_stack.setMinimumHeight(260)
        self.param_stack.setProperty("card", True)
        self.param_stack.setStyleSheet(
            f"QStackedWidget[card=\"true\"] {{"
            f"  background-color: {C_CARD};"
            f"  border: 1px solid {C_BORDER};"
            f"  border-radius: {RADIUS}px;"
            f"  padding: {CARD_PAD}px;"
            f"}}"
        )
        self._build_merge_page()
        self._build_uph_page()
        self._build_eff_page()
        self._build_alarm_page()
        self._build_status_page()
        self._build_all_page()
        root.addWidget(self.param_stack)

        # ─── 文件路径选择卡片 ───
        path_grid = QGridLayout()
        path_grid.setVerticalSpacing(GAP_ROW)
        path_grid.setHorizontalSpacing(GAP_INNER)
        self.src_path_edit = QLineEdit()
        self.src_path_edit.setReadOnly(True)
        self.src_path_edit.setPlaceholderText("未选择")
        src_btn = QPushButton("浏览")
        src_btn.setProperty("secondary", True)
        src_btn.clicked.connect(self.controller.browse_source)
        path_grid.addWidget(QLabel("源文件夹"), 0, 0)
        path_grid.addWidget(self.src_path_edit, 0, 1)
        path_grid.addWidget(src_btn, 0, 2)

        self.out_path_edit = QLineEdit()
        self.out_path_edit.setReadOnly(True)
        self.out_path_edit.setPlaceholderText("未选择")
        out_btn = QPushButton("浏览")
        out_btn.setProperty("secondary", True)
        out_btn.clicked.connect(self.controller.browse_output)
        path_grid.addWidget(QLabel("输出文件夹"), 1, 0)
        path_grid.addWidget(self.out_path_edit, 1, 1)
        path_grid.addWidget(out_btn, 1, 2)

        path_grid.setColumnStretch(1, 1)
        root.addWidget(_card("文件路径选择", path_grid))

        # ─── 操作按钮 ───
        btn_row = QHBoxLayout()
        btn_row.setSpacing(GAP_ROW)
        start_btn = QPushButton("自动报告")
        start_btn.setProperty("primary", True)
        start_btn.clicked.connect(self.controller.run_parse)
        clear_btn = QPushButton("清空结果")
        clear_btn.setProperty("secondary", True)
        clear_btn.clicked.connect(self.controller.clear_results)
        self.skip_btn = QPushButton("跳转至下一步")
        self.skip_btn.setProperty("secondary", True)
        self.skip_btn.clicked.connect(self.controller.request_skip)
        btn_row.addWidget(start_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addWidget(self.skip_btn)
        btn_row.addStretch(1)
        root.addLayout(btn_row)

        # ─── 进度条 ───
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(8)
        self.progress.hide()
        root.addWidget(self.progress)

        # ─── 结果卡片 ───
        result_layout = QVBoxLayout()
        result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("解析结果将显示在此处 ...")
        result_layout.addWidget(self.result_text)
        root.addWidget(_card("解析结果", result_layout), 1)
        self.tabs.addTab(log_page, "日志分析")

        # ── 页签 2：设备效能 ──
        web_page = self._build_web_report_page()
        self.tabs.addTab(web_page, "设备效能")

        # 初始化
        self._on_feature_changed(0)
        self._apply_template()

    # ── 参数页 ──────────────────────────────────────────────────
    def _form_page(self, form_rows, note=None):
        """构建含标签和控件行的表单页。note 可以是字符串或已创建的 QLabel。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP_ROW)
        if note is not None:
            layout.addWidget(_hint(note) if isinstance(note, str) else note)
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setVerticalSpacing(GAP_ROW)
        form.setHorizontalSpacing(GAP_INNER)
        for label_text, widget in form_rows:
            form.addRow(QLabel(label_text), widget)
        layout.addLayout(form)
        layout.addStretch(1)
        self.param_stack.addWidget(page)

    def _build_merge_page(self):
        note = _hint("按关键词筛选日志行，可选按分隔符拆分列。")
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(GAP_ROW)
        layout.addWidget(note)
        grid = QGridLayout()
        grid.setVerticalSpacing(GAP_ROW)
        grid.setHorizontalSpacing(GAP_INNER)
        grid.setColumnStretch(1, 1)
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setAlignment(Qt.AlignLeft)
        self.keyword_edit.setPlaceholderText("多个关键词用空格、分号、顿号或中文逗号分隔")
        self.separator_edit = QLineEdit()
        self.separator_edit.setAlignment(Qt.AlignLeft)
        self.separator_edit.setPlaceholderText("留空则不拆分，例如 , 或 \\t")
        grid.addWidget(QLabel("关键词"), 0, 0)
        grid.addWidget(self.keyword_edit, 0, 1)
        grid.addWidget(QLabel("分隔符"), 1, 0)
        grid.addWidget(self.separator_edit, 1, 1)
        layout.addLayout(grid)
        layout.addStretch(1)
        self.param_stack.addWidget(page)

    def _threshold_spin(self, value):
        spin = QDoubleSpinBox()
        spin.setRange(0.1, 86400.0)
        spin.setDecimals(1)
        spin.setValue(value)
        spin.setSuffix(" 秒")
        return spin

    def _build_uph_page(self):
        note = _hint("行内容包含任一关键词即记为一个产出周期，多个用逗号分隔。")
        self.uph_trigger_edit = QLineEdit(DEFAULT_TRIGGER_KEYWORDS)
        self.uph_trigger_edit.setPlaceholderText("多个用逗号分隔")
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
        self.uph_step_coef_spin = QDoubleSpinBox()
        self.uph_step_coef_spin.setRange(1.0, 10.0)
        self.uph_step_coef_spin.setDecimals(1)
        self.uph_step_coef_spin.setValue(1.5)
        self.uph_step_coef_spin.setSuffix(" ×中位时长")
        self._form_page([
            ("完成动作关键词", self.uph_trigger_edit),
            ("每周期产出数",     self.uph_units_spin),
            ("正常周期阈值",     self.uph_normal_spin),
            ("计划性停机阈值",   self.uph_planned_spin),
            ("理想周期CT(秒)",   self.uph_ideal_ct_edit),
            ("最大理论周期CT(秒)", self.uph_max_ct_edit),
            ("步骤异常系数",     self.uph_step_coef_spin),
        ], note)

    def _build_eff_page(self):
        note = _hint(
            "按 CoreTech AME 定义：EFF = 操作时间(运行+待机) / 计划生产时间。\n"
            "基于 RUN / IDLE / DOWN 状态统计，停机可依 ReasonID 拆分为 pDT / uDT。\n"
            "数据来源选「联网接口」时，从戰情中心 CMS 后端拉取机台状态日志与 EFF 汇总，"
            "无需本地日志；机台类型（如 CAW/LM/FR/ACF）与机台号至少填一项。"
        )
        self.eff_planned_hours_edit = QLineEdit()
        self.eff_planned_hours_edit.setPlaceholderText("留空则取日志总时长")
        self.eff_pdt_reason_edit = QLineEdit()
        self.eff_pdt_reason_edit.setPlaceholderText("如 0000000411,0000000412，留空则全部计入可用性损失")
        self.eff_source_combo = QComboBox()
        self.eff_source_combo.addItems(["本地日志", "联网接口"])
        self.eff_source_combo.currentIndexChanged.connect(self._on_eff_source_changed)
        self.web_api_url_edit = QLineEdit(web_api.DEFAULT_BASE_URL)
        self.web_api_url_edit.setPlaceholderText("CMS FS 后端地址")
        self.web_plant_edit = QLineEdit(web_api.DEFAULT_PLANT_ID)
        self.web_plant_edit.setPlaceholderText("PlantID")
        self.web_machine_type_edit = QLineEdit()
        self.web_machine_type_edit.setPlaceholderText("如 CAW / LM / FR / ACF，与机台号至少填一项")
        self.web_machine_nos_edit = QLineEdit()
        self.web_machine_nos_edit.setPlaceholderText("逗号分隔，如 CAW7203,CAW7205；留空=该类型全部")
        self.web_begin_edit = QLineEdit()
        self.web_begin_edit.setPlaceholderText("留空=昨天06:00，格式 yyyy/MM/dd HH:mm:ss")
        self.web_end_edit = QLineEdit()
        self.web_end_edit.setPlaceholderText("留空=今天06:00")
        self.web_head_edit = QLineEdit()
        self.web_head_edit.setPlaceholderText("多模组机台头（可空）")
        self._form_page([
            ("计划生产时间(小时)", self.eff_planned_hours_edit),
            ("计划停机ReasonID",   self.eff_pdt_reason_edit),
            ("数据来源",           self.eff_source_combo),
            ("接口地址",           self.web_api_url_edit),
            ("PlantID",            self.web_plant_edit),
            ("机台类型",           self.web_machine_type_edit),
            ("机台号",             self.web_machine_nos_edit),
            ("开始时间",           self.web_begin_edit),
            ("结束时间",           self.web_end_edit),
            ("机台头Head",         self.web_head_edit),
        ], note)
        self._on_eff_source_changed(0)

    def _on_eff_source_changed(self, _index):
        """切换 EFF 数据来源时，启用/禁用联网参数。"""
        web = self.eff_source_combo.currentText() == "联网接口"
        for w in (self.web_api_url_edit, self.web_plant_edit, self.web_machine_type_edit,
                  self.web_machine_nos_edit, self.web_begin_edit, self.web_end_edit,
                  self.web_head_edit):
            w.setEnabled(web)

    def _build_alarm_page(self):
        note = _hint("多个关键词用逗号、空格或分号分隔，忽略大小写。")
        self.alarm_keywords_edit = QLineEdit(DEFAULT_ALARM_KEYWORDS)
        self.alarm_keywords_edit.setPlaceholderText("多个关键词用逗号分隔")
        self._form_page([("报警关键词", self.alarm_keywords_edit)], note)

    def _build_status_page(self):
        note = _hint(
            "自动识别日志中的 status:RUN / IDLE / DOWN 状态行，\n"
            "统计各状态时长与占比，并按小时输出分布。"
        )
        self._form_page([], note)

    def _build_all_page(self):
        note = _hint(
            "按当前制程模板依次运行 UPH / EFF / 报警 / 机台状态四项分析，\n"
            "分别输出 UPH_Analysis.xlsx、EFF_Analysis.xlsx、Alarm_Analysis.xlsx、Status_Analysis.xlsx（不含 PPT）；\n"
            "PPT 报告请使用「设备效能」功能，以联网数据生成。"
        )
        self._form_page([], note)

    def _build_web_report_page(self):
        """构建「设备效能」独立页签：Apple 轻量三段式布局。"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        # ── 顶部：页面标题 + 轻量描述 ──
        title = QLabel("设备效能")
        title.setObjectName("webTitle")
        layout.addWidget(title)
        sub = QLabel("从戰情中心 CMS 拉取机台产出 / 状态 / 报警数据，一键生成 UPH · EFF · 报警 · 状态报告")
        sub.setObjectName("webSub")
        layout.addWidget(sub)
        layout.addSpacing(6)

        # ── 第一行：站位 + 机台号 + 查询数据（核心必填） ──
        row1 = QHBoxLayout()
        row1.setSpacing(GAP_INNER)
        row1.addWidget(QLabel("站位"))
        self.web_station_combo = QComboBox()
        self.web_station_combo.setEditable(True)
        self.web_station_combo.setFixedWidth(150)
        self.web_station_combo.addItems(station_config.load_stations())
        self._station_refresh_timer = QTimer(self)
        self._station_refresh_timer.setSingleShot(True)
        self._station_refresh_timer.setInterval(500)
        self._station_refresh_timer.timeout.connect(self.controller.refresh_station_machines)
        self.web_station_combo.currentTextChanged.connect(
            lambda _text: self._station_refresh_timer.start()
        )
        row1.addWidget(self.web_station_combo)
        station_btn = QPushButton("维护站位")
        station_btn.setProperty("outline", True)
        station_btn.clicked.connect(self.controller.manage_stations)
        row1.addWidget(station_btn)
        row1.addSpacing(14)
        row1.addWidget(QLabel("机台号"))
        self._last_machine_station = None
        self.web_report_machine_combo = QComboBox()
        self.web_report_machine_combo.setEditable(True)
        self.web_report_machine_combo.setFixedWidth(280)
        self.web_report_machine_combo.setMaxVisibleItems(15)
        self.web_report_machine_combo.lineEdit().setPlaceholderText("留空则查询该站位下所有机台（可逗号分隔多台）")
        row1.addWidget(self.web_report_machine_combo)
        row1.addSpacing(16)
        self.web_query_btn = QPushButton("查询数据")
        self.web_query_btn.setProperty("primary", True)
        self.web_query_btn.setFixedWidth(110)
        self.web_query_btn.clicked.connect(self.controller.query_web_report)
        row1.addWidget(self.web_query_btn)
        row1.addStretch(1)
        layout.addLayout(row1)

        # ── 第二行：时间（内联日期选择器）+ 重置今天 ──
        row2 = QHBoxLayout()
        row2.setSpacing(GAP_INNER)
        row2.addWidget(QLabel("开始时间"))
        self.web_report_begin_dt = QDateTimeEdit()
        self.web_report_begin_dt.setCalendarPopup(True)
        self.web_report_begin_dt.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
        self.web_report_begin_dt.setFixedWidth(200)
        default_begin = QDateTime.currentDateTime().addDays(-1)
        default_begin.setTime(QTime(6, 0, 0))
        self.web_report_begin_dt.setDateTime(default_begin)
        row2.addWidget(self.web_report_begin_dt)
        row2.addWidget(QLabel("至"))
        self.web_report_end_dt = QDateTimeEdit()
        self.web_report_end_dt.setCalendarPopup(True)
        self.web_report_end_dt.setDisplayFormat("yyyy/MM/dd HH:mm:ss")
        self.web_report_end_dt.setFixedWidth(200)
        default_end = QDateTime.currentDateTime()
        default_end.setTime(QTime(6, 0, 0))
        self.web_report_end_dt.setDateTime(default_end)
        row2.addWidget(self.web_report_end_dt)
        reset_btn = QPushButton("↺ 重置到今天")
        reset_btn.setProperty("linkblue", True)
        reset_btn.clicked.connect(self.reset_web_report_time)
        row2.addWidget(reset_btn)
        hint = QLabel("❓")
        hint.setToolTip("默认昨天 06:00 ~ 今天 06:00；点日历箭头选日期，时间可直接修改")
        hint.setStyleSheet(f"color: {C_SUB};")
        row2.addWidget(hint)
        row2.addStretch(1)
        layout.addLayout(row2)

        # ── 第三行：高级参数（Apple 显示更多，平铺一行） ──
        self.web_advanced_btn = QPushButton("▶ 高级参数")
        self.web_advanced_btn.setProperty("link", True)
        self.web_advanced_btn.setCheckable(True)
        self.web_advanced_btn.toggled.connect(self._on_advanced_toggled)
        layout.addWidget(self.web_advanced_btn, 0, Qt.AlignLeft)

        self.web_advanced_panel = QWidget()
        self.web_advanced_panel.setMaximumHeight(0)
        adv = QHBoxLayout(self.web_advanced_panel)
        adv.setContentsMargins(0, 4, 0, 0)
        adv.setSpacing(8)
        self.web_report_api_url_edit = QLineEdit(web_api.DEFAULT_BASE_URL)
        self.web_report_api_url_edit.setFixedWidth(170)
        self.web_report_plant_edit = QLineEdit(web_api.DEFAULT_PLANT_ID)
        self.web_report_plant_edit.setFixedWidth(64)
        head_label = QLabel("机台头Head ❓")
        head_label.setToolTip("多模组机台头，如填写 A 则只取 Head=A 的数据，可逗号分隔多选")
        self.web_report_head_edit = QLineEdit()
        self.web_report_head_edit.setFixedWidth(80)
        self.web_report_head_edit.setToolTip(head_label.toolTip())
        self.web_report_planned_hours_edit = QLineEdit()
        self.web_report_planned_hours_edit.setFixedWidth(70)
        self.web_report_planned_hours_edit.setPlaceholderText("自动填")
        self.web_report_pdt_edit = QLineEdit()
        self.web_report_pdt_edit.setFixedWidth(150)
        self.web_report_pdt_edit.setPlaceholderText("计划停机ReasonID")
        groups = [
            (QLabel("接口"), self.web_report_api_url_edit),
            (QLabel("PlantID"), self.web_report_plant_edit),
            (head_label, self.web_report_head_edit),
            (QLabel("计划生产(h)"), self.web_report_planned_hours_edit),
            (QLabel("停机Reason"), self.web_report_pdt_edit),
        ]
        for gi, (lab, w) in enumerate(groups):
            if gi:
                dot = QLabel("·")
                dot.setStyleSheet(f"color: {C_BORDER}; font-size: 16px;")
                adv.addWidget(dot)
            adv.addWidget(lab)
            adv.addWidget(w)
        adv.addStretch(1)
        layout.addWidget(self.web_advanced_panel)

        # ── 输出区：输出报告 + 输出路径 ──
        out_row = QHBoxLayout()
        out_row.setSpacing(GAP_INNER)
        self.web_export_btn = QPushButton("输出报告")
        self.web_export_btn.setProperty("outline", True)
        self.web_export_btn.setEnabled(False)
        self.web_export_btn.clicked.connect(self.controller.export_web_report)
        out_row.addWidget(self.web_export_btn)
        out_row.addSpacing(16)
        out_row.addWidget(QLabel("📁 输出路径："))
        self.web_out_path_label = QLabel("未选择")
        self.web_out_path_label.setStyleSheet(f"color: {C_SUB}; font-size: 12px;")
        out_row.addWidget(self.web_out_path_label)
        out_btn = QPushButton("选择保存路径…")
        out_btn.setProperty("linkblue", True)
        out_btn.clicked.connect(self.controller.browse_output)
        out_row.addWidget(out_btn)
        out_row.addStretch(1)
        layout.addLayout(out_row)

        # ── 状态胶囊 + 分割线 ──
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        self.web_status_label = QLabel("● 已就绪")
        self.web_count_label = QLabel("📋 数据行数：0")
        self.web_last_query_label = QLabel("🕒 最后查询：--")
        for lab in (self.web_status_label, self.web_count_label, self.web_last_query_label):
            lab.setProperty("chip", True)
        status_row.addWidget(self.web_status_label)
        status_row.addWidget(self.web_count_label)
        status_row.addWidget(self.web_last_query_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #E5E5EA; border: none; max-height: 1px;")
        layout.addWidget(sep)

        # ── 日志 + 预览表 ──
        log_label = QLabel("日志输出")
        log_label.setProperty("heading", True)
        layout.addWidget(log_label)
        self.web_report_result = QPlainTextEdit()
        self.web_report_result.setObjectName("webLog")
        self.web_report_result.setReadOnly(True)
        self.web_report_result.setPlaceholderText("准备就绪，请选择参数后点击「查询数据」")
        self.web_report_result.setMaximumHeight(130)
        layout.addWidget(self.web_report_result)

        table_label = QLabel("数据预览（前 5 行）")
        table_label.setProperty("heading", True)
        layout.addWidget(table_label)
        self.web_preview_table = QTableWidget(0, 0)
        self.web_preview_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.web_preview_table, 1)
        return page

    def reload_stations(self):
        """维护站位后刷新下拉（保留当前选中项）。"""
        stations = station_config.load_stations()
        current = self.web_station_combo.currentText()
        self.web_station_combo.blockSignals(True)
        self.web_station_combo.clear()
        self.web_station_combo.addItems(stations)
        if current in stations:
            self.web_station_combo.setCurrentText(current)
        self.web_station_combo.blockSignals(False)

    def apply_station_machines(self, nos, station):
        """把数据库拉到的机台号填充到下拉框（过期结果丢弃，同站位保留已输入机台号）。"""
        combo = self.web_report_machine_combo
        if nos is None:
            combo.lineEdit().setPlaceholderText("加载中...")
            return
        if station and station != self.web_station_combo.currentText():
            return  # 站位已切换，丢弃过期结果
        prev_text = combo.currentText().strip()
        combo.blockSignals(True)
        combo.clear()
        for no in nos or []:
            combo.addItem(str(no))
        if self._last_machine_station == station and prev_text:
            combo.setCurrentText(prev_text)  # 同站位刷新：保留用户输入/记忆的机台号
        else:
            combo.setCurrentText("")
        combo.blockSignals(False)
        self._last_machine_station = station
        combo.lineEdit().setPlaceholderText("留空则查询该站位下所有机台（可逗号分隔多台）")

    def selected_machine_nos(self):
        """返回机台号（下拉选择或直接输入，逗号分隔；空串=该站位全部）。"""
        if not hasattr(self, 'web_report_machine_combo'):
            return ""
        return self.web_report_machine_combo.currentText().strip()

    def _on_advanced_toggled(self, checked):
        """Apple 显示更多：平滑展开/收起高级参数。"""
        self.web_advanced_btn.setText(("▼ " if checked else "▶ ") + "高级参数")
        panel = self.web_advanced_panel
        panel.setVisible(True)
        anim = QPropertyAnimation(panel, b"maximumHeight", self)
        anim.setDuration(180)
        anim.setEasingCurve(QEasingCurve.InOutQuad)
        anim.setStartValue(0 if not checked else panel.maximumHeight())
        anim.setEndValue(170 if checked else 0)
        anim.finished.connect(
            lambda: panel.setVisible(False) if not checked else None
        )
        self._web_adv_anim = anim
        anim.start()

    def reset_web_report_time(self):
        """重置时间到默认窗口：昨天 06:00 ~ 今天 06:00。"""
        now = QDateTime.currentDateTime()
        begin = now.addDays(-1)
        begin.setTime(QTime(6, 0, 0))
        end = QDateTime(now.date(), QTime(6, 0, 0))
        self.web_report_begin_dt.setDateTime(begin)
        self.web_report_end_dt.setDateTime(end)

    def on_web_query_start(self):
        """查询开始：状态置为查询中，禁用输出报告。"""
        self.web_status_label.setText("● 查询中…")
        self.set_web_export_enabled(False)

    def on_web_query_done(self, data):
        """查询完成：回填状态栏/预览表格/计划时间，启用输出报告。"""
        record_count = int(data.get('record_count') or 0)
        machine_count = len(data.get('candidates') or [])
        self.web_status_label.setText(f"● 查询成功（{machine_count} 台机台）")
        self.web_count_label.setText(f"📋 数据行数：{record_count}")
        self.web_last_query_label.setText(
            f"🕒 最后查询：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        # 计划生产时间：留空则自动填充统计总时长（窗口小时），可手动覆盖
        if not self.web_report_planned_hours_edit.text().strip() and data.get('window_hours'):
            self.web_report_planned_hours_edit.setText(str(data['window_hours']))
        # 预览表格（前 5 行，避免信息过载）
        rows = (data.get('preview_rows') or [])[:5]
        self.web_preview_table.clear()
        if rows:
            headers = list(rows[0].keys())
            self.web_preview_table.setColumnCount(len(headers))
            self.web_preview_table.setHorizontalHeaderLabels(headers)
            self.web_preview_table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, key in enumerate(headers):
                    self.web_preview_table.setItem(i, j, QTableWidgetItem(str(row.get(key, ''))))
        else:
            self.web_preview_table.setColumnCount(0)
            self.web_preview_table.setRowCount(0)
        self.set_web_export_enabled(True)

    def set_web_export_enabled(self, enabled):
        if hasattr(self, 'web_export_btn'):
            btn = self.web_export_btn
            btn.setEnabled(enabled)
            btn.setProperty("success", True if enabled else False)
            btn.setText("✓ 输出报告" if enabled else "输出报告")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def restore_web_report_memory(self):
        """启动时恢复上一次关闭软件时的站位/机台号/时间等选择方案。"""
        mem = station_config.load_web_report_memory()
        if not mem:
            return
        station = str(mem.get('station') or '').strip()
        if station:
            self.web_station_combo.setCurrentText(station)
        machine_nos = mem.get('machine_nos')
        if machine_nos is not None:
            self.web_report_machine_combo.setCurrentText(str(machine_nos))
        self._last_machine_station = station  # 刷新时保留记忆的机台号
        for attr, key in (
            ('web_report_begin_dt', 'begin_time'),
            ('web_report_end_dt', 'end_time'),
        ):
            if mem.get(key):
                dt = QDateTime.fromString(str(mem[key]), "yyyy/MM/dd HH:mm:ss")
                if dt.isValid():
                    getattr(self, attr).setDateTime(dt)
        for attr, key in (
            ('web_report_api_url_edit', 'api_url'),
            ('web_report_plant_edit', 'plant_id'),
            ('web_report_head_edit', 'head'),
            ('web_report_planned_hours_edit', 'planned_hours'),
            ('web_report_pdt_edit', 'pdt_reason_ids'),
        ):
            if mem.get(key) is not None:
                getattr(self, attr).setText(str(mem[key]))

    # ── 模板/功能切换 ──────────────────────────────────────────
    def _on_template_changed(self, _index):
        self._apply_template()

    def _apply_template(self):
        """按当前制程模板预填各功能参数。"""
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
            sa = uph.get("step_analysis") or {}
            if sa.get("coefficient") is not None:
                self.uph_step_coef_spin.setValue(float(sa["coefficient"]))
            self.eff_planned_hours_edit.setText("" if not eff.get("planned_hours") else str(eff["planned_hours"]))
            self.eff_pdt_reason_edit.setText(str(eff.get("pdt_reason_ids") or ""))
            if hasattr(self, 'eff_source_combo'):
                self.eff_source_combo.setCurrentIndex(1 if eff.get("eff_source") == "web" else 0)
                for attr, key in (
                    ("web_api_url_edit", "web_api_url"),
                    ("web_plant_edit", "web_plant_id"),
                    ("web_machine_type_edit", "web_machine_type"),
                    ("web_machine_nos_edit", "web_machine_nos"),
                    ("web_begin_edit", "web_begin_time"),
                    ("web_end_edit", "web_end_time"),
                    ("web_head_edit", "web_head"),
                ):
                    if eff.get(key) is not None:
                        getattr(self, attr).setText(str(eff[key]))
            self.alarm_keywords_edit.setText(str(alarm.get("alarm_keywords") or DEFAULT_ALARM_KEYWORDS))
            if hasattr(self, 'reason_combo'):
                reason_device = str(tpl.get("reason_list") or "")
                if reason_device and self.reason_combo.findText(reason_device) >= 0:
                    self.reason_combo.setCurrentText(reason_device)
                else:
                    self.reason_combo.setCurrentIndex(0)
            filters = tpl.get("file_filters")
            self.custom_filter_edit.setText(", ".join(filters) if filters else "")

    def _on_feature_changed(self, index):
        self.param_stack.setCurrentIndex(index)
        for i, action in enumerate(self._feature_actions):
            action.setChecked(i == index)

    def closeEvent(self, event):
        """关闭软件前保存设备效能选择方案（站位/机台号/时间等）。"""
        if hasattr(self, 'controller') and hasattr(self.controller, 'save_web_report_memory'):
            self.controller.save_web_report_memory()
        super().closeEvent(event)

    # ── 对话框 ──────────────────────────────────────────────────
    def _show_about(self):
        QMessageBox.about(
            self,
            "关于",
            "设备效能分析工具 v1.0\n\n"
            "文档合并与内容拆分 / UPH分析 / EFF分析 / 报警分析 / 机台状态分析",
        )

    def _show_user_guide(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("使用说明")
        dialog.resize(760, 640)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(USER_GUIDE_HTML)
        layout.addWidget(browser, 1)
        close_btn = QPushButton("关闭")
        close_btn.setProperty("secondary", True)
        close_btn.clicked.connect(dialog.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(close_btn)
        btn_row.setContentsMargins(12, 8, 12, 12)
        layout.addLayout(btn_row)
        dialog.exec_()

    # ── 控制器回调 ──────────────────────────────────────────────
    def update_result(self, text):
        self.result_text.append(text)

    def update_web_report_result(self, text):
        if hasattr(self, 'web_report_result'):
            self.web_report_result.appendPlainText(
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}"
            )

    def show_progress(self, value=0):
        self.progress.setValue(value)
        self.progress.show()

    def update_progress(self, value):
        self.progress.setValue(value)

    def update_status(self, text):
        self.statusBar().showMessage(text)

    def hide_progress(self):
        self.progress.hide()

    def after(self, ms, callback):
        QTimer.singleShot(ms, callback)
