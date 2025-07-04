// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.setup");
erpnext.setup.EmployeeController = class EmployeeController extends frappe.ui.form.Controller {
	setup() {
		this.frm.fields_dict.user_id.get_query = function (doc, cdt, cdn) {
			return {
				query: "frappe.core.doctype.user.user.user_query",
				filters: { ignore_user_type: 1 },
			};
		};
		this.frm.fields_dict.reports_to.get_query = function (doc, cdt, cdn) {
			return { query: "erpnext.controllers.queries.employee_query" };
		};
		this.set_earning_deduction_component(this.frm);
	}

	refresh() {
		erpnext.toggle_naming_series();
		
		
	}
// my code that is adding the filtering of earning and deduction column
	set_earning_deduction_component(frm) {
		if (!frm.doc.company) return;
		frm.set_query("salary_component", "earnings", function () {
			return {
				filters: { component_type: "earning", company: frm.doc.company },
				query: "erpnext.setup.doctype.employee.employee.get_salary_component",
			};
		});
		frm.set_query("salary_component", "deductions", function () {
			return {
				filters: { component_type: "deduction", company: frm.doc.company },
				query: "erpnext.setup.doctype.employee.employee.get_salary_component",
			};
		});
	}
};

frappe.ui.form.on("Employee", {
		
		add_default_benefit: function(frm) {
			frappe.call({
				method: "erpnext.setup.doctype.employee.employee.get_default_salary_components",
				callback: function(r) {
					if (r.message) {
						(r.message.earnings || []).forEach((comp) => {
							let exists = frm.doc.earnings.some(e => e.salary_component === comp.name);
							if (!exists) {
								frm.add_child("earnings", {
									salary_component: comp.name,
									salary_component_abbr: comp.salary_component_abbr,
									description: comp.description,
									depends_on_payment_days: comp.depends_on_payment_days,
									is_tax_applicable: comp.is_tax_applicable,
									deduct_full_tax_on_selected_payroll_date: comp.deduct_full_tax_on_selected_payroll_date,
									variable_based_on_taxable_salary: comp.variable_based_on_taxable_salary,
									is_income_tax_component: comp.is_income_tax_component,
									exempted_from_income_tax: comp.exempted_from_income_tax,
									round_to_the_nearest_integer: comp.round_to_the_nearest_integer,
									statistical_component: comp.statistical_component,
									do_not_include_in_total: comp.do_not_include_in_total,
									remove_if_zero_valued: comp.remove_if_zero_valued,
									disabled: comp.disabled,
									loan_component: comp.loan_component,
									condition: comp.condition,
									amount_based_on_formula: comp.amount_based_on_formula,
									formula: comp.formula,
									amount: comp.amount,
									help: comp.help,
								});
							}
						});
	
						(r.message.deductions || []).forEach((comp) => {
							let exists = frm.doc.deductions.some(e => e.salary_component === comp.name);
							if (!exists) {
								frm.add_child("deductions", {
									salary_component: comp.name,
									salary_component_abbr: comp.salary_component_abbr,
									description: comp.description,
									depends_on_payment_days: comp.depends_on_payment_days,
									is_tax_applicable: comp.is_tax_applicable,
									deduct_full_tax_on_selected_payroll_date: comp.deduct_full_tax_on_selected_payroll_date,
									variable_based_on_taxable_salary: comp.variable_based_on_taxable_salary,
									is_income_tax_component: comp.is_income_tax_component,
									exempted_from_income_tax: comp.exempted_from_income_tax,
									round_to_the_nearest_integer: comp.round_to_the_nearest_integer,
									statistical_component: comp.statistical_component,
									do_not_include_in_total: comp.do_not_include_in_total,
									remove_if_zero_valued: comp.remove_if_zero_valued,
									disabled: comp.disabled,
									loan_component: comp.loan_component,
									condition: comp.condition,
									amount_based_on_formula: comp.amount_based_on_formula,
									formula: comp.formula,
									amount: comp.amount,
									help: comp.help,
								});
							}
						});
	
						frm.refresh_field("earnings");
						frm.refresh_field("deductions");
					}
				},
			});
		},

		department: function (frm) {
			// clear section when department changes
			frm.set_value("section", null);
		  },
		
		  section: function (frm) {
			// optional: additional logic if needed on section select
		  },
	
	
	onload: function (frm) {
		frm.trigger('set_earning_deduction_component')//my triger the filter
		frm.set_query("department", function () {
			return {
				filters: {
					company: frm.doc.company,
				},
			};
		});
		frm.set_query("section", function () {
			if (!frm.doc.department) return {};
			return {
			  filters: {
				department: frm.doc.department
			  }
			};
		  });

		
    
		
	},
	prefered_contact_email: function (frm) {
		frm.events.update_contact(frm);
	},

	personal_email: function (frm) {
		frm.events.update_contact(frm);
	},

	company_email: function (frm) {
		frm.events.update_contact(frm);
	},

	user_id: function (frm) {
		frm.events.update_contact(frm);
	},

	update_contact: function (frm) {
		var prefered_email_fieldname = frappe.model.scrub(frm.doc.prefered_contact_email) || "user_id";
		frm.set_value("prefered_email", frm.fields_dict[prefered_email_fieldname].value);
	},

	status: function (frm) {
		return frm.call({
			method: "deactivate_sales_person",

			args: {
				employee: frm.doc.employee,
				status: frm.doc.status,
			},
		});
	},

	create_user: function (frm) {
		if (!frm.doc.prefered_email) {
			frappe.throw(__("Please enter Preferred Contact Email"));
		}
		frappe.call({
			method: "erpnext.setup.doctype.employee.employee.create_user",
			args: {
				employee: frm.doc.name,
				email: frm.doc.prefered_email,
			},
			freeze: true,
			freeze_message: __("Creating User..."),
			callback: function (r) {
				frm.reload_doc();
			},
		});
	},
	    // Add formula handling
		formula: function (frm, cdt, cdn) {
			const row = locals[cdt][cdn];
			if (row.formula && !row.amount_based_on_formula && !frm.alerted_rows.includes(cdn)) {
				frappe.msgprint({
					message: __("{0} Row #{1}: {2} needs to be enabled for the formula to be considered.",
						[toTitle(row.parentfield), row.idx, __("Amount based on formula").bold()]),
					title: __("Warning"),
					indicator: "orange",
				});
				frm.alerted_rows.push(cdn);
			}
		},
	
		amount_based_on_formula: function (frm, cdt, cdn) {
			const child = locals[cdt][cdn];
			if (child.amount_based_on_formula == 1) {
				frappe.model.set_value(cdt, cdn, "amount", null);
				const index = frm.alerted_rows.indexOf(cdn);
				if (index > -1) frm.alerted_rows.splice(index, 1);
			} else {
				frappe.model.set_value(cdt, cdn, "formula", null);
			}
		},
});

