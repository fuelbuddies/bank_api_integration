import frappe
from frappe.model.naming import parse_naming_series
import time
from urllib.parse import urlparse

def name_outward_bank_payment(doc, action):
	parsed_url = urlparse(frappe.utils.get_url())
	site_name = parsed_url.netloc
	ym = time.strftime("%y%m")
	if "gta.lnder.in" == site_name:
		doc.name = parse_naming_series(f"OBP{ym}.#####")
	else:
		doc.name = parse_naming_series(f"DDBP{ym}.#####")
