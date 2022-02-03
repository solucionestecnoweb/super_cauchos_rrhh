# -*- coding: utf-8 -*-
{
    'name': "Correccion al conciliar pagos entre facturas y/o pagos pendientes",

    'summary': """CCorreccion al conciliar pagos entre facturas y/o pagos pendientes""",

    'description': """
       Correccion de Error al dar el siguiente mensaje: 
       No puede hacer esta modificación en una entrada de diario conciliada. 
       Puede cambiar algunos campos no legales o primero debe romper conciliación.
       Colaborador: Ing. Darrell Sojo
    """,
    'version': '1.0',
    'author': 'INM&LDR Soluciones Tecnologicas',
    'category': 'Correccion al conciliar pagos entre facturas y/o pagos pendientes',

    # any module necessary for this one to work correctly
    'depends': ['account'],

    # always loaded
    'data': [
        #'acccount_move_line_inherit.xml',
        #'view_add.xml',
        #'security/ir.model.access.csv',
    ],
    'application': True,
}
