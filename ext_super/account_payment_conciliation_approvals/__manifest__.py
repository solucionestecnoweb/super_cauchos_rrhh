{
    'name': 'Conciliation Approvals',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['account', 'approvals','l10n_ve_igtf'],
    'data': [
        'views/approval_fields_extend.xml',
        'views/account_payment_approvals.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
