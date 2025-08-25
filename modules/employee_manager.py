import pandas as pd
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from dialogs.AddEmployeeDialog import AddEmployeeDialog
from utils.utils import normalize_shift


class EmployeeMixin:
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
