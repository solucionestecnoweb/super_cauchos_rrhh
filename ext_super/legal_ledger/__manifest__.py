{
    'name': 'Libro Mayor Legal',
    'description': 'Issuance of the Legal Ledger',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['account', 'administration_module'],
    'data': [
        'views/wizard_legal_ledger.xml',
        'reports/legal_ledger_report.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
