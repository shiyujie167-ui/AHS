import pandas as pd
import pymysql
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (
    QTableWidgetItem, QMenu, QMessageBox, QFileDialog, QInputDialog
)

from dialogs.AddShiftDialog import AddShiftDialog
from utils.utils import (
    normalize_shift, normalize_time_format,
    parse_single_time_as_interval, slot_in_interval,
    floor_to_half_hour, ceil_to_half_hour,
    compute_shift_effective_hours, compute_interval_hours
)
from pyecharts.charts import Line
from pyecharts import options as opts


class ScheduleMixin:
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
        except Exception:
            return False

    def plot_chart(self):
        try:
            selected_dept = self.dept_filter.currentText()
            selected_date = self.date_picker.date().toString("yyyy-MM-dd")

            df = self.filtered_df.copy()
            if df.empty:
                QMessageBox.warning(self, "提示", "当日无排班数据")
                return

            merged = df
            earliest_time = None
            latest_time = None
            for _, row in merged.iterrows():
                try:
                    shift = row.get("班次", "")
                    if "-" not in shift:
                        continue
                    s, e = shift.split("-")
                    start = datetime.strptime(s.strip(), "%H:%M")
                    end = datetime.strptime(e.strip(), "%H:%M")
                    if end <= start:
                        end += timedelta(days=1)
                    if earliest_time is None or start < earliest_time:
                        earliest_time = start
                    if latest_time is None or end > latest_time:
                        latest_time = end
                    for field in ["午餐时间", "晚餐时间", "请假时间段", "放休时间段", "加班时间段", "加班2时间段"]:
                        interval = row.get(field, "").strip()
                        if interval and "-" in interval:
                            st, ed = interval.split("-")
                            st = datetime.strptime(st.strip(), "%H:%M")
                            ed = datetime.strptime(ed.strip(), "%H:%M")
                            if ed <= st:
                                ed += timedelta(days=1)
                            if st < earliest_time:
                                earliest_time = st
                            if ed > latest_time:
                                latest_time = ed
                except:
                    continue

            if earliest_time is None or latest_time is None:
                earliest_time = datetime.strptime("08:00", "%H:%M")
                latest_time = datetime.strptime("19:00", "%H:%M")

            earliest_time = floor_to_half_hour(earliest_time)
            latest_time = ceil_to_half_hour(latest_time)

            time_labels = []
            t = earliest_time
            while t <= latest_time:
                time_labels.append(t.strftime("%H:%M"))
                t += timedelta(minutes=30)

            support_adjustments = [0] * len(time_labels)
            efficiency_adjustments = [0.0] * len(time_labels)

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

                lunch_interval, dinner_interval = support_meal_map.get((acc, selected_date), (None, None))

                for i, label in enumerate(time_labels):
                    slot_start = datetime.strptime(label, "%H:%M")
                    slot_end = slot_start + timedelta(minutes=15)

                    if not slot_in_interval(slot_start, slot_end, interval):
                        continue

                    if (lunch_interval and slot_in_interval(slot_start, slot_end, lunch_interval)) or \
                    (dinner_interval and slot_in_interval(slot_start, slot_end, dinner_interval)):
                        continue

                    if selected_dept == support_dept:
                        support_adjustments[i] += 1
                        efficiency_adjustments[i] += eff_support
                    elif selected_dept == source_dept:
                        support_adjustments[i] -= 1
                        efficiency_adjustments[i] -= eff_source

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
                    print(f"获取预测量数据失败: {e}")
                    predict_y = [None] * len(time_labels)
            else:
                predict_y = [None] * len(time_labels)

            line = (
                Line()
                .add_xaxis(time_labels)
                .add_yaxis("在岗人数", onsite, is_smooth=True)
                .add_yaxis("工作量预测", predict_y)
                .add_yaxis("人效", efficiency, yaxis_index=1)
                .set_global_opts(
                    yaxis_opts=[
                        opts.AxisOpts(name="人数"),
                        opts.AxisOpts(name="人效", position="right")
                    ],
                    tooltip_opts=opts.TooltipOpts(trigger="axis")
                )
            )

            self.webview.setHtml(line.render_embed())
            self.update_support_info(support_records, selected_dept)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"绘制图表失败：{e}")

    def update_support_info(self, support_records, selected_dept):
        html_lines = []
        support_in = []
        support_out = []

        for r in support_records:
            acc = r.get("account")
            emp_info = self.employee_df[self.employee_df["账号"] == acc]
            name = emp_info["姓名"].values[0] if not emp_info.empty else acc
            source_dept = r.get("source_dept", "")
            support_dept = r.get("support_dept", "")
            interval = r.get("support_interval", "")
            if selected_dept == support_dept:
                support_in.append(f"{name} 从 {source_dept} 支援至 {support_dept} ({interval})")
            elif selected_dept == source_dept:
                support_out.append(f"{name} 从 {source_dept} 支援至 {support_dept} ({interval})")

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

            summary_list = []
            for name in monthly_sched["姓名"].unique():
                emp_sched = monthly_sched[monthly_sched["姓名"] == name]
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
