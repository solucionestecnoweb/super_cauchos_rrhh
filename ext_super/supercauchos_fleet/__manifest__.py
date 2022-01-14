# Copyright 2020 GregorioCode <Info@gregoriocode.com>


{
    "name": "Super Cauchos Chakao Flota",
    "version": "13.0.1.0.1",
    "category": "app",
    "author": "Ing Gregorio Blanco",
    "website": "https://gregoriocode.com",
    "license": "AGPL-3",
    "depends": ['base', 'fleet', 'maintenance'],
    "data": [
        "security/ir.model.access.csv",
        #VEHICULOS
        "views/flota_vehiculos.xml",
        #Contro Disponibilidad
        "views/wizard_flota_control_disponibilidad.xml",
        "report/flota_control_disponibilidad.xml",
        #Registro Consumo de Combustible
        "views/flota_registro_combustible.xml",
        #Asignaciones de Vehiculos
        "data/assignment_fleet_data.xml",
        "views/flota_control_asignaciones_vehiculo.xml",
        #Reporte de Control de Disponibilidad Viajes
        "report/flota_control_disponibilidad.xml",
        "views/wizard_flota_control_disponibilidad.xml",
        #Reporte de Control de Disponibilidad Mantenimiento
        "report/flota_control_disponibilidad_mantenimiento.xml",
        "views/wizard_flota_control_disponibilidad_mantenimiento.xml",
        #Reporte de Control de Servicio de Conductores
        "report/flota_control_servicio.xml",
        "views/wizard_flota_control_servicio.xml",
        #Reporte de Control de Servicio de Vehiculos
        "report/flota_control_servicio_vehiculo.xml",
        "views/wizard_flota_control_servicio_vehiculo.xml",
    ],
    'installable': True,
}
