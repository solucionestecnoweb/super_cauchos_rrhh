# -*- coding: utf-8 -*-

{
    "name": "Multi Sucursales",
    "version": "15.0.1",
    "author": "Oasis Consultora  C.A",
    "category": "Sucursales",
    "description":  """ Multi Sucursales """,
    "maintainer": "Oasis Consultora  C.A",
    "website": "https://oasisconsultora.com/",
	'images': ['static/description/icon.png'],
    "depends": [
        'base',
        'product',
        'account', 
        'purchase', 
        'sale',
        'ext_personalizacion_lanta',
        'l10n_ve_fiscal_requirements',
        'l10n_ve_formato_factura_nd_nc',
        'ext_filtros_diarios_fact',
        ],
    "data": [
        'security/ir.model.access.csv',
        'views/sucursal.xml',
        'views/account_move_view.xml',
        'views/account_journal_views.xml',
        'wizards/wizards.xml'
    ],

    "installable": True
}
