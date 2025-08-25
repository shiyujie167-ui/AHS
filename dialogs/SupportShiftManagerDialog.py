from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QComboBox, QMessageBox
)
from PyQt5.QtCore import Qt

def normalize_time_format(tstr):
    """标准化时间格式为HH:MM"""
    if not isinstance(tstr, str):
        tstr = str(tstr) if tstr is not None else ""
    tstr = tstr.strip()
    if not tstr:
        return ""
    import re
    # 补全纯数字小时为 :00
    if re.match(r'^\d{1,2}$', tstr):
        tstr = tstr + ":00"
    parts = tstr.split(":")
    if len(parts) >= 2 and len(parts[0]) == 1:
        parts[0] = "0" + parts[0]
    tstr_norm = ":".join(parts)
    try:
        from datetime import datetime
        dt = datetime.strptime(tstr_norm, "%H:%M")
        return dt.strftime("%H:%M")
    except:
        return tstr_norm

class SupportShiftManagerDialog(QDialog):
    def __init__(self, name, account, date, support_data, parent=None, source_dept="", employee_type=""):
        super().__init__(parent)
        self.employee_type = employee_type
        self.source_dept = source_dept
        self.setWindowTitle(f"{name} - {date} 支援信息管理")
        self.resize(600, 300)
        self.name = name
        self.account = account
        self.date = date
        self.support_data = support_data

        self.layout = QVBoxLayout(self)

        self.table = QTableWidget(len(support_data), 2)
        self.table.setHorizontalHeaderLabels(["支援部门", "支援时间段"])

        departments = ["合力在线", "回收在线", "回收400", "客诉", "协商", "带教", "其他"]

        for row, entry in enumerate(support_data):
            combo = QComboBox()
            combo.addItems(departments)
            current_dept = entry["support_dept"]
            if current_dept in departments:
                combo.setCurrentText(current_dept)
            self.table.setCellWidget(row, 0, combo)
            self.table.setItem(row, 1, QTableWidgetItem(entry["support_interval"]))

        self.layout.addWidget(self.table)

        # 绑定实时格式化逻辑
        self.table.cellChanged.connect(self.on_cell_changed)

        buttons = QHBoxLayout()
        self.btn_add = QPushButton("➕ 添加")
        self.btn_delete = QPushButton("🗑 删除")
        self.btn_save = QPushButton("💾 保存")
        buttons.addWidget(self.btn_add)
        buttons.addWidget(self.btn_delete)
        buttons.addWidget(self.btn_save)
        self.layout.addLayout(buttons)

        self.btn_add.clicked.connect(self.add_row)
        self.btn_delete.clicked.connect(self.delete_row)
        self.btn_save.clicked.connect(self.accept)

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        departments = ["合力在线", "回收在线", "回收400", "客诉", "协商", "带教", "其他"]
        combo = QComboBox()
        combo.addItems(departments)
        self.table.setCellWidget(row, 0, combo)
        self.table.setItem(row, 1, QTableWidgetItem(""))

    def delete_row(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def on_cell_changed(self, row, col):
        # 只处理“支援时间段”列
        if col == 1:
            item = self.table.item(row, col)
            if item:
                raw = item.text()
                if "-" in raw:
                    try:
                        parts = raw.split("-")
                        if len(parts) == 2:
                            start = normalize_time_format(parts[0])
                            end = normalize_time_format(parts[1])
                            formatted = f"{start}-{end}"
                            if raw != formatted:
                                self.table.blockSignals(True)
                                item.setText(formatted)
                                self.table.blockSignals(False)
                    except:
                        pass

    def get_updated_records(self):
        updated = []
        for row in range(self.table.rowCount()):
            dept_widget = self.table.cellWidget(row, 0)
            time_item = self.table.item(row, 1)
            dept = dept_widget.currentText().strip() if dept_widget else ""
            interval = time_item.text().strip() if time_item else ""

            if dept and interval:
                updated.append({
                    "name": self.name,
                    "account": self.account,
                    "date": self.date,
                    "support_dept": dept,
                    "support_interval": interval,
                    "source_dept": self.source_dept,
                    "employee_type": self.employee_type
                })
        return updated
