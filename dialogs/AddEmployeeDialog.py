from PyQt5.QtWidgets import (QPushButton, QComboBox, QDialog, QLineEdit, QFormLayout,)


class AddEmployeeDialog(QDialog):
    """添加员工对话框"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加员工")
        self.layout = QFormLayout()
        self.setLayout(self.layout)
        self.name_input = QLineEdit()
        self.id_input = QLineEdit()
        self.dept_input = QLineEdit()
        self.group_input = QComboBox()
        self.group_input.addItems(["A组", "B组"])
        self.type_input = QComboBox()
        self.type_input.addItems(["正式", "试用期"])
        self.eff_input = QLineEdit()
        self.eff_input.setText("15")
        self.layout.addRow("姓名：", self.name_input)
        self.layout.addRow("工号：", self.id_input)
        self.layout.addRow("部门：", self.dept_input)
        self.layout.addRow("分组：", self.group_input)
        self.layout.addRow("员工类型：", self.type_input)
        self.layout.addRow("人效（默认15）：", self.eff_input)
        self.submit_btn = QPushButton("添加")
        self.submit_btn.clicked.connect(self.accept)
        self.layout.addRow(self.submit_btn)

    def get_data(self):
        return {
            "姓名": self.name_input.text(),
            "工号": self.id_input.text(),
            "部门": self.dept_input.text(),
            "分组": self.group_input.currentText(),
            "员工类型": self.type_input.currentText(),
            "人效": self.eff_input.text() or "15"
        }