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
		{"label":"Date of Hire (G.C)","fieldname":"date_of_hire","fieldtype":"Date","width":120},
		{"label":"Date of Birth","fieldname":"date_of_birth","fieldtype":"Date","width":120},
		{"label":"Section","fieldname":"section","fieldtype":"data","width": 200},
		{"label":"Grade","fieldname":"grade","fieldtype":"data","width": 100},
		
	]


def get_data(filters=None):
    filters = filters or {}
    from_date = getdate(filters.get("from_date"))
    to_date = getdate(filters.get("to_date"))
    company = filters.get("company")

    # Build employee filters dictionary
    employee_filters = {
		# "from_date" : from_date,
		# "to_date" : to_date,
        "company": company,
        "status": "Active"
    }

    # Add optional filters if provided
    if filters.get("employee"):
         employee_filters["employee"] = filters.get("employee")
    if filters.get("department"):
        employee_filters["department"] = filters.get("department")
    if filters.get("grade"):
        employee_filters["grade"] = filters.get("grade")
    if filters.get("employee_type"):
        employee_filters["employment_type"] = filters.get("employee_type")
    if filters.get("designation"):
        employee_filters["designation"] = filters.get("designation")
    if filters.get("branch"):
         employee_filters["branch"] = filters.get("branch")

    # Fetch all active employees with department & applied filters
    employees = frappe.get_all(
        "Employee",
        filters=employee_filters,
        fields=[
            "name as employee_id",
            "employee_name",
            "gender",
            "designation",
            "date_of_joining as date_of_hire",
            "date_of_birth",
            "department",
            "grade",
            "employment_type"
        ],
        order_by="department asc, employee_name asc"
    )

    data = []
    current_department = None

    for emp in employees:
        department = emp.department or "No Department"
        
        # Add department header row if new department
        if department != current_department:
            data.append({
                "employee_id": f"▶ {department}",
                "employee_name": "",
                "gender": "",
                "designation": "",
                "date_of_hire": "",
                "date_of_birth": "",
                "section": "",
                "grade": ""
            })
            current_department = department

        # Add employee row
        data.append({
            "employee_id": emp.employee_id,
            "employee_name": emp.employee_name,
            "gender": emp.gender,
            "designation": emp.designation,
            "date_of_hire": emp.date_of_hire,
            "date_of_birth": emp.date_of_birth,
            "section": emp.department,
            "grade": emp.grade
        })

    return data


def get_months_in_range(start_date, end_date):
	start = getdate(start_date)
	end = getdate(end_date)

	months = []
	while start <= end:
		months.append(start)
		start = add_months(start, 1)
	return months