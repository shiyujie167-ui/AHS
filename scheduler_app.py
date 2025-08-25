import pandas as pd
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QLabel, QTableWidget, QHBoxLayout,
    QDateEdit, QComboBox, QSplitter, QTextEdit
)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView

from utils.DatabaseManager import DatabaseManager
from modules.employee_manager import EmployeeMixin
from modules.schedule_manager import ScheduleMixin

# ======= Main Application =======
class SchedulerApp(EmployeeMixin, ScheduleMixin, QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("排班助手 V3.3")
        self.resize(1280, 800)
        self.db = DatabaseManager()
        self.employee_df = pd.DataFrame()
        self.schedule_df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()

        central = QWidget()
        self.setCentralWidget(central)
        self.layout = QVBoxLayout(central)

        # 顶部工具栏
        top = QHBoxLayout()
        self.add_emp_btn = QPushButton("➕ 添加员工")
        self.add_emp_btn.clicked.connect(self.add_employee)
        self.import_btn = QPushButton("📥 导入员工")
        self.import_btn.clicked.connect(self.import_employees)
        self.clear_btn = QPushButton("🗑️ 清空数据")
        self.clear_btn.clicked.connect(self.clear_data)
        self.add_shift_btn = QPushButton("📝 添加排班")
        self.add_shift_btn.clicked.connect(self.add_shift)
        self.refresh_btn = QPushButton("🔄 刷新图表")
        self.refresh_btn.clicked.connect(self.plot_chart)
        self.export_btn = QPushButton("📤 导出排班")
        self.export_btn.clicked.connect(self.export_result)
        self.monthly_btn = QPushButton("📊 生成月度汇总")
        self.monthly_btn.clicked.connect(self.generate_monthly_summary)
        self.dept_filter = QComboBox()
        self.dept_filter.currentTextChanged.connect(self.filter_group)
        self.date_picker = QDateEdit(QDate.currentDate())
        self.date_picker.setCalendarPopup(True)
        self.date_picker.dateChanged.connect(self.filter_group)

        top.addWidget(self.add_emp_btn)
        top.addWidget(self.import_btn)
        top.addWidget(self.clear_btn)
        top.addWidget(self.add_shift_btn)
        top.addWidget(self.refresh_btn)
        top.addWidget(QLabel("部门："))
        top.addWidget(self.dept_filter)
        top.addWidget(QLabel("日期："))
        top.addWidget(self.date_picker)
        top.addWidget(self.export_btn)
        top.addWidget(self.monthly_btn)
        self.layout.addLayout(top)

        # 主表格和图表视图
        self.table = QTableWidget()
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.cellChanged.connect(self.handle_cell_change)
        self.layout.addWidget(self.table)

        # 创建图表和右侧支援信息区域
        self.webview = QWebEngineView()
        self.support_info_box = QTextEdit()
        self.support_info_box.setReadOnly(True)
        self.support_info_box.setMinimumWidth(300)
        self.support_info_box.setStyleSheet("font-size: 13px;")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.webview)
        splitter.addWidget(self.support_info_box)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        self.layout.addWidget(splitter)

        self.load_all()
        self.update_dept_filter()
        self.filter_group()

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.db.close()
        event.accept()
