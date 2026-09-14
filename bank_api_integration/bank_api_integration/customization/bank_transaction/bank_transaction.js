frappe.ui.form.on("Bank Transaction", {
    onload(frm) {
        frm.set_query("payment_document", "payment_entries", function () {
            return {
                filters: {
                    name: [
                        "in",
                        [
                            "Payment Entry",
                            "Journal Entry",
                            "Sales Invoice",
                            "Purchase Invoice",
                            "Expense Claim",
                            "Payment Order Detail"
                        ],
                    ],
                },
            };
        });
    }
})