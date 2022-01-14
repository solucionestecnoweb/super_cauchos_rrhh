{
    'name': 'Requisitions Request',
    'version': '13.0.1.0.1',
    'category': 'purchase',
    'author': 'Oasis Consultora C.A.',
    'license': 'AGPL-3',
    'depends': ['base', 'purchase', 'stock', 'approvals'],
    'data': [
        'security/ir.model.access.csv',
        'data/requisition_sequence.xml',
        'views/approval_requisition_fields_extend.xml',
        'views/purchase_requisitions_request.xml',
        'views/requisitions_related_fields.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
