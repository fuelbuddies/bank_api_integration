# -*- coding: utf-8 -*-
# Copyright (c) 2021, Aerele and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe, json
from frappe import _
from frappe.model.document import Document
from frappe.utils import today
from six import string_types
from erpnext.accounts.doctype.payment_entry.payment_entry import get_negative_outstanding_invoices, get_orders_to_be_billed
from erpnext.controllers.accounts_controller import get_supplier_block_status
from erpnext.accounts.utils import get_outstanding_invoices, get_account_currency
from frappe.utils import add_months, nowdate
from bank_api_integration.bank_api_integration.doctype.bank_api_integration.bank_api_integration import is_authorized
from erpnext.accounts.party import get_party_account
from urllib.parse import urlparse

class OutwardBankPayment(Document):
	def validate(self):
		final_remark=""
	#	symbols=[',','.','/','-']
		for i in self.remarks:
			if (ord(i) >= 65 and ord(i) <= 90) or (ord(i) >= 97 and ord(i) <= 122) or (ord(i) >= 48 and ord(i) <= 57):
				final_remark+=i
		if len(final_remark)>25:
			final_remark = final_remark[0:25]
		self.remarks = final_remark
	def on_update(self):
		is_authorized(self)
	def on_change(self):
		parsed_url = urlparse(frappe.utils.get_url())
		site_name = parsed_url.netloc
		doc = self.get_doc_before_save()
		if "desk.lnder.in" == site_name and self.workflow_state == "Transaction Completed" and not doc.workflow_state == "Transaction Completed":
			if self.payment_references:
				for row in self.payment_references:
					if row.reference_doctype == "Payment Order Detail" and row.reference_name:
						previous_paid_amt = frappe.db.get_value("Payment Order Detail",{"name":row.reference_name},"paid_amount")
						frappe.db.sql("""Update `tabPayment Order Detail` set paid_amount = {0},paid_doc_ref = '{2}' where name = '{1}'
                    					""".format((previous_paid_amt+row.allocated_amount),row.reference_name,self.name))
		if "gta.lnder.in" == site_name and self.workflow_state == "Pending" and self.owner != "Administrator":
			user_list = frappe.db.sql("""Select c.company from `tabCompany Wise User` as c join `tabCompany Wise User Table` as ct on ct.parent = c.name where c.company != '{0}' and ct.user = '{1}' """.format(self.company,self.owner),as_dict = True)
			if user_list:
				credit_limit = frappe.db.get_value("Company",{"name":user_list[0].company},"credit_balance")
				credit_limit -= self.amount
				frappe.db.sql("""Update `tabCompany` set credit_balance = '{0}' where name = '{1}' """.format(credit_limit,user_list[0].company))

		if "gta.lnder.in" == site_name and self.workflow_state == "Pending" and self.party_type == "Supplier":
			if frappe.db.get_value("Supplier",{"name":self.party},"whatsapp_no"):
				self.mobile_no = "91"+frappe.db.get_value("Supplier",{"name":self.party},"whatsapp_no")

		if self.bobp and not self.workflow_state == 'Pending':
			status = 'Processing'
			failed_doc_count = frappe.db.count('Outward Bank Payment', {'bobp': self.bobp, 'workflow_state': ['in',  ['Initiation Failed','Initiation Error', 'Transaction Error', 'Transaction Failed']]})
			completed_doc_count = frappe.db.count('Outward Bank Payment', {'bobp': self.bobp, 'workflow_state': 'Transaction Completed'})
			initiated_doc_count = frappe.db.count('Outward Bank Payment', {'bobp': self.bobp, 'workflow_state': 'Initiated'})
			total_payments = frappe.db.get_value('Bulk Outward Bank Payment', {'name': self.bobp}, 'no_of_payments')
			if initiated_doc_count == total_payments:
				status = 'Initiated'
			if failed_doc_count and not completed_doc_count:
				status = 'Failed'
			if completed_doc_count>=1:
				status = 'Partially Completed'
			if completed_doc_count == total_payments:
				status = 'Completed'
			frappe.db.set_value('Bulk Outward Bank Payment', {'name': self.bobp}, 'workflow_state', status)
			frappe.db.set_value('Outward Bank Payment Details',{'parent':self.bobp,
							'party_type': self.party_type,
							'party': self.party,
							'amount': self.amount,
							'outward_bank_payment': self.name},'status', self.workflow_state)
			frappe.db.commit()
		if self.reconcile_action == 'Auto Reconcile Oldest First Invoice' and self.workflow_state == 'Transaction Completed' and not doc.workflow_state == "Transaction Completed":
			references = []
			amount = self.amount
			month_threshold = -6
			from_date = add_months(nowdate(), month_threshold)
			invoices = frappe.db.get_all('Purchase Invoice',{'supplier': self.party, 'posting_date': ['>=', from_date], 'posting_date': ['<=', nowdate()]}, ['grand_total', 'due_date', 'bill_no', 'name'])
			for inv in invoices:
				if inv['grand_total'] <= amount:
					references.append({
					'reference_doctype': 'Purchase Invoice',
					'reference_name': inv['name'],
					'bill_no': inv['bill_no'],
					'due_date': inv['due_date'],
					'total_amount': inv['grand_total']
					})
					amount-= inv['grand_total']
			self.create_payment_entry(references)
		if self.reconcile_action == 'Manual Reconcile' and self.workflow_state == 'Transaction Completed' and not doc.workflow_state == "Transaction Completed":
			purchase_invoice_references = []
			payment_order_detail_references = []
			for row in self.payment_references:
				if row.reference_doctype == "Purchase Invoice" and row.reference_name:
					purchase_invoice_references.append({
						'reference_doctype': row.reference_doctype,
						'reference_name': row.reference_name,
						'bill_no': row.bill_no,
						'due_date': row.due_date,
						'total_amount': row.total_amount,
						'outstanding_amount': row.outstanding_amount,
						'allocated_amount': row.allocated_amount,
						'exchange_rate': row.exchange_rate
					})
				if row.reference_doctype == "Payment Order Detail" and row.reference_name:
					payment_order_detail_references.append({
						'reference_doctype': row.reference_doctype,
						'reference_name': row.reference_name,
						'total_amount': row.total_amount,
						'outstanding_amount': row.outstanding_amount,
						'allocated_amount': row.allocated_amount,
					})
			if purchase_invoice_references:
				references = purchase_invoice_references
				self.create_payment_entry(references)
			if payment_order_detail_references:
				references = payment_order_detail_references
				self.create_payment_order_detail_journal(references)

		if self.reconcile_action == 'Skip Reconcile' and self.workflow_state == 'Transaction Completed':
			payment_order_detail_references = []
			for row in self.payment_references:
				if row.reference_doctype == "Payment Order Detail" and row.reference_name:
					payment_order_detail_references.append({
						'reference_doctype': row.reference_doctype,
						'reference_name': row.reference_name,
						'total_amount': row.total_amount,
						'outstanding_amount': row.outstanding_amount,
						'allocated_amount': row.allocated_amount,
					})
			if payment_order_detail_references:
				references = payment_order_detail_references
				self.create_payment_order_detail_journal(references)
			else:
				references = []
				self.create_payment_entry(references)

	def create_payment_entry(self, references):
		account_paid_from = frappe.db.get_value("Bank Account", self.company_bank_account, "account")
		account_currency = frappe.db.get_value("Account", account_paid_from, "account_currency")
		payment_entry_dict = {
			"company" : self.company,
			"payment_type" : 'Pay',
			"mode_of_payment": 'Wire Transfer',
			"party_type" :  self.party_type,
			"party" :  self.party,
			"posting_date" : today(),
			"paid_amount": self.amount,
			"received_amount":self.amount,
			"reference_no":self.utr_number,
			"reference_date":today(),
			"source_exchange_rate": 1,
			"target_exchange_rate": 1,
			"paid_from": account_paid_from,
			"paid_from_account_currency": account_currency,
			"references": references,
			"is_deposit":self.is_deposit
		}
		payment_entry = frappe.new_doc("Payment Entry")
		payment_entry.update(payment_entry_dict)

		payment_entry.insert()
		payment_entry.submit()

		frappe.db.set_value(self.doctype, self.name, "payment_entry", payment_entry.name)

	@frappe.whitelist()
	def create_payment_order_detail_journal(self,references):
		account_paid_from = frappe.db.get_value("Bank Account", self.company_bank_account, "account")
		accounts=[]
		for row in references:
			gta_service_allocation_details=frappe.db.get_value("Payment Order Detail",{'name':row.get('reference_name')},['super_customer'],as_dict=True)
			default_party_recevieable_account=get_party_account('Customer',gta_service_allocation_details.get('customer'),self.company) or frappe.db.get_value("Company",self.company,"default_receivable_account")
			accounts.append({
				"account":account_paid_from,
				"credit_in_account_currency":row.get('allocated_amount')
			})
			accounts.append({
				"account": default_party_recevieable_account,
				"party_type": "Customer",
				"party": gta_service_allocation_details.get('super_customer'),
				"debit_in_account_currency": row.get('allocated_amount')
			})
		if accounts:
			je = frappe.new_doc("Journal Entry")
			je.outward_bank_payment = self.name
			je.posting_date = today()
			je.cheque_no = self.utr_number
			je.cheque_date = today()
			je.extend("accounts",accounts)
			je.user_remark = "Payment Order Detail - " + self.name
			je.save(ignore_permissions = True)
			je.submit()
