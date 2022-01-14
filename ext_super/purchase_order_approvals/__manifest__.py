{
    'name': 'Purchase Order Approvals',
    'version': '13.0.1.0.0',
    'author': 'OasisConsultora',
    'maintainer': 'OasisConsultora',
    'website': 'oasisconsultora.com',
    'license': 'AGPL-3',
    'depends': ['purchase', 'approvals', 'purchase_report_supercauchos'],
    'data': [
        'views/approval_purchase_fields_extend.xml',
        'views/purchase_order_approvals.xml',
        ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
