frappe.listview_settings['Outward Bank Payment'] = {
	// triggers once before the list is loaded
	onload(listview){
		listview.page.add_inner_button(__('Fetch Balance'), function() {
                        frappe.call({
				method:"ogive_api.api.account_balance",
				args:{

				},
				async:false,
                                callback: function(r) {

				}
			});
                });
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				'doctype': 'User',
				'filters': {'name': frappe.session.user},
				'fieldname': [
						'role_profile_name'
						]
			},
			async:false,
			callback: function(r) {
				//console.log(r.message["role_profile_name"])
				if(frappe.session.user == "Administrator" || r.message["role_profile_name"] == "OBP"){
					listview.page.add_action_item(__('Process Payment'), function() {
                                                let d = new frappe.ui.Dialog({
                                                title: '',
                                                fields: [
                                                        {
                                                                label: 'Transaction Password',
                                                                fieldname: 'transaction_password',
                                                                fieldtype: 'Password',
                                                                reqd:1
                                                        }
                                                ],
                                                primary_action_label: 'Submit',
                                                primary_action(values) {
                                                //      console.log(typeof(values.transaction_password));
                                                        d.hide();
                                                //      let doc = frappe.model.get_doc('Outward Bank Payment', listview.$checks[0].dataset.name)
                                                        var checked_value = []
                                                //      console.log(listview);
                                                        var l = listview.$checks.length;
                                                        for(let row = 0; row<l; row++){
                                                                checked_value.push(listview.$checks[row].dataset.name)
                                                        }
                                                                                        frappe.call({
                                                                                                method: 'ogive_api.api.process_payment',
                                                                                                args: {
                                                                                                        "obp_list" : checked_value,
                                                                                                        "password" : values.transaction_password
                                        //                                                              "otp": null
                                                                                                },
                                                                                                async:false,
                                                                                                //freeze:true,
                                                                                                //freeze_message: __("Initiating Payment ..."),
                                                                                                callback: function(r) {
                                                                                                        cur_list.refresh()
                                                                                                        //frappe.show_progress(__('Processing'),row,l, 'Please wait');
                                                                                                        //frm.reload_doc();
                                                                                                }
                                                                                        });
                                                }
                                        });
                                        d.show();
                                        }).addClass("btn-primary");
					listview.page.add_action_item(__('Process Payment With Bulk Payout'), function() {
						let d = new frappe.ui.Dialog({
						title: '',
						fields: [
								{
									label: 'Transaction Password',
									fieldname: 'transaction_password',
									fieldtype: 'Password',
									reqd:1
								}
							],
						primary_action_label: 'Submit',
						primary_action(values) {
						d.hide();
						var checked_value = []
						var l = listview.$checks.length;
						for(let row = 0; row<l; row++){
							checked_value.push(listview.$checks[row].dataset.name)
						}
															frappe.call({
																	method: 'ogive_api.api.process_payment_with_bulk_payout',
																	args: {
																			"obp_list" : checked_value,
																			"password" : values.transaction_password
																	},
																	async:false,
																	callback: function(r) {
																			cur_list.refresh()
																	}
															});
						}
					});
					d.show();
					}).addClass("btn-primary");
					listview.page.add_action_item(__('Verify and Initiate Payment'), function() {
						let d = new frappe.ui.Dialog({
						title: '',
						fields: [
							{
								label: 'Transaction Password',
								fieldname: 'transaction_password',
								fieldtype: 'Password',
								reqd:1
							}
						],
						primary_action_label: 'Submit',
						primary_action(values) {
						//	console.log(typeof(values.transaction_password));
							d.hide();
						//	let doc = frappe.model.get_doc('Outward Bank Payment', listview.$checks[0].dataset.name)
							var checked_value = []
						//	console.log(listview);
							var l = listview.$checks.length;
							for(let row = 0; row<l; row++){
								checked_value.push(listview.$checks[row].dataset.name)
							}
					//		for(var row=0;row<l;row++){
					//			frappe.call({
					//				method: "frappe.client.get",
					//				args: {
					//				doctype: "Outward Bank Payment",
					//				name: listview.$checks[row].dataset.name,
					//				},
					//				async:false,
					//				callback: function(r) {
					//					if(r.message) {
					//						var doc = r.message;
											//console.log(listview.$checks);
											frappe.call({
												method: 'ogive_api.api.obp',
												args: {
													"obp_list" : checked_value,
													"password" : values.transaction_password
					//								"otp": null
												},
												async:false,
												//freeze:true,
												//freeze_message: __("Initiating Payment ..."),
												callback: function(r) {
													cur_list.refresh()
													//frappe.show_progress(__('Processing'),row,l, 'Please wait');
													//frm.reload_doc();
                	        	        		        			}
					        		                        });
						}
					});
					d.show();
					}).addClass("btn-primary");
					listview.page.add_action_item(__('Update Transaction Status'), function() {
						var checked_value = []
						var l = listview.$checks.length;
						for(var row=0;row<l;row++){
							frappe.call({
								method: 'bank_api_integration.bank_api_integration.doctype.bank_api_integration.bank_api_integration.update_transaction_status',
								args: {
									obp_name:listview.$checks[row].dataset.name
								},
								async:false,
							//	freeze:true,
							//	freeze_message: __("Processing..."),
								callback: function(r) {
									//frm.reload_doc();
								}
							});
						}
					});
					listview.page.add_inner_button(__('Total Amount'), function() {
						var checked_value = []
                                                //      console.log(listview);
                                                var l = listview.$checks.length;
                                                for(let row = 0; row<l; row++){
                                                	checked_value.push(listview.$checks[row].dataset.name)
                                                }
                        			frappe.call({
                                			method:"ogive_api.api.total_amount",
                                			args:{
                                        			obp_list:checked_value
                                			},
                                			async:false,
                               				 callback: function(r) {

                                			}
                        			});
                			});
					listview.page.add_inner_button(__('On Process'), function() {
                                                frappe.call({
                                                        method:"ogive_api.api.on_process",
                                                        args:{

                                                        },
                                                        async:false,
                                                         callback: function(r) {

                                                        }
                                                });
                                        });
				}

			}
		});
	}
}