@frappe.whitelist()
def make_bank_payment(source_name, target_doc=None):
	supplier=frappe.db.get_value("Purchase Invoice",{"name":source_name},"supplier")
	if(frappe.db.get_value("Bank Account",{"party":supplier},"is_default")):
		#Assigning party type as supplier
		def set_supplier(source_doc,target_doc,source_parent):
			target_doc.party_type="Supplier"
			target_doc.reconcile_action="Manual Reconcile"
			target_doc.remarks = source_doc.items[0].item_code
			target_doc.append('payment_references',{
				'reference_name': source_doc.name,
				'reference_doctype': 'Purchase Invoice',
				"total_amount": source_doc.rounded_total,
				"outstanding_amount":source_doc.outstanding_amount,
				"allocated_amount":source_doc.outstanding_amount
			})
		from frappe.model.mapper import get_mapped_doc
		doclist = get_mapped_doc("Purchase Invoice", source_name,{
			"Purchase Invoice": {
				"postprocess": set_supplier,
				"doctype": "Outward Bank Payment",
				"field_map": {
					"supplier": "party",
					#"name" : "remarks",
					"outstanding_amount" : "amount"
				}
				}

			}, target_doc)
		return doclist
	else:
		frappe.throw(_(f'{supplier} ' "have no bank account"))

