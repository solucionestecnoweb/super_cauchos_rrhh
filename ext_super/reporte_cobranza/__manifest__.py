{
    'name': 'Reporte de Cierre de Cobranza',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['base', 'account', 'l10n_ve_currency_rate', 'commission_management_super'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_closing_report.xml',
        'views/closing_report_views.xml',
        'report/closing_report.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}