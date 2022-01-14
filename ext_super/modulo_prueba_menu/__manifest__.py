{
    'name': 'modulo de prueba',
    'description': 'Modulo de prueba menu',
    'version': '13.0.1.0.0',
    'author': 'Ing. Darrell Sojo',
    'depends': ['account', 'base','fleet','maintenance'],
    'data': [
        'views/menu.xml',
        'views/fleet_vehicle_inherit.xml',
        #'security/ir.model.access.csv',
        ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
