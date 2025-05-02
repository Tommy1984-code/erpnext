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
	company = filters.get("company")

	# Fetch all active employees with department
	employees = frappe.get_all(
		"Employee",
		filters={
			"company": company,
			"status": "Active"
		},
		fields=[
			"name as employee_id",
			"employee_name",
			"gender",
			"designation",
			"date_of_joining as date_of_hire",
			"date_of_birth",
			"department",
			"grade"
		],
		order_by="department asc, employee_name asc"
	)

	data = []
	current_department = None

	for emp in employees:
		department = emp.department or "No Department"
		
		# Check if we are entering a new department group
		if department != current_department:
			# Add a group title row
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
