{
    'name': 'Sale Order Approvals',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['sale', 'approvals', 'account_accountant', 'sale_report_supercauchos'],
    'data': [
        'views/approval_sale_fields_extend.xml',
        'views/sale_order_approvals.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
