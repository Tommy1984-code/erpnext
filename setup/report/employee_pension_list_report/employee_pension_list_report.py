# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate


def execute(filters=None):

	columns = get_columns()
	employee_rows = get_data(filters)

	#Fetch company data for header
	company_filter = filters.get("company") if filters else None
	company = frappe.get_doc("Company",company_filter) if company_filter else None

	company_data = {
		"company_name" : company.company_name if company else "",
		"organization_tin_number":company.tax_id if company else "",
		"tax_account_number":company.tax_account_number if company else "",
		"region":company.region if company else "",
		"zonesub_district":company.zonesub_district if company else "",
		"name_of_the_tax_collector":company.name_of_the_tax_collector if company else "",
		"document_number_for_office_use":company.document_number_for_office_use_only if company else "",
		"woreda":company.woreda if company else "",
		"kebele":company.kebele if company else "",
		"house_number":company.house_number if company else "",
		"phone":company.phone_no if company else "",
		"fax":company.fax if company else ""
	}
	
	if filters.get("from_date"):
		from_date = getdate(filters["from_date"])
		period_for_payment = f"{from_date.strftime('%B')} {from_date.year}"  # Format: "Month Year"
		company_data["period_for_payment"] = period_for_payment
		
	for row in employee_rows:
		row.update(company_data)
	# frappe.msgprint(f"this is the data of {data}")

	return columns, employee_rows

def get_columns():
	return[
		{"label":"Full Name","fieldname":"employee_name","fieldtype":"Data","width": 200},
		{"label":"TIN Number","fieldname":"tin_number","fieldtype":"Data","width": 120},
		{"label":"Date of Hire (G.C)","fieldname":"date_of_hire","fieldtype":"Date","width":120},
		{"label":"Basic Salary","fieldname":"basic_salary","fieldtype":"Currency","width": 120},
		{"label":"Employee Pension(7%)","fieldname":"employee_pension","fieldtype":"Currency","width": 150},
		{"label":"Company Pension (11%)","fieldname":"company_pension","fieldtype":"Currency","width": 150},
		{"label":"Total Pension (18%)","fieldname":"total_pension","fieldtype":"Currency","width": 150},
		{"label":"Signature","fieldname":"signature","fieldtype":"Data","width": 100},
	]
def get_data(filters=None):

	company_filter = filters.get("company") if filters else None
	conditions = ""
	if filters.get("from_date") and filters.get("to_date"):
		conditions += f"""
            AND status = 'Active'  # Employee is active
            AND (date_of_joining <= '{filters['to_date']}'  # Employee joined before or on the to_date
			AND (relieving_date IS NULL OR relieving_date >= '{filters['from_date']}'))  # Employee hasn't been terminated before from_date"""
	if company_filter:
		conditions += f" AND company = '{company_filter}'"


	employees = frappe.db.sql(f"""
        SELECT
            employee_name,
            employee_tin_no,
            date_of_joining,
            base
        FROM
            `tabEmployee`
        WHERE
            status = 'Active' {conditions}
    """, as_dict=True)

	data = []
	for emp in employees:
		employee_pension = emp.base * 0.07 if emp.base else 0
		company_pension = emp.base *0.11 if emp.base else 0
		total_pension = employee_pension + company_pension

		data.append({
			"employee_name":emp.employee_name,
			"tin_number":emp.employee_tin_no,
			"date_of_hire":emp.date_of_joining,
			"basic_salary":emp.base,
			"employee_pension":employee_pension,
			"company_pension":company_pension,
			"total_pension": total_pension,
			"signature":""

		})
	return data

