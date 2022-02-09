# -*- coding: utf-8 -*-
{
    'name': "Mantenimineto y Flota e Inventario",
    'summary': """
        agrego botones y vistas de flota en mantenimiento y registro los
        repuesto que se utilizaron desde el modulo de inventario
    """,

    'description': """
        agrego botones y vistas de flota en mantenimiento y registro los
        repuesto que se utilizaron desde el modulo de inventario
    """,

    'author': "INM & LDR Soluciones Tecnológicas y Empresariales C.A",
    'website': "http://www.yourcompany.com",
    'contribuitors': "Bryan Gómez <bryan.gomez1311@gmail.com>,  Ing Johan Morey",

    'category': 'maintenance stock',
    'version': '0.1',
    'depends': ['fleet', 'maintenance', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'data/maintenace_petition_sequence.xml',
        'data/assignment_fleet_sequence.xml',
        'views/maintenance_views.xml',
        'views/fleet_vehicle_views.xml',
        'views/product_template_views.xml',
        'views/stock_views.xml',
        'views/fleet_vehicle_log_assignment_control_views.xml',
    ],

    'installable': True,
    'application': False,
    'auto_install': False,
}


