# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import frappe
from frappe import _, scrub, throw
from frappe.model.naming import set_name_by_naming_series
from frappe.permissions import (
	add_user_permission,
	get_doc_permissions,
	has_permission,
	remove_user_permission,
)
from frappe.utils import cstr, getdate, today, validate_email_address
from frappe.utils.nestedset import NestedSet
from hrms.payroll.utils import sanitize_expression

from erpnext.utilities.transaction_base import delete_events


class EmployeeUserDisabledError(frappe.ValidationError):
	pass


class InactiveEmployeeStatusError(frappe.ValidationError):
	pass


class Employee(NestedSet):
	nsm_parent_field = "reports_to"

	def autoname(self):
		set_name_by_naming_series(self)
		self.employee = self.name
	# adding for the data import for protecting the exsting recodrd
	def before_save(self):
		if frappe.flags.in_import:
			self.merge_salary_details()
		
	def before_validate(self):
		self.sanitize_condition_and_formula_fields()

	def before_update_after_submit(self):
		self.sanitize_condition_and_formula_fields()
	

	def validate(self):
		from erpnext.controllers.status_updater import validate_status

		validate_status(self.status, ["Active", "Inactive", "Suspended", "Left"])
		self.validate_formula_setup()

		self.employee = self.name
		self.set_employee_name()
		self.validate_date()
		self.validate_email()
		self.validate_status()
		self.validate_reports_to()
		self.validate_preferred_email()

		if self.user_id:
			self.validate_user_details()
		else:
			existing_user_id = frappe.db.get_value("Employee", self.name, "user_id")
			if existing_user_id:
				user = frappe.get_doc("User", existing_user_id)
				validate_employee_role(user, ignore_emp_check=True)
				user.save(ignore_permissions=True)
				remove_user_permission("Employee", self.name, existing_user_id)

	def after_rename(self, old, new, merge):
		self.db_set("employee", new)

	def set_employee_name(self):
		self.employee_name = " ".join(
			filter(lambda x: x, [self.first_name, self.middle_name, self.last_name])
		)

	def validate_user_details(self):
		if self.user_id:
			data = frappe.db.get_value("User", self.user_id, ["enabled", "user_image"], as_dict=1)

			if not data:
				self.user_id = None
				return

			if data.get("user_image") and self.image == "":
				self.image = data.get("user_image")
			self.validate_for_enabled_user_id(data.get("enabled", 0))
			self.validate_duplicate_user_id()

	def update_nsm_model(self):
		frappe.utils.nestedset.update_nsm(self)

	def on_update(self):
		self.update_nsm_model()
		if self.user_id:
			self.update_user()
			self.update_user_permissions()
		self.reset_employee_emails_cache()

	def update_user_permissions(self):
		if not self.create_user_permission:
			return
		if not has_permission("User Permission", ptype="write", raise_exception=False):
			return

		employee_user_permission_exists = frappe.db.exists(
			"User Permission", {"allow": "Employee", "for_value": self.name, "user": self.user_id}
		)

		if employee_user_permission_exists:
			return

		add_user_permission("Employee", self.name, self.user_id)
		add_user_permission("Company", self.company, self.user_id)

	def update_user(self):
		# add employee role if missing
		user = frappe.get_doc("User", self.user_id)
		user.flags.ignore_permissions = True

		if "Employee" not in user.get("roles"):
			user.append_roles("Employee")

		# copy details like Fullname, DOB and Image to User
		if self.employee_name and not (user.first_name and user.last_name):
			employee_name = self.employee_name.split(" ")
			if len(employee_name) >= 3:
				user.last_name = " ".join(employee_name[2:])
				user.middle_name = employee_name[1]
			elif len(employee_name) == 2:
				user.last_name = employee_name[1]

			user.first_name = employee_name[0]

		if self.date_of_birth:
			user.birth_date = self.date_of_birth

		if self.gender:
			user.gender = self.gender

		if self.image:
			if not user.user_image:
				user.user_image = self.image
				try:
					frappe.get_doc(
						{
							"doctype": "File",
							"file_url": self.image,
							"attached_to_doctype": "User",
							"attached_to_name": self.user_id,
						}
					).insert(ignore_if_duplicate=True)
				except frappe.DuplicateEntryError:
					# already exists
					pass

		user.save()

	def validate_date(self):
		if self.date_of_birth and getdate(self.date_of_birth) > getdate(today()):
			throw(_("Date of Birth cannot be greater than today."))

		self.validate_from_to_dates("date_of_birth", "date_of_joining")
		self.validate_from_to_dates("date_of_joining", "date_of_retirement")
		self.validate_from_to_dates("date_of_joining", "relieving_date")
		self.validate_from_to_dates("date_of_joining", "contract_end_date")

	def validate_email(self):
		if self.company_email:
			validate_email_address(self.company_email, True)
		if self.personal_email:
			validate_email_address(self.personal_email, True)

	def set_preferred_email(self):
		preferred_email_field = frappe.scrub(self.prefered_contact_email)
		if preferred_email_field:
			preferred_email = self.get(preferred_email_field)
			self.prefered_email = preferred_email

	def validate_status(self):
		if self.status == "Left":
			reports_to = frappe.db.get_all(
				"Employee",
				filters={"reports_to": self.name, "status": "Active"},
				fields=["name", "employee_name"],
			)
			if reports_to:
				link_to_employees = [
					frappe.utils.get_link_to_form("Employee", employee.name, label=employee.employee_name)
					for employee in reports_to
				]
				message = _("The following employees are currently still reporting to {0}:").format(
					frappe.bold(self.employee_name)
				)
				message += "<br><br><ul><li>" + "</li><li>".join(link_to_employees)
				message += "</li></ul><br>"
				message += _("Please make sure the employees above report to another Active employee.")
				throw(message, InactiveEmployeeStatusError, _("Cannot Relieve Employee"))
			if not self.relieving_date:
				throw(_("Please enter relieving date."))

	def validate_for_enabled_user_id(self, enabled):
		if not self.status == "Active":
			return

		if enabled is None:
			frappe.throw(_("User {0} does not exist").format(self.user_id))
		if enabled == 0:
			frappe.throw(_("User {0} is disabled").format(self.user_id), EmployeeUserDisabledError)

	def validate_duplicate_user_id(self):
		Employee = frappe.qb.DocType("Employee")
		employee = (
			frappe.qb.from_(Employee)
			.select(Employee.name)
			.where(
				(Employee.user_id == self.user_id)
				& (Employee.status == "Active")
				& (Employee.name != self.name)
			)
		).run()
		if employee:
			throw(
				_("User {0} is already assigned to Employee {1}").format(self.user_id, employee[0][0]),
				frappe.DuplicateEntryError,
			)
	#my code i added to validate formula and condition
	def validate_formula_setup(self):
		for table in ["earnings", "deductions"]:
			for row in self.get(table):
				if not row.amount_based_on_formula and row.formula:
					frappe.msgprint(
						_(
							"{0} Row #{1}: Formula is set but {2} is disabled for the Salary Component {3}."
						).format(
							table.capitalize(),
							row.idx,
							frappe.bold(_("Amount Based on Formula")),
							frappe.bold(row.salary_component),
						),
						title=_("Warning"),
						indicator="orange",
					)

	def sanitize_condition_and_formula_fields(self):
			
		for table in ("earnings", "deductions"):
			for row in self.get(table):
				row.condition = row.condition.strip() if row.condition else ""
				row.formula = row.formula.strip() if row.formula else ""
				row._condition, row.condition = row.condition, sanitize_expression(row.condition)
				row._formula, row.formula = row.formula, sanitize_expression(row.formula)

	def validate_reports_to(self):
		if self.reports_to == self.name:
			throw(_("Employee cannot report to himself."))

	def on_trash(self):
		self.update_nsm_model()
		delete_events(self.doctype, self.name)

	def validate_preferred_email(self):
		if self.prefered_contact_email and not self.get(scrub(self.prefered_contact_email)):
			frappe.msgprint(_("Please enter {0}").format(self.prefered_contact_email))

	def reset_employee_emails_cache(self):
		prev_doc = self.get_doc_before_save() or {}
		cell_number = cstr(self.get("cell_number"))
		prev_number = cstr(prev_doc.get("cell_number"))
		if cell_number != prev_number or self.get("user_id") != prev_doc.get("user_id"):
			frappe.cache().hdel("employees_with_number", cell_number)
			frappe.cache().hdel("employees_with_number", prev_number)

	#my added code for data import tool not to override the existing one
	def merge_salary_details(self):
		if not self.name:
			return

		try:
			existing = frappe.get_doc("Employee", self.name)
		except frappe.DoesNotExistError:
			return  # New employee; nothing to merge

		def merge_table(table_name):
			existing_rows = {row.salary_component: row for row in getattr(existing, table_name)}
			imported_rows = {row.salary_component: row for row in getattr(self, table_name)}

			# Keep existing components that are not in the import
			final_rows = []

			for comp, row in existing_rows.items():
				if comp not in imported_rows:
					final_rows.append(row)

			# Add/overwrite imported rows
			for comp, row in imported_rows.items():
				final_rows.append(row)

			# Clear and re-append
			self.set(table_name, [])
			for row in final_rows:
				#make sure to return to this back their is unfinished logic 
				self.append(table_name, {
					"salary_component": row.salary_component,
					
					"amount": row.amount
				})

		merge_table("earnings")
		merge_table("deductions")
    
	#my code added 
	def get_abbr_for_component(self, component):
		return frappe.db.get_value("Salary Component", component, "abbr") or component[:3].upper()


