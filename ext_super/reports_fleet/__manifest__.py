# Copyright 2020 GregorioCode <Info@gregoriocode.com>

{
    "name": "Report Fleet",
    "version": "13.0.1.0.1",
    "category": "reporting",
    'summary':
        """
            Genracion de reportes de flota personalizados
        """,
    "author": "INM & LDR Soluciones Tecnológicas y Empresariales C.A",
    "website": "http://www.yourcompany.com",
    'contribuitors': "Bryan Gómez <bryan.gomez1311@gmail.com>",
    "license": "AGPL-3",
    "depends": ['maintenance_stock'],
    "data": [
        "security/ir.model.access.csv",
        "views/wizard_flota_control_disponibilidad.xml",
        "views/wizard_flota_control_disponibilidad_mantenimiento.xml",
        "views/wizard_flota_control_servicio.xml",
        "views/wizard_flota_control_servicio_vehiculo.xml",
        "report/flota_control_disponibilidad.xml",
        "report/flota_control_disponibilidad.xml",
        "report/flota_control_disponibilidad_mantenimiento.xml",
        "report/flota_control_servicio.xml",
        "report/flota_control_servicio_vehiculo.xml",
        "report/paperformat.xml",
        "report/ir_actions_reports.xml",
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}

