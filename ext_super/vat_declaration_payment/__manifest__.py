{
    'name': 'VAT Declaration & Payment',
    'description': 'summary for tax declaration and payment',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['account'],
    'data': [
        'views/wizard_vat_declaration.xml',
        'report/vat_declaration_payment_report.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