def validate_employee_role(doc, method=None, ignore_emp_check=False):
	# called via User hook
	if not ignore_emp_check:
		if frappe.db.get_value("Employee", {"user_id": doc.name}):
			return

	user_roles = [d.role for d in doc.get("roles")]
	if "Employee" in user_roles:
		frappe.msgprint(_("User {0}: Removed Employee role as there is no mapped employee.").format(doc.name))
		doc.get("roles").remove(doc.get("roles", {"role": "Employee"})[0])

	if "Employee Self Service" in user_roles:
		frappe.msgprint(
			_("User {0}: Removed Employee Self Service role as there is no mapped employee.").format(doc.name)
		)
		doc.get("roles").remove(doc.get("roles", {"role": "Employee Self Service"})[0])


def update_user_permissions(doc, method):
	# called via User hook
	if "Employee" in [d.role for d in doc.get("roles")]:
		if not has_permission("User Permission", ptype="write", raise_exception=False):
			return
		employee = frappe.get_doc("Employee", {"user_id": doc.name})
		employee.update_user_permissions()


def get_employee_email(employee_doc):
	return (
		employee_doc.get("user_id") or employee_doc.get("personal_email") or employee_doc.get("company_email")
	)


def get_holiday_list_for_employee(employee, raise_exception=True):
	if employee:
		holiday_list, company = frappe.get_cached_value("Employee", employee, ["holiday_list", "company"])
	else:
		holiday_list = ""
		company = frappe.db.get_single_value("Global Defaults", "default_company")

	if not holiday_list:
		holiday_list = frappe.get_cached_value("Company", company, "default_holiday_list")

	if not holiday_list and raise_exception:
		frappe.throw(
			_("Please set a default Holiday List for Employee {0} or Company {1}").format(employee, company)
		)

	return holiday_list


