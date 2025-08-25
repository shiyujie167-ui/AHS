import sys
from PyQt5.QtWidgets import QApplication
from scheduler_app import SchedulerApp

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SchedulerApp()
    window.show()
    sys.exit(app.exec_())
