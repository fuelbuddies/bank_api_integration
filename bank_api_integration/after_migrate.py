from bank_api_integration.bank_api_integration.customization.bank_transaction.custom_field import bt_field_customization

def after_migrate():
	bt_field_customization()