def is_holiday(employee, date=None, raise_exception=True, only_non_weekly=False, with_description=False):
	"""
	Returns True if given Employee has an holiday on the given date
	        :param employee: Employee `name`
	        :param date: Date to check. Will check for today if None
	        :param raise_exception: Raise an exception if no holiday list found, default is True
	        :param only_non_weekly: Check only non-weekly holidays, default is False
	"""

	holiday_list = get_holiday_list_for_employee(employee, raise_exception)
	if not date:
		date = today()

	if not holiday_list:
		return False

	filters = {"parent": holiday_list, "holiday_date": date}
	if only_non_weekly:
		filters["weekly_off"] = False

	holidays = frappe.get_all("Holiday", fields=["description"], filters=filters, pluck="description")

	if with_description:
		return len(holidays) > 0, holidays

	return len(holidays) > 0


@frappe.whitelist()
def deactivate_sales_person(status=None, employee=None):
	if status == "Left":
		sales_person = frappe.db.get_value("Sales Person", {"Employee": employee})
		if sales_person:
			frappe.db.set_value("Sales Person", sales_person, "enabled", 0)


@frappe.whitelist()
def create_user(employee, user=None, email=None):
	emp = frappe.get_doc("Employee", employee)

	employee_name = emp.employee_name.split(" ")
	middle_name = last_name = ""

	if len(employee_name) >= 3:
		last_name = " ".join(employee_name[2:])
		middle_name = employee_name[1]
	elif len(employee_name) == 2:
		last_name = employee_name[1]

	first_name = employee_name[0]

	if email:
		emp.prefered_email = email

	user = frappe.new_doc("User")
	user.update(
		{
			"name": emp.employee_name,
			"email": emp.prefered_email,
			"enabled": 1,
			"first_name": first_name,
			"middle_name": middle_name,
			"last_name": last_name,
			"gender": emp.gender,
			"birth_date": emp.date_of_birth,
			"phone": emp.cell_number,
			"bio": emp.bio,
		}
	)
	user.insert()
	emp.user_id = user.name
	emp.save()
	return user.name


