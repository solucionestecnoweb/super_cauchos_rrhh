{
    'name': "Localizacion Venezolana Modulo de Anticipo proveedores y clientes",

    'summary': """Modulo de Anticipo proveedores y clientes""",

    'description': """
       Ejecuta tambien los anticipos de pagos de proveedores y clientes

    """,
    'version': '2.0',
    'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A',
    'category': 'Tools',
    'website': 'http://soluciones-tecno.com/',

    # any module necessary for this one to work correctly
    'depends': ['base','account'],

    # always loaded
    'data': [
    'security/ir.model.access.csv',
    'vista/res_partner_view.xml',
    'vista/account_payment_view.xml',
    'vista/account_move_view.xml',
    ],
    'application': True,
}
