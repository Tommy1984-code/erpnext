# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate,add_months
from datetime import datetime, timedelta


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
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    company = filters.get("company")

    if not (from_date and to_date):
        frappe.throw("Please set both From Date and To Date")

    months = get_months_in_range(from_date, to_date)
    data = []

    for month in months:
        month = getdate(month)

        # Get all salary slips for the current month with base salary components
        query = """
            SELECT
                e.name AS employee_id,
                e.employee_name,
                e.employee_tin_no,
                e.date_of_joining,
                ss.name AS salary_slip,
                sd.amount AS basic_salary
            FROM `tabSalary Slip` ss
            JOIN `tabEmployee` e ON ss.employee = e.name
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.start_date <= %(month_end)s
                AND ss.end_date >= %(month_start)s
                AND ss.docstatus = 1
                AND sd.abbr IN ('B', 'VB')
        """

        conditions = {
            "month_start": month.replace(day=1),
            "month_end": (add_months(month.replace(day=1), 1) - timedelta(days=1))
        }

        if company:
            query += " AND e.company = %(company)s"
            conditions["company"] = company

        results = frappe.db.sql(query, conditions, as_dict=True)

        for row in results:
            base_salary = row.basic_salary
            employee_pension = base_salary * 0.07
            company_pension = base_salary * 0.11
            total_pension = employee_pension + company_pension

            data.append({
                "employee_name": row.employee_name,
                "tin_number": row.employee_tin_no,
                "date_of_hire": row.date_of_joining,
                "basic_salary": base_salary,
                "employee_pension": employee_pension,
                "company_pension": company_pension,
                "total_pension": total_pension,
                "signature": "",
                "month": month.strftime("%B %Y")
            })

    return data

def get_base_from_salary_slip(employee_id, month):
    # Fetch BASIC or VBASIC for a specific month
    for abbr in ["B", "VB"]:
        result = frappe.db.sql("""
            SELECT sd.amount
            FROM `tabSalary Slip` ss
            JOIN `tabSalary Detail` sd ON sd.parent = ss.name
            WHERE ss.employee = %s
                AND ss.start_date <= %s
                AND ss.end_date >= %s
                AND ss.docstatus = 1
                AND sd.abbr = %s
                AND sd.parentfield = 'earnings'
            ORDER BY ss.end_date DESC
            LIMIT 1
        """, (employee_id, month, month, abbr), as_dict=True)

        if result:
            return result[0].amount

    return 0


def get_months_in_range(start_date, end_date):
    """Generate all months in the range from start_date to end_date"""
    months = []
    current_month = start_date

    while current_month <= end_date:
        months.append(current_month)
        current_month = add_months(current_month, 1)

    return months
    