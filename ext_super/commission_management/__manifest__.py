{
    'name': 'Commission Management',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['contacts', 'account_payment_plan_reports'],
    'data': [
        'security/ir.model.access.csv',
        'views/agents_views.xml',
        'views/commission_type_views.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
