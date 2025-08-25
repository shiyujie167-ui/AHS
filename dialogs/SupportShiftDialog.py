from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QComboBox,
    QLineEdit, QPushButton, QMessageBox
)

class SupportShiftDialog(QDialog):
    def __init__(self, employee_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加支援时间段")
        self.resize(300, 150)
        self.employee_name = employee_name

        layout = QVBoxLayout(self)

        self.dept_combo = QComboBox()
        self.dept_combo.addItems(["回收400", "回收在线", "合力在线", "其他"])

        self.time_edit = QLineEdit()
        self.time_edit.setPlaceholderText("例如：13:00-17:00")

        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.validate_and_accept)

        layout.addWidget(QLabel(f"为员工 {employee_name} 添加支援："))
        layout.addWidget(QLabel("支援部门："))
        layout.addWidget(self.dept_combo)
        layout.addWidget(QLabel("支援时间段："))
        layout.addWidget(self.time_edit)
        layout.addWidget(self.ok_btn)

    def validate_and_accept(self):
        if "-" not in self.time_edit.text():
            QMessageBox.warning(self, "格式错误", "请使用格式 13:00-17:00")
            return
        self.accept()

    def get_data(self):
        return self.dept_combo.currentText(), self.time_edit.text().strip()
