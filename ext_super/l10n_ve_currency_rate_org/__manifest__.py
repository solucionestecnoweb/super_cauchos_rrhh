# -*- coding: utf-8 -*-

{
    "name": "Localización Venezolana: Currency",
    "version": "14.0.1",
    "author": "Oasis Consultora  C.A",
    "category": "Localization",
    "description":
    """
    Localización Venezolana: Currency
     """,
    "maintainer": "Oasis Consultora  C.A",
    "website": "https://oasisconsultora.com/",
	'images': ['static/description/icon.png'],
    "depends": ['base', 'product','account', 'purchase', 'sale'],
    "init_xml": [],
    "demo_xml": [],
    "data": [
        'views/res_currency_rate.xml',
        'views/product.xml',
        'views/exchange_rate.xml',
        'views/account_move.xml',
        'views/sale_order.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
    ],
    'qweb': [
        'static/src/xml/systray.xml',
    ],
    "installable": True
}