def get_all_employee_emails(company):
	"""Returns list of employee emails either based on user_id or company_email"""
	employee_list = frappe.get_all(
		"Employee", fields=["name", "employee_name"], filters={"status": "Active", "company": company}
	)
	employee_emails = []
	for employee in employee_list:
		if not employee:
			continue
		user, company_email, personal_email = frappe.db.get_value(
			"Employee", employee, ["user_id", "company_email", "personal_email"]
		)
		email = user or company_email or personal_email
		if email:
			employee_emails.append(email)
	return employee_emails


def get_employee_emails(employee_list):
	"""Returns list of employee emails either based on user_id or company_email"""
	employee_emails = []
	for employee in employee_list:
		if not employee:
			continue
		user, company_email, personal_email = frappe.db.get_value(
			"Employee", employee, ["user_id", "company_email", "personal_email"]
		)
		email = user or company_email or personal_email
		if email:
			employee_emails.append(email)
	return employee_emails


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False, is_tree=False):
	filters = [["status", "=", "Active"]]
	if company and company != "All Companies":
		filters.append(["company", "=", company])

	fields = ["name as value", "employee_name as title"]

	if is_root:
		parent = ""
	if parent and company and parent != company:
		filters.append(["reports_to", "=", parent])
	else:
		filters.append(["reports_to", "=", ""])

	employees = frappe.get_list(doctype, fields=fields, filters=filters, order_by="name")

	for employee in employees:
		is_expandable = frappe.get_all(doctype, filters=[["reports_to", "=", employee.get("value")]])
		employee.expandable = 1 if is_expandable else 0

	return employees


def on_doctype_update():
	frappe.db.add_index("Employee", ["lft", "rgt"])


def has_user_permission_for_employee(user_name, employee_name):
	return frappe.db.exists(
		{
			"doctype": "User Permission",
			"user": user_name,
			"allow": "Employee",
			"for_value": employee_name,
		}
	)


def has_upload_permission(doc, ptype="read", user=None):
	if not user:
		user = frappe.session.user
	if get_doc_permissions(doc, user=user, ptype=ptype).get(ptype):
		return True
	return doc.user_id == user
#my Code to filter out the components
@frappe.whitelist()
def get_salary_component(doctype, txt, searchfield, start, page_len, filters):
	sc = frappe.qb.DocType("Salary Component")
	sca = frappe.qb.DocType("Salary Component Account")

	salary_components = (
		frappe.qb.from_(sc)
		.left_join(sca)
		.on(sca.parent == sc.name)
		.select(sc.name, sca.account, sca.company)
		.where(
			(sc.type == filters.get("component_type"))
			& (sc.disabled == 0)
			& (sc[searchfield].like(f"%{txt}%") | sc.name.like(f"%{txt}%"))
		)
		.limit(page_len)
		.offset(start)
	).run(as_dict=True)

	accounts = []
	for component in salary_components:
		if not component.company:
			accounts.append((component.name, component.account, component.company))
		else:
			if component.company == filters["company"]:
				accounts.append((component.name, component.account, component.company))

	return accounts

#my code 
@frappe.whitelist()
def get_default_salary_components():
    fields = [
        "name",
        "salary_component",
        "salary_component_abbr",
        "type",
        "description",
        "depends_on_payment_days",
        "is_tax_applicable",
        "deduct_full_tax_on_selected_payroll_date",
        "variable_based_on_taxable_salary",
        "is_income_tax_component",
        "exempted_from_income_tax",
        "round_to_the_nearest_integer",
        "statistical_component",
        "do_not_include_in_total",
        "remove_if_zero_valued",
        "disabled",
        "loan_component",
        "default_component",
        "condition",
        "amount_based_on_formula",
        "formula",
        "amount",
        "round_to_the_nearest_integer",
        
    ]

    earnings = frappe.get_all(
        "Salary Component",
        filters={"type": "Earning", "default_component": 1, "disabled": 0},
        fields=fields,
    )
    deductions = frappe.get_all(
        "Salary Component",
        filters={"type": "Deduction", "default_component": 1, "disabled": 0},
        fields=fields,
    )
    return {"earnings": earnings, "deductions": deductions}