@frappe.whitelist()
def bank_payment_for_purchase_order(source_name, target_doc=None):
	supplier=frappe.db.get_value("Purchase Order",{"name":source_name},"supplier")
	if(frappe.db.get_value("Bank Account",{"party":supplier},"is_default")):
		#Assigning party type as supplier
		def set_supplier(source_doc,target_doc,source_parent):
			target_doc.party_type="Supplier"
			target_doc.reconcile_action="Manual Reconcile"
			target_doc.append('payment_references',{
				'reference_name': source_doc.name,

				'reference_doctype': 'Purchase Order',
				"total_amount": source_doc.rounded_total,
				"allocated_amount":source_doc.rounded_total
			})

		from frappe.model.mapper import get_mapped_doc
		doclist = get_mapped_doc("Purchase Order", source_name,{
			"Purchase Order": {
				"postprocess": set_supplier,
				"doctype": "Outward Bank Payment",
				"field_map": {
					"supplier": "party",
					"name" : "remarks",
					"grand_total" : "amount"
				}
				}

			}, target_doc)
		return doclist
	else:
		frappe.throw(_(f'{supplier} ' "have no bank account"))

@frappe.whitelist()
def get_outstanding_reference_documents(args):

	if isinstance(args, string_types):
		args = json.loads(args)

	if args.get('party_type') == 'Member':
		return

	args['party_account'] =  frappe.db.get_value('Account', {'account_type': 'Payable','is_group': 0, 'company': args.get('company')})

	# confirm that Supplier is not blocked
	if args.get('party_type') == 'Supplier':
		supplier_status = get_supplier_block_status(args['party'])
		if supplier_status['on_hold']:
			if supplier_status['hold_type'] == 'All':
				return []
			elif supplier_status['hold_type'] == 'Payments':
				if not supplier_status['release_date'] or getdate(nowdate()) <= supplier_status['release_date']:
					return []

	party_account_currency = get_account_currency(args.get("party_account"))
	company_currency = frappe.get_cached_value('Company',  args.get("company"),  "default_currency")

	# Get negative outstanding sales /purchase invoices
	negative_outstanding_invoices = []
	if args.get("party_type") not in ["Student", "Employee"] and not args.get("voucher_no"):
		negative_outstanding_invoices = get_negative_outstanding_invoices(args.get("party_type"), args.get("party"),
			args.get("party_account"), args.get("company"), party_account_currency, company_currency)

	# Get positive outstanding sales /purchase invoices/ Fees
	condition = ""
	if args.get("voucher_type") and args.get("voucher_no"):
		condition = " and voucher_type={0} and voucher_no={1}"\
			.format(frappe.db.escape(args["voucher_type"]), frappe.db.escape(args["voucher_no"]))

	# Add cost center condition
	if args.get("cost_center"):
		condition += " and cost_center='%s'" % args.get("cost_center")

	date_fields_dict = {
		'posting_date': ['from_posting_date', 'to_posting_date'],
		'due_date': ['from_due_date', 'to_due_date']
	}

	for fieldname, date_fields in date_fields_dict.items():
		if args.get(date_fields[0]) and args.get(date_fields[1]):
			condition += " and {0} between '{1}' and '{2}'".format(fieldname,
				args.get(date_fields[0]), args.get(date_fields[1]))

	if args.get("company"):
		condition += " and company = {0}".format(frappe.db.escape(args.get("company")))

	outstanding_invoices = get_outstanding_invoices(args.get("party_type"), args.get("party"),
		args.get("party_account"), filters=args, condition=condition)

	for d in outstanding_invoices:
		d["exchange_rate"] = 1
		if party_account_currency != company_currency:
			if d.voucher_type in ("Sales Invoice", "Purchase Invoice", "Expense Claim"):
				d["exchange_rate"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "conversion_rate")
			elif d.voucher_type == "Journal Entry":
				d["exchange_rate"] = get_exchange_rate(
					party_account_currency,	company_currency, d.posting_date
				)
		if d.voucher_type in ("Purchase Invoice"):
			d["bill_no"] = frappe.db.get_value(d.voucher_type, d.voucher_no, "bill_no")

	# Get all SO / PO which are not fully billed or aginst which full advance not paid
	orders_to_be_billed = []
	if (args.get("party_type") != "Student"):
		orders_to_be_billed =  get_orders_to_be_billed(args.get("posting_date"),args.get("party_type"),
			args.get("party"), args.get("company"), party_account_currency, company_currency, filters=args)

	data = negative_outstanding_invoices + outstanding_invoices + orders_to_be_billed
	if not data:
		frappe.msgprint(_("No outstanding invoices found for the {0} {1} which qualify the filters you have specified.")
			.format(args.get("party_type").lower(), frappe.bold(args.get("party"))))

	return data
