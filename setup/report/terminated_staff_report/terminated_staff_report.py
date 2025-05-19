# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta
from collections import defaultdict


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	
	return columns, data


def get_columns():
	return[
		{"label":"Employee ID","fieldname":"employee_id","fieldtype":"Data","width": 200},
		{"label":"Full Name","fieldname":"employee_name","fieldtype":"Data","width": 200},
		{"label":"Sex","fieldname":"gender","fieldtype":"Data","width": 120},
		{"label":"Job Title","fieldname":"designation","fieldtype":"Data","width": 120},
		{"label":"Termination Date","fieldname":"relieving_date","fieldtype":"Date","width":120},
		{"label":"Salary","fieldname":"basic_salary","fieldtype":"Currency","width":120},
		{"label":"Term. Salary","fieldname":"termination_salary","fieldtype":"Currency","width":120},
		{"label":"Department","fieldname":"department","fieldtype":"data","width": 200},
		{"label":"Employment Type","fieldname":"employment_type","fieldtype":"data","width": 120},
		
	]

def get_data(filters=None):
    filters = filters or {}
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")
    employee = filters.get("employee")
    grade = filters.get("grade")
    department = filters.get("department")
    employee_type = filters.get("employee_type")
    branch = filters.get("branch")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    # Prepare dynamic filter clauses
    company_clause = "AND e.company = %(company)s" if company else ""
    employee_clause = "AND e.name = %(employee)s" if employee else ""
    department_clause = "AND e.department = %(department)s" if department else ""
    grade_clause = "AND e.grade = %(grade)s" if grade else ""
    employee_type_clause = "AND e.employment_type = %(employee_type)s" if employee_type else ""
    branch_clause = "AND e.branch = %(branch)s" if branch else ""

    query = f"""
        SELECT e.name AS employee_id,
               e.employee_name,
               e.gender,
               e.designation,
               e.relieving_date,
               e.base AS basic_salary,
               e.department,
               e.employment_type,
               ss.name AS salary_slip
        FROM `tabEmployee` e
        LEFT JOIN `tabSalary Slip` ss ON ss.employee = e.name
            AND ss.start_date <= %(to_date)s
            AND ss.end_date >= %(from_date)s
            AND ss.docstatus = 1
        WHERE e.status = 'Left'
          AND e.relieving_date BETWEEN %(from_date)s AND %(to_date)s
          {company_clause}
          {employee_clause}
          {department_clause}
          {grade_clause}
          {employee_type_clause}
          {branch_clause}
        ORDER BY e.relieving_date ASC
    """

    params = {
        "from_date": from_date,
        "to_date": to_date,
    }

    # Add filter params only if they are used in the query
    if company:
        params["company"] = company
    if employee:
        params["employee"] = employee
    if department:
        params["department"] = department
    if grade:
        params["grade"] = grade
    if employee_type:
        params["employee_type"] = employee_type
    if branch:
        params["branch"] = branch

    employees = frappe.db.sql(query, params, as_dict=True)

    result = []
    for emp in employees:
        termination_salary = 0

        if emp.salary_slip:
            # Get salary details from the slip
            salary_details = frappe.db.sql("""
                SELECT sd.amount, sd.abbr, sd.parentfield
                FROM `tabSalary Detail` sd
                WHERE sd.parent = %s
            """, (emp.salary_slip,), as_dict=True)

            earnings = {
                comp.abbr: comp.amount
                for comp in salary_details
                if comp.parentfield == 'earnings'
            }

            termination_salary = earnings.get('B') or earnings.get('VB') or 0

        emp['termination_salary'] = termination_salary
        result.append(emp)

    return result

def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months
	