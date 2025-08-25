import sys
import os
import pandas as pd
import pymysql
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton,
    QFileDialog, QLabel, QTableWidget, QTableWidgetItem, QHBoxLayout,
    QDateEdit, QMessageBox, QComboBox, QMenu, QInputDialog,
    QSplitter, QTextEdit
)
from PyQt5.QtCore import QDate, QUrl, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView
from pyecharts.charts import Line
from pyecharts import options as opts
from utils.DatabaseManager import DatabaseManager
from dialogs.AddEmployeeDialog import AddEmployeeDialog
from dialogs.AddShiftDialog import AddShiftDialog
from utils.utils import *

# ======= Main Application =======
class SchedulerApp(QMainWindow):
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

    def load_all(self):
        self.employee_df = self.db.get_employees()
        self.schedule_df = self.db.get_schedules()

        if not self.employee_df.empty:
            self.employee_df.rename(columns={
                "name": "姓名",
                "employee_id": "工号",
                "account": "账号",      
                "department": "部门",
                "group_name": "分组",
                "employee_type": "员工类型",
                "region": "地区",
                "efficiency": "人效"
            }, inplace=True)

        if not self.schedule_df.empty:
            required_columns = ["姓名", "日期", "班次", "午餐时间", "晚餐时间",
                                "请假时间段", "放休时间段", "加班时间段", "加班2时间段","部门", "人效", "地区"]
            for col in required_columns:
                if col not in self.schedule_df.columns:
                    self.schedule_df[col] = ""

            # 调整列顺序：将地区放最前
            cols = self.schedule_df.columns.tolist()
            if "地区" in cols:
                cols = ["地区"] + [c for c in cols if c != "地区"]
                self.schedule_df = self.schedule_df[cols]


    def update_dept_filter(self):
        """更新部门筛选器的选项"""
        if not self.employee_df.empty and "部门" in self.employee_df.columns:
            depts = sorted(self.employee_df["部门"].dropna().unique().tolist())
        else:
            depts = []
        self.dept_filter.clear()
        self.dept_filter.addItem("全部")
        self.dept_filter.addItems(depts)

    def import_employees(self):
        """从Excel文件导入员工数据"""
        file_path, _ = QFileDialog.getOpenFileName(self, "导入新版员工排班表", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            try:
                df = pd.read_excel(file_path, dtype=str)
                df.fillna("", inplace=True)

                # 识别日期列（从"4月1号"开始的列）
                date_cols = [col for col in df.columns if "月" in str(col) and "号" in str(col)]

                # 检查基础信息字段
                required_fields = ["团队", "员工类型", "工号", "账号", "姓名"]
                for field in required_fields:
                    if field not in df.columns:
                        QMessageBox.warning(self, "格式错误", f"缺少必要列：{field}")
                        return

                emp_rows = []
                sched_rows = []


                for _, row in df.iterrows():
                    dept = row.get("部门", "")
                    emp_type = row.get("员工类型", "")
                    eff_val = self.db.get_efficiency_by_mapping(dept, emp_type)

                    emp_rows.append({
                        "姓名": row["姓名"],
                        "工号": row["工号"],
                        "账号": row["账号"], 
                        "部门": dept,
                        "分组": row.get("团队", ""),
                        "员工类型": emp_type,
                        "人效": eff_val,
                        "地区": row.get("地区", "")
                    })

                    for col in date_cols:
                        shift_raw = str(row[col]).strip()
                        if shift_raw == "" or shift_raw.upper() == "R":
                            continue
                        shift = normalize_shift(shift_raw)
                        try:
                            # 将"4月1号"这种字符串转为日期
                            date_obj = pd.to_datetime("2025年" + col, format="%Y年%m月%d号", errors="coerce")
                            if pd.isna(date_obj):
                                continue
                            sched_rows.append({
                                "姓名": row["姓名"],
                                "账号": row["账号"],        # ✅ 添加这行
                                "工号": row["工号"], 
                                "日期": date_obj.strftime("%Y-%m-%d"),
                                "班次": shift,
                                "午餐时间": "",
                                "晚餐时间": "",
                                "请假时间段": "",
                                "放休时间段": "",
                                "加班时间段": "",
                                "加班2时间段": ""
                            })
                        except:
                            continue

                # 批量导入员工数据
                for emp in emp_rows:
                    self.db.add_employee(emp)

                # 批量导入排班数据
                for sched in sched_rows:
                    self.db.add_schedule(sched)

                self.load_all()
                self.update_dept_filter()
                self.filter_group()
                QMessageBox.information(self, "导入成功", "新版排班表导入成功！")

            except Exception as e:
                QMessageBox.critical(self, "导入失败", f"发生错误：{e}")

    def add_employee(self):
        """添加新员工"""
        dialog = AddEmployeeDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            data["人效"] = self.db.get_efficiency_by_mapping(
                data.get("部门", ""),
                data.get("员工类型", "")
            )
            if self.db.add_employee(data):
                self.load_all()
                self.update_dept_filter()
                self.filter_group()
            else:
                QMessageBox.warning(self, "错误", "添加员工失败")

    def add_shift(self):
        """添加排班记录"""
        dialog = AddShiftDialog(self.employee_df["姓名"].tolist(), self)
        if dialog.exec_():
            data = dialog.get_data()
            if not data["姓名"]:
                QMessageBox.warning(self, "错误", "请输入姓名")
                return

            # ✅ 先查员工信息，补全字段
            emp_info = self.employee_df[self.employee_df["姓名"] == data["姓名"]]
            if emp_info.empty:
                QMessageBox.warning(self, "错误", "未找到该员工信息")
                return
            data["账号"] = emp_info["账号"].values[0]
            data["工号"] = emp_info["工号"].values[0]
            data["部门"] = emp_info["部门"].values[0]
            data["人效"] = emp_info["人效"].values[0]
            data["地区"] = emp_info["地区"].values[0]

            # 班次处理
            raw_shift = data["班次"].strip()
            if raw_shift:
                try:
                    data["班次"] = normalize_shift(raw_shift)
                except Exception:
                    data["班次"] = raw_shift

            # 添加到数据库
            if self.db.add_schedule(data):
                self.load_all()
                self.filter_group()
            else:
                QMessageBox.warning(self, "错误", "添加排班失败")



    def clear_data(self):
        """清空所有数据"""
        reply = QMessageBox.question(self, "确认清空", "是否清空所有员工和排班数据？", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.clear_all_data():
                self.employee_df = pd.DataFrame()
                self.schedule_df = pd.DataFrame()
                self.update_dept_filter()
                self.filter_group()
            else:
                QMessageBox.warning(self, "错误", "清空数据失败")

    def export_result(self):
        """导出排班数据到Excel"""
        out, _ = QFileDialog.getSaveFileName(self, "导出排班", "排班统计.xlsx", "Excel Files (*.xlsx)")
        if out:
            self.schedule_df.to_excel(out, index=False)
            QMessageBox.information(self, "成功", "导出成功！")


    def handle_cell_change(self, row, col):
        """处理表格单元格内容变更"""
        try:
            df = self.filtered_df
            headers = df.columns.tolist()
            key = headers[col]
            value = self.table.item(row, col).text()
            index = df.index[row]

            if key == "人效":
                name = df.at[index, "姓名"]
                self.employee_df.loc[self.employee_df["姓名"] == name, "人效"] = value
                self.db.add_employee({
                    "姓名": name,
                    "工号": self.employee_df.loc[self.employee_df["姓名"] == name, "工号"].values[0],
                    "部门": self.employee_df.loc[self.employee_df["姓名"] == name, "部门"].values[0],
                    "分组": self.employee_df.loc[self.employee_df["姓名"] == name, "分组"].values[0],
                    "员工类型": self.employee_df.loc[self.employee_df["姓名"] == name, "员工类型"].values[0],
                    "人效": value,
                    "地区": self.employee_df.loc[self.employee_df["姓名"] == name, "地区"].values[0]
                })

            elif key in ["午餐时间", "晚餐时间"]:
                norm_time = normalize_time_format(value)
                self.schedule_df.at[index, key] = norm_time
                self.table.item(row, col).setText(norm_time)
                self.db.add_schedule({
                    "姓名": df.at[index, "姓名"],
                    "日期": df.at[index, "日期"],
                    "班次": df.at[index, "班次"],
                    "午餐时间": norm_time if key == "午餐时间" else df.at[index, "午餐时间"],
                    "晚餐时间": norm_time if key == "晚餐时间" else df.at[index, "晚餐时间"],
                    "请假时间段": df.at[index, "请假时间段"],
                    "放休时间段": df.at[index, "放休时间段"],
                    "加班时间段": df.at[index, "加班时间段"],
                    "加班2时间段": df.at[index, "加班2时间段"]
                })

            elif key == "班次":
                norm_shift = normalize_shift(value)
                self.schedule_df.at[index, key] = norm_shift
                self.table.item(row, col).setText(norm_shift)
                self.db.add_schedule({
                    "姓名": df.at[index, "姓名"],
                    "日期": df.at[index, "日期"],
                    "班次": norm_shift,
                    "午餐时间": df.at[index, "午餐时间"],
                    "晚餐时间": df.at[index, "晚餐时间"],
                    "请假时间段": df.at[index, "请假时间段"],
                    "放休时间段": df.at[index, "放休时间段"],
                    "加班时间段": df.at[index, "加班时间段"],
                    "加班2时间段": df.at[index, "加班2时间段"]
                })

            elif key in ["请假时间段", "放休时间段", "加班时间段", "加班2时间段"]:
                norm_parts = [normalize_time_format(p) for p in value.split("-")]
                if len(norm_parts) == 2:
                    norm_interval = "-".join(norm_parts)
                else:
                    norm_interval = ""
                self.schedule_df.at[index, key] = norm_interval
                self.table.item(row, col).setText(norm_interval)

                schedule_data = {
                    "姓名": df.at[index, "姓名"],
                    "日期": df.at[index, "日期"],
                    "班次": df.at[index, "班次"],
                    "午餐时间": df.at[index, "午餐时间"],
                    "晚餐时间": df.at[index, "晚餐时间"],
                    "请假时间段": norm_interval if key == "请假时间段" else df.at[index, "请假时间段"],
                    "放休时间段": norm_interval if key == "放休时间段" else df.at[index, "放休时间段"],
                    "加班时间段": norm_interval if key == "加班时间段" else df.at[index, "加班时间段"],
                    "加班2时间段": norm_interval if key == "加班2时间段" else df.at[index, "加班2时间段"]
                }
                self.db.add_schedule(schedule_data)

            else:
                self.schedule_df.at[index, key] = value

            self.filter_group()

        except Exception as e:
            print(f"修改失败: {e}")

    def show_context_menu(self, pos):
        """显示表格右键菜单"""
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        menu = QMenu()
        support_action = menu.addAction("🛠 添加/修改支援信息")
        delete_action = menu.addAction("🗑️ 删除该排班记录")
        export_action = menu.addAction("📤 导出该员工所有工作记录")
        action = menu.exec_(self.table.viewport().mapToGlobal(pos))
        if action == delete_action:
            self.delete_row(row)
        elif action == export_action:
            self.export_employee_schedule(row)
        elif action == support_action:
            self.manage_support_shift(row)


    def manage_support_shift(self, row):
        df = self.filtered_df if not self.filtered_df.empty else self.schedule_df
        try:
            index = df.index[row]
            name = df.at[index, "姓名"]
            account = df.at[index, "账号"]
            date = df.at[index, "日期"]

            # 获取原所属部门和员工类型
            source_row = self.employee_df[self.employee_df["姓名"] == name]
            source_dept = source_row["部门"].values[0] if not source_row.empty else ""
            employee_type = source_row["员工类型"].values[0] if not source_row.empty else ""

            # 获取已有支援信息
            existing = self.db.get_support_shifts_by_account_and_date(account, date)

            # 传递 employee_type 给对话框
            from dialogs.SupportShiftManagerDialog import SupportShiftManagerDialog
            dialog = SupportShiftManagerDialog(name, account, date, existing, self, source_dept, employee_type)

            if dialog.exec_():
                updated_records = dialog.get_updated_records()
                self.db.delete_support_shifts_by_account_and_date(account, date)
                for r in updated_records:
                    self.db.add_support_shift(**r)
                QMessageBox.information(self, "成功", "支援信息已更新")
                self.plot_chart()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"管理支援信息失败：{e}")

    def delete_row(self, row):
        """删除选中的排班记录"""
        df = self.filtered_df if not self.filtered_df.empty else self.schedule_df
        try:
            employee_name = df.at[df.index[row], "姓名"]
            date = df.at[df.index[row], "日期"]
            if self.db.delete_schedule(employee_name, date):
                self.load_all()
                self.filter_group()
            else:
                QMessageBox.warning(self, "错误", "删除排班记录失败")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"删除失败：{e}")

    def export_employee_schedule(self, row):
        """导出指定员工的所有排班记录"""
        df = self.filtered_df if not self.filtered_df.empty else self.schedule_df
        try:
            employee_name = df.at[df.index[row], "姓名"]
            # 从数据库获取该员工的所有排班记录
            query = """
                SELECT 
                    s.date AS 日期,
                    s.shift AS 班次,
                    s.lunch_time AS 午餐时间,
                    s.dinner_time AS 晚餐时间,
                    s.leave_interval AS 请假时间段,
                    s.off_interval AS 放休时间段,
                    s.overtime_interval AS 加班时间段,
                    s.overtime_interval2 AS 加班2时间段
                FROM schedules s
                WHERE s.employee_name = %s
                ORDER BY s.date
            """
            cursor = self.db.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, (employee_name,))
            result = cursor.fetchall()
            cursor.close()

            if not result:
                QMessageBox.information(self, "提示", f"{employee_name} 没有排班记录")
                return

            emp_sched = pd.DataFrame(result)
            out, _ = QFileDialog.getSaveFileName(self, f"导出 {employee_name} 的工作记录", f"{employee_name}_工作记录.xlsx",
                                                 "Excel Files (*.xlsx)")
            if out:
                emp_sched.to_excel(out, index=False)
                QMessageBox.information(self, "成功", f"{employee_name} 的工作记录导出成功！")
        except Exception as e:
            QMessageBox.warning(self, "错误", f"导出失败：{e}")

    def filter_group(self):
        """根据筛选条件过滤数据"""
        dept = self.dept_filter.currentText()
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")

        # 从数据库获取筛选后的数据
        query = """
            SELECT 
                e.region AS 地区,
                e.name AS 姓名,
                e.account AS 账号, 
                s.date AS 日期,
                s.shift AS 班次,
                s.lunch_time AS 午餐时间,
                s.dinner_time AS 晚餐时间,
                s.leave_interval AS 请假时间段,
                s.off_interval AS 放休时间段,
                s.overtime_interval AS 加班时间段,
                s.overtime_interval2 AS 加班2时间段,
                e.department AS 部门,
                e.efficiency AS 人效
            FROM schedules s
            JOIN employees e ON s.employee_name = e.name
            WHERE s.date = %s
        """
        params = [selected_date]

        if dept != "全部":
            query += " AND e.department = %s"
            params.append(dept)

        try:
            cursor = self.db.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, tuple(params))
            result = cursor.fetchall()
            cursor.close()
            self.filtered_df = pd.DataFrame(result)
            self.populate_table()
            self.plot_chart()#
        except Exception as e:
            print(f"筛选数据时出错: {e}")
            self.filtered_df = pd.DataFrame()
            self.populate_table()

    def populate_table(self):
        """将数据填充到表格中"""
        df = self.filtered_df.copy()
        self.table.blockSignals(True)
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns.astype(str).tolist())
        for row in range(len(df)):
            for col in range(len(df.columns)):
                self.table.setItem(row, col, QTableWidgetItem(str(df.iloc[row, col])))
        self.table.blockSignals(False)
        # ✅ 隐藏不需要显示的列（如：账号）
        hidden_columns = ["账号"]
        for col in hidden_columns:
            if col in df.columns:
                col_index = df.columns.get_loc(col)
                self.table.setColumnHidden(col_index, True)

    def is_slot_working(self, row, slot_start, slot_end):
        """判断指定时间段是否在工作"""
        try:
            shift_time = row.get("班次", "").strip()
            if "-" not in shift_time:
                raise ValueError(f"班次格式错误：{shift_time}")
            shift_start_str, shift_end_str = shift_time.split("-")
            
            s = datetime.strptime(shift_start_str.strip(), "%H:%M")
            e = datetime.strptime(shift_end_str.strip(), "%H:%M") if shift_end_str.strip() != "24:00" else datetime.strptime("00:00", "%H:%M") + timedelta(days=1)
            

            # 将午餐、晚餐时间转换为区间，默认30分钟
            lunch_interval = parse_single_time_as_interval(row.get("午餐时间", ""), duration_minutes=30)
            dinner_interval = parse_single_time_as_interval(row.get("晚餐时间", ""), duration_minutes=30)

            # 获取请假、放休、加班时间段（都是字符串形式）
            leave_interval = row.get("请假时间段", "").strip()
            off_interval = row.get("放休时间段", "").strip()
            overtime_interval = row.get("加班时间段", "").strip()

            overtime_interval2 = row.get("加班2时间段", "").strip()
            if (overtime_interval and slot_in_interval(slot_start, slot_end, overtime_interval)) or \
            (overtime_interval2 and slot_in_interval(slot_start, slot_end, overtime_interval2)):
                return True

            # 若当前时间段完全不在班次内，直接返回 False
            if e <= slot_start or s >= slot_end:
                return False

            # 判断是否落在午餐、晚餐、请假或放休时间内
            intervals_to_exclude = [lunch_interval, dinner_interval, leave_interval, off_interval]
            for interval in intervals_to_exclude:
                if interval and slot_in_interval(slot_start, slot_end, interval):
                    return False  # 被排除区间覆盖，则视为不在岗

            # 正常工作时间段内，且不在排除区间，则视为在岗
            return True

        except Exception as e:
            print(f"[ERROR] is_slot_working 判断失败: {e}")
            return False

    def plot_chart(self):
        """绘制在岗人数和人效曲线图"""
        selected_date = self.date_picker.date().toString("yyyy-MM-dd")
        merged = self.filtered_df
        selected_dept = self.dept_filter.currentText()

        # ========== 如果没有数据，显示空图表 ==========
        if merged.empty:
            line = (
                Line()
                .add_xaxis([])
                .add_yaxis("在岗人数", [])
                .add_yaxis("人效曲线", [])
                .set_global_opts(
                    title_opts=opts.TitleOpts(title=f"{selected_date} 无排班数据"),
                    xaxis_opts=opts.AxisOpts(type_="category", name="时间"),
                    yaxis_opts=opts.AxisOpts(type_="value", name="人数 / 人效")
                )
            )
            html = "chart_v2.4.html"
            line.render(html)
            with open(html, "r", encoding="utf-8") as f:
                html_content = f.read()
            html_content = html_content.replace('style="width:600px;height:400px;"', 'style="width:100%;height:500px;"')
            html_content = html_content.replace('"width":"600px"', '"width":"100%"')
            with open(html, "w", encoding="utf-8") as f:
                f.write(html_content)
            self.webview.load(QUrl.fromLocalFile(os.path.abspath(html)))
            return

        # ========== 确定时间范围 ==========
        earliest_time, latest_time = None, None
        for _, row in merged.iterrows():
            try:
                shift_start, shift_end = row.get("班次", "").split("-")
                s = datetime.strptime(shift_start.strip(), "%H:%M")
                e = datetime.strptime(shift_end.strip(), "%H:%M") if shift_end.strip() != "24:00" else datetime.strptime("00:00", "%H:%M") + timedelta(days=1)

                if earliest_time is None or s < earliest_time:
                    earliest_time = s
                if latest_time is None or e > latest_time:
                    latest_time = e

                for key in ["加班时间段", "加班2时间段"]:
                    ot = row.get(key, "").strip()
                    if ot:
                        _, ot_end = ot.split("-")
                        ot_e = datetime.strptime(ot_end.strip(), "%H:%M")
                        if ot_end.strip() == "24:00":
                            ot_e += timedelta(days=1)
                        if ot_e > latest_time:
                            latest_time = ot_e
            except:
                continue

        if earliest_time is None or latest_time is None:
            earliest_time = datetime.strptime("08:00", "%H:%M")
            latest_time = datetime.strptime("19:00", "%H:%M")

        earliest_time = floor_to_half_hour(earliest_time)
        latest_time = ceil_to_half_hour(latest_time)

        # ========== 生成时间标签 ==========
        time_labels = []
        t = earliest_time
        while t <= latest_time:
            time_labels.append(t.strftime("%H:%M"))
            t += timedelta(minutes=30)

        # ========== 初始化支援调整数组 ==========
        support_adjustments = [0] * len(time_labels)
        efficiency_adjustments = [0.0] * len(time_labels)

        # ========== 支援逻辑处理 ==========
        support_records = self.db.get_support_shifts_by_date(selected_date)
        support_meal_map = {}
        try:
            cursor = self.db.connection.cursor(pymysql.cursors.DictCursor)
            accounts = [r["account"] for r in support_records]
            if accounts:
                placeholder = ','.join(['%s'] * len(accounts))
                query = f"""
                    SELECT account, date, lunch_time, dinner_time 
                    FROM schedules 
                    WHERE account IN ({placeholder}) AND date = %s
                """
                cursor.execute(query, (*accounts, selected_date))
                rows = cursor.fetchall()
                for row in rows:
                    lunch_interval = parse_single_time_as_interval(row.get("lunch_time", ""), duration_minutes=30)
                    dinner_interval = parse_single_time_as_interval(row.get("dinner_time", ""), duration_minutes=30)
                    support_meal_map[(row["account"], selected_date)] = (lunch_interval, dinner_interval)
            cursor.close()
        except Exception as e:
            print(f"[ERROR] 获取支援员工午餐晚餐信息失败: {e}")
        eff_map = self.db.get_efficiency_mapping()

        for record in support_records:
            acc = record["account"]
            support_dept = record["support_dept"]
            interval = record["support_interval"]
            emp_type = record["employee_type"]
            source_dept = record.get("source_dept", "")

            if selected_dept not in [support_dept, source_dept]:
                continue

            eff_support = eff_map.get((support_dept, emp_type), 15)
            eff_source = eff_map.get((source_dept, emp_type), 15)

            # 取出该员工当日的午餐/晚餐区间
            lunch_interval, dinner_interval = support_meal_map.get((acc, selected_date), (None, None))

            for i, label in enumerate(time_labels):
                slot_start = datetime.strptime(label, "%H:%M")
                slot_end = slot_start + timedelta(minutes=15)

                # 不在支援时间段内就跳过
                if not slot_in_interval(slot_start, slot_end, interval):
                    continue

                # 如果支援人在吃饭，就跳过
                if (lunch_interval and slot_in_interval(slot_start, slot_end, lunch_interval)) or \
                (dinner_interval and slot_in_interval(slot_start, slot_end, dinner_interval)):
                    continue

                if selected_dept == support_dept:
                    support_adjustments[i] += 1
                    efficiency_adjustments[i] += eff_support
                elif selected_dept == source_dept:
                    support_adjustments[i] -= 1
                    efficiency_adjustments[i] -= eff_source

        # ========== 统计在岗人数和人效 ==========
        onsite = []
        efficiency = []
        for i, label in enumerate(time_labels):
            slot_start = datetime.strptime(label, "%H:%M")
            slot_end = slot_start + timedelta(minutes=15)
            count = 0
            total_eff = 0
            for _, row in merged.iterrows():
                if self.is_slot_working(row, slot_start, slot_end):
                    count += 1
                    try:
                        total_eff += float(row.get("人效", "15"))
                    except:
                        total_eff += 15
            onsite.append(count + support_adjustments[i])

            efficiency.append(int(round(total_eff + efficiency_adjustments[i])))


        # ========== 查询预测量数据 ==========
        predict_y = []
        predict_table = None
        if selected_dept == "回收在线":
            predict_table = "咚咚预测拆分"
        elif selected_dept == "回收400":
            predict_table = "400预测拆分"

        if predict_table:
            try:
                cursor = self.db.connection.cursor(pymysql.cursors.DictCursor)
                query = f"SELECT * FROM `{predict_table}` WHERE 日期 = %s"
                cursor.execute(query, (selected_date,))
                result = cursor.fetchone()
                cursor.close()
                if result:
                    for label in time_labels:
                        value = result.get(label, None)
                        predict_y.append(int(value) if value is not None else None)
                else:
                    predict_y = [None] * len(time_labels)
            except Exception as e:
                print(f"[ERROR] 查询预测量失败: {e}")
                predict_y = [None] * len(time_labels)
        else:
            predict_y = [None] * len(time_labels)

        # 计算该部门的最高人效（用于估算人力缺口）
        dept_max_eff = 15  # 默认
        dept_eff = self.employee_df[self.employee_df["部门"] == selected_dept]
        if not dept_eff.empty:
            try:
                dept_max_eff = dept_eff["人效"].astype(float).max()
            except:
                pass

        # 计算人力缺口（预测量 - 实际人效） / 最高人效
        manpower_gap = []
        for pred, actual_eff in zip(predict_y, efficiency):
            if pred is None:
                manpower_gap.append(None)
            else:
                gap = (pred - actual_eff) / dept_max_eff
                manpower_gap.append(round(gap, 2))


        # === 新的“人力差值”逻辑：冗余为正，缺口为负 ===
        manpower_delta = []
        for pred, actual_eff in zip(predict_y, efficiency):
            if pred is None:
                manpower_delta.append(None)
            else:
                manpower_delta.append(round((actual_eff - pred) / dept_max_eff, 2))




        # ========== 绘图 ==========

                
        from pyecharts.commons.utils import JsCode

        label_option_gap = opts.LabelOpts(
            is_show=True,
            position="top",
            formatter=JsCode("""
                function(params) {
                    return (params.dataIndex % 5 === 0) ? params.value : '';
                }
            """)
        )

        line = Line(init_opts=opts.InitOpts(width="100%", height="500px"))
        line.add_xaxis(time_labels)
        line.add_yaxis("在岗人数", onsite, is_smooth=True, label_opts=opts.LabelOpts(is_show=False))
        line.add_yaxis("人效曲线", efficiency, is_smooth=True, label_opts=opts.LabelOpts(is_show=False))

        if any(predict_y):
            line.add_yaxis(
                "预估进线量", predict_y, is_smooth=True,
                linestyle_opts=opts.LineStyleOpts(type_="dashed"),
                label_opts=opts.LabelOpts(is_show=False)
            )

        if any(manpower_gap):
            line.extend_axis(
                yaxis=opts.AxisOpts(
                    type_="value",
                    name="人力缺口",
                    position="right",
                    offset=60,
                    axisline_opts=opts.AxisLineOpts(),
                    axislabel_opts=opts.LabelOpts(formatter="{value}")
                )
            )
            line.add_yaxis(
                "人力缺口",
                manpower_gap,
                is_smooth=True,
                yaxis_index=1,
                linestyle_opts=opts.LineStyleOpts(type_="dotted"),
                label_opts=label_option_gap  # ✅ 只在人力缺口上加标签
            )

                
        line = Line(init_opts=opts.InitOpts(width="100%", height="500px"))
        line.add_xaxis(time_labels)
        line.add_yaxis("在岗人数", onsite, is_smooth=True)
        line.add_yaxis("人效曲线", efficiency, is_smooth=True)

        if any(predict_y):
            line.add_yaxis("预估进线量", predict_y, is_smooth=True, linestyle_opts=opts.LineStyleOpts(type_="dashed"))

        if any(manpower_gap):
            line.extend_axis(
                yaxis=opts.AxisOpts(
                    type_="value",
                    name="人力缺口",
                    position="right",
                    offset=60,
                    axisline_opts=opts.AxisLineOpts(),
                    axislabel_opts=opts.LabelOpts(formatter="{value}")
                )
            )
            line.add_yaxis(
                "人力缺口",
                manpower_gap,
                is_smooth=True,
                yaxis_index=1,
                linestyle_opts=opts.LineStyleOpts(type_="dotted")
            )

        line.set_global_opts(
            title_opts=opts.TitleOpts(title=f"{selected_date} 在岗人数 & 人效 & 预测量"),
            tooltip_opts=opts.TooltipOpts(
                trigger="axis",
                trigger_on="mousemove"  # 👈 明确指定为悬浮触发
            ),

            xaxis_opts=opts.AxisOpts(type_="category", name="时间", boundary_gap=False),
            yaxis_opts=opts.AxisOpts(type_="value", name="人数 / 人效 / 接待量"),
            toolbox_opts=opts.ToolboxOpts()
        )


        html = "chart_v2.4.html"
        line.render(html)
        self.webview.load(QUrl.fromLocalFile(os.path.abspath(html)))
        # ========== 更新支援信息面板（结构化显示） ==========
        support_in = []
        support_out = []
        for r in support_records:
            acc = r['employee_name']
            emp_type = r['employee_type']
            source_dept = r.get("source_dept", "")
            target_dept = r['support_dept']
            interval = r['support_interval']
            eff = eff_map.get((target_dept, emp_type), 15)
            if selected_dept == target_dept:
                support_in.append(f"{acc}（{source_dept} → {target_dept}）<br>{interval}")
            elif selected_dept == source_dept:
                support_out.append(f"{acc}（{source_dept} → {target_dept}）<br>{interval}")

        html_lines = [f"<b>📌 {selected_dept} 部门支援情况（{selected_date}）</b><br><br>"]

        if support_in:
            html_lines.append("✅ 支援进来：<br>")
            html_lines.extend([f"{line}<br>" for line in support_in])
        else:
            html_lines.append("✅ 支援进来：<br>无<br>")

        html_lines.append("<br>")

        if support_out:
            html_lines.append("❌ 支援出去：<br>")
            html_lines.extend([f"{line}<br>" for line in support_out])
        else:
            html_lines.append("❌ 支援出去：<br>无<br>")

        self.support_info_box.setHtml("".join(html_lines))



    def generate_monthly_summary(self):
        """生成月度汇总报告"""
        month_str, ok = QInputDialog.getText(self, "输入月份", "请输入月份（格式 YYYY-MM）：", text=datetime.now().strftime("%Y-%m"))
        if not ok or not month_str.strip():
            return
        month_str = month_str.strip()

        # 从数据库获取该月的排班数据
        query = """
            SELECT 
                e.name AS 姓名,
                s.date AS 日期,
                s.shift AS 班次,
                s.lunch_time AS 午餐时间,
                s.dinner_time AS 晚餐时间,
                s.leave_interval AS 请假时间段,
                s.off_interval AS 放休时间段,
                s.overtime_interval AS 加班时间段,
                s.overtime_interval2 AS 加班2时间段,
                e.efficiency AS 人效
            FROM schedules s
            JOIN employees e ON s.employee_name = e.name
            WHERE s.date LIKE %s
            ORDER BY e.name, s.date
        """
        try:
            cursor = self.db.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, (f"{month_str}%",))
            result = cursor.fetchall()
            cursor.close()

            if not result:
                QMessageBox.information(self, "提示", "该月份没有排班记录。")
                return

            monthly_sched = pd.DataFrame(result)

            # 计算汇总数据
            summary_list = []
            for name in monthly_sched["姓名"].unique():
                emp_sched = monthly_sched[monthly_sched["姓名"] == name]
                # 计算 base shift 有效工时
                total_shift_hours = 0.0
                leave_records = []
                off_records = []
                overtime_records = []
                total_leave_hours = 0.0
                total_off_hours = 0.0
                total_overtime_hours = 0.0
                for _, row in emp_sched.iterrows():
                    effective_hours = compute_shift_effective_hours(
                        row.get("班次", ""),
                        row.get("午餐时间", ""),
                        row.get("晚餐时间", ""),
                        row.get("请假时间段", ""),
                        row.get("放休时间段", "")
                    )
                    total_shift_hours += effective_hours
                    date_str = row.get("日期", "")
                    if row.get("请假时间段", "").strip():
                        record = f"{date_str} {row.get('请假时间段', '').strip()}"
                        leave_records.append(record)
                        total_leave_hours += compute_interval_hours(row.get("请假时间段", ""))
                    if row.get("放休时间段", "").strip():
                        record = f"{date_str} {row.get('放休时间段', '').strip()}"
                        off_records.append(record)
                        total_off_hours += compute_interval_hours(row.get("放休时间段", ""))
                    if row.get("加班时间段", "").strip():
                        record = f"{date_str} {row.get('加班时间段', '').strip()}"
                        overtime_records.append(record)
                        total_overtime_hours += compute_interval_hours(row.get("加班时间段", ""))
                    if row.get("加班2时间段", "").strip():
                        record = f"{date_str} {row.get('加班2时间段', '').strip()}"
                        overtime_records.append(record)
                        total_overtime_hours += compute_interval_hours(row.get("加班2时间段", ""))
                summary_list.append({
                    "姓名": name,
                    "班次总时长（小时）": round(total_shift_hours, 2),
                    "请假记录": "; ".join(leave_records),
                    "请假总时长": round(total_leave_hours, 2),
                    "放休记录": "; ".join(off_records),
                    "放休总时长": round(total_off_hours, 2),
                    "加班记录": "; ".join(overtime_records),
                    "加班总时长": round(total_overtime_hours, 2)
                })

            summary_df = pd.DataFrame(summary_list)
            out, _ = QFileDialog.getSaveFileName(self, "导出月度汇总", f"{month_str}_月度汇总.xlsx", "Excel Files (*.xlsx)")
            if out:
                summary_df.to_excel(out, index=False)
                QMessageBox.information(self, "成功", "月度汇总导出成功！")

        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"获取月度数据时出错: {e}")

    def closeEvent(self, event):
        """关闭窗口时关闭数据库连接"""
        self.db.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu"
    # QWebEngineProfile.defaultProfile().setCachePath("")
    window = SchedulerApp()
    window.show()
    sys.exit(app.exec_())