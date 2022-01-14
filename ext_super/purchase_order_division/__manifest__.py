{
    'name': 'Purchase Order Division',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['purchase', 'sale_report_supercauchos'],
    'data': [
        'views/purchase_order_division.xml',
        'views/sale_order_purchase_division.xml',
        'views/purchase_order_attributes.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}