cur_frm.cscript = new erpnext.setup.EmployeeController({
	frm: cur_frm,
});

frappe.tour["Employee"] = [
	{
		fieldname: "first_name",
		title: "First Name",
		description: __(
			"Enter First and Last name of Employee, based on Which Full Name will be updated. IN transactions, it will be Full Name which will be fetched."
		),
	},
	{
		fieldname: "company",
		title: "Company",
		description: __("Select a Company this Employee belongs to."),
	},
	{
		fieldname: "date_of_birth",
		title: "Date of Birth",
		description: __(
			"Select Date of Birth. This will validate Employees age and prevent hiring of under-age staff."
		),
	},
	{
		fieldname: "date_of_joining",
		title: "Date of Joining",
		description: __(
			"Select Date of joining. It will have impact on the first salary calculation, Leave allocation on pro-rata bases."
		),
	},
	{
		fieldname: "reports_to",
		title: "Reports To",
		description: __(
			"Here, you can select a senior of this Employee. Based on this, Organization Chart will be populated."
		),
	},
];

frappe.ui.form.on("Salary Detail", {
	form_render: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		hrms.payroll_utils.set_autocompletions_for_condition_and_formula(frm, row);
	},

	amount: function (frm) {
		calculate_totals(frm.doc);
	},

	earnings_remove: function (frm) {
		calculate_totals(frm.doc);
	},

	deductions_remove: function (frm) {
		calculate_totals(frm.doc);
	},

	formula: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.formula && !row?.amount_based_on_formula && !frm.alerted_rows.includes(cdn)) {
			frappe.msgprint({
				message: __(
					"{0} Row #{1}: {2} needs to be enabled for the formula to be considered.",
					[toTitle(row.parentfield), row.idx, __("Amount based on formula").bold()],
				),
				title: __("Warning"),
				indicator: "orange",
			});
			frm.alerted_rows.push(cdn);
		}
	},

	salary_component: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.salary_component) {
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Salary Component",
					name: child.salary_component,
				},
				callback: function (data) {
					if (data.message) {
						var result = data.message;
						frappe.model.set_value(cdt, cdn, "condition", result.condition);
						frappe.model.set_value(
							cdt,
							cdn,
							"amount_based_on_formula",
							result.amount_based_on_formula,
						);
						if (result.amount_based_on_formula == 1) {
							frappe.model.set_value(cdt, cdn, "formula", result.formula);
						} else {
							frappe.model.set_value(cdt, cdn, "amount", result.amount);
						}
						frappe.model.set_value(
							cdt,
							cdn,
							"statistical_component",
							result.statistical_component,
						);
						frappe.model.set_value(
							cdt,
							cdn,
							"depends_on_payment_days",
							result.depends_on_payment_days,
						);
						frappe.model.set_value(
							cdt,
							cdn,
							"do_not_include_in_total",
							result.do_not_include_in_total,
						);
						frappe.model.set_value(
							cdt,
							cdn,
							"variable_based_on_taxable_salary",
							result.variable_based_on_taxable_salary,
						);
						frappe.model.set_value(
							cdt,
							cdn,
							"is_tax_applicable",
							result.is_tax_applicable,
						);
						frappe.model.set_value(
							cdt,
							cdn,
							"is_flexible_benefit",
							result.is_flexible_benefit,
						);
						refresh_field("earnings");
						refresh_field("deductions");
					}
				},
			});
		}
	},

	amount_based_on_formula: function (frm, cdt, cdn) {
		var child = locals[cdt][cdn];
		if (child.amount_based_on_formula == 1) {
			frappe.model.set_value(cdt, cdn, "amount", null);
			const index = frm.alerted_rows.indexOf(cdn);
			if (index > -1) frm.alerted_rows.splice(index, 1);
		} else {
			frappe.model.set_value(cdt, cdn, "formula", null);
		}
	},

	salary_component: function (frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const selected = row.salary_component;
	
		if (!selected) return;
	
		// Check for duplicates across BOTH earnings and deductions
		const all_components = [
			...(frm.doc.earnings || []),
			...(frm.doc.deductions || []),
		];
	
		const duplicate = all_components.find(
			r => r.salary_component === selected && r.name !== row.name
		);
	
		if (duplicate) {
			frappe.msgprint(__("This Salary Component is already used."));
			// Use a short delay to ensure UI responds before clearing
			setTimeout(() => {
				frappe.model.set_value(cdt, cdn, "salary_component", null);
			}, 100);
			return; // ← This is critical to prevent executing the fetch
		}
	
		// ✅ Only fetch if NOT duplicate
		frappe.call({
			method: "frappe.client.get",
			args: {
				doctype: "Salary Component",
				name: selected,
			},
			callback: function (data) {
				if (data.message) {
					const result = data.message;
					frappe.model.set_value(cdt, cdn, "condition", result.condition);
					frappe.model.set_value(cdt, cdn, "amount_based_on_formula", result.amount_based_on_formula);
					if (result.amount_based_on_formula == 1) {
						frappe.model.set_value(cdt, cdn, "formula", result.formula);
					} else {
						frappe.model.set_value(cdt, cdn, "amount", result.amount);
					}
					frappe.model.set_value(cdt, cdn, "statistical_component", result.statistical_component);
					frappe.model.set_value(cdt, cdn, "depends_on_payment_days", result.depends_on_payment_days);
					frappe.model.set_value(cdt, cdn, "do_not_include_in_total", result.do_not_include_in_total);
					frappe.model.set_value(cdt, cdn, "variable_based_on_taxable_salary", result.variable_based_on_taxable_salary);
					frappe.model.set_value(cdt, cdn, "is_tax_applicable", result.is_tax_applicable);
					frappe.model.set_value(cdt, cdn, "is_flexible_benefit", result.is_flexible_benefit);
					refresh_field("earnings");
					refresh_field("deductions");
				}
			}
		});
	}
	
	
});



