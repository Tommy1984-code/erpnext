// Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
// For license information, please see license.txt

frappe.query_reports["Existing Man Power Report"] = {
	"filters": [
		{
            "fieldname": "company",
            "label": "Company",
            "fieldtype": "Link",
            "options": "Company",
            "reqd": 1
        },
        {
            "fieldname": "employee",
            "label": "Employee",
            "fieldtype": "Link",
            "options": "Employee",
            "reqd": 0
        },
        {
            "fieldname": "branch",
            "label": "Branch",
            "fieldtype": "Link",
            "options": "Branch"
        },
        {
            "fieldname": "department",
            "label": "Department",
            "fieldtype": "Link",
            "options": "Department"
        },
        {
            "fieldname": "grade",
            "label": "Grade",
            "fieldtype": "Link",
            "options": "Employee Grade"
        },
        {
            "fieldname": "employee_type",
            "label": "Employee Type",
            "fieldtype": "Select",
            "options": "\nFull-Time\nPart-Time\nContract\nTemporary"
        },
       
	]
};
