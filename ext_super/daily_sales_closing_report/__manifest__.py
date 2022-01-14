{
    'name': 'Daily Sales Closing Report',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['base', 'account', 'l10n_ve_currency_rate'],
    'data': [
        'security/ir.model.access.csv',
        'views/wizard_daily_sales_closing_report.xml',
        'views/daily_sales_closing_report_views.xml',
        'report/daily_sales_closing_report.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}