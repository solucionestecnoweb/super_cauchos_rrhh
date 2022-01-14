{
    'name': 'Product Prices List Multi Currency',
    'version': '13.0.1.0.1',
    'category': 'sales',
    'author': 'Oasis Consultora C.A.',
    'license': 'AGPL-3',
    'depends': ['base', 'sale', 'supercauchos_stock'],
    'data': [
        'views/prices_list.xml',
        'views/product_category.xml',
        'views/product_brand.xml',
        'views/wizard_price_list.xml',
        'views/wizard_price_list_accounting.xml',
        'report/prices_list_report.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
