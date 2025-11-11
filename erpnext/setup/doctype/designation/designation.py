# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document
import frappe

class Designation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.
	

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		department: DF.Link | None
		description: DF.Text | None
		designation_name: DF.Data
	# end: auto-generated types

	def validate(self):
			self.ensure_unique_designation_in_department()

	def ensure_unique_designation_in_department(self):
		if self.department and self.designation_name:
			existing = frappe.db.exists(
				"Designation",
				{
					"department": self.department,
					"designation_name": self.designation_name,
					"name": ["!=", self.name],  # Exclude self during update
				}
			)
			if existing:
				frappe.throw(
					f"The designation '{self.designation_name}' already exists in the department '{self.department}'."
				)
