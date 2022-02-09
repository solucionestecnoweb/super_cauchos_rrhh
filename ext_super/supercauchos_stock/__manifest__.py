# Copyright 2020 GregorioCode <Info@gregoriocode.com>


{
    "name": "Super Cauchos Chakao Inventario",
    "version": "13.0.1.0.1",
    "category": "app",
    "author": "Ing Gregorio Blanco",
    "website": "https://gregoriocode.com",
    "license": "AGPL-3",
    "depends": ['base', 'stock', 'fleet', 'web', 'sale', 'purchase', 'account'],
    "data": [
       # "static/src/js/subst.xml",
        "security/ir.model.access.csv",
        "views/inventory_products.xml",
        "views/brands_views.xml",
        "views/account_move.xml",
        "views/sale_order.xml",
        "views/purchase_order.xml",
        "report/inventario_toma_fisica.xml",
        "report/inventario_picking_salidas.xml",
        "views/wizard_inventory_picking_salida.xml",
        "views/wizard_inventory_toma_fisica.xml",
    ],
    'installable': True,
}
