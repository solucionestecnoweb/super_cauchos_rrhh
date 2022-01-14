{
    'name': 'Libro Mayor de Análisis',
    'description': 'Emisión del libro mayor de análisis',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['account', 'administration_module'],
    'data': [
        'views/wizard_analysis_ledger.xml',
        'reports/analysis_ledger_report.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
