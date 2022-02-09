# -*- coding: utf-8 -*-
{
    'name': "Approvals Payment",
    'summary': """""",
    'description': """""",
    'author': "INM & LDR Soluciones Tecnológicas y Empresariales C.A",
    'website': "http://www.yourcompany.com",
    'contribuitors': "Bryan Gómez <bryan.gomez1311@gmail.com>",
    'category': 'Extras Tools',
    'version': '0.1',
    'depends': ['custom_approvals', 'account', 'payment', 'l10n_ve_check_printing'],
    'data': [
        'views/approval_category_views.xml',
        'views/approval_request_views.xml',
        'views/account_payment_views.xml',
        ],
    'installable': True,
    'application': False,
    'auto_install': False,
}


