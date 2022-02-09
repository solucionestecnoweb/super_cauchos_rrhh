# -*- coding: utf-8 -*-
{
    'name': "Custom Stock",
    'summary': """""",
    'description': """""",
    'author': "INM & LDR Soluciones Tecnológicas y Empresariales C.A",
    'website': "http://www.yourcompany.com",
    'contribuitors': "Bryan Gómez <bryan.gomez1311@gmail.com>",

    'category': 'stock',
    'version': '0.1',
    'depends': ['sale_stock','supercauchos_stock','stock'],
    'data': [
        'views/stock_views.xml',
        'views/dispatch.xml',
        'views/dispatch_report.xml',
        'views/stock_move_views.xml',

    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}


