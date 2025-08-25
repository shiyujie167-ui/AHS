from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QComboBox, QDateEdit, QMessageBox, QCompleter
from PyQt5.QtCore import QDate, Qt

class AddShiftDialog(QDialog):
    def __init__(self, name_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加排班记录")
        self.resize(400, 150)
        layout = QVBoxLayout()

        # 姓名输入框 + 自动补全
        self.name_edit = QLineEdit()
        completer = QCompleter(name_list)
        completer.setFilterMode(Qt.MatchContains)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.name_edit.setCompleter(completer)
        layout.addWidget(QLabel("姓名："))
        layout.addWidget(self.name_edit)

        # 日期选择
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        layout.addWidget(QLabel("日期："))
        layout.addWidget(self.date_edit)

        # 班次输入
        self.shift_edit = QLineEdit()
        self.shift_edit.setPlaceholderText("例如 09:00-18:00")
        layout.addWidget(QLabel("班次："))
        layout.addWidget(self.shift_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.cancel_btn = QPushButton("取消")
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # 绑定事件
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

    def get_data(self):
        return {
            "姓名": self.name_edit.text().strip(),
            "日期": self.date_edit.date().toString("yyyy-MM-dd"),
            "班次": self.shift_edit.text().strip(),
            "午餐时间": "",
            "晚餐时间": "",
            "请假时间段": "",
            "放休时间段": "",
            "加班时间段": "",
            "加班2时间段": ""
        }
