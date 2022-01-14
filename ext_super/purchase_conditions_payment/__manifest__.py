{
    "name": "Purchase Conditions Payment",
    "version": "13.0.1.0.1",
    "author": "Oasis Consultora",
    "website": "https://gregoriocode.com",
    "license": "AGPL-3",
    "depends": ['base', 'purchase', 'contacts', 'purchase_report_supercauchos', 'sale_logic_extend', 'account_accountant'],
    "data": [
        "security/ir.model.access.csv",
        "data/purchase_pay_orders_data.xml",
        "views/purchase_extra_fields.xml",
        "views/purchase_pay_order_fields.xml",
    ],
    'installable': True,
}
