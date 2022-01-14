# -*- coding: utf-8 -*-

{
        'name': 'Cambio propiedad de campos en vat retention, municipality tax e ISLR par multi compañia',
        'version': '0.1',
        'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A',
        'summary': 'Cambio propiedad de campos en vat retention, municipality tax e ISLR par multi compañia',
        'description': """Este Modulo cambia las caracteristicas de los campos de las cuentas contables y diarios 
        para las retenciones iva, impuesto municipal e ISLR""",
        'category': 'Accounting/Accounting',
        'website': '',
        'images': [],
        'depends': [
            'account',
            'account_accountant',
            'base',
            'vat_retention',
            'municipality_tax',
            'isrl_retention',
            'l10n_ve_fiscal_requirements',
            ],
        'data': [
            ],
        'installable': True,
        'application': True,
        'auto_install': False,
                      
}
