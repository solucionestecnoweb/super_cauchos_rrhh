# -*- coding: utf-8 -*-
{
    'name': "Liberar Campos fechas en las solicitudes de compras y ventas",

    'summary': """Liberar Campos fechas en las solicitudes de compras y ventas""",

    'description': """
       Liberar Campos fechas en las solicitudes de compras y ventas
       Colaborador: Ing. Darrell Sojo
    """,
    'version': '1.0',
    'author': 'INM&LDR Soluciones Tecnologicas',
    'category': 'Liberar Campos fechas en las solicitudes de compras y ventas',

    # any module necessary for this one to work correctly
    'depends': ['product','base', 'account','sale','purchase','stock'],

    # always loaded
    'data': [
        'vista/sale_order_inherit.xml',
        #'vista/stock_piking_inherit.xml',
        #'security/ir.model.access.csv',
    ],
    'application': True,
}
