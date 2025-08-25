import traceback

import pandas as pd
import pymysql
# 数据库配置
from PyQt5.QtWidgets import QMessageBox

DB_CONFIG = {
    #'host': '112.124.3.180', # 主机
    'host': '14.103.156.179', # 主机
    'user': 'root',       #用户名
    'password': 'ahs123456',  #密码
    'port': 3306,         #端口 3306
    'database':'ahslist',   #数据库名
    'autocommit':True
}


# ======= 数据库操作类 =======
class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
        self.initialize_database()

    def get_efficiency_by_mapping(self, department, employee_type):
        """根据部门和员工类型查询匹配的人效"""
        try:
            query = """
                SELECT efficiency 
                FROM efficiency_mapping 
                WHERE department = %s AND employee_type = %s
            """
            cursor = self.connection.cursor()
            cursor.execute(query, (department, employee_type))
            result = cursor.fetchone()
            cursor.close()
            return float(result[0]) if result else 0.0
        except Exception as e:
            print(f"查询人效匹配时出错: {e}")
            return 0.0


    def connect(self):
        """连接到MySQL数据库"""
        try:
            self.connection = pymysql.connect(**DB_CONFIG)
            if self.connection.open:
                print("成功连接到MySQL数据库")
        except Exception as e:
            traceback.print_exc()
            print(f"连接数据库时出错: {e}")
            QMessageBox.critical(None, "数据库错误", f"无法连接到数据库: {e}")

    def initialize_database(self):
        """初始化数据库表结构"""
        try:
            cursor = self.connection.cursor()

            # 创建employees表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS employees (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    account VARCHAR(100) NOT NULL,
                    employee_id VARCHAR(50),
                    department VARCHAR(100),
                    group_name VARCHAR(50),
                    employee_type VARCHAR(50),
                    region VARCHAR(100),
                    efficiency VARCHAR(20),
                    UNIQUE KEY unique_name_id (name, employee_id)
                )
            """)

            # 创建schedules表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    employee_name VARCHAR(100) NOT NULL,
                    account VARCHAR(100) NOT NULL,
                    employee_id VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    shift VARCHAR(50),
                    lunch_time VARCHAR(50),
                    dinner_time VARCHAR(50),
                    leave_interval VARCHAR(100),
                    off_interval VARCHAR(100),
                    overtime_interval VARCHAR(100),
                    overtime_interval2 VARCHAR(100),
                    UNIQUE KEY unique_employee_date (employee_name, date)
                )
            """)

            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"初始化数据库时出错: {e}")
            QMessageBox.critical(None, "数据库错误", f"初始化数据库失败: {e}")

    def get_employees(self):
        """获取所有员工数据"""
        try:
            query = "SELECT name, account,employee_id, department, group_name, employee_type,region, efficiency FROM employees"
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return pd.DataFrame(result)
        except Exception as e:
            print(f"获取员工数据时出错: {e}")
            return pd.DataFrame()

    def get_schedules(self):
        """获取所有排班数据"""
        try:
            query = """
                SELECT 
                    e.name AS 姓名,
                    s.date AS 日期,
                    s.shift AS 班次,
                    e.account AS 账号,
                    e.employee_id AS 工号, 
                    s.lunch_time AS 午餐时间,
                    s.dinner_time AS 晚餐时间,
                    s.leave_interval AS 请假时间段,
                    s.off_interval AS 放休时间段,
                    s.overtime_interval AS 加班时间段,
                    s.overtime_interval2 AS 加班2时间段,
                    e.department AS 部门,
                    e.efficiency AS 人效,
                    e.region AS 地区
                FROM schedules s
                JOIN employees e ON s.employee_name = e.name
            """
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query)
            result = cursor.fetchall()
            cursor.close()
            return pd.DataFrame(result)
        except Exception as e:
            print(f"获取排班数据时出错: {e}")
            return pd.DataFrame()

    def add_employee(self, data):
        """添加新员工"""
        try:

            query = """
                INSERT INTO employees (name, account, employee_id, department, group_name, employee_type, efficiency, region)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    department = VALUES(department),
                    group_name = VALUES(group_name),
                    employee_type = VALUES(employee_type),
                    efficiency = VALUES(efficiency),
                    region = VALUES(region)
            """
            cursor = self.connection.cursor()
            cursor.execute(query, (
                data["姓名"],
                data["账号"],
                data["工号"],
                data["部门"],
                data.get("分组", ""),
                data["员工类型"],
                data["人效"],
                data["地区"]
            ))

            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"添加员工时出错: {e}")
            return False

    def add_schedule(self, data):
        """添加排班记录"""
        try:
            data.setdefault("账号", "")
            data.setdefault("工号", "")
            query = """
                INSERT INTO schedules (
                    employee_name, account, employee_id, date,
                    shift, lunch_time, dinner_time,
                    leave_interval, off_interval,
                    overtime_interval, overtime_interval2
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    shift = VALUES(shift),
                    lunch_time = VALUES(lunch_time),
                    dinner_time = VALUES(dinner_time),
                    leave_interval = VALUES(leave_interval),
                    off_interval = VALUES(off_interval),
                    overtime_interval = VALUES(overtime_interval),
                    overtime_interval2 = VALUES(overtime_interval2)
            """
            cursor = self.connection.cursor()
            cursor.execute(query, (
                data["姓名"],
                data["账号"],
                data["工号"],
                data["日期"],
                data["班次"],
                data["午餐时间"],
                data["晚餐时间"],
                data["请假时间段"],
                data["放休时间段"],
                data["加班时间段"],
                data.get("加班2时间段", "")
            ))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"添加排班时出错: {e}")
            return False


    def delete_schedule(self, employee_name, date):
        """删除排班记录"""
        try:
            query = "DELETE FROM schedules WHERE employee_name = %s AND date = %s"
            cursor = self.connection.cursor()
            cursor.execute(query, (employee_name, date))
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"删除排班时出错: {e}")
            return False

    def clear_all_data(self):
        """清空所有数据"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("DELETE FROM schedules")
            cursor.execute("DELETE FROM employees")
            self.connection.commit()
            cursor.close()
            return True
        except Exception as e:
            print(f"清空数据时出错: {e}")
            return False
        
    def get_support_shifts_by_account_and_date(self, account, date):
        query = "SELECT support_dept, support_interval FROM support_shifts WHERE account = %s AND date = %s"
        cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (account, date))
        result = cursor.fetchall()
        cursor.close()
        return result

    def delete_support_shifts_by_account_and_date(self, account, date):
        query = "DELETE FROM support_shifts WHERE account = %s AND date = %s"
        cursor = self.connection.cursor()
        cursor.execute(query, (account, date))
        self.connection.commit()
        cursor.close()


    def add_support_shift(self, name, account, date, support_dept, support_interval, source_dept, employee_type):
        query = """
            INSERT INTO support_shifts (employee_name, account, date, support_dept, support_interval, source_dept, employee_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor = self.connection.cursor()
        cursor.execute(query, (name, account, date, support_dept, support_interval, source_dept, employee_type))
        self.connection.commit()
        cursor.close()

    def get_support_shifts(self, date):
        try:
            query = "SELECT * FROM support_shifts WHERE date = %s"
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute(query, (date,))
            result = cursor.fetchall()
            cursor.close()
            return result
        except Exception as e:
            print(f"获取支援排班失败: {e}")
            return []

    def get_support_shifts_by_date(self, date_str):
        query = """
            SELECT account, employee_name,support_dept, support_interval, employee_type, source_dept
            FROM support_shifts
            WHERE date = %s
        """
        cursor = self.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, (date_str,))
        result = cursor.fetchall()
        cursor.close()
        return result

    def get_efficiency_mapping(self):
        """
        获取人效映射字典，形式为 {(部门, 员工类型): 人效}
        """
        try:
            query = "SELECT department, employee_type, efficiency FROM efficiency_mapping"
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            cursor.close()

            eff_map = {}
            for dept, emp_type, eff in rows:
                try:
                    eff_map[(dept, emp_type)] = float(eff)
                except:
                    eff_map[(dept, emp_type)] = 15.0  # 默认人效
            return eff_map
        except Exception as e:
            print(f"[ERROR] 获取人效映射表失败: {e}")
            return {}


    def close(self):
        if self.connection:
            self.connection.close()
            print("数据库连接已关闭")