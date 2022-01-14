# -*- coding: utf-8 -*-
{
    'name': "2da Adaptacion contable de moneda local Bs a Dolares modulo contabilidad",

    'summary': """2da Adaptacion contable de moneda local Bs a Dolares modulo contabilidad""",

    'description': """
       2da Adaptacion contable de moneda local Bs a Dolares modulo contabilidad
       Colaborador: Ing. Darrell Sojo
    """,
    'version': '1.0',
    'author': 'INM&LDR Soluciones Tecnologicas',
    'category': '2da Adaptacion contable de moneda local Bs a Dolares modulo contabilidad',

    # any module necessary for this one to work correctly
    'depends': ['product',
    'base', 
    'account',
    'account_reports',
    #'l10n_ve_res_currency',
    #'libro_ventas',
    #'libro_compras',
    #'libros_filtros',
    #'vat_retention',
    #'municipality_tax',
    #'isrl_retention',
    #'l10n_ve_txt_iva',
    ],

    # always loaded
    'data': [
        'vista/res_company_inherit.xml',
        'vista/account_move_inherit.xml',
    ],
    'application': True,
}
