# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt


from frappe.model.document import Document


class Branch(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		branch_name: DF.Data | None
		branch_region: DF.Literal["", "Addis Ababa", "Oromia Region", "Amhara Region", "Tigray Region", "Sidama Region", "Dire Dawa", "Central Ethiopia Regional State"]
	# end: auto-generated types

	pass
