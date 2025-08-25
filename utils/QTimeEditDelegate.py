from PyQt5.QtWidgets import (QTimeEdit, QStyledItemDelegate)
from PyQt5.QtCore import QDate, QUrl, Qt, QTime

class QTimeEditDelegate(QStyledItemDelegate):
    """用于在表格中编辑时间的委托类"""

    def createEditor(self, parent, option, index):
        editor = QTimeEdit(parent)
        editor.setDisplayFormat("HH:mm")
        editor.setTime(QTime.currentTime())
        return editor

    def setEditorData(self, editor, index):
        time_str = index.model().data(index, Qt.EditRole)
        try:
            time_obj = QTime.fromString(time_str, "HH:mm")
            if time_obj.isValid():
                editor.setTime(time_obj)
        except:
            pass

    def setModelData(self, editor, model, index):
        model.setData(index, editor.time().toString("HH:mm"), Qt.EditRole)

