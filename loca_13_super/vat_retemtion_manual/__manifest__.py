# -*- coding: utf-8 -*-

{
        'name': 'VAT Retention Manual for Venezuela',
        'version': '0.1',
        'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A',
        'summary': 'VAT Retention Manual',
        'description': """This model do the retention about taxes in Venezuela.""",
        'category': 'Accounting/Accounting',
        'website': '',
        'images': [],
        'depends': [
            'account',
            'account_accountant',
            'base',
            'l10n_ve_currency_rate',
            'vat_retention',
            'ext_draft_voucher',
            'administration_module',
            ],
        'data': [
            'views/retention_vat_views.xml',
            #'views/menu_vat_retention.xml',
            ],
        'installable': True,
        'application': True,
        'auto_install': False,
                      
}
