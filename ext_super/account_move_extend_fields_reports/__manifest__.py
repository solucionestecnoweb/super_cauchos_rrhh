# Copyright 2020 GregorioCode <Info@gregoriocode.com>


{
    "name": "Account Move Extend",
    "version": "13.0.1.0.1",
    "author": "Ing Gregorio Blanco",
    "website": "https://gregoriocode.com",
    "license": "AGPL-3",
    "depends": ['base', 'account_accountant', 'l10n_ve', 'sale_logic_extend'],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_form_extend.xml",
        "views/account_payment_form_extend.xml",
        "views/company_paper_format.xml",
        "views/account_move_condition_payment.xml",
        "report/paper_format.xml",
        "report/bs_invoices.xml",
        "report/usd_invoices.xml",
        "report/account_payment_extend.xml",
        "report/purchase_order_invoice.xml",
        "views/invoice_html.xml"
    ],
    'installable': True,
}
