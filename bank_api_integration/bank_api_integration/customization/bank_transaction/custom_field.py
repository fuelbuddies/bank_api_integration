from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def bt_field_customization():
	bt_property_setter()

def bt_property_setter():
	make_property_setter(
		"Bank Transaction",
		"status",
		"options",
		"\nPending\nSettled\nUnreconciled\nReconciled\nDuplicate Entry\nCash Entry Unreconciled\nCash Entry Reconciled",
		"Small Text",
		validate_fields_for_doctype=False,
	),
	make_property_setter(
		"Bank Transaction",
		"transaction_id",
		"unique",
		0,
		"Check",
		validate_fields_for_doctype=False,
	)
	make_property_setter(
		"Bank Transaction",
		"transaction_id",
		"read_only",
		1,
		"Check",
		validate_fields_for_doctype=False,
